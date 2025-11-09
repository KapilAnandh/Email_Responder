import os
import base64
import re
import click
from dotenv import load_dotenv
from rich.table import Table
from rich.console import Console
from rich import box

from src.gmail_client import get_message, list_messages, get_service, send_message
from src.classifier import classify_email
from src.agent import EmailAgent
from src.utils.text import clean_html
from src.utils.logger import info

console = Console()
load_dotenv()


def short_id(full_id: str) -> str:
    """Show only first 8 characters – enough to copy-paste."""
    return full_id[:8]


@click.group()
def cli():
    """Automated Email Responder Agent CLI"""
    pass


# ──────────────────────────────── FETCH COMMAND ────────────────────────────────
@cli.command()
@click.option('--q', default='-in:chats -category:social -category:promotions newer_than:2d',
              help='Gmail search query (default: recent personal mails)')
@click.option('--n', default=5, help='Max results to fetch')
def fetch(q, n):
    """Fetch and display recent emails (short IDs)."""
    svc = get_service()
    msgs = list_messages(svc, q, n)
    table = Table(title="Recent Emails", box=box.ROUNDED)
    table.add_column("#", style="cyan")
    table.add_column("Short ID", style="magenta")
    table.add_column("From", style="green")
    table.add_column("Subject", style="yellow")

    for i, m in enumerate(msgs, 1):
        full = get_message(svc, m['id'])
        hdrs = {h['name'].lower(): h['value'] for h in full['payload'].get('headers', [])}
        frm = hdrs.get('from', '')[:40]
        subj = hdrs.get('subject', '')[:60]
        table.add_row(str(i), short_id(m['id']), frm, subj)

    console.print(table)


# ──────────────────────────────── REPLY COMMAND ────────────────────────────────
@cli.command()
@click.argument('msg_id')
@click.option('--send', is_flag=True, help='Actually send the reply')
@click.option('--feedback', default='', help='Free-text feedback to refine the draft')
def reply(msg_id, send, feedback):
    """Classify → draft → (optional refine) → (optional send)."""
    svc = get_service()

    # === Resolve short ID to full ===
    if len(msg_id) < 16:
        recent_msgs = list_messages(svc, query=None, max_results=20)
        matching_ids = [m['id'] for m in recent_msgs if m['id'].startswith(msg_id)]
        if not matching_ids:
            console.print(f"[bold red]Error: No recent message found with ID starting with '{msg_id}'[/]")
            return
        if len(matching_ids) > 1:
            console.print(f"[bold red]Error: Multiple messages match '{msg_id}'; use full ID or a longer prefix[/]")
            return
        msg_id = matching_ids[0]
        info(f"Resolved short ID to full: {msg_id}")

    full = get_message(svc, msg_id)

    hdrs = {h['name'].lower(): h['value'] for h in full['payload'].get('headers', [])}
    frm = hdrs.get('from', '')
    subj = hdrs.get('subject', '(no subject)')

    # ---------- extract email body ----------
    payload = full.get('payload', {})
    body_html = ''
    if 'data' in payload.get('body', {}):
        body_html = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    else:
        for p in payload.get('parts', []) or []:
            mt = p.get('mimeType', '')
            if mt.startswith('text/'):
                data = p['body'].get('data', '') or ''
                body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                break

    snippet = clean_html(body_html)[:140]
    cat = classify_email(subj, snippet, frm, body_html)

    agent = EmailAgent()

    console.rule("Classification")
    console.print(cat)

    # --- Generate draft ---
    draft = agent.draft_reply(subj, frm, body_html)

    # --- Optional refinement with feedback ---
    if feedback:
        console.rule("Refined Draft (based on feedback)")
        refined = agent.refine(draft, feedback)
        console.print(refined)
        final_text = refined
    else:
        console.rule("Draft Reply")
        console.print(draft)
        final_text = draft

    # --- Optional sending ---
    if send:
        to_addr = agent._extract_email(frm)
        info(f"Sending to {to_addr} ...")
        send_message(svc, to_addr, f"Re: {subj}", final_text)
        info("Sent!")


# ──────────────────────────────── MEMORY COMMAND (Improved) ────────────────────────────────
@cli.command()
@click.argument('query')
@click.option('--k', default=5)
def memory(query, k):
    """
    Search local vector memory (Chroma) for similar or matching emails/drafts.
    Filters results to show only those containing the search term, with fallback to top semantic matches.
    """
    from src.memory import Memory
    mem = Memory("emails")
    results = mem.search(query, k=k)

    query_lower = query.lower()
    matched = []
    for r in results:
        doc = r["document"].lower()
        # Filter by keyword presence
        if query_lower in doc:
            matched.append(r)

    if not matched:
        console.print("[bold yellow]No exact keyword matches found — showing closest semantic results.[/]")
        matched = results  # fallback to semantic matches

    for r in matched:
        console.print("-" * 60)
        console.print(r["document"][:600])
        console.print(r["metadata"])


# ──────────────────────────────── SUGGEST COMMAND ────────────────────────────────
@cli.command()
@click.argument('subject')
@click.argument('body')
def suggest(subject, body):
    """Generate a new reply suggestion based on memory-similar past emails."""
    from src.agent import EmailAgent
    agent = EmailAgent()
    suggestion = agent.suggest_with_memory(subject, body)

    console.rule("Memory-Based Suggestion")
    if suggestion:
        console.print(suggestion)
    else:
        console.print("[bold yellow]No similar drafts found in memory.[/]")


if __name__ == '__main__':
    cli()
