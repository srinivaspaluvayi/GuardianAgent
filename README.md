# Guardian Agent Supervisor

A supervisor that evaluates agent actions (via API), scores risk with an LLM and policy engine, and either allows, blocks, requests approval, or rewrites risky actions. Redis Streams consumer can be added at deployment for real-time ingestion.

## Tech stack

- **FastAPI** – HTTP API (health, policies, approvals, action evaluate)
- **MongoDB** – Policies, approval requests (flexible schema)
- **Policy rules** – JSON/DSL (allow/deny by action type and resource pattern)
- **LLM** – Risk scoring and safe rewriting (OpenAI)

## Quick start

1. **Install**

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **MongoDB**

   Run MongoDB locally or set the connection URL:

   ```bash
   export MONGODB_URL="mongodb://localhost:27017"
   # optional: export MONGODB_DB_NAME="guardian"
   ```

3. **Run**

   ```bash
   ./run.sh
   # or: .venv/bin/uvicorn app.main:app --reload
   ```

4. **Health**

   ```bash
   curl http://localhost:8000/health
   ```

## API

- `GET /health` – DB status
- `GET /policies`, `POST /policies` – List and create policy rules
- `POST /actions/evaluate` – Submit an action; get policy + LLM decision (allowed / blocked / needs_approval / rewritten)
- `GET /approvals`, `GET /approvals/{id}` – List and get approval requests
- `POST /approvals/{id}/approve`, `POST /approvals/{id}/deny` – Resolve pending approvals

## Policy format

POST a policy with `definition` like:

```json
{
  "rules": [
    { "effect": "deny", "match": { "action_type": "read_file", "resource_pattern": "/etc/*" } },
    { "effect": "allow", "match": { "action_type": "read_file", "resource_pattern": "/tmp/*" } }
  ]
}
```

Resource patterns support glob (`/tmp/*`) or regex (`re:^/etc/.*\\.key$`).


=======
