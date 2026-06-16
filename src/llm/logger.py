import logging

from src.llm.config import RAGConfig


def get_logger(name: str = "rag") -> logging.Logger:
    """Console + file logger. Level from LOG_LEVEL env (default INFO)."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = (RAGConfig.LOG_LEVEL or "INFO").upper()
    if not isinstance(logging.getLevelName(level), int):
        level = "INFO"
    logger.setLevel(level)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler("rag.log")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
