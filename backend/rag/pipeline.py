"""End-to-end PDF-to-chunks pipeline."""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Literal, Union, Optional

from .chunking_utils import count_tokens
from .postprocessing import (
    check_chunk_gaps,
    get_page_info,
    get_title_info,
    repair_gaps_between_chunks,
)
from .splitters import RecursiveSplitter


def chunk_files(
    input_path: Union[str, Path],
    parser: Optional[object] = None,
    parser_type: Literal["marker", "docling", "pymupdf"] = "pymupdf",
    chunk_size: int = 600,
    chunk_overlap: int = 50,
    separators: Optional[list[str]] = None,
    merging: Literal["to_chunk_size", "small_only"] = "small_only",
    min_chunk_tokens: int = 100,
    output_dir: Optional[Union[str, Path]] = None,
    device: Optional[str] = None,
    overwrite_outputs: bool = False,
) -> list[dict]:
    """Parse PDF(s) and split into chunks in one step.

    Args:
        input_path: Path to a single PDF file or directory of PDFs.
        parser: A parser instance (PyMuPDFParser, DoclingParser, etc.).
        parser_type: The default parser to use if ``parser`` is None.
            Can be ``"pymupdf"`` (default), ``"docling"``, or ``"marker"``.
        chunk_size: Maximum chunk size in tokens.
        chunk_overlap: Overlap between chunks in tokens.
        separators: Separators for recursive splitting.
            Defaults to ``["\\n\\n", "\\n", " ", ""]``.
        merging: Merge strategy (``"to_chunk_size"`` or ``"small_only"``).
        min_chunk_tokens: Minimum chunk size in tokens (for ``"small_only"`` merging).
        output_dir: Directory to save parsed JSON files. If *None*, uses a
            temporary directory that is cleaned up automatically.
        device: Device to run the parser on (e.g., 'cpu', 'cuda'). 
            Mainly used for Marker or Docling.
        overwrite_outputs: Whether to overwrite existing intermediate results.

    Returns:
        List of dicts with chunk data and metadata.
    """
    input_path = Path(input_path)

    if separators is None:
        separators = ["\n\n", "\n", " ", ""]

    # Create parser if not provided
    if parser is None:
        if parser_type == "pymupdf":
            from .pymupdf import PyMuPDFParser
            parser = PyMuPDFParser(count_tokens_func=count_tokens)
        elif parser_type == "docling":
            from .docling import DoclingParser
            parser = DoclingParser(device=device or "cpu")
        else:
            from .parsing_marker_pdf import MarkerParser
            parser = MarkerParser(device=device)

    # Handle single file vs directory
    tmp_input_dir = None
    if input_path.is_file():
        tmp_input_dir = tempfile.mkdtemp()
        shutil.copy2(input_path, Path(tmp_input_dir) / input_path.name)
        pdf_dir = Path(tmp_input_dir)
    elif input_path.is_dir():
        pdf_dir = input_path
    else:
        raise FileNotFoundError(f"Path does not exist: {input_path}")

    # Setup output directories
    tmp_output_dir = None
    if output_dir is None:
        tmp_output_dir = tempfile.mkdtemp()
        raw_dir = Path(tmp_output_dir) / "raw"
        parsed_dir = Path(tmp_output_dir) / "parsed"
    else:
        output_dir = Path(output_dir)
        raw_dir = output_dir / "raw"
        parsed_dir = output_dir / "parsed"

    try:
        # Step 1: Parse PDFs → raw parser output
        parser.parse_docs_in_dir(pdf_dir, raw_dir, overwrite_outputs=overwrite_outputs)

        # Step 2: Convert raw output → standard JSON
        parsed_docs = parser.convert_raw_results_to_markdown(raw_dir, parsed_dir)

        # Step 3: Split into chunks
        splitter = RecursiveSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            merging=merging,
            min_chunk_tokens=min_chunk_tokens,
        )

        results: list[dict] = []
        for doc in parsed_docs:
            doc_name = doc["document_name"]
            full_text = doc["full_text"]

            if not full_text:
                continue

            chunks = splitter.split_text(full_text)
            chunks = repair_gaps_between_chunks(chunks=chunks, text=full_text)

            if not check_chunk_gaps(chunks, full_text):
                raise RuntimeError(
                    f"Chunk gap recovery failed for '{doc_name}'. "
                    "This is a bug."
                )

            page_info = get_page_info(
                pages=doc["pages"], chunks=chunks, text=full_text
            )
            title_info = get_title_info(
                titles=doc["titles"], chunks=chunks, text=full_text
            )

            for i, chunk_text in enumerate(chunks):
                results.append(
                    {
                        "doc_name": doc_name,
                        "chunk_index": i,
                        "chunk_text": chunk_text,
                        "chunk_pages": page_info[i],
                        "titles_context": title_info[i],
                        "chunk_len": count_tokens(chunk_text),
                    }
                )

        return results

    finally:
        if tmp_input_dir:
            shutil.rmtree(tmp_input_dir, ignore_errors=True)
        if tmp_output_dir:
            shutil.rmtree(tmp_output_dir, ignore_errors=True)


# if __name__ == "__main__":
#     from pathlib import Path
    
#     # 1. Đường dẫn tới file PDF của bạn
#     pdf_path = r"D:\lung2.pdf"
    
#     # 2. Gọi hàm chunk_files
#     # Mặc định sử dụng PyMuPDFParser
#     chunks = chunk_files(
#         input_path=pdf_path,
#         chunk_size=800,
#         chunk_overlap=100,
#         overwrite_outputs=True
#     )
    
#     # 3. Xem kết quả và lưu ra file txt
#     output_txt = "chunks_output12345.txt"
#     print(f"Đã chia thành {len(chunks)} đoạn. Đang lưu vào {output_txt}...")
    
#     with open(output_txt, "w", encoding="utf-8") as f:
#         for i, chunk in enumerate(chunks):
#             f.write(f"=========================================\n")
#             f.write(f"CHUNK INDEX: {chunk['chunk_index']}\n")
#             f.write(f"TRANG: {chunk['chunk_pages']}\n")
#             f.write(f"TIÊU ĐỀ: {chunk['titles_context']}\n")
#             f.write(f"ĐỘ DÀI: {chunk['chunk_len']} tokens\n")
#             f.write(f"-----------------------------------------\n")
#             f.write(f"NỘI DUNG:\n{chunk['chunk_text']}\n")
#             f.write(f"=========================================\n\n")
    
#     print("Hoàn tất lưu file!")
