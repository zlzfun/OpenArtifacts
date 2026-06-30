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

## Linux Backend Deployment

The deployment script assumes `uv`, `sudo`, and `nginx` are present. It can
bootstrap Node and PM2 locally through `uvx nodeenv` when the machine does not
already have `npm` or `pm2`.

Edit `scripts/deploy_backend_linux.conf`, then run the script directly:

```bash
./scripts/deploy_backend_linux.sh
```

The script syncs Python dependencies with `uv`, starts or restarts the FastAPI
backend with PM2, writes `/etc/nginx/conf.d/open-artifacts.conf`, validates
nginx, and reloads it. Runtime files are stored under `.deploy/` and `.data/`.

For IP-only deployment, keep nginx as a catch-all server and set the public URL
to the server IP:

```bash
NGINX_SERVER_NAME="_"
PUBLIC_BASE_URL="http://203.0.113.10"
```

For domain deployment:

```bash
NGINX_SERVER_NAME="artifacts.example.com"
PUBLIC_BASE_URL="https://artifacts.example.com"
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
