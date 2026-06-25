import base64
import sys

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

from src.llm.logger import get_logger
from src.llm.rag.constant import RAGConstant

logger = get_logger("rag.vision")

_PROMPT = (
    "Describe this image in detail, including any data, numbers, labels, axes, "
    "legends, and what it shows. If it is a chart or diagram, explain what it conveys."
)

# Intentional build-once singleton: the vision model is reused across all images.
_model = None


def _get_model():
    """Lazily build the (reused OpenAI) vision model once."""
    global _model
    if _model is None:
        _model = init_chat_model(
            RAGConstant.MODEL,
            model_provider=RAGConstant.PROVIDER,
            temperature=0,
        )
    return _model


def _mime(path: str) -> str:
    return "image/png" if path.lower().endswith(".png") else "image/jpeg"


def describe_image(image_path: str) -> str:
    """Return a text description of an image via the configured multimodal LLM.

    On any failure returns "" so ingestion skips the image instead of crashing.
    """
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        message = HumanMessage(
            content=[
                {"type": "text", "text": _PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{_mime(image_path)};base64,{b64}"},
                },
            ]
        )
        response = _get_model().invoke([message])
        text = response.content if isinstance(response.content, str) else str(response.content)
        logger.info("VISION described %s (%d chars)", image_path, len(text))
        return text.strip()

    except Exception as e:
        # Intentional deviation from "raise, never sentinel": a single failed image
        # must not abort the whole ingest, so it is logged and skipped.
        logger.warning("VISION failed for %s: %s", image_path, e)
        return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m src.llm.rag.injection.describe_image <image>")
        raise SystemExit(1)
    print(describe_image(sys.argv[1]))
