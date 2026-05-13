import numpy as np
import os
from sentence_transformers import SentenceTransformer
from core.logger import logger

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_models", "embedding_model")

_embedding_model = None

def load_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            if os.path.exists(MODEL_DIR) and os.listdir(MODEL_DIR):
                logger.info(f"Loading embedding model from local directory: {MODEL_DIR}")
                _embedding_model = SentenceTransformer(MODEL_DIR)
            else:
                logger.info(f"Downloading embedding model {MODEL_ID} from HuggingFace...")
                _embedding_model = SentenceTransformer(MODEL_ID)
                os.makedirs(MODEL_DIR, exist_ok=True)
                _embedding_model.save(MODEL_DIR)
                logger.info(f"Embedding model saved to {MODEL_DIR}")
        except Exception as e:
            logger.error(f"Error loading/downloading embedding model: {e}")
            raise e
    return _embedding_model

async def get_embeddings(texts):
    if isinstance(texts, str):
        texts = [texts]
        
    model = load_embedding_model()
    embeddings = model.encode(texts)
    
    return np.array(embeddings, dtype=np.float32)

from fastembed import SparseTextEmbedding

_sparse_embedding_model = None
SPARSE_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_models")

def load_sparse_embedding_model():
    global _sparse_embedding_model
    if _sparse_embedding_model is None:
        logger.info(f"Loading FastEmbed Sparse model (Qdrant/bm25) to {SPARSE_MODEL_DIR}...")
        os.makedirs(SPARSE_MODEL_DIR, exist_ok=True)
        # Tải model về và lưu tại thư mục ai_models
        _sparse_embedding_model = SparseTextEmbedding(model_name="Qdrant/bm25", cache_dir=SPARSE_MODEL_DIR)
    return _sparse_embedding_model

async def get_sparse_embeddings(texts):
    """
    Tạo Sparse Vector sử dụng thư viện fastembed (Qdrant/bm25).
    """
    if isinstance(texts, str):
        texts = [texts]
        
    model = load_sparse_embedding_model()
    
    # model.embed trả về generator chứa các SparseEmbedding objects
    embeddings = list(model.embed(texts))
    
    sparse_vectors = []
    for emb in embeddings:
        sparse_vectors.append({
            "indices": emb.indices.tolist(),
            "values": emb.values.tolist()
        })
        
    return sparse_vectors
