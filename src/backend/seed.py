import json

from src.llm.rag.constant import RAGConstant


def seed_documents(client) -> None:
    """Seed the Document collection with the chapter PDFs, skipping duplicates."""
    collection = client.collections.use("Document")

    documents = [
        {
            "document_path": "IP/leip1ps.pdf",
            "metadata": {"document_name": "CH-0"},
        },
        {
            "document_path": "IP/leip101.pdf",
            "metadata": {"document_name": "CH-1"},
        },
        {
            "document_path": "IP/leip102.pdf",
            "metadata": {"document_name": "CH-2"},
        },
        {
            "document_path": "IP/leip103.pdf",
            "metadata": {"document_name": "CH-3"},
        },
        {
            "document_path": "IP/leip104.pdf",
            "metadata": {"document_name": "CH-4"},
        },
        {
            "document_path": "IP/leip105.pdf",
            "metadata": {"document_name": "CH-5"},
        },
        {
            "document_path": "IP/leip106.pdf",
            "metadata": {"document_name": "CH-6"},
        },
        {
            "document_path": "IP/leip107.pdf",
            "metadata": {"document_name": "CH-7"},
        },
    ]

    # Fetch existing docs to avoid duplicates (ON CONFLICT DO NOTHING equivalent)
    existing = collection.query.fetch_objects(return_properties=["document_path"])
    existing_paths = {obj.properties["document_path"] for obj in existing.objects}

    with collection.batch.fixed_size(RAGConstant.INGEST_BATCH_SIZE) as batch:
        for doc in documents:
            if doc["document_path"] in existing_paths:
                continue

            batch.add_object(
                properties={
                    "document_path": doc["document_path"],
                    "metadata": json.dumps(doc["metadata"]),
                }
            )
