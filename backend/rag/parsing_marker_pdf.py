import json
import re
from pathlib import Path
from typing import Callable, List, Optional
from .chunking_utils import count_tokens
from abc import ABC, abstractmethod
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    print("IMPORT MARKER OK")
except Exception as e:
    print("IMPORT MARKER ERROR:", e)
    raise


class BaseParser(ABC):
    """Abstract base class for document parsers.

    All parsers must produce JSON output with this structure:
    {
        "document_name": str,
        "pages": {page_num: "markdown content"},
        "full_text": str,
        "split_points": [int],
        "titles": [{"title": str, "start": int, "end": int, "level": int}]
    }
    """

    @abstractmethod
    def parse_docs_in_dir(
        self,
        input_dir: Path | str,
        output_dir: Path | str,
        overwrite_outputs: bool = False,
    ) -> list[dict]:
        """Parse raw documents and save intermediate results."""

    @abstractmethod
    def convert_raw_results_to_markdown(
        self,
        raw_input_dir: Path | str,
        output_dir: Path | str,
    ) -> list[dict]:
        """Convert parsed results to standard JSON format."""


class MarkerParser(BaseParser):
    """
    Local PDF parser using marker-pdf library (latest class-based API).
    Ideal for scientific papers and documents with complex layouts or math.
    """

    def __init__(self,
                 count_tokens_func: Callable[[str], int] = count_tokens,
                 max_tokens_per_block: int = 1000,
                 device: Optional[str] = None):
        
        if PdfConverter is None:
            raise ImportError(
                "marker-pdf is required for MarkerParser. "
                "Install with: pip install marker-pdf"
            )
        
        self.count_tokens_func = count_tokens_func
        self.max_tokens_per_block = max_tokens_per_block
        self.device = device
        self._converter = None

    def _get_converter(self):
        """Lazy initialization of the PdfConverter to avoid heavy model loading until needed."""
        if self._converter is None:
            print(f"Initializing Marker PdfConverter on {self.device or 'auto-detected device'}...")
            # create_model_dict loads the required ML models
            model_dict = create_model_dict(device=self.device)
            self._converter = PdfConverter(artifact_dict=model_dict)
        return self._converter

    def parse_docs_in_dir(
        self,
        input_dir: Path | str,
        output_dir: Path | str,
        overwrite_outputs: bool = False,
    ) -> list[dict]:
        input_dir, output_dir = Path(input_dir), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Parsing docs with Marker from {input_dir}...")

        converter = self._get_converter()
        
        # Track existing files to skip if overwrite_outputs is False
        current_output_files = {p.name for p in output_dir.rglob("*.json")}

        for doc_path in sorted(input_dir.rglob("*.pdf")):
            if not doc_path.is_file():
                continue
            
            doc_name = doc_path.with_suffix("").name
            save_name = f"marker_output_{doc_name}.json"

            if not overwrite_outputs and save_name in current_output_files:
                print(f"Skipping {doc_name} parsing, overwrite_outputs is False")
                continue

            print(f"Parsing {doc_name}...")
            try:
                # Convert PDF using the new PdfConverter API
                rendered = converter(str(doc_path))
                
                # Extract markdown text and metadata
                full_text, _, metadata = text_from_rendered(rendered)
                
                # Save raw result to JSON
                save_path = output_dir / save_name
                raw_data = {
                    "full_text": full_text,
                    "metadata": metadata,
                }

                with open(save_path, "w", encoding="utf-8") as fp:
                    json.dump(raw_data, fp, ensure_ascii=False, indent=2)
                
            except Exception as e:
                print(f"Failed to parse {doc_name}: {e}")
                continue

        print(f"\nRaw Marker outputs saved to {output_dir}")

    def convert_raw_results_to_markdown(
        self,
        raw_input_dir: Path | str,
        output_dir: Path | str,
    ) -> list[dict]:
        raw_input_dir, output_dir = Path(raw_input_dir), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Reading Marker outputs from {raw_input_dir}...")

        extracted_texts: list[dict] = []

        for json_path in sorted(raw_input_dir.rglob("marker_output_*.json")):
            if not json_path.is_file():
                continue

            doc_name = json_path.with_suffix("").name.replace("marker_output_", "")
            print(f"Converting {doc_name}")

            with open(json_path, encoding="utf-8") as fp:
                raw_data = json.load(fp)

            raw_text = raw_data["full_text"]
            
            # Marker typically separates pages with \n\n---\n\n
            page_splits = re.split(r'\n\n---\n\n', raw_text)
            
            pages_content: dict[int, str] = {}
            split_points: list[int] = []
            titles: list[dict] = []
            current_offset = 0

            for i, page_md in enumerate(page_splits):
                page_num = i + 1
                
                if not page_md.strip():
                    pages_content[page_num] = ""
                    continue

                # Detect headings for metadata
                lines = page_md.split("\n")
                processed_page_md = ""
                
                for line in lines:
                    heading_match = re.match(r"^(#{1,6})\s+(.+)", line)
                    if heading_match:
                        level = len(heading_match.group(1))
                        title_text = line.strip()
                        titles.append({
                            "title": title_text,
                            "start": current_offset + len(processed_page_md),
                            "level": level,
                        })
                    processed_page_md += line + "\n"

                # Add page break marker (matching project convention)
                if i < len(page_splits) - 1:
                    processed_page_md += "<!-- PageBreak -->\n\n"

                pages_content[page_num] = processed_page_md
                
                # Add split point at the end of each page
                current_offset += len(processed_page_md)
                split_points.append(current_offset)

            # Remove last split point (end of document)
            if split_points:
                split_points.pop()

            # Build final full_text
            full_text = "".join(pages_content[k] for k in sorted(pages_content))

            # Compute end offsets for titles
            for idx, t in enumerate(titles):
                lvl = t["level"]
                end_pos = len(full_text)
                for next_t in titles[idx+1:]:
                    if next_t["level"] <= lvl:
                        end_pos = next_t["start"]
                        break
                t["end"] = end_pos

            out_data = {
                "document_name": doc_name,
                "pages": pages_content,
                "full_text": full_text,
                "split_points": split_points,
                "titles": titles,
            }
            extracted_texts.append(out_data)

            # Save the standardized JSON output
            save_path = output_dir / f"{doc_name}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2)

        print(f"\nStandardized outputs saved to {output_dir}")
        return extracted_texts
