import os
import base64
from email.mime.text import MIMEText
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from src.utils.logger import info

# Gmail OAuth Scopes Mapping
SCOPES_MAP = {
    "read_only": "https://www.googleapis.com/auth/gmail.readonly",
    "send": "https://www.googleapis.com/auth/gmail.send",
    "modify": "https://www.googleapis.com/auth/gmail.modify",
}

def _load_scopes() -> List[str]:
    raw = os.getenv("GMAIL_SCOPES", "read_only,send").split(",")
    return [SCOPES_MAP[s.strip()] for s in raw if s.strip() in SCOPES_MAP]

def get_service():
    creds = None
    token_path = os.path.join("data", "token.json")
    cred_path = os.path.join("credentials.json")  # Fixed: was in data/
    scopes = _load_scopes()
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, scopes)
            creds = flow.run_local_server(port=0)
        os.makedirs("data", exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    info("Gmail service initialized successfully.")
    return service

def list_messages(service, query: str = None, max_results: int = 10) -> List[Dict]:
    user = os.getenv("GMAIL_USER", "me")
    resp = service.users().messages().list(
        userId=user,
        q=query or "",
        maxResults=max_results
    ).execute()
    return resp.get("messages", [])

def get_message(service, msg_id: str) -> Dict:
    user = os.getenv("GMAIL_USER", "me")
    return service.users().messages().get(
        userId=user,
        id=msg_id,
        format="full"
    ).execute()

def send_message(service, to_addr: str, subject: str, body: str, thread_id: Optional[str] = None):
    user = os.getenv("GMAIL_USER", "me")
    message = MIMEText(body)
    message["to"] = to_addr
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body_dict = {"raw": raw}
    if thread_id:
        body_dict["threadId"] = thread_id
    sent = service.users().messages().send(
        userId=user,
        body=body_dict
    ).execute()
    info(f"Sent email to {to_addr} with subject: '{subject}'")
    return sent