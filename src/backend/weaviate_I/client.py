import weaviate
from weaviate.connect import ConnectionParams


def get_client():
    client = weaviate.WeaviateClient(
        connection_params=ConnectionParams.from_url(
            "http://127.0.0.1:8080", grpc_port=50051
        )
    )
    client.connect()
    # print(client.is_ready())

    if not client.is_ready():
        raise RuntimeError("Weaviate is not ready")

    return client
