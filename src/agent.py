import os
import re
import textwrap
from typing import Optional
from models.llm import LocalLLM
from src.prompts import REFINE_TEMPLATE
from src.utils.text import clean_html
from src.utils.logger import info
from src.memory import Memory
from src.classifier import classify_email


class EmailAgent:
    """
    Context-aware email agent that writes as Kapil Anandh.
    Responds naturally, confidently, and assumes knowledge of the sender’s request.
    """

    def __init__(self):
        self.llm = LocalLLM()
        self.mem = Memory("emails")

        # Identity from environment
        self.name = os.getenv("USER_NAME", "Kapil Anandh").strip()
        self.title = os.getenv("USER_TITLE", "AI/ML Engineer").strip()
        self.org = os.getenv("ORG_NAME", "One Data Software Solutions").strip()

        self.signature = f"Sincerely,\n{self.name}\n{self.title}\n{self.org}"

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_email(header: str) -> str:
        """Extract only the email address."""
        m = re.search(r"<([^>]+)>", header or "")
        return m.group(1) if m else (header or "").strip()

    @staticmethod
    def _sender_name(header: str) -> str:
        """Extract sender's first name from header."""
        if "<" in header:
            part = header.split("<")[0].strip()
        else:
            part = header.strip().split("@")[0]
        part = part.replace(".", " ").strip().title()
        return part.split()[0] if part else "there"

    # ------------------------------------------------------------------ #
    # Draft Generation
    # ------------------------------------------------------------------ #
    def draft_reply(self, subject: str, sender: str, body_html: str) -> str:
        """Generate a natural, human-style reply in Kapil Anandh’s tone."""
        body = clean_html(body_html)
        sender_name = self._sender_name(sender)

        # 1️⃣ Classify tone
        cat = classify_email(subject, body[:200], sender, body_html)
        label = cat.get("label", "general")

        # 2️⃣ Greeting and tone
        greeting, tone = self._context_style(label, sender_name)
        keywords = self._extract_keywords(body)
        context_line = f"Key context: {', '.join(keywords)}.\n" if keywords else ""

        # 3️⃣ Role-aware prompt
        prompt = textwrap.dedent(f"""
        You are {self.name}, {self.title} at {self.org}.
        You are replying to an email from {sender_name}.
        The sender wrote the message below — you are responding to them.

        Assume you fully understand their request already.
        Write your reply as Kapil Anandh would — direct, polite, and confident.
        Avoid robotic phrasing or unnecessary explanations.

        Tone: {tone}
        {context_line}
        Greeting: {greeting}
        End with this signature exactly:\n{self.signature}

        Original Email:
        Subject: {subject}
        Body: {body[:1200]}

        Write a short reply (≤120 words) that:
        - Sounds conversational and natural
        - Directly answers or acknowledges the sender
        - Uses short, clear sentences
        - Ends with the exact signature above
        """)

        draft = self.llm.generate(prompt, temperature=0.25)
        draft = self._clean_output(draft, greeting)

        # Save draft to memory
        doc = f"SUBJECT: {subject}\nLABEL: {label}\nFROM: {sender}\nBODY: {body}\nDRAFT: {draft}"
        self.mem.add(
            [doc],
            metadatas=[{"label": label, "sender": sender, "type": "draft"}],
            ids=[f"draft::{abs(hash(doc))}"],
        )

        return draft.strip()

    # ------------------------------------------------------------------ #
    # Tone + Greeting Mapping
    # ------------------------------------------------------------------ #
    def _context_style(self, label: str, sender_name: str):
        if label == "urgent":
            return f"Hi {sender_name},", "Decisive, direct, reassuring"
        elif label == "work":
            return f"Dear {sender_name},", "Professional, concise, and respectful"
        elif label == "personal":
            return f"Hi {sender_name},", "Friendly, casual, and conversational"
        else:
            return f"Hello {sender_name},", "Polite and neutral"

    # ------------------------------------------------------------------ #
    # Keyword Extraction
    # ------------------------------------------------------------------ #
    def _extract_keywords(self, body: str, limit: int = 5) -> list:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", body.lower())
        ignores = {"thank", "please", "email", "hello", "regards", "from", "that", "this"}
        result = []
        for w in words:
            if w not in ignores and w not in result:
                result.append(w)
        return result[:limit]

    # ------------------------------------------------------------------ #
    # Cleanup Output (Improved)
    # ------------------------------------------------------------------ #
    def _clean_output(self, text: str, greeting: str) -> str:
        """Cleans generated text: removes duplicate greetings, AI artifacts, or signatures."""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        body = []
        for line in lines:
            lower = line.lower()
            if lower.startswith("subject:"):
                continue
            if any(x in lower for x in ["sincerely", "regards", "best regards", self.name.lower()]):
                continue
            if any(line.lower().startswith(x) for x in ["hi ", "hello", "dear"]):
                continue
            if "ai/ml engineer" in lower and "kapil" not in lower:
                continue
            if line.strip() == self.signature.strip():
                continue
            body.append(line)

        cleaned = " ".join(body).strip()
        words = cleaned.split()
        if len(words) > 120:
            cleaned = " ".join(words[:120])

        # Nicely formatted final version
        return f"{greeting}\n\n{textwrap.fill(cleaned, 80)}\n\n{self.signature}"

    # ------------------------------------------------------------------ #
    # Refinement (Improved)
    # ------------------------------------------------------------------ #
    def refine(self, draft: str, feedback: str) -> str:
        """Refine the draft naturally based on Kapil's feedback."""
        greeting = draft.splitlines()[0] if draft.splitlines() else "Hi there,"

        prompt = textwrap.dedent(f"""
        You are improving an email reply written by {self.name}, {self.title} at {self.org}.

        Original draft:
        {draft.strip()}

        Feedback from Kapil (the author):
        "{feedback.strip()}"

        Task:
        - Apply the feedback directly to the draft.
        - Keep the same meaning and tone — do not rewrite it entirely.
        - Do NOT repeat the feedback text literally.
        - Preserve the greeting and closing signature exactly as they were.
        - Make the final version sound natural and human.

        Output ONLY the improved email text.
        """)

        improved = self.llm.generate(prompt, temperature=0.25)
        improved = self._clean_output(improved, greeting)

        # Store refined version in memory
        self.mem.add(
            [f"FEEDBACK: {feedback}\nIMPROVED: {improved}"],
            metadatas=[{"type": "refine"}],
            ids=[f"refine::{abs(hash(draft + feedback))}"],
        )

        return improved.strip()

    # ------------------------------------------------------------------ #
    # Memory Recall
    # ------------------------------------------------------------------ #
    def suggest_with_memory(self, subject: str, body: str) -> Optional[str]:
        """Use vector memory to find similar past replies."""
        results = self.mem.search(f"{subject} {body}", k=3)
        if not results:
            return None
        ctx = "\n\n".join([r["document"][:600] for r in results])
        prompt = textwrap.dedent(f"""
        You are {self.name}, {self.title} at {self.org}.
        Use similar phrasing or tone from these past drafts:
        {ctx}

        Write a concise (≤120 words) and human-like reply in your tone.
        Always end with your real signature.
        """)
        return self.llm.generate(prompt, temperature=0.2).strip()
