from src.utils.text import heuristic_classify
from src.utils.logger import info


def classify_email(subject: str, snippet: str, sender: str, body: str) -> dict:
    """Fast heuristic classification (LLM is optional and removed)."""
    return heuristic_classify(subject, snippet, sender)