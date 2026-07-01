import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")
    DOCUMENT_COLLECTION = os.getenv("DOCUMENT_COLLECTION", "Document")
    CHUNK_COLLECTION = os.getenv("CHUNK_COLLECTION", "DocumentChunk")
