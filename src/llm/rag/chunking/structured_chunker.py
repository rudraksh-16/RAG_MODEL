import sys
from collections import Counter
from dataclasses import dataclass
from typing import Callable, List, Optional

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element

from src.llm.logger import get_logger
from src.llm.rag.constant import RAGConstant

logger = get_logger("rag.chunk")


@dataclass
class Chunk:
    """Unified contract every element type collapses into (M6).

    `text` is what gets embedded, BM25-matched and reranked. The rest is metadata
    carried through to Weaviate so retrieval can cite source/page/type.
    """

    text: str
    source_file: str
    page_number: Optional[int]
    element_type: str  # "text" | "table" | "image"
    section: Optional[str] = None
    image_path: Optional[str] = None


def _section_of(composite: Element) -> Optional[str]:
    """Nearest heading for a composite chunk: first Title/Header among its originals."""
    originals = getattr(composite.metadata, "orig_elements", None) or []
    for el in originals:
        if el.category in ("Title", "Header"):
            return el.text
    return None


def build_chunks(
    elements: List[Element],
    source_file: str,
    describe_image: Optional[Callable[[str], str]] = None,
    max_characters: int = RAGConstant.CHUNK_MAX_CHARS,
    new_after_n_chars: int = RAGConstant.CHUNK_NEW_AFTER_N_CHARS,
    combine_text_under_n_chars: int = RAGConstant.CHUNK_COMBINE_UNDER_N_CHARS,
) -> List[Chunk]:
    """Convert typed elements into structure-aware chunks.

    - Text/Title/list elements -> grouped under headings via chunk_by_title (no
      mid-section cuts), one Chunk(element_type="text") per composite.
    - Table elements -> their own Chunk(element_type="table"), text = HTML so rows
      and columns survive.
    - Image elements -> their own Chunk(element_type="image") whose text is a vision
      description, only when a describe_image callback is supplied (M5).
    """
    text_elements: List[Element] = []
    chunks: List[Chunk] = []

    for el in elements:
        if el.category == "Table":
            html = getattr(el.metadata, "text_as_html", None) or el.text or ""
            chunks.append(
                Chunk(
                    text=html,
                    source_file=source_file,
                    page_number=el.metadata.page_number,
                    element_type="table",
                    section=None,
                )
            )
        elif el.category == "Image":
            image_path = getattr(el.metadata, "image_path", None)
            if describe_image and image_path:
                description = describe_image(image_path)
                if description:
                    chunks.append(
                        Chunk(
                            text=description,
                            source_file=source_file,
                            page_number=el.metadata.page_number,
                            element_type="image",
                            image_path=image_path,
                        )
                    )
        else:
            text_elements.append(el)

    composites = chunk_by_title(
        text_elements,
        max_characters=max_characters,
        new_after_n_chars=new_after_n_chars,
        combine_text_under_n_chars=combine_text_under_n_chars,
    )
    for comp in composites:
        chunks.append(
            Chunk(
                text=comp.text,
                source_file=source_file,
                page_number=comp.metadata.page_number,
                element_type="text",
                section=_section_of(comp),
            )
        )

    logger.info(
        "CHUNKED %s -> %d chunks %s",
        source_file,
        len(chunks),
        dict(Counter(c.element_type for c in chunks)),
    )
    return chunks


if __name__ == "__main__":
    import os

    from src.llm.rag.injection.parse import parse_pdf

    if len(sys.argv) < 2:
        print("usage: python -m src.llm.rag.chunking.structured_chunker <pdf>")
        raise SystemExit(1)

    path = sys.argv[1]
    els = parse_pdf(path, "images/_debug")
    result = build_chunks(els, os.path.basename(path))

    print("TOTAL CHUNKS:", len(result))
    print("BY TYPE:", dict(Counter(c.element_type for c in result)))
    print("-" * 60)
    for c in result[:12]:
        head = f"[{c.element_type}] p{c.page_number} sec={c.section!r}"
        print(head, "|", c.text[:90].replace("\n", " "))
