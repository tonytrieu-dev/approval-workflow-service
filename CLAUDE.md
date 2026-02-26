# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A standalone approval workflow service for an AI agent platform. When automated agents hit sensitive steps (e.g., terminating cloud resources, resetting credentials), the service pauses execution, requests human approval, and resumes or times out based on the response.

## Commands

Once the project is set up, update this section with the actual commands. Expected commands:

```bash
# Install dependencies
uv sync

# Run the application
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/path/to/test_file.py::test_function_name -v

# Lint / format
uv run ruff check .
uv run ruff format .
```

## Architecture

The service is built around a **pause-and-resume** pattern for long-running agentic workflows:

1. **Approval Request** — An agent calls the service with a description of the action needing approval and a callback mechanism (webhook or polling endpoint).
2. **Pending State** — The request is persisted and an approver is notified (email, Slack, webhook, etc.).
3. **Human Decision** — An approver accepts or rejects via an API endpoint or UI.
4. **Resume or Timeout** — The agent resumes on approval, gets a rejection response, or times out after a configurable window with a defined default behavior.

### Key Design Decisions

- **Async-first**: Uses FastAPI + async database access to handle concurrent approvals without blocking.
- **Durable state**: Approval requests are persisted (SQLite for dev, PostgreSQL for prod) so the service survives restarts.
- **Dependencies**: Defined in `pyproject.toml`; managed exclusively with `uv`.
- **Timeout handling**: Background tasks (via APScheduler or Celery) sweep for expired requests and apply a configured default action (auto-reject or escalate).
- **Idempotency**: Approval request creation is idempotent on a caller-supplied `request_id` to handle retries.

### Module Layout (expected)

```
app/
  main.py          # FastAPI app factory, middleware, router registration
  models.py        # SQLAlchemy ORM models (ApprovalRequest, AuditLog)
  schemas.py       # Pydantic request/response schemas
  routers/
    approvals.py   # POST /approvals, GET /approvals/{id}, POST /approvals/{id}/respond
  services/
    approval.py    # Business logic: create, respond, expire
    notifier.py    # Pluggable notifier (log/email/webhook)
  db.py            # Database session and engine setup
  config.py        # Settings via pydantic-settings / environment variables
tests/
  test_approvals.py
```

### Core Data Model

`ApprovalRequest` — the central entity:
- `id` (UUID)
- `status`: `pending | approved | rejected | expired`
- `action_description`: human-readable description of the action
- `metadata`: JSON blob for arbitrary context
- `requested_by`: identifier of the requesting agent
- `expires_at`: deadline for human response
- `decided_at`, `decided_by`: populated on resolution
- `created_at`

## Coding Principles

### Naming
- No leading underscores on module-level functions. `_name` is reserved for private class members only. Public helper functions use plain names (`apply_lazy_timeout`, not `_apply_lazy_timeout`).
- Names must be **intention-revealing**: a new developer should understand what a variable is and why it exists without needing a comment. If you need a comment to explain the name, rename it instead.
- **No abbreviations**. Write the full word: `workflow_identifier` not `wf_id`, `timeout_minutes` not `timeout_mins`, `requested_by_agent` not `req_agent`.
- **No vague identifiers**: never use `data`, `result`, `temp`, `item`, `handler`, `value`, `obj`, or similar. Name what the thing actually is.
- **Booleans use a question prefix**: `is_`, `has_`, `can_`, `should_`. Example: `is_workflow_pending`, `has_reviewer`, `should_auto_reject`.
- **Functions use verb + noun**: describe the action and its target. `fetch_and_timeout`, `resolve_workflow`, `apply_lazy_timeout` — not `process`, `handle`, `do_thing`.
- **Names must be searchable**: a name that appears once in the codebase should be unique enough to find with a grep. Avoid names so generic they match everywhere.

  ```python
  # bad — vague, requires mental mapping
  result = store.get(wf_id)
  data = replace(rec, status=s)

  # good — self-documenting
  workflow_record = store.get(workflow_id)
  updated_workflow_record = replace(existing_record, status=target_status)
  ```

### Single Responsibility Principle
- Each function does one thing. Route handlers only handle HTTP concerns (parse input, return response). Business logic lives in dedicated helpers. If a function is doing two distinct things, split it.

### Never Nest
- Avoid nested `if` blocks. Use early returns and guard clauses to handle error/edge cases at the top of a function, keeping the happy path flat. Example:
  ```python
  # bad — nested
  def foo(x):
      if x is not None:
          if x > 0:
              return x * 2

  # good — flat
  def foo(x):
      if x is None:
          return None
      if x <= 0:
          return None
      return x * 2
  ```

### Fail Fast
- Validate and reject bad input at the earliest possible point. Don't let invalid state travel deeper into the call stack. Guard clauses at the top of a function (check for `None`, wrong status, missing fields) before doing any real work. This is the same principle as never-nest — the happy path should only be reached once all preconditions are confirmed.

### Key Flows

- **Create**: `POST /approvals` → persists request, fires notification, returns `{id, status: "pending"}`
- **Poll**: `GET /approvals/{id}` → agent polls for status change
- **Respond**: `POST /approvals/{id}/respond` → approver submits `{decision: "approved"|"rejected", decided_by}`
- **Expire**: background job marks `pending` requests past `expires_at` as `expired`
