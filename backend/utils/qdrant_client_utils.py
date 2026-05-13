from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import os

qdrant_client = None
COLLECTION_NAME = "pdf_chunk"

def get_qdrant_client():
    global qdrant_client
    if qdrant_client is None:
        # Nếu dùng local thì Qdrant url mặc định là http://localhost:6333
        qdrant_url = os.getenv("URL_QRDANT")
        qdrant_api_key = os.getenv("API_KEY_QRDANT")

        print("URL_QRDANT =", qdrant_url)
        print("API_KEY_QRDANT =", qdrant_api_key[:15] if qdrant_api_key else None)
        
        if qdrant_api_key:
            qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=60)
        else:
            qdrant_client = QdrantClient(url=qdrant_url, timeout=60)
            
    return qdrant_client

from qdrant_client.http import models

def init_qdrant():
    client = get_qdrant_client()
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if COLLECTION_NAME not in names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=384,          # model embedding size
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams(
                    modifier=models.Modifier.IDF, # Qdrant tự động tính IDF (BM25)
                )
            }
        )
        print(f"Created Qdrant collection: {COLLECTION_NAME}")
    else:
        print(f"Qdrant collection exists: {COLLECTION_NAME}")

    # Đảm bảo index cho payload tồn tại để có thể filter theo user_id, document_id
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="user_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="document_id",
        field_schema=models.PayloadSchemaType.INTEGER,
    )
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="is_public",
        field_schema=models.PayloadSchemaType.BOOL,
    )
    print(f"Payload indexes ensured for: {COLLECTION_NAME}")
