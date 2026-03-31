# Cyborgs Protected Chat System

FastAPI + React application for evaluating and demonstrating defenses against prompt injection, RAG poisoning, steganographic content, attachment-based attacks, tool abuse, and basic volume attacks.

The repository currently contains:

- A FastAPI backend with a defense pipeline, admin APIs, in-memory metrics, and abuse protection
- A React/Vite frontend for chat, admin mode control, dashboard metrics, and decision logs
- A backend test suite covering auth, security decisions, tools, attachments, abuse protection, and attack-corpus runs

## What The Project Does

The backend accepts chat requests, runs them through a layered security pipeline, then either:

- `ALLOW`s the request
- `SANITIZE`s the prompt/context before model execution
- `BLOCK`s the request before it reaches the model

The pipeline currently includes:

- Prompt injection detection
- RAG context retrieval and validation
- Tool request detection and authorization
- Attachment validation, extraction, and signal analysis
- Steganography checks
- Risk scoring and mode-based policy decisions
- In-memory rate limiting and concurrency protection on `/chat/`

The frontend exposes that system through four tabs:

- `Chat`: secure chat UI with tool toggles and file/image attachment upload
- `Dashboard`: aggregated metrics and KPI cards
- `Admin`: global security mode selector
- `Logs`: recent decision records

## Current Architecture

### Backend

Main backend areas:

- `backend/app/api/routes`
  - `chat.py`: protected chat endpoint
  - `admin.py`: mode, events, decisions, metrics
  - `health.py`: health check
- `backend/app/controller`
  - `defense_controller.py`: orchestrates the full protection pipeline
- `backend/app/services`
  - `input_content_checker.py`: prompt injection and suspicious pattern analysis
  - `policy_engine.py`: risk scoring and allow/sanitize/block decisions
  - `rag_manager.py`: retrieves local benign/poisoned text corpus
  - `rag_content_validator.py`: validates retrieved context before use
  - `tool_gatekeeper.py`: tool detection and authorization policy
  - `tool_plugins.py`: calculator, file reader, web, database, and deny-by-policy write/command plugins
  - `attachment_manager.py`: attachment validation, extraction, and signal aggregation
  - `steganography_detector.py`: hidden-content signal checks
  - `metrics_logger.py`: in-memory events, decisions, admin KPIs
  - `traffic_guard.py`: in-memory rate limiting, quota enforcement, concurrency cap, and spike alerts
  - `llm_service.py`: Hugging Face router integration with deterministic fallback
- `backend/app/data/rag`
  - benign and poisoned sample RAG documents used by tests and demo flows

### Frontend

Main frontend areas:

- `frontend/src/App.tsx`: top-level tabbed app shell
- `frontend/src/hooks/useChat.ts`: chat request lifecycle
- `frontend/src/hooks/useAdmin.ts`: admin mode + metrics loading
- `frontend/src/services/api.ts`: backend API client
- `frontend/src/components/chat`: chat window, composer, response rendering, tool and RAG badges
- `frontend/src/components/dashboard`: dashboard KPI cards
- `frontend/src/components/admin`: security mode selector
- `frontend/src/components/logs`: recent decision table

## Security Features Implemented

### 1. Prompt Injection Protection

The system analyzes prompts for suspicious patterns such as:

- instruction override attempts
- role manipulation
- prompt leakage attempts
- encoding/obfuscation indicators
- multi-step and structural attack patterns

The result feeds into risk scoring and mode-specific policy decisions.

### 2. Security Modes

The backend uses a single global security mode:

- `Off`
- `Weak`
- `Normal`
- `Strong`

The request body does not control the active mode. `/chat/` always uses the global mode from the admin state.

### 3. RAG Validation

The project includes a local document corpus with both benign and poisoned documents. When prompts trigger retrieval behavior, the backend:

- retrieves matching local contexts
- validates them
- strips unsafe content before the model sees it
- records whether context was used and whether it validated safely

### 4. Tool Abuse Prevention

Tool intent can be inferred from the prompt or passed explicitly in `requested_tools`.

Supported tool names:

- `calculator`
- `file_reader`
- `web`
- `database`
- `write_file`
- `execute_command`

Current behavior:

- `write_file` and `execute_command` are deny-by-policy plugins
- `file_reader`, `web`, and `database` are mode- and risk-gated
- `calculator` is the most permissive tool
- tool execution is audited and time-bounded

### 5. Attachment Handling

The chat API supports structured attachments with base64 content. The pipeline validates and analyzes:

- plain text
- CSV
- JSON
- PDF
- PNG
- JPEG
- WebP

Attachment flow:

- validate MIME and payload
- extract bounded text previews
- use direct PDF text extraction where possible
- fall back to OCR for PDFs/images when dependencies are available
- analyze extracted text for risky signals
- allow, flag, or block the attachment

### 6. Volume-Attack Protection

`/chat/` now has in-memory abuse protection:

- per-IP rate limit
- per-API-key rate limit
- optional per-user minute and daily quotas
- global in-flight request cap
- hard request timeout
- spike detection surfaced through admin metrics/events

Important limitation:

- this is single-instance protection only
- counters live in memory
- limits are not globally correct across multiple workers or multiple app instances

## API Summary

### Public / Main Routes

- `GET /`
- `GET /health/`
- `POST /chat/`

### Admin Routes

- `POST /admin/mode`
- `GET /admin/mode`
- `GET /admin/events`
- `GET /admin/events/old`
- `GET /admin/decisions`
- `GET /admin/metrics`

## Chat Request Contract

`POST /chat/` expects:

```json
{
  "user_id": "demo-user",
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
  "requested_tools": ["file_reader"]
}
```

Successful responses include:

- decision and risk level
- trace ID
- tool request / allow results
- RAG usage flags
- attachment analysis results
- whether the model was called

### Error Behavior

Authentication failures:

- `401` when `X-API-Key` is missing or invalid

Volume/overload failures:

- `429` for rate limits, quotas, or chat capacity exhaustion
- `504` for chat processing timeouts

## Admin Metrics and Logs

The backend maintains in-memory events and decisions and exposes them through admin routes.

Current metrics include:

- total chat traces
- decision distribution
- risk distribution
- attack-success proxy
- false-positive proxy
- abuse-protection limits
- active in-flight requests
- recent rejections
- cumulative rejection totals
- active and recent spike alerts

Current log/event categories include:

- chat requests
- risk scoring
- tool checks
- RAG checks
- attachment checks
- timeout events
- rate limit and quota rejections
- concurrency rejections
- spike alerts

## Frontend Behavior

The frontend is a thin client over the backend API.

What it currently supports:

- sending prompts to `/chat/`
- selecting requested tools in the UI
- attaching files and images and sending them as base64 payloads
- switching the global security mode
- showing KPI cards from `/admin/metrics`
- showing recent decision records from `/admin/decisions`
- polling health status

Important frontend note:

- the `Logs` tab currently renders decision records, not raw `/admin/events` entries

## Local Setup

## 1. Backend

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` from the example:

```bash
copy .env.example .env
```

Run the backend:

```bash
uvicorn backend.app.main:app --reload
```

Backend default URL:

```text
http://localhost:8000
```

Swagger / OpenAPI:

```text
http://localhost:8000/docs
```

## 2. Frontend

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the frontend:

```bash
npm run dev
```

Typical frontend dev URL:

```text
http://localhost:5173
```

## Environment Variables

Current backend `.env` surface from `.env.example`:

```env
HF_MODEL_NAME=microsoft/DialoGPT-medium
HF_PROVIDER=
API_KEY=your_hugging_face_token_here
CLIENT_API_KEY=choose_a_separate_client_api_key_here
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
DEBUG=true
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
CHAT_REQUEST_TIMEOUT_SECONDS=12
SPIKE_ALERT_WINDOW_SECONDS=60
SPIKE_ALERT_THRESHOLD_REQUESTS=50
SPIKE_ALERT_COOLDOWN_SECONDS=300
```

Frontend expects:

- `VITE_API_URL`
- `VITE_CLIENT_API_KEY`

## Model Behavior

The backend can operate in two modes:

- real backend mode when `API_KEY` is configured for Hugging Face Router
- deterministic fallback mode when no backend key is present

The deterministic fallback is intentional and helps keep evaluation/test output stable.

## Test Coverage

The backend test suite currently covers:

- auth behavior
- security decisions across modes
- sanitize flow
- tool authorization and deterministic tool execution
- attachment extraction and prompt-injection detection through attachments
- abuse protection and volume controls
- Swagger/manual red-team policy expectations
- bulk attack corpus execution

Recent verification in this workspace:

- `pytest backend/tests -q`
- result: `90 passed`

## Known Limitations

- Abuse protection is in-memory and single-instance only
- Admin routes are not protected by separate admin authentication
- The frontend logs view shows decision records rather than the raw event stream
- Web tool execution is restricted to a tiny allowlist
- Database access is a seeded in-memory demo data source, not a production data layer
- Write-file and command-execution tools are intentionally disabled

## Repository Structure

```text
backend/
  app/
    api/
    controller/
    core/
    data/
    models/
    services/
    utils/
  tests/
frontend/
  src/
README.md
requirements.txt
```

## Purpose

This repository is best understood as a protected-chat demo and evaluation environment rather than a finished production platform. It is useful for:

- red-team exercises
- security-mode comparisons
- attachment attack experiments
- RAG poisoning demonstrations
- testing tool-gating behavior
- experimenting with lightweight volume-attack defenses
