# Artifact Schema

Use JSON payloads with `schema_version: "0.1"`.

Required top-level fields:

- `title`: short artifact title.
- `kind`: one of `work-summary`, `investigation`, `walkthrough`, `checklist`, `dashboard`.
- `summary`: short human-readable summary.
- `status`: `draft`, `ready`, or another short status string.
- `workspace.name`: workspace identifier.
- `source.agent`: agent name.
- `blocks`: ordered list of supported blocks.

Supported blocks:

- `markdown`: `{ "type": "markdown", "title": "Summary", "content": "The investigation found one failing test." }`
- `timeline`: `{ "type": "timeline", "title": "Timeline", "items": [{"time": "2026-06-29T10:00:00Z", "label": "Started", "detail": "The agent reproduced the issue."}] }`
- `code-reference`: `{ "type": "code-reference", "title": "Relevant code", "references": [{"path": "src/auth.py", "start_line": 1, "end_line": 2, "label": "Session check"}] }`
- `command-output`: `{ "type": "command-output", "title": "Test output", "command": "pytest tests/test_auth.py", "exit_code": 0, "content": "1 passed" }`
- `diff`: `{ "type": "diff", "title": "Patch", "content": "--- a/src/auth.py\n+++ b/src/auth.py" }`
- `checklist`: `{ "type": "checklist", "title": "Readiness", "items": [{"label": "Tests pass", "state": "done", "detail": "Auth tests passed."}] }`
- `metric`: `{ "type": "metric", "title": "Error rate", "value": "0.2%", "trend": "down", "detail": "Error rate recovered after the fix." }`
- `table`: `{ "type": "table", "title": "Dependencies", "columns": ["Package"], "rows": [["fastapi"]] }`

Do not include raw HTML or JavaScript.
