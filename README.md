# Open Artifacts

Open Artifacts is a Skill-first MVP for publishing agent work as versioned,
shareable, live-updating web artifacts.

## MVP Shape

- `skill/`: preconfigured agent Skill and publish helper.
- `server/`: FastAPI server, SQLite store, viewer, and Gallery.

## Local Development

```bash
uv run pytest
uv run uvicorn open_artifacts_server.app:app --app-dir server --host 127.0.0.1 --port 8787
```
