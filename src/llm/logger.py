import logging
import time
from contextlib import contextmanager
from pathlib import Path

from src.llm.config import RAGConfig


def get_logger(name: str = "rag") -> logging.Logger:
    """File-only logger (rag.log). Level from LOG_LEVEL env (default INFO)."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = (RAGConfig.LOG_LEVEL or "INFO").upper()
    if not isinstance(logging.getLevelName(level), int):
        level = "INFO"
    logger.setLevel(level)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "rag.log")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


@contextmanager
def log_duration(logger: logging.Logger, label: str):
    """Log how long the wrapped block took, in milliseconds."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("%s | %.0f ms", label, elapsed_ms)
