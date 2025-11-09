CLASSIFY_TEMPLATE = (
    "You are a helpful email triage assistant. "
    "Classify the email into one of: urgent, personal, work, general.\n"
    "Return JSON with keys: label, confidence (0-1), and reasons.\n\n"
    "Subject: {subject}\n"
    "From: {sender}\n"
    "Body: {body}\n"
)

DRAFT_TEMPLATE = """You are a polite and concise email assistant.
Read the following email and write a clear, professional, and friendly reply (under 120 words).

Subject: {subject}
Sender: {sender}
Body:
{body}

Organization: {org_name}

Your reply should sound human and end with this signature:
{signature}
"""

REFINE_TEMPLATE = (
    "Improve the draft based on the feedback.\n\n"
    "Draft:\n{draft}\n\n"
    "Feedback:\n{feedback}\n\n"
    "Return **only** the improved draft."
)
