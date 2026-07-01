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

Deployment settings live in `scripts/deploy_backend_linux.conf`, which is local
and ignored by git. The tracked template is
`scripts/deploy_backend_linux.example.conf`; if the local config is missing, the
script creates it from the template.

Edit `scripts/deploy_backend_linux.conf`, then run the script directly:

```bash
./scripts/deploy_backend_linux.sh
```

The script creates a virtual environment with `uv venv`, installs Python
dependencies with `uv pip install -e .`, starts or restarts the FastAPI backend
with PM2, writes `/etc/nginx/conf.d/open-artifacts.conf`, validates nginx, and
reloads it. Runtime files are stored under `.deploy/` and `.data/`.

For IP-only deployment, set nginx to match the actual server IP and set the
public URL to the same IP:

```bash
NGINX_SERVER_NAME="203.0.113.10"
PUBLIC_BASE_URL="http://203.0.113.10"
```

If another backend already owns `IP:80`, use a distinct nginx listen port:

```bash
NGINX_SERVER_NAME="203.0.113.10"
NGINX_LISTEN_PORT="8788"
PUBLIC_BASE_URL="http://203.0.113.10:8788"
```

`NGINX_SERVER_NAME="_"` is still supported as a catch-all, but it is fragile
when multiple nginx sites share the same IP and port.

For domain deployment:

```bash
NGINX_SERVER_NAME="artifacts.example.com"
PUBLIC_BASE_URL="https://artifacts.example.com"
```

If the server needs an explicit Python package index, set it in
`scripts/deploy_backend_linux.conf`. Leave these blank to use the server's
existing pip/uv configuration:

```bash
UV_INDEX_URL=""
UV_EXTRA_INDEX_URL=""
UV_INSECURE_HOST=""
```

## Manual Smoke Test

Start the server:

```bash
uv run uvicorn open_artifacts_server.app:app --app-dir server --host 127.0.0.1 --port 8787
```

Publish a payload through stdin so no temporary payload file is needed:

```bash
uv run python open-artifacts/scripts/publish_artifact.py \
  --config open-artifacts/config/open-artifacts.toml \
  --payload - \
  --idempotency-key local-smoke-1 <<'JSON'
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
JSON
```

Open the returned URL and `/gallery`.

If publishing succeeds but the returned viewer URL misses a non-default nginx
port, fix the server deployment config and redeploy:

```bash
NGINX_LISTEN_PORT="8788"
PUBLIC_BASE_URL="http://203.0.113.10:8788"
```
