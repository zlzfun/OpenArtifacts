# Open Artifacts

Open Artifacts is a Skill-first MVP for publishing agent work as versioned,
shareable, live-updating web artifacts.

## MVP Shape

- `open-artifacts/`: preconfigured agent Skill and publish helper.
- `server/`: FastAPI server, SQLite store, viewer, and Gallery.

## Local Development

```bash
uv run pytest
uv run uvicorn open_artifacts_server.app:app --app-dir server --host 127.0.0.1 --port 8787
```

## Manual Smoke Test

Start the server:

```bash
uv run uvicorn open_artifacts_server.app:app --app-dir server --host 127.0.0.1 --port 8787
```

Create `/tmp/open-artifact-payload.json`:

```json
{
  "schema_version": "0.1",
  "title": "Local smoke test",
  "kind": "work-summary",
  "summary": "A local test artifact.",
  "status": "draft",
  "workspace": {"name": "default"},
  "source": {"agent": "manual", "skill_version": "0.1.0", "published_by": "developer"},
  "blocks": [
    {"type": "markdown", "title": "Summary", "content": "The server accepted this artifact."}
  ]
}
```

Publish it:

```bash
uv run python open-artifacts/scripts/publish_artifact.py \
  --config open-artifacts/config/open-artifacts.toml \
  --payload /tmp/open-artifact-payload.json \
  --idempotency-key local-smoke-1
```

Open the returned URL and `/gallery`.
