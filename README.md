# Cyborgs Protected Chat System

FastAPI + React/Vite application for experimenting with defensive controls around LLM chat. The project is built as a protected gateway that evaluates prompts, attachments, retrieval context, and tool requests before deciding whether to allow, sanitize, or block a request.

It is best understood as a security-focused demo and evaluation harness, not a production-ready chat platform.

## What This Repository Includes

- A FastAPI backend with a layered defense pipeline
- A React frontend with chat, dashboard, admin, and decision-log views
- Local RAG indexing and retrieval with poisoned-corpus handling
- Attachment validation, extraction, OCR fallback, and content-risk analysis
- Tool intent detection, authorization, and deterministic tool execution
- Local SQLite-backed conversation memory and evaluation review storage
- In-memory rate limiting, concurrency caps, timeout handling, and spike alerts
- A backend-heavy test suite covering chat policy, attachments, RAG, tools, auth, memory, and attack-corpus runs

## Core Behavior

Every `POST /chat/` request is processed through a security pipeline that can return one of three outcomes:

- `ALLOW`: request is considered safe enough to run normally
- `SANITIZE`: risky text/context is cleaned before model execution
- `BLOCK`: request is rejected before the model is allowed to answer

The backend returns structured telemetry with each chat response, including:

- `decision` and `risk_level`
- `trace_id` for request correlation
- tool request and authorization results
- RAG retrieval and validation metadata
- attachment extraction and security results
- conversation-memory usage stats
- whether the model was actually called

## Defense Pipeline

The main orchestration lives in [backend/app/controller/defense_controller.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/controller/defense_controller.py).

At a high level, each chat request goes through:

1. Trace ID assignment and request counting middleware
2. Client API key validation
3. Conversation creation or lookup
4. Traffic-guard admission checks
5. Prompt analysis for injection, obfuscation, jailbreak, and risky patterns
6. Attachment inspection, text extraction, OCR fallback, and signal analysis
7. Optional upload indexing into the local RAG store
8. Optional steganography checks
9. Optional secure RAG retrieval and chunk validation
10. Conversation-memory replay
11. Tool detection and tool authorization
12. Risk scoring and mode-based policy decisioning
13. Prompt/context sanitization when required
14. LLM or deterministic fallback response generation
15. Decision/event logging and evaluation-record persistence

## Security Modes

The active security mode is global and managed server-side through the admin API. The chat request body does not control the effective mode.

Supported modes:

- `Off`
- `Weak`
- `Normal`
- `Strong`

Mode changes are handled by the shared mode manager and exposed through `/admin/mode`.

## Major Security Features

### Prompt Injection and Obfuscation Detection

The backend analyzes prompts for signals such as:

- instruction override attempts
- system or developer prompt references
- prompt leakage attempts
- jailbreak patterns
- encoded or obfuscated content
- suspicious structural or role-manipulation patterns

Relevant modules:

- [backend/app/services/input_content_checker.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/input_content_checker.py)
- [backend/app/utils/text_sanitizer.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/utils/text_sanitizer.py)
- [backend/app/services/policy_engine.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/policy_engine.py)

### Secure RAG and Poisoned Context Handling

The backend includes a local corpus under [backend/app/data/rag](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/data/rag) with:

- trusted documents
- benign documents
- quarantined or poisoned sample documents

RAG behavior includes:

- deterministic local embeddings
- an in-memory Qdrant-compatible vector store
- chunking and indexing of static documents
- optional indexing of uploaded attachment text
- per-user isolation for uploaded documents
- quarantine of risky sources
- validation and optional sanitization of retrieved chunks
- hard caps on chunks, context size, and per-source usage

Relevant modules:

- [backend/app/services/rag_manager.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/rag_manager.py)
- [backend/app/services/rag_content_validator.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/rag_content_validator.py)
- [backend/app/services/vector_store.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/vector_store.py)
- [backend/app/services/embedding_service.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/embedding_service.py)

### Attachment Defense

Attachments are accepted as structured base64 payloads and pass through:

- MIME/type validation
- bounded payload inspection
- text extraction for text-like files
- direct PDF extraction where possible
- OCR fallback for PDFs and images when supported
- signal analysis on extracted text
- per-attachment allow/flag/block dispositioning

Supported attachment result metadata includes:

- `disposition`
- `flags`
- `text_preview`
- `extraction_status`
- `extraction_method`
- `ocr_used`
- `page_count`
- derived `signals`

Relevant modules:

- [backend/app/services/attachment_manager.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/attachment_manager.py)
- [backend/app/services/attachment_validator.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/attachment_validator.py)
- [backend/app/services/attachment_text_extractor.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/attachment_text_extractor.py)
- [backend/app/services/attachment_signal_analyzer.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/attachment_signal_analyzer.py)
- [backend/app/services/steganography_detector.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/steganography_detector.py)

### Tool Abuse Prevention

The system detects requested tool usage from the prompt and/or the explicit `requested_tools` field.

Registered tool names:

- `calculator`
- `file_reader`
- `web`
- `database`
- `write_file`
- `execute_command`

Current tool behavior:

- `calculator` executes deterministic arithmetic expressions
- `file_reader` is restricted to repository-safe paths or uploaded attachment previews
- `web` is restricted to a strict allowlist (`example.com` and `www.example.com`)
- `database` is a seeded in-memory SQLite demo database
- `write_file` is deny-by-policy
- `execute_command` is deny-by-policy

Tool execution is time-bounded and audited.

Relevant modules:

- [backend/app/services/tool_gatekeeper.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/tool_gatekeeper.py)
- [backend/app/services/tool_plugins.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/tool_plugins.py)

### Traffic and Volume Attack Protection

The chat endpoint is protected by an in-process traffic guard that enforces:

- per-IP rate limits
- per-client-key rate limits
- optional per-user minute and daily quotas
- maximum in-flight chat requests
- request timeout accounting
- request-spike alerts

Important scope limit:

- these controls are single-instance only
- counters live in memory
- they are not shared across workers, containers, or machines

Relevant module:

- [backend/app/services/traffic_guard.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/services/traffic_guard.py)

## Persistence and Data Stores

The project uses both persistent and in-memory storage:

- `backend/data/chat_memory.sqlite`: conversation transcripts and turn history
- `backend/data/evaluation.sqlite`: evaluation records and review labels
- in-memory vector index for current RAG data
- in-memory runtime metrics, event buffers, and abuse-protection counters

Conversation memory behavior:

- conversations are identified by UUID
- full transcripts are stored locally
- only bounded recent turns are replayed to the model
- blocked or sanitized turns can be excluded via settings

Evaluation store behavior:

- every decision becomes a predicted label
- `ALLOW` maps to predicted `benign`
- `SANITIZE` and `BLOCK` map to predicted `attack`
- admin review endpoints allow attachment of ground-truth labels
- labeled metrics include FPR, ASR, and a confusion matrix

## Backend Architecture

### Main Backend Packages

- `backend/app/main.py`: FastAPI app creation, lifespan setup, CORS, root route, global exception handler
- `backend/app/api/routes`: route modules for `chat`, `admin`, and `health`
- `backend/app/api/dependencies/auth.py`: client/admin API key enforcement and client IP extraction
- `backend/app/controller`: defense orchestration
- `backend/app/core`: settings, logging, and security-mode configuration
- `backend/app/models`: Pydantic schemas for request/response contracts
- `backend/app/services`: defense, tooling, RAG, storage, metrics, traffic control, and model access
- `backend/app/utils`: text sanitization helpers
- `backend/app/data/rag`: static trusted, benign, and poisoned RAG sources

### Main Backend Endpoints

Public routes:

- `GET /`
- `GET /health/`
- `POST /chat`
- `POST /chat/`

Admin routes:

- `GET /admin/mode`
- `POST /admin/mode`
- `GET /admin/events`
- `GET /admin/events/old`
- `GET /admin/decisions`
- `GET /admin/metrics`
- `POST /admin/reset-runtime`
- `GET /admin/evaluations`
- `GET /admin/evaluations/{trace_id}`
- `POST /admin/evaluations/{trace_id}/review`
- `GET /admin/rag/status`
- `GET /admin/rag/sources`
- `POST /admin/rag/reindex`
- `GET /admin/conversations`
- `GET /admin/conversations/{conversation_id}`

### Authentication Model

All protected routes use the `X-API-Key` header.

- `POST /chat/` requires `CLIENT_API_KEY`
- `/admin/*` requires `ADMIN_API_KEY` when configured
- if `ADMIN_API_KEY` is not set, admin routes fall back to `CLIENT_API_KEY`

This behavior is implemented in [backend/app/api/dependencies/auth.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/api/dependencies/auth.py).

## Frontend Architecture

The frontend lives under `frontend/` and is a React 18 + TypeScript + Vite app.

Main areas:

- [frontend/src/App.tsx](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/frontend/src/App.tsx): app shell, tabs, health polling, dashboard/log refresh logic
- [frontend/src/hooks/useChat.ts](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/frontend/src/hooks/useChat.ts): chat request lifecycle and message persistence
- [frontend/src/hooks/useAdmin.ts](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/frontend/src/hooks/useAdmin.ts): mode and metrics loading
- [frontend/src/services/api.ts](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/frontend/src/services/api.ts): backend client and shared header handling
- `frontend/src/components/chat`: chat UI, prompt composer, response cards, RAG/tool badges
- `frontend/src/components/dashboard`: metrics overview cards
- `frontend/src/components/admin`: security-mode selector
- `frontend/src/components/logs`: decision log table
- `frontend/src/components/common`: shared layout, branding, and status components

Frontend behavior:

- stores chat messages in `localStorage`
- uses `VITE_API_URL` to target the backend
- uses `VITE_CLIENT_API_KEY` for every API request, including admin requests
- polls `/health/` every 30 seconds
- refreshes metrics on dashboard entry and after chat activity
- renders decision records in the Logs tab, not raw event records

Important frontend auth note:

- the current frontend client has only one configured API key value
- if you set `ADMIN_API_KEY` to something different from `CLIENT_API_KEY`, the current frontend admin views will fail until the client is updated to send the admin key for admin routes

## API Contracts

### Chat Request

`POST /chat/`

```json
{
  "user_id": "demo-user",
  "conversation_id": "optional-uuid",
  "prompt": "Summarize the attached PDF",
  "attachments": [
    {
      "id": "attachment-1",
      "name": "report.pdf",
      "mime_type": "application/pdf",
      "kind": "file",
      "content_b64": "<base64>"
    }
  ],
  "requested_tools": ["file_reader"],
  "rag_enabled": true,
  "rag_scope": "default",
  "rag_document_ids": ["security_playbook"]
}
```

`rag_scope` supports:

- `default`
- `static_only`
- `user_uploads_only`

### Chat Response

The response model includes:

- decision fields: `decision`, `risk_level`, `reason`
- trace and identity fields: `trace_id`, `user_id`, `conversation_id`
- memory fields: `memory_used`, `memory_turns_loaded`, `memory_chars_loaded`, `memory_truncated`
- tool fields: `tools_requested`, `tools_allowed`, `tool_decisions`
- RAG fields: `rag_context_used`, `rag_context_validated`, `rag_retrieval_attempted`, `rag_sources_considered`, `rag_chunks_retrieved`, `rag_chunks_used`, `rag_chunks_dropped`, `rag_sources_used`, `rag_warnings`
- attachment fields: `attachments_received`, `attachments_flagged`, `attachment_results`
- execution fields: `model_called`, `timestamp`
- compact signal data: `signals`

### Error Behavior

- `401`: missing or invalid API key
- `403`: conversation ownership violation
- `404`: conversation or evaluation record not found, or invalid conversation target
- `429`: rate limit, quota, or concurrency rejection
- `500`: internal processing failure
- `504`: chat processing timeout

## Metrics and Admin Observability

Admin metrics aggregate several kinds of state:

- chat trace counts
- decision distribution
- risk distribution
- evaluation metrics and pending reviews
- RAG status and source counts
- abuse-protection limits and live counters
- active and recent spike alerts

Admin event streams include entries such as:

- `chat_request`
- `attachments_checked`
- `steganography_checked`
- `rag_checked`
- `tool_checked`
- `risk_scored`
- `chat_timeout`
- `rate_limit_rejected`
- `quota_rejected`
- `concurrency_rejected`
- `traffic_spike_alert`
- `conversation_memory_error`
- `error`

Decision records are paginated separately from raw events.

## Repository Structure

```text
backend/
  app/
    api/
      dependencies/
      routes/
    controller/
    core/
    data/
      rag/
        benign/
        poisoned/
        trusted/
    models/
    services/
    utils/
  data/
    chat_memory.sqlite
    evaluation.sqlite
  tests/
    attacks/
frontend/
  src/
    components/
      admin/
      chat/
      common/
      dashboard/
      logs/
    hooks/
    services/
README.md
requirements.txt
```

## Local Setup

### Backend

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create a local env file:

```bash
copy .env.example .env
```

Run the backend:

```bash
uvicorn backend.app.main:app --reload
```

Backend URLs:

- app: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Frontend

Install dependencies:

```bash
cd frontend
npm install
```

Run the dev server:

```bash
npm run dev
```

Typical frontend URL:

- `http://localhost:5173`

## Environment Variables

The backend supports more settings than the current `.env.example` documents. The source of truth is [backend/app/core/config.py](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/backend/app/core/config.py).

### Model and Auth

```env
HF_MODEL_NAME=microsoft/DialoGPT-medium
HF_PROVIDER=
HF_FALLBACK_PROVIDERS=novita
HF_REQUEST_TIMEOUT_SECONDS=20
API_KEY=
CLIENT_API_KEY=
ADMIN_API_KEY=
```

### Server and Logging

```env
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOG_LEVEL=INFO
```

### Core Security and Traffic Guard

```env
DEFAULT_SECURITY_MODE=Normal
MAX_PROMPT_LENGTH=10000
ENABLE_METRICS_LOGGING=true
MAX_RESPONSE_TOKENS=512
ENABLE_TRAFFIC_GUARD=true
TRUST_PROXY_HEADERS=false
RATE_LIMIT_IP_PER_MINUTE=30
RATE_LIMIT_API_KEY_PER_MINUTE=60
ENABLE_USER_QUOTAS=false
USER_QUOTA_PER_MINUTE=20
USER_QUOTA_PER_DAY=500
CHAT_MAX_IN_FLIGHT=8
CHAT_REQUEST_TIMEOUT_SECONDS=30
SPIKE_ALERT_WINDOW_SECONDS=60
SPIKE_ALERT_THRESHOLD_REQUESTS=50
SPIKE_ALERT_COOLDOWN_SECONDS=300
```

### RAG and Embeddings

```env
VECTOR_DB_PROVIDER=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=rag_chunks
QDRANT_API_KEY=
RAG_ENABLED=true
RAG_TOP_K=8
RAG_MAX_CHUNKS_TO_MODEL=3
RAG_MAX_CHUNKS_PER_SOURCE=2
RAG_MAX_CONTEXT_CHARS=4000
RAG_ENABLE_UPLOAD_INDEXING=true
RAG_UPLOAD_TTL_SECONDS=86400
RAG_QUARANTINE_ON_POISON_SCAN=true
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_NAME=local-hash-embedding-v1
EMBEDDING_BATCH_SIZE=16
EMBEDDING_TIMEOUT_SECONDS=5
EMBEDDING_DIMENSION=128
```

### Conversation Memory and Evaluation Storage

```env
MEMORY_ENABLED=true
MEMORY_DB_PATH=backend/data/chat_memory.sqlite
EVAL_DB_PATH=backend/data/evaluation.sqlite
MEMORY_MAX_TURNS_TO_MODEL=12
MEMORY_MAX_CONTEXT_CHARS=6000
MEMORY_INCLUDE_BLOCKED=true
MEMORY_INCLUDE_SANITIZED=true
```

### Frontend

```env
VITE_API_URL=http://localhost:8000
VITE_CLIENT_API_KEY=
```

## Dependencies

Python dependencies from [requirements.txt](/abs/path/c:/Users/royce/CYBORGS%20PROJECT/CyborgsProtectedLLM/requirements.txt):

- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `python-dotenv`
- `pytest`
- `httpx`
- `Pillow`
- `pymupdf`
- `rapidocr-onnxruntime`
- `qdrant-client`

Frontend dependencies include React 18, TypeScript, Vite, Tailwind CSS, and `lucide-react`.

## Testing and Verification

Backend tests in `backend/tests/` cover:

- auth behavior
- health endpoint behavior
- defense-controller sanitization
- prompt-injection policy behavior across modes
- attachment extraction and prompt-injection detection
- tool authorization and deterministic tool execution
- database demo-tool behavior
- conversation-memory persistence and admin retrieval
- evaluation-store review flows
- abuse-protection metrics and rejection logging
- RAG indexing, retrieval, and quarantine behavior
- Swagger-style red-team policy assertions
- attack-corpus bulk execution

Verification run in this workspace on April 22, 2026:

- `pytest backend/tests -q`
  Result: `50 passed`, `72 failed`
  Primary failure pattern: admin endpoints now require an admin API key, while many tests still call `/admin/*` without the required header and receive `401 Invalid or missing admin API key`.
- `npm run build` in `frontend/`
  Result: failed in this sandbox with `Error: spawn EPERM` while Vite/esbuild attempted to start a child process

## Known Limitations and Current Gaps

- The system is not production hardened; it is a local evaluation/demo environment.
- Traffic protection, vector search state, and metrics are in-memory and single-instance.
- The vector store is Qdrant-shaped but currently implemented as an in-memory compatible backend.
- The embedding system is deterministic local hashing, not a semantic embedding service backed by a model provider.
- The frontend currently uses one API key for both chat and admin routes; separate admin auth requires frontend work.
- The current `.env.example` does not list every supported environment variable from `config.py`.
- The Logs tab shows decision records, not the raw event stream from `/admin/events`.
- Tool coverage is intentionally narrow and heavily restricted.
- `write_file` and `execute_command` are intentionally disabled by policy.
- The `web` tool is limited to an allowlist intended for demo use.
- The `database` tool is a seeded in-memory demo dataset, not an application database.
- The backend CORS policy currently allows all origins.
- Several backend tests are currently out of sync with the stricter admin-auth requirement.

## Intended Use Cases

This repository is useful for:

- prompt-injection defense demos
- RAG poisoning and quarantine experiments
- attachment-security testing
- tool-gating experiments
- red-team or policy-regression exercises
- evaluation workflows using labeled attack/benign review data
- demonstrating lightweight volume-attack protections around an LLM gateway
