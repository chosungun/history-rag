import chromadb
from sentence_transformers import SentenceTransformer
from app.core.config import settings

_client = None
_collection = None
_embedder = None

async def init_chroma():
    global _client, _collection, _embedder
    _client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port
    )
    _collection = _client.get_or_create_collection(
        name="korean_history",
        metadata={"hnsw:space": "cosine"}
    )
    _embedder = SentenceTransformer(settings.embed_model)
    print(f"✅ ChromaDB 연결 완료 — 문서 수: {_collection.count()}")

def get_collection():
    return _collection

def get_embedder():
    return _embedder

def embed(texts: list[str]) -> list[list[float]]:
    return _embedder.encode(texts, normalize_embeddings=True).tolist()
