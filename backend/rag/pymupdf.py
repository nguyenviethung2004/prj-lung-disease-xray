import json
import re
from pathlib import Path
from typing import Callable, List, Dict, Optional, Union
from abc import ABC, abstractmethod

from .chunking_utils import count_tokens

class BaseParser(ABC):
    """Abstract base class for document parsers."""
    @abstractmethod
    def parse_docs_in_dir(self, input_dir: Path | str, output_dir: Path | str, overwrite_outputs: bool = False) -> list[dict]:
        pass

    @abstractmethod
    def convert_raw_results_to_markdown(self, raw_input_dir: Path | str, output_dir: Path | str) -> list[dict]:
        pass


class PyMuPDFParser(BaseParser):
    """Lightweight local PDF parser using PyMuPDF4LLM with text cleaning capabilities."""

    def __init__(self,
                 count_tokens_func: Callable[[str], int] = count_tokens,
                 max_tokens_per_block: int = 1000):
        try:
            import pymupdf4llm  # noqa: F401
        except ImportError:
            raise ImportError(
                "pymupdf4llm is required for PyMuPDFParser. "
                "Install with: pip install pymupdf4llm"
            )
        self.count_tokens_func = count_tokens_func
        self.max_tokens_per_block = max_tokens_per_block

    def _is_toc_page(self, text: str) -> bool:
        """
        Nhận diện trang Mục lục (TOC) một cách tổng quát cho nhiều loại PDF.
        Sử dụng kết hợp từ khóa, mẫu dòng (leader lines) và mật độ dòng dạng mục lục.
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            return False

        # 1. Kiểm tra từ khóa tiêu đề (thường nằm ở các dòng đầu tiên)
        header_text = "\n".join(lines[:5]).lower()
        toc_keywords = [
            r'mục lục', r'table of contents', r'contents', r'tóm tắt nội dung',
            r'danh mục', r'list of tables', r'list of figures', r'index'
        ]
        has_keyword = any(re.search(kw, header_text) for kw in toc_keywords)

        # 2. Mẫu dòng có "Leader" (dấu chấm/gạch nối nối dài tới số trang/số La Mã)
        leader_pattern = r'.+?[\.\-_]{3,}\s*(?:\d+|[ivx]+)\s*$'
        
        # 3. Mẫu dòng kết thúc bằng số hoặc số La Mã với khoảng trắng rộng (TOC không dấu nối)
        gap_num_pattern = r'^[^\s].+?\s{4,}(?:\d+|[ivx]+)\s*$'

        leader_count = 0
        gap_num_count = 0
        
        for line in lines:
            if re.search(leader_pattern, line, re.IGNORECASE):
                leader_count += 1
            elif re.search(gap_num_pattern, line, re.IGNORECASE):
                gap_num_count += 1

        # Tiêu chí quyết định
        total_matches = leader_count + gap_num_count
        return (has_keyword and total_matches >= 2) or (total_matches >= 8)

    def _clean_boilerplate(self, text: str, extra_boilerplate: set[str] = None) -> str:
        """
        Dọn dẹp Header, Footer, Page number, và Copyright một cách tổng quát.
        Loại bỏ cả URL, Email và các dòng boilerplate lặp lại.
        """
        if not text:
            return ""

        # 0. Loại bỏ các dòng boilerplate lặp lại được truyền vào (Document-specific)
        if extra_boilerplate:
            lines = text.split('\n')
            text = "\n".join([line for line in lines if line.strip() not in extra_boilerplate])

        # 1. Dọn dẹp số trang (Page numbers)
        patterns_page = [
            r'(?i)\b(?:page|trang|p\.)\s*\d+\s*(?:of|/|on)?\s*\d*\b',
            # Bắt số trang đơn lẻ (số thường, số La Mã, có thể in đậm hoặc nằm trong ngoặc)
            # VD: "12", "**iv**", "[ 5 ]", "- 1 -", "__2__"
            r'^\s*(?:\*\*|__)?\s*[-|\[|\(]?\s*(?:\d+|[ivx]+)\s*[-|\]|\)]?\s*(?:\*\*|__)?\s*$',
            r'^\s*\d+\s*/\s*\d+\s*$'
        ]
        for pattern in patterns_page:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)

        # 2. Dọn dẹp Copyright và Thông tin bảo mật
        patterns_legal = [
            r'(?i)(?:©|copyright|copyrights|copyleft|bản quyền)\s*(?:\d{4}|by)?.*?$',
            r'(?i)all rights reserved\.?',
            r'(?i)confidential|internal use only|phổ biến nội bộ',
            r'(?i)proprietary and confidential',
            r'(?i)bản quyền thuộc về.*$'
        ]
        for pattern in patterns_legal:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)

        # 3. Dọn dẹp URL và Email
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)

        # 4. Dọn dẹp nhiễu đồ họa và Artifacts
        text = re.sub(r'^\s*[\-_*]{3,}\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'[|||]', '', text)

        # 5. Chuẩn hóa khoảng trắng
        lines = [line.strip() for line in text.split('\n')]
        clean_lines = []
        for line in lines:
            if not line:
                clean_lines.append("")
                continue
            if re.match(r'^[\.\-_ ]+$', line):
                continue
            clean_lines.append(line)

        text = "\n".join(clean_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip() 
        # Bắt "______" hoặc "-------" dùng làm đường viền
        text = re.sub(r'^[_]{4,}\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[-]{4,}\s*$', '', text, flags=re.MULTILINE)
        
        # 4. Dọn dẹp khoảng trắng
        text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE) # Trim đầu dòng
        text = re.sub(r'\n{3,}', '\n\n', text) # Giảm nhiều dòng trống liên tiếp
        
        return text.strip()

    def parse_docs_in_dir(
        self,
        input_dir: Path | str,
        output_dir: Path | str,
        overwrite_outputs: bool = False,
    ) -> list[dict]:
        import pymupdf4llm

        input_dir, output_dir = Path(input_dir), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Parsing docs with PyMuPDF from {input_dir}...")

        current_output_files = {p.stem for p in output_dir.rglob("*.json")}

        for doc_path in sorted(input_dir.rglob("*.pdf")):
            if not doc_path.is_file():
                continue
            doc_name = doc_path.with_suffix("").name
            save_name = f"pymupdf_output_{doc_path.parent.name}_{doc_name}"

            if not overwrite_outputs and save_name in current_output_files:
                print(f"Skipping {doc_name} parsing, overwrite_outputs is False")
                continue

            print(f"Parsing {doc_name}")
            try:
                page_chunks = pymupdf4llm.to_markdown(str(doc_path), page_chunks=True)
            except Exception as e:
                print(f"Failed to parse {doc_name}: {e}")
                continue

            # Save raw page chunks as JSON
            save_path = output_dir / f"{save_name}.json"
            serializable = []
            for chunk in page_chunks:
                entry = {"text": chunk.get("text", ""), "metadata": {}}
                meta = chunk.get("metadata", {})
                if isinstance(meta, dict):
                    entry["metadata"] = {k: v for k, v in meta.items()
                                         if isinstance(v, (str, int, float, bool, list))}
                serializable.append(entry)

            with open(save_path, "w", encoding="utf-8") as fp:
                json.dump(serializable, fp, ensure_ascii=False, indent=2)

        print(f"\nRaw PyMuPDF outputs saved to {output_dir}")

    def convert_raw_results_to_markdown(
        self,
        raw_input_dir: Path | str,
        output_dir: Path | str,
    ) -> list[dict]:
        raw_input_dir, output_dir = Path(raw_input_dir), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Reading PyMuPDF outputs from {raw_input_dir}...")

        extracted_texts: list[dict] = []

        for doc_path in sorted(raw_input_dir.rglob("*.json")):
            if not doc_path.is_file():
                continue

            doc_name = doc_path.with_suffix("").name.replace("pymupdf_output_", "")
            print(f"Converting {doc_name}")

            with open(doc_path, encoding="utf-8") as fp:
                page_chunks = json.load(fp)

            # --- TỰ ĐỘNG NHẬN DIỆN HEADER/FOOTER LẶP LẠI TRONG DOCUMENT ---
            from collections import Counter
            all_lines = []
            for chunk in page_chunks:
                text_lines = [line.strip() for line in chunk.get("text", "").split('\n') if line.strip()]
                all_lines.extend(text_lines)
            
            line_counts = Counter(all_lines)
            num_pages = len(page_chunks)
            # Dòng xuất hiện > 30% số trang (hoặc ít nhất 5 lần) thường là Header/Footer lặp lại
            extra_boilerplate = {line for line, count in line_counts.items() 
                                 if count > 1 and (count >= num_pages * 0.3 or count >= 5)}
            # ------------------------------------------------------------

            pages_content: dict[int, str] = {}
            split_points: list[int] = []
            titles: list[dict] = []
            current_offset = 0

            for page_idx, chunk in enumerate(page_chunks):
                page_number = page_idx + 1
                raw_text = chunk.get("text", "")

                # 1. BỎ QUA TRANG MỤC LỤC
                if self._is_toc_page(raw_text):
                    print(f"  -> Skipping page {page_number} (Detected as TOC)")
                    continue

                # 2. DỌN DẸP RÁC VĂN BẢN (Header/Footer)
                clean_text = self._clean_boilerplate(raw_text, extra_boilerplate=extra_boilerplate)

                if not clean_text.strip():
                    continue

                # 3. TRÍCH XUẤT TIÊU ĐỀ
                lines = clean_text.split("\n")
                page_md = ""

                for line in lines:
                    heading_match = re.match(r"^(#{1,6})\s+(.+)", line)
                    if heading_match:
                        level = len(heading_match.group(1))
                        title_text = line.strip()
                        titles.append({
                            "title": title_text,
                            "start": current_offset + len(page_md),
                            "level": level,
                        })

                    page_md += line + "\n"
                
                # Không thêm nữa để tiết kiệm token
                # Thêm khoảng trắng cách trang cho sạch sẽ
                page_md += "\n" 

                pages_content[page_number] = page_md

                # 4. CẬP NHẬT SPLIT POINTS
                current_offset += len(page_md)
                split_points.append(current_offset)

            # Xóa split_point cuối cùng vì nó là điểm kết thúc tài liệu
            if split_points:
                split_points.pop()

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