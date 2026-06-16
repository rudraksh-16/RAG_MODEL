import weaviate

from src.backend.models.document import initialize_document_collection
from src.backend.models.document_chunk import initialize_document_chunk_collection
from src.backend.seed import seed_documents
from src.logger import setup_logging


def main() -> None:
    setup_logging()

    client = weaviate.connect_to_local()
    try:
        # 1. Reset DocumentChunk completely (dev-friendly)
        # DISABLED: dropping this collection wipes all ingested chunks.
        # Uncomment only for an intentional full re-ingest.
        # if client.collections.exists("DocumentChunk"):
        #     client.collections.delete("DocumentChunk")
        #     print("DocumentChunk collection deleted")

        # 2. Ensure schemas exist
        initialize_document_collection(client)
        initialize_document_chunk_collection(client)

        # 3. Seed documents (PASS client in)
        seed_documents(client)

        # 4. Verify
        print("Collections:", client.collections.list_all())

        docs = client.collections.use("Document").query.fetch_objects()
        for d in docs.objects:
            print(d.properties)

    finally:
        client.close()

    # try:
    #     chunk_collection = client.collections.use("DocumentChunk")

    #     res = chunk_collection.query.fetch_objects(
    #         limit=1,
    #         include_vector=True
    #     )

    #     obj = res.objects[0]
    #     print(type(obj.vector))
    #     print(len(obj.vector))

    #     vec_dict = obj.vector
    #     embedding = list(vec_dict.values())[0]

    #     print(type(embedding))
    #     print(len(embedding))
    # finally:
    #     client.close()


if __name__ == "__main__":
    main()
