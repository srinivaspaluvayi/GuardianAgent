# Guardian Supervisor

A policy and security supervisor for AI agents. Guardian evaluates action intents (e.g. HTTP requests, email sends, Slack posts) and returns a decision: **ALLOW**, **REWRITE**, **REQUIRE_APPROVAL**, or **BLOCK**, using rule-based policies plus optional LLM risk scoring.

## Features

- **Policy engine** — Match on action type, tool, target, data classification, and allowlists (e.g. external domains). Effects: ALLOW, BLOCK, REQUIRE_APPROVAL, REWRITE with configurable priority and risk boost.
- **Security classifiers** — Lightweight regex-based detection of PII (SSN, email) and secrets (API keys) in action payloads; results feed into policy matching.
- **Optional LLM risk scoring** — Uses Ollama (local) or any OpenAI-compatible API to produce a 0–1 risk score and reasons; combined with policy hits for the final decision.
- **Dual evaluation modes**  
  - **Sync** — `POST /v1/evaluate`: in-process evaluation, no Redis (ideal for API/Postman testing).  
  - **Async** — `POST /v1/decide`: submit intent to Redis; a worker consumes, evaluates, persists to DB, and emits to `action.decision` stream.
- **Approvals** — Pending approvals list and approve/deny endpoints; decisions are emitted to an approval stream for downstream consumers.
- **Policies CRUD** — List, create, get, delete policies via `/v1/policies`; policies are stored in the database (SQLite or Postgres).

## Architecture

```
Agent → POST /v1/decide (intent) → Redis stream "action.intent"
                                        ↓
                    Guardian worker (consumer) → classify + policy engine + LLM score
                                        ↓
                    DB (actions, decisions, approvals) + Redis "action.decision"
```

For synchronous testing without Redis:

```
Client → POST /v1/evaluate (intent) → in-process classify + policies + LLM → decision JSON
```

## Requirements

- Python 3.10+
- Redis (for `/decide` and the background worker)
- SQLite (default) or PostgreSQL
- Optional: [Ollama](https://ollama.ai) or another OpenAI-compatible API for LLM risk scoring

## Dependencies

Install with:

```bash
pip install -r requirements.txt
```

Main packages:

| Package | Purpose |
|---------|---------|
| fastapi, uvicorn | API server |
| pydantic, pydantic-settings | Config and request/response models |
| redis | Redis Streams (intent/decision queues) |
| sqlalchemy | Database (SQLite/Postgres) |
| psycopg2-binary | PostgreSQL driver |
| alembic | DB migrations (production) |
| openai | LLM client (Ollama/OpenAI-compatible) |
| pytest, pytest-asyncio, httpx | Tests |
| deepeval | Guardian compliance tests |

## Setup

1. **Clone and create a virtualenv**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Environment**

   Copy or create a `.env` in the project root. All settings are optional and have defaults; use the `GUARDIAN_` prefix to override:

   | Variable | Default | Description |
   |----------|---------|-------------|
   | `GUARDIAN_DATABASE_URL` | `sqlite:///./guardian.db` | SQLAlchemy URL (use Postgres in production). |
   | `GUARDIAN_REDIS_URL` | `redis://localhost:6379/0` | Redis URL for streams. |
   | `GUARDIAN_LLM_BASE_URL` | (empty) | e.g. `http://localhost:11434/v1` for Ollama. |
   | `GUARDIAN_LLM_MODEL` | `llama3.2:3b` | Model name for risk scoring. |
   | `GUARDIAN_LLM_API_KEY` | (empty) | API key for OpenAI-compatible APIs; not needed for Ollama. |

3. **Database and policies**

   The app creates tables on startup. Seed default policies:

   ```bash
   python scripts/seed_policies.py
   ```

4. **Run the API**

   ```bash
   ./run.sh
   ```

   Or manually:

   ```bash
   export PYTHONPATH="${PWD}:${PYTHONPATH}"
   uvicorn app.main:app --reload --port 8000
   ```

   Docs: http://localhost:8000/docs

5. **Run the worker (optional, for async flow)**

   With Redis running:

   ```bash
   python -m app.streams.consumer
   ```

   This consumes `action.intent`, evaluates each intent, writes to the DB, and publishes to `action.decision`.

## API overview

| Endpoint | Description |
|----------|-------------|
| `GET /v1/health` | Health check. |
| `POST /v1/evaluate` | Synchronous evaluation: send intent, get decision (no Redis). |
| `POST /v1/decide` | Submit intent; returns 202 and `event_id`; decision appears on `action.decision` stream (requires Redis). |
| `GET /v1/policies` | List policies. |
| `POST /v1/policies` | Create policy. |
| `GET /v1/policies/{policy_id}` | Get policy. |
| `DELETE /v1/policies/{policy_id}` | Delete policy. |
| `GET /v1/approvals/pending` | List pending approvals. |
| `POST /v1/approvals/{id}/approve` | Approve. |
| `POST /v1/approvals/{id}/deny` | Deny. |

## Evaluate request/response

**Request** (`POST /v1/evaluate`): same shape as an action intent — `trace_id`, `action` (type, tool, target, method?, args), `context` (e.g. user_prompt, data_classification, workspace).

**Response**: `decision` (ALLOW | REWRITE | BLOCK | REQUIRE_APPROVAL), `risk` (score, severity, reasons), `policy_hits`, optional `rewrite`, `approval_required`.

## Policy shape

Policies are stored as JSON in the DB. Example (from seed):

- `policy_id`, `version`, `priority`, `enabled`
- `match`: dict of field path → value or list of allowed values (e.g. `action.type`, `context.data_classification`)
- `conditions`: list of `in_allowlist` / `not_in_allowlist` (e.g. `action.target_domain` vs `EXTERNAL_DOMAINS_ALLOWLIST`)
- `effect`: ALLOW | BLOCK | REQUIRE_APPROVAL | REWRITE
- `risk_boost`, `message`

Allowlists (e.g. `EXTERNAL_DOMAINS_ALLOWLIST`) are defined in `app/policy/allowlists.py` and resolved when loading policies.

## Project layout

```
app/
  main.py              # FastAPI app, lifespan, routes
  config.py            # Settings (env, GUARDIAN_*)
  models.py            # Pydantic event schemas
  db.py                # SQLAlchemy engine, session, init_db
  db_models.py         # Action, Decision, Approval, Policy
  api/                 # Routers: health, evaluate, decide, policies, approvals
  policy/              # engine, store, allowlists
  security/            # classifiers (PII/secret detection)
  llm/                 # scorer (risk score), rewrite (stub)
  streams/             # redis_streams, consumer (worker)
scripts/
  seed_policies.py     # Insert default policies
tests/
  unit/                # Policy engine tests
  deepeval/            # Guardian compliance tests
```

## Tests

```bash
pytest
```

## License

MIT. See [LICENSE](LICENSE).
