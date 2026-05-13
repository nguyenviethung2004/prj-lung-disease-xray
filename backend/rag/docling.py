import json
from pathlib import Path
from typing import Callable, List, Dict, Optional, Union
from abc import ABC, abstractmethod

try:
    from docling_core.types.doc import DoclingDocument as DLDocument
    from docling_core.types.doc import TextItem, TableItem
except ImportError:
    DLDocument = None
    TextItem = None
    TableItem = None

from .chunking_utils import count_tokens


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


class DoclingParser(BaseParser):
    """Local open-source PDF parser using IBM Docling."""

    def __init__(self,
                 count_tokens_func: Callable[[str], int] = count_tokens,
                 max_tokens_per_block: int = 1000,
                 device: str = "cpu"):
        if DLDocument is None:
             raise ImportError(
                "docling-core is required for DoclingParser. "
                "Install with: pip install docling-core"
            )
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
            from docling.datamodel.base_models import InputFormat
        except ImportError:
            raise ImportError(
                "docling is required for DoclingParser. "
                "Install with: pip install docling"
            )
            
        # 1. Cấu hình phần cứng
        accel_device = AcceleratorDevice.AUTO
        if device.lower() == "cpu":
            accel_device = AcceleratorDevice.CPU
        elif device.lower() in ("cuda", "gpu"):
            accel_device = AcceleratorDevice.CUDA
        elif device.lower() == "mps":
            accel_device = AcceleratorDevice.MPS

        pipeline_options = PdfPipelineOptions(
            accelerator_options=AcceleratorOptions(
                device=accel_device,
                num_threads=4 if accel_device == AcceleratorDevice.CPU else 1
            )
        )
        pipeline_options.do_ocr = False
        pipeline_options.images_scale = 1.0
        
        # 2. Khởi tạo converter với cấu hình trên cho PDF
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        
        self.count_tokens_func = count_tokens_func
        self.max_tokens_per_block = max_tokens_per_block

    def parse_docs_in_dir(
        self,
        input_dir: Path | str,
        output_dir: Path | str,
        overwrite_outputs: bool = False,
    ) -> list[dict]:
        input_dir, output_dir = Path(input_dir), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Parsing docs with Docling from {input_dir}...")

        current_output_files = {p.stem for p in output_dir.rglob("*.json")}

        for doc_path in sorted(input_dir.rglob("*.pdf")):
            if not doc_path.is_file():
                continue
            doc_name = doc_path.with_suffix("").name
            save_name = f"docling_output_{doc_path.parent.name}_{doc_name}"

            if not overwrite_outputs and save_name in current_output_files:
                print(f"Skipping {doc_name} parsing, overwrite_outputs is False")
                continue

            print(f"Parsing {doc_name}")
            try:
                conv_result = self.converter.convert(str(doc_path))
            except Exception as e:
                print(f"Failed to parse {doc_name}: {e}")
                continue

            # Save raw docling result as JSON
            raw_dict = conv_result.document.export_to_dict()
            save_path = output_dir / f"{save_name}.json"
            with open(save_path, "w", encoding="utf-8") as fp:
                json.dump(raw_dict, fp, ensure_ascii=False, indent=2)

        print(f"\nRaw Docling outputs saved to {output_dir}")

    def convert_raw_results_to_markdown(
        self,
        raw_input_dir: Path | str,
        output_dir: Path | str,
    ) -> list[dict]:
        

        raw_input_dir, output_dir = Path(raw_input_dir), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Reading Docling outputs from {raw_input_dir}...")

        extracted_texts: list[dict] = []

        for doc_path in sorted(raw_input_dir.rglob("*.json")):
            if not doc_path.is_file():
                continue

            doc_name = doc_path.with_suffix("").name.replace("docling_output_", "")
            print(f"Converting {doc_name}")

            with open(doc_path, encoding="utf-8") as fp:
                raw_dict = json.load(fp)

            dl_doc = DLDocument.model_validate(raw_dict)

            # Build pages_content, split_points, titles by iterating items
            pages_content: dict[int, str] = {}
            split_points: list[int] = []
            titles: list[dict] = []
            current_offset = 0
            last_page_number = None

            for item, level in dl_doc.iterate_items():
                # Determine page number from provenance
                page_number = 1
                if hasattr(item, "prov") and item.prov:
                    page_number = item.prov[0].page_no

                # Add page breaks between pages and update offsets
                if last_page_number is not None and page_number > last_page_number:
                    pb = "<!-- PageBreak -->\n\n"
                    pages_content.setdefault(last_page_number, "")
                    pages_content[last_page_number] += pb
                    current_offset += len(pb)
                
                last_page_number = page_number
                block_text = ""
                item_type = None

                if isinstance(item, TableItem):
                    # Export table as markdown
                    try:
                        table_df = item.export_to_dataframe(doc=dl_doc)
                        table_md = table_df.to_markdown(index=False)
                    except Exception:
                        table_md = item.text if hasattr(item, "text") else ""

                    # Split large tables
                    table_blocks = self._split_table_markdown(table_md)
                    for k, tbl_md in enumerate(table_blocks):
                        tbl_block = f"<Table>\n{tbl_md}\n</Table>\n\n"
                        pages_content.setdefault(page_number, "")
                        pages_content[page_number] += tbl_block
                        
                        # Add split point at the end of each table block (or just the last one)
                        current_offset += len(tbl_block)
                        is_last_tbl = k == len(table_blocks) - 1
                        if is_last_tbl:
                            split_points.append(current_offset)
                    
                    item_type = "TABLE"
                    continue

                elif isinstance(item, TextItem):
                    text = item.text
                    label = item.label.value if hasattr(item.label, "value") else str(item.label)

                    if label in ("section_header", "title"):
                        heading_level = max(1, level)
                        block_text = "#" * heading_level + " " + text + "\n\n"
                        titles.append({
                            "title": block_text.strip(),
                            "start": current_offset,
                            "level": heading_level,
                        })
                        item_type = "HEADING"
                    elif label == "caption":
                        block_text = f"<Figure>\n{text}\n</Figure>\n\n"
                        item_type = "FIGURE"
                    elif label == "page_header":
                        block_text = f"<!-- PageHeader: {text} -->\n\n"
                        item_type = "PAGE_HEADER"
                    elif label == "page_footer":
                        block_text = f"<!-- PageFooter: {text} -->\n\n"
                        item_type = "PAGE_FOOTER"
                    elif label == "footnote":
                        block_text = r"\* " + text + "\n\n"
                        item_type = "FOOTNOTE"
                    elif label == "formula":
                        block_text = f"<Formula>\n{text}\n</Formula>\n\n"
                        item_type = "FORMULA"
                    else:
                        block_text = text + "\n\n"
                        item_type = "TEXT"
                else:
                    # PictureItem or other - skip unless it has a caption
                    if hasattr(item, "caption") and item.caption:
                        cap_text = item.caption if isinstance(item.caption, str) else str(item.caption)
                        block_text = f"<Figure>\n{cap_text}\n</Figure>\n\n"
                        item_type = "FIGURE"
                    else:
                        continue

                pages_content.setdefault(page_number, "")
                pages_content[page_number] += block_text
                current_offset += len(block_text)

                # Split-point rules (mirroring AzureDIParser logic)
                add_split = True
                if item_type in ("HEADING", "FOOTNOTE", "PAGE_HEADER", "PAGE_FOOTER"):
                    add_split = False
                elif item_type == "TEXT" and self.count_tokens_func(text) < 100:
                    add_split = False

                if add_split:
                    split_points.append(current_offset)

            # Build full_text
            full_text = "".join(pages_content[k] for k in sorted(pages_content))

            # Compute end offsets for titles
            for idx, t in enumerate(titles):
                level_val = t["level"]
                end = len(full_text)
                for jdx in range(idx + 1, len(titles)):
                    if titles[jdx]["level"] <= level_val:
                        end = titles[jdx]["start"]
                        break
                t["end"] = end

            out_data = {
                "document_name": doc_name,
                "pages": pages_content,
                "full_text": full_text,
                "split_points": split_points,
                "titles": titles,
            }
            extracted_texts.append(out_data)

            save_path = output_dir / f"{doc_name}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2)

        print(f"\nOutputs saved to {output_dir}")
        return extracted_texts

    def _split_table_markdown(self, table_md: str) -> list[str]:
        """Split a large table markdown into chunks respecting max_tokens_per_block."""
        if self.count_tokens_func(table_md) <= self.max_tokens_per_block:
            return [table_md]

        lines = table_md.split("\n")
        if len(lines) < 3:
            return [table_md]

        # First two lines are header + separator
        header = lines[0] + "\n" + lines[1]
        data_lines = lines[2:]

        sub_mds: list[str] = []
        current_lines: list[str] = []

        for line in data_lines:
            candidate = header + "\n" + "\n".join(current_lines + [line])
            if self.count_tokens_func(candidate) > self.max_tokens_per_block and current_lines:
                sub_mds.append(header + "\n" + "\n".join(current_lines))
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            sub_mds.append(header + "\n" + "\n".join(current_lines))

        return sub_mds
