import os
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from models.embeddings import OllamaEmbeddingFunction

CHROMA_DIR = os.path.join("data", "chroma")


class Memory:
    def __init__(self, collection_name: str = "emails"):
        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False)
        )
        self.embed_fn = OllamaEmbeddingFunction()
        # Pass the actual embedding function object
        self.col = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "l2"},
            embedding_function=self.embed_fn,
        )

    def add(self, docs: List[str], metadatas: List[Dict], ids: List[str]):
        embeddings = self.embed_fn(docs) if docs else None
        self.col.upsert(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)

    def search(self, query: str, k: int = 5):
        q_emb = self.embed_fn([query])[0]
        res = self.col.query(query_embeddings=[q_emb], n_results=k)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        ids = res.get("ids", [[]])[0]
        return [{"id": i, "document": d, "metadata": m} for i, d, m in zip(ids, docs, metas)]