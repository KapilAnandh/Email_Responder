import re
from email.utils import parseaddr

# --- Keyword and domain sets ---
WORK_KEYWORDS = {"invoice", "meeting", "deadline", "deliverable", "sla", "client", "sow", "po"}
URGENT_KEYWORDS = {"urgent", "asap", "immediately", "important", "priority", "escalated"}
PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}


def clean_html(text: str) -> str:
    """
    Remove HTML tags and extra spaces from email body or snippet.
    """
    text = re.sub(r"<[^>]+>", " ", text)  # remove HTML tags
    text = re.sub(r"\s+", " ", text).strip()  # collapse multiple spaces
    return text


def infer_sender_type(email_address: str) -> str:
    """
    Classify sender based on email domain.
    Returns 'personal' or 'work'.
    """
    _, addr = parseaddr(email_address)
    domain = addr.split("@")[-1].lower() if "@" in addr else ""
    
    if domain in PERSONAL_DOMAINS:
        return "personal"
    elif domain:
        return "work"
    else:
        return "unknown"


def heuristic_classify(subject: str, snippet: str, sender: str) -> dict:
    """
    Heuristically classify an email as 'urgent', 'work', 'personal', or 'general'
    using keyword matching and sender domain.
    """
    s = f"{subject} {snippet}".lower()
    label = "general"
    score = 0.5

    # Check urgency
    if any(k in s for k in URGENT_KEYWORDS):
        label = "urgent"
        score = 0.9

    # Check work-related
    elif any(k in s for k in WORK_KEYWORDS):
        label = "work"
        score = 0.8

    # Infer sender type
    sender_type = infer_sender_type(sender)

    # If personal sender & general content → classify as personal
    if sender_type == "personal" and label == "general":
        label = "personal"
        score = 0.7

    return {
        "label": label,
        "score": score,
        "sender_type": sender_type
    }
