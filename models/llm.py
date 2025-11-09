import os
import requests
from pydantic import BaseModel, Field

class LocalLLM(BaseModel):
    model: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "gemma3:270m"))
    base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    timeout: int = 120

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """Send a prompt to the local Ollama model and return the text output."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {"temperature": temperature},
            "stream": False
        }
        r = requests.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()
