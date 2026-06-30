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
- `chart`: `{ "type": "chart", "title": "Test trend", "chart_type": "bar", "series": [{"label": "Unit", "value": 42}], "caption": "Tests passing by category." }`
- `image`: `{ "type": "image", "title": "Reference screenshot", "src": "https://example.com/screenshot.png", "alt": "Reference screenshot", "caption": "User-provided visual reference." }`
- `svg`: `{ "type": "svg", "title": "System flow", "svg": "<svg viewBox=\"0 0 120 40\" role=\"img\" aria-label=\"System flow\"><rect x=\"4\" y=\"4\" width=\"40\" height=\"20\"></rect></svg>", "caption": "Generated diagram." }`
- `callout`: `{ "type": "callout", "tone": "decision", "title": "Decision", "content": "Use the Editorial Lab Notebook style." }`
- `stat-grid`: `{ "type": "stat-grid", "title": "Run summary", "stats": [{"label": "Tests", "value": "24", "detail": "all passing"}] }`
- `flow`: `{ "type": "flow", "title": "Publishing loop", "items": [{"label": "Agent", "detail": "Builds payload"}] }`

Prefer visual blocks when they make the artifact easier to understand: use `chart` for quantitative comparisons, `flow` for processes or architecture, `stat-grid` for key figures, `image` for browser-visible screenshots or generated images, `svg` for compact generated diagrams, and `callout` for decisions, risks, outcomes, or next steps.

`image.src` must be browser-visible: use `http`/`https`, a relative URL already served by the Open Artifacts server, or a small raster `data:image/png`, `data:image/jpeg`, `data:image/gif`, or `data:image/webp` payload. Local filesystem paths from a conversation are not automatically visible in the browser. Put generated SVG markup in an `svg` block instead of an `image` data URL.

`svg` is restricted to safe inline SVG only. Do not include scripts, event handlers, `foreignObject`, external references, or unsafe URL protocols.

Do not include raw HTML or JavaScript.
