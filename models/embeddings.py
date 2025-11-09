import os
import requests
from typing import List
from pydantic import BaseModel, Field


class OllamaEmbeddingFunction(BaseModel):
    """Lightweight embedding function using Ollama's local API."""
    model: str = Field(default_factory=lambda: os.getenv("EMBED_MODEL", "nomic-embed-text"))
    base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    timeout: int = 120

    # Chroma calls this to compare persisted vs. supplied embedding functions
    def name(self) -> str:
        return f"ollama_{self.model}"

    def __call__(self, input: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/api/embeddings"
        vectors = []
        for text in input:
            payload = {"model": self.model, "prompt": text}
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            vectors.append(data.get("embedding", []))
        return vectors