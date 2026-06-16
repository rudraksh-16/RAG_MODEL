import logging
from pathlib import Path

from src.llm.config import RAGConfig


def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "ai_tutor.log"

    level = (RAGConfig.LOG_LEVEL or "INFO").upper()
    if not isinstance(logging.getLevelName(level), int):
        level = "INFO"

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
