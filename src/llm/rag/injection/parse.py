import os
import sys
from collections import Counter
from typing import List, Set

from pypdf import PdfReader
from unstructured.documents.elements import Element
from unstructured.partition.docx import partition_docx
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.text import partition_text

from src.llm.logger import get_logger

logger = get_logger("rag.parse")


def _pages_with_text(elements: List[Element]) -> Set[int]:
    """Pages that produced real (non-image) text."""
    return {
        el.metadata.page_number
        for el in elements
        if el.category != "Image" and (el.text or "").strip()
    }


def _total_pages(file_path: str) -> int:
    with open(file_path, "rb") as f:
        return len(PdfReader(f).pages)


def parse_pdf(file_path: str, image_output_dir: str) -> List[Element]:
    """Parse a PDF into typed, page-aware elements (Title/NarrativeText/Table/Image/...).

    Uses hi_res layout detection so tables and images are recognized:
    - infer_table_structure -> Table elements carry metadata.text_as_html
    - Image blocks are cropped to image_output_dir and their path is stored on
      metadata.image_path for downstream vision description.

    OCR fallback (M4): any page hi_res left with no text layer is re-parsed with
    Tesseract (strategy="ocr_only") so scanned/image-only pages never go blank.
    """
    elements = partition_pdf(
        filename=file_path,
        strategy="hi_res",
        infer_table_structure=True,
        extract_image_block_types=["Image"],
        extract_image_block_output_dir=image_output_dir,
    )

    covered = _pages_with_text(elements)
    missing = [p for p in range(1, _total_pages(file_path) + 1) if p not in covered]
    if missing:
        logger.info("OCR fallback: %d page(s) with no text layer: %s", len(missing), missing)
        ocr_elements = partition_pdf(file_path, strategy="ocr_only")
        recovered = [
            el
            for el in ocr_elements
            if el.metadata.page_number in set(missing) and (el.text or "").strip()
        ]
        elements.extend(recovered)
        logger.info("OCR recovered %d element(s)", len(recovered))

    logger.info("PARSED %s -> %d elements", file_path, len(elements))
    return elements


def parse_document(file_path: str, image_output_dir: str) -> List[Element]:
    """Route a source file to the right partitioner by extension.

    PDF runs the full hi_res + OCR + image-extraction pipeline (parse_pdf). DOCX
    and TXT are plain text/table sources: no layout inference, no image output,
    so image_output_dir is unused for them.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path, image_output_dir)
    if ext == ".docx":
        return partition_docx(filename=file_path)
    if ext == ".txt":
        return partition_text(filename=file_path)
    raise ValueError(f"unsupported file type: {ext}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m src.llm.rag.injection.parse <pdf> [image_dir]")
        raise SystemExit(1)

    path = sys.argv[1]
    img_dir = sys.argv[2] if len(sys.argv) > 2 else "images/_debug"
    els = parse_pdf(path, img_dir)

    print("TOTAL:", len(els))
    print("BY TYPE:", dict(Counter(e.category for e in els)))
    print("-" * 60)
    for e in els:
        text = (e.text or "")[:70].replace("\n", " ")
        line = f"[{e.category}] p{e.metadata.page_number} | {text}"
        if getattr(e.metadata, "image_path", None):
            line += f"  <img:{e.metadata.image_path}>"
        print(line)
