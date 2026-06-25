class RAGConstant:
    PROVIDER = "openai"
    TEMPERATURE = 0.5
    MODEL = "gpt-4.1-mini"
    COHERE_RERANK_MODEL = "rerank-english-v3.0"
    DEFAULT_MAX_ITERATION = 5

    # Retrieval tuning
    HYBRID_SEARCH_ALPHA = 0.5
    RETRIEVAL_CANDIDATES = 20
    RERANK_TOP_K = 5

    # Ingestion
    INGEST_BATCH_SIZE = 50
    SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt")

    # Chunking
    CHUNK_MAX_CHARS = 1000
    CHUNK_NEW_AFTER_N_CHARS = 800
    CHUNK_COMBINE_UNDER_N_CHARS = 200
