# Automated Email Responder Agent

An end-to-end, privacy-friendly **email responder** that:
- Fetches Gmail messages
- Classifies them (urgent / work / personal / general)
- Drafts human-like replies via **local LLM (Ollama)**
- Improves drafts from **user feedback**
- Stores drafts & contexts in **ChromaDB** for semantic memory

> Built for the assessment with clean architecture, strong modularity, and production-ready ergonomics.

##  Features

- **Local LLM** via Ollama (`gemma3:270m` by default)
- **Embeddings** via Ollama (`nomic-embed-text`) + **ChromaDB** semantic memory
- **Gmail** integration (OAuth) for fetching/sending emails
- **Heuristic classifier** (fast, interpretable)
- **Refinement loop**: apply your feedback to the draft
- **CLI** for fetch/reply/memory/suggest workflows
- **Docker** support

---

##  Repository Structure
├─ data/ # tokens and ChromaDB (persisted/mounted)
├─ models/
│ ├─ embeddings.py # OllamaEmbeddingFunction (calls /api/embeddings)
│ └─ llm.py # LocalLLM wrapper (calls /api/generate)
├─ src/
│ ├─ agent.py # EmailAgent: draft, refine, memory-augmented reply
│ ├─ classifier.py # classification facade over heuristic rules
│ ├─ gmail_client.py # Gmail OAuth + list/get/send helpers
│ ├─ memory.py # ChromaDB persistent vector store wrapper
│ ├─ prompts.py # Prompt templates
│ ├─ utils/
│ │ ├─ logger.py # Rich logger facade
│ │ └─ text.py # cleaning + heuristic classification
│ └─ main.py # Click-based CLI (fetch/reply/memory/suggest)
├─ .env # runtime config (optional in Docker; also set via env)
├─ requirements.txt
├─ Dockerfile
└─ README.md

## Prerequisites

1. **Ollama** installed on your host: <https://ollama.com>
2. Pull models (or equivalents you prefer):
   ```bash
   ollama pull gemma3:270m
   ollama pull nomic-embed-text
   
Google Cloud OAuth client:
Create OAuth credentials (Desktop app)
Download the credentials.json
Keep it safe; you’ll mount it read-only into the container

## Environment Variables

You can use a .env file (for local runs) or -e KEY=VALUE flags with Docker.
# Gmail
GMAIL_SCOPES=read_only,send,modify
GMAIL_USER=me

# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma3:270m
EMBED_MODEL=nomic-embed-text

# Agent identity
USER_NAME=Kapil Anandh
USER_TITLE=AI/ML Engineer
ORG_NAME=One Data Software Solutions

## CLI Usage

* List recent emails - python -m src.main fetch --q "-in:chats newer_than:2d" --n 5

* Reply (optionally refine with feedback) - python -m src.main reply <SHORT_OR_FULL_MSG_ID>
python -m src.main reply 19a675ec --feedback "Be more confident and proactive"

* Send the reply - python -m src.main reply 19a675ec --send

* Search memory (Chroma) - python -m src.main memory "invoice"

* Suggest with memory - python -m src.main suggest "Timeline extension" "We may need one extra week for QA"

## Design Notes

* Heuristic classifier (fast, transparent) for labels + tone control.
* LLM drafting via local Ollama → fully private and offline.
* Refinement applies your feedback without rewriting the whole email.
* ChromaDB stores drafts and contexts → memory-augmented suggestions.
* Click CLI keeps workflow simple, auditable, and demo-friendly.
* Rich logger for clear console output.
