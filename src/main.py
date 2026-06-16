# import weaviate

# with weaviate.connect_to_local() as client:
#     # print(client.collections.list_all())
#     collection = client.collections.get("DocumentChunk")
# #   print(collection)

#     collection.data.insert(
#         properties={
#             "text": "Weaviate is a vector database for AI applications.",
#             "source": "test_doc",
#             "chunk_id": 0
#         },
#         vector=[0.01] * 768   # must match your embedding size
#     )

#     results = collection.query.near_vector(
#         near_vector=[0.01] * 768,
#         limit=1
#     )

#     print(results.objects[0].properties)

# with weaviate.connect_to_local() as client:
#     collection = client.collections.get("DocumentChunk")

    # obj = collection.query.fetch_object_by_id(
    #     uuid="0016a3e8-7fbf-4b92-af1a-458342ab51c4",
    #     include_vector=True
    # )

    # print("Vectors:", obj.vector)
    # results = collection.query.fetch_objects(
    #     limit=1,
    #     include_vector=True
    # )

    # for obj in results.objects:
    #     print(obj.vector)
    # collection = client.collections.get("DocumentChunk")

    # count = collection.aggregate.over_all(total_count=True)
    # print("Total entries:", count.total_count)
    # response = collection.query.fetch_objects(
    #     limit=5, return_properties=["chunk_text", "document_id", "chunk_index"]
    # )

    # for obj in response.objects:
    #     print("-" * 50)
    #     print("Doc ID:", obj.properties["document_id"])
    #     print("Chunk index:", obj.properties["chunk_index"])
    #     print("Text:", obj.properties["chunk_text"][:200])
