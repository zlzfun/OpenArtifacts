# Open Artifacts Skill-First MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Skill-first Open Artifacts MVP: a preconfigured publishing Skill plus a FastAPI/SQLite server that renders safe, versioned, live-updating Artifact pages and a Gallery.

**Architecture:** The Skill is a publishing adapter that turns agent-visible context into a structured payload and calls the server. The FastAPI server owns validation, storage, version history, restore, SSE update events, viewer rendering, Gallery, and simple token-based MVP access control. Viewer and Gallery use server-rendered HTML, plain CSS, and vanilla JavaScript.

**Tech Stack:** Python, FastAPI, SQLite, Jinja2 templates, vanilla JavaScript, pytest, FastAPI TestClient.

---

## File Structure

- Create: `pyproject.toml` - project metadata, dependencies, test configuration, console scripts.
- Create: `README.md` - local development and MVP usage.
- Create: `server/open_artifacts_server/__init__.py` - package marker.
- Create: `server/open_artifacts_server/config.py` - server settings loaded from environment with local defaults.
- Create: `server/open_artifacts_server/schema.py` - Artifact payload validation and sanitization constraints.
- Create: `server/open_artifacts_server/db.py` - SQLite connection, schema creation, transaction helper.
- Create: `server/open_artifacts_server/store.py` - persistence operations for artifacts, versions, and publish events.
- Create: `server/open_artifacts_server/app.py` - FastAPI app, API routes, viewer routes, SSE.
- Create: `server/open_artifacts_server/templates/viewer.html` - Artifact viewer shell.
- Create: `server/open_artifacts_server/templates/gallery.html` - Gallery shell.
- Create: `server/open_artifacts_server/static/app.js` - viewer/Gallery client fetch, render, SSE refresh.
- Create: `server/open_artifacts_server/static/styles.css` - restrained operational UI styling.
- Create: `tests/server/test_schema.py` - payload validation tests.
- Create: `tests/server/test_store.py` - SQLite persistence and version tests.
- Create: `tests/server/test_api.py` - publish/read/restore/list/auth tests.
- Create: `tests/server/test_viewer.py` - viewer/Gallery route and SSE behavior tests.
- Create: `skill/SKILL.md` - agent-facing workflow instructions.
- Create: `skill/agents/openai.yaml` - Skill display metadata.
- Create: `skill/config/open-artifacts.toml` - open-source localhost config.
- Create: `skill/references/artifact-schema.md` - Skill-readable schema guide.
- Create: `skill/references/publishing-protocol.md` - Skill-readable publish protocol.
- Create: `skill/scripts/publish_artifact.py` - deterministic publish helper.
- Create: `tests/skill/test_publish_artifact.py` - helper config, validation, and HTTP behavior tests.

### Task 1: Project Scaffold And Test Harness

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `server/open_artifacts_server/__init__.py`
- Create: `server/open_artifacts_server/config.py`
- Create: `tests/server/test_config.py`

- [ ] **Step 1: Write failing config tests**

Create `tests/server/test_config.py`:

```python
from open_artifacts_server.config import Settings


def test_settings_have_local_dev_defaults():
    settings = Settings()

    assert settings.database_path.endswith("open-artifacts.sqlite3")
    assert settings.publish_token == "dev-token"
    assert settings.public_base_url == "http://localhost:8787"


def test_settings_accept_overrides():
    settings = Settings(
        database_path="/tmp/custom.sqlite3",
        publish_token="secret",
        public_base_url="https://artifacts.example.com",
    )

    assert settings.database_path == "/tmp/custom.sqlite3"
    assert settings.publish_token == "secret"
    assert settings.public_base_url == "https://artifacts.example.com"
```

- [ ] **Step 2: Add project metadata**

Create `pyproject.toml`:

```toml
[project]
name = "open-artifacts"
version = "0.1.0"
description = "Skill-first open artifact publishing server and Skill helper"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "uvicorn>=0.30",
  "jinja2>=3.1",
  "pydantic>=2.7",
  "python-multipart>=0.0.9"
]

[project.optional-dependencies]
test = [
  "pytest>=8.2",
  "httpx>=0.27"
]

[project.scripts]
open-artifacts-server = "open_artifacts_server.app:main"

[tool.pytest.ini_options]
pythonpath = ["server", "skill/scripts"]
testpaths = ["tests"]
```

- [ ] **Step 3: Add config implementation**

Create `server/open_artifacts_server/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `server/open_artifacts_server/config.py`:

```python
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_path: str = os.environ.get(
        "OPEN_ARTIFACTS_DB", "/tmp/open-artifacts.sqlite3"
    )
    publish_token: str = os.environ.get("OPEN_ARTIFACTS_PUBLISH_TOKEN", "dev-token")
    public_base_url: str = os.environ.get(
        "OPEN_ARTIFACTS_PUBLIC_BASE_URL", "http://localhost:8787"
    )
```

Create `README.md`:

````markdown
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
````

- [ ] **Step 4: Run tests and verify scaffold passes**

Run:

```bash
uv run pytest tests/server/test_config.py -v
```

Expected: `2 passed`.

- [ ] **Step 5: Commit scaffold**

```bash
git add pyproject.toml README.md server/open_artifacts_server/__init__.py server/open_artifacts_server/config.py tests/server/test_config.py
git commit -m "chore: scaffold open artifacts project"
```

### Task 2: Payload Schema Validation

**Files:**
- Create: `server/open_artifacts_server/schema.py`
- Create: `tests/server/test_schema.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/server/test_schema.py`:

```python
import pytest

from open_artifacts_server.schema import validate_payload


def base_payload():
    return {
        "schema_version": "0.1",
        "title": "Auth investigation",
        "kind": "investigation",
        "summary": "Short summary",
        "status": "draft",
        "workspace": {"name": "payments", "branch": "main"},
        "source": {"agent": "codex", "skill_version": "0.1.0"},
        "blocks": [
            {"type": "markdown", "title": "Summary", "content": "No raw HTML"},
            {
                "type": "timeline",
                "title": "Timeline",
                "items": [{"time": "2026-06-29T10:00:00Z", "label": "Started"}],
            },
            {
                "type": "code-reference",
                "title": "Relevant code",
                "references": [{"path": "src/auth.py", "start_line": 1, "end_line": 5}],
            },
        ],
    }


def test_valid_payload_round_trips():
    payload = validate_payload(base_payload())

    assert payload["title"] == "Auth investigation"
    assert payload["blocks"][0]["type"] == "markdown"


def test_rejects_unknown_kind():
    payload = base_payload()
    payload["kind"] = "incident-postmortem"

    with pytest.raises(ValueError, match="Unsupported artifact kind"):
        validate_payload(payload)


def test_rejects_raw_html_in_markdown():
    payload = base_payload()
    payload["blocks"][0]["content"] = "<script>alert(1)</script>"

    with pytest.raises(ValueError, match="Raw HTML is not allowed"):
        validate_payload(payload)


def test_rejects_unknown_block_type():
    payload = base_payload()
    payload["blocks"] = [{"type": "html", "content": "<b>bad</b>"}]

    with pytest.raises(ValueError, match="Unsupported block type"):
        validate_payload(payload)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/server/test_schema.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `validate_payload`.

- [ ] **Step 3: Implement schema validation**

Create `server/open_artifacts_server/schema.py`:

```python
from copy import deepcopy
import re
from typing import Any


SUPPORTED_KINDS = {"work-summary", "investigation", "walkthrough", "checklist", "dashboard"}
SUPPORTED_BLOCKS = {
    "markdown",
    "timeline",
    "code-reference",
    "command-output",
    "diff",
    "checklist",
    "metric",
    "table",
}
BLOCKED_HTML = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def validate_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(raw)

    if payload.get("schema_version") != "0.1":
        raise ValueError("Unsupported schema_version")
    if not payload.get("title"):
        raise ValueError("Artifact title is required")
    if payload.get("kind") not in SUPPORTED_KINDS:
        raise ValueError("Unsupported artifact kind")
    if not isinstance(payload.get("blocks"), list):
        raise ValueError("Artifact blocks must be a list")

    for index, block in enumerate(payload["blocks"]):
        if not isinstance(block, dict):
            raise ValueError(f"Block {index} must be an object")
        block_type = block.get("type")
        if block_type not in SUPPORTED_BLOCKS:
            raise ValueError("Unsupported block type")
        if block_type == "markdown" and BLOCKED_HTML.search(block.get("content", "")):
            raise ValueError("Raw HTML is not allowed")

    return payload
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
uv run pytest tests/server/test_schema.py -v
```

Expected: `4 passed`.

- [ ] **Step 5: Commit schema validation**

```bash
git add server/open_artifacts_server/schema.py tests/server/test_schema.py
git commit -m "feat: validate artifact payload schema"
```

### Task 3: SQLite Store And Version History

**Files:**
- Create: `server/open_artifacts_server/db.py`
- Create: `server/open_artifacts_server/store.py`
- Create: `tests/server/test_store.py`

- [ ] **Step 1: Write failing store tests**

Create `tests/server/test_store.py`:

```python
from open_artifacts_server.db import init_db
from open_artifacts_server.store import ArtifactStore


def payload(title="First"):
    return {
        "schema_version": "0.1",
        "title": title,
        "kind": "work-summary",
        "summary": "summary",
        "status": "draft",
        "workspace": {"name": "default"},
        "source": {"agent": "test"},
        "blocks": [{"type": "markdown", "title": "Summary", "content": "hello"}],
    }


def test_publish_creates_artifact_and_first_version(tmp_path):
    db_path = tmp_path / "artifacts.sqlite3"
    init_db(str(db_path))
    store = ArtifactStore(str(db_path), public_base_url="http://localhost:8787")

    result = store.publish(
        artifact_id=None,
        visibility="private",
        payload=payload(),
        created_by="tester",
        organization="local-dev",
        workspace="default",
        idempotency_key="first",
    )

    assert result["version"] == 1
    assert result["url"].endswith(f"/a/{result['artifact_id']}")
    assert store.get_artifact(result["artifact_id"])["current_version"] == 1


def test_publish_existing_artifact_appends_version(tmp_path):
    db_path = tmp_path / "artifacts.sqlite3"
    init_db(str(db_path))
    store = ArtifactStore(str(db_path), public_base_url="http://localhost:8787")

    first = store.publish(None, "private", payload("First"), "tester", "local-dev", "default", "first")
    second = store.publish(first["artifact_id"], "private", payload("Second"), "tester", "local-dev", "default", "second")

    versions = store.list_versions(first["artifact_id"])
    current = store.get_current_payload(first["artifact_id"])

    assert second["version"] == 2
    assert [version["version_number"] for version in versions] == [1, 2]
    assert current["title"] == "Second"


def test_restore_creates_new_current_version_from_old_payload(tmp_path):
    db_path = tmp_path / "artifacts.sqlite3"
    init_db(str(db_path))
    store = ArtifactStore(str(db_path), public_base_url="http://localhost:8787")

    first = store.publish(None, "private", payload("First"), "tester", "local-dev", "default", "first")
    store.publish(first["artifact_id"], "private", payload("Second"), "tester", "local-dev", "default", "second")
    restored = store.restore(first["artifact_id"], version_number=1, created_by="tester")

    assert restored["version"] == 3
    assert store.get_current_payload(first["artifact_id"])["title"] == "First"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/server/test_store.py -v
```

Expected: FAIL with missing `db` or `store` modules.

- [ ] **Step 3: Implement database schema**

Create `server/open_artifacts_server/db.py`:

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def connect(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path: str) -> None:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              kind TEXT NOT NULL,
              owner TEXT NOT NULL,
              organization TEXT NOT NULL,
              workspace TEXT NOT NULL,
              visibility TEXT NOT NULL,
              status TEXT NOT NULL,
              current_version INTEGER NOT NULL,
              archived_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS artifact_versions (
              id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
              version_number INTEGER NOT NULL,
              payload TEXT NOT NULL,
              summary TEXT,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(artifact_id, version_number)
            );

            CREATE TABLE IF NOT EXISTS publish_events (
              id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
              version_number INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              idempotency_key TEXT,
              created_at TEXT NOT NULL,
              UNIQUE(idempotency_key)
            );
            """
        )


@contextmanager
def transaction(database_path: str) -> Iterator[sqlite3.Connection]:
    with connect(database_path) as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
```

- [ ] **Step 4: Implement store**

Create `server/open_artifacts_server/store.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid
from typing import Any

from .db import connect, transaction
from .schema import validate_payload


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(row):
    return dict(row) if row is not None else None


class ArtifactStore:
    def __init__(self, database_path: str, public_base_url: str) -> None:
        self.database_path = database_path
        self.public_base_url = public_base_url.rstrip("/")

    def publish(
        self,
        artifact_id: str | None,
        visibility: str,
        payload: dict[str, Any],
        created_by: str,
        organization: str,
        workspace: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = validate_payload(payload)
        timestamp = now()
        with transaction(self.database_path) as db:
            if artifact_id is None:
                artifact_id = f"art_{uuid.uuid4().hex[:12]}"
                version = 1
                db.execute(
                    """
                    INSERT INTO artifacts
                    (id, title, kind, owner, organization, workspace, visibility, status, current_version, archived_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                    """,
                    (
                        artifact_id,
                        payload["title"],
                        payload["kind"],
                        created_by,
                        organization,
                        workspace,
                        visibility,
                        payload.get("status", "draft"),
                        version,
                        timestamp,
                        timestamp,
                    ),
                )
            else:
                current = db.execute(
                    "SELECT current_version FROM artifacts WHERE id = ?", (artifact_id,)
                ).fetchone()
                if current is None:
                    raise KeyError("Artifact not found")
                version = int(current["current_version"]) + 1
                db.execute(
                    """
                    UPDATE artifacts
                    SET title = ?, kind = ?, visibility = ?, status = ?, current_version = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        payload["title"],
                        payload["kind"],
                        visibility,
                        payload.get("status", "draft"),
                        version,
                        timestamp,
                        artifact_id,
                    ),
                )

            db.execute(
                """
                INSERT INTO artifact_versions
                (id, artifact_id, version_number, payload, summary, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"ver_{uuid.uuid4().hex[:12]}",
                    artifact_id,
                    version,
                    json.dumps(payload, ensure_ascii=False),
                    payload.get("summary"),
                    created_by,
                    timestamp,
                ),
            )
            db.execute(
                """
                INSERT INTO publish_events
                (id, artifact_id, version_number, event_type, idempotency_key, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"evt_{uuid.uuid4().hex[:12]}",
                    artifact_id,
                    version,
                    "published",
                    idempotency_key,
                    timestamp,
                ),
            )
        return {
            "artifact_id": artifact_id,
            "version": version,
            "url": f"{self.public_base_url}/a/{artifact_id}",
            "gallery_url": f"{self.public_base_url}/gallery",
        }

    def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        with connect(self.database_path) as db:
            row = db.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        if row is None:
            raise KeyError("Artifact not found")
        return row_to_dict(row)

    def get_current_payload(self, artifact_id: str) -> dict[str, Any]:
        artifact = self.get_artifact(artifact_id)
        with connect(self.database_path) as db:
            row = db.execute(
                """
                SELECT payload FROM artifact_versions
                WHERE artifact_id = ? AND version_number = ?
                """,
                (artifact_id, artifact["current_version"]),
            ).fetchone()
        return json.loads(row["payload"])

    def list_versions(self, artifact_id: str) -> list[dict[str, Any]]:
        with connect(self.database_path) as db:
            rows = db.execute(
                """
                SELECT id, artifact_id, version_number, summary, created_by, created_at
                FROM artifact_versions
                WHERE artifact_id = ?
                ORDER BY version_number
                """,
                (artifact_id,),
            ).fetchall()
        return [row_to_dict(row) for row in rows]

    def restore(self, artifact_id: str, version_number: int, created_by: str) -> dict[str, Any]:
        with connect(self.database_path) as db:
            row = db.execute(
                "SELECT payload FROM artifact_versions WHERE artifact_id = ? AND version_number = ?",
                (artifact_id, version_number),
            ).fetchone()
        if row is None:
            raise KeyError("Version not found")
        artifact = self.get_artifact(artifact_id)
        return self.publish(
            artifact_id=artifact_id,
            visibility=artifact["visibility"],
            payload=json.loads(row["payload"]),
            created_by=created_by,
            organization=artifact["organization"],
            workspace=artifact["workspace"],
            idempotency_key=f"restore-{artifact_id}-{version_number}-{uuid.uuid4().hex}",
        )
```

- [ ] **Step 5: Run store tests**

Run:

```bash
uv run pytest tests/server/test_store.py -v
```

Expected: `3 passed`.

- [ ] **Step 6: Commit store**

```bash
git add server/open_artifacts_server/db.py server/open_artifacts_server/store.py tests/server/test_store.py
git commit -m "feat: store artifact versions in sqlite"
```

### Task 4: Publish And Read API

**Files:**
- Create: `server/open_artifacts_server/app.py`
- Create: `tests/server/test_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/server/test_api.py`:

```python
from fastapi.testclient import TestClient

from open_artifacts_server.app import create_app
from open_artifacts_server.config import Settings


def valid_payload(title="Example"):
    return {
        "schema_version": "0.1",
        "title": title,
        "kind": "work-summary",
        "summary": "summary",
        "status": "draft",
        "workspace": {"name": "default"},
        "source": {"agent": "test"},
        "blocks": [{"type": "markdown", "title": "Summary", "content": "hello"}],
    }


def client(tmp_path):
    settings = Settings(
        database_path=str(tmp_path / "api.sqlite3"),
        publish_token="secret",
        public_base_url="http://testserver",
    )
    return TestClient(create_app(settings))


def test_publish_requires_token(tmp_path):
    response = client(tmp_path).post(
        "/api/artifacts/publish",
        json={"visibility": "private", "payload": valid_payload(), "idempotency_key": "one"},
    )

    assert response.status_code == 401


def test_publish_creates_and_reads_artifact(tmp_path):
    app_client = client(tmp_path)
    response = app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={"visibility": "private", "payload": valid_payload(), "idempotency_key": "one"},
    )

    assert response.status_code == 200
    body = response.json()
    artifact_id = body["artifact_id"]
    assert body["version"] == 1
    assert body["url"] == f"http://testserver/a/{artifact_id}"

    read_response = app_client.get(f"/api/artifacts/{artifact_id}")
    assert read_response.status_code == 200
    assert read_response.json()["payload"]["title"] == "Example"


def test_publish_update_same_artifact_creates_second_version(tmp_path):
    app_client = client(tmp_path)
    first = app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={"visibility": "private", "payload": valid_payload("First"), "idempotency_key": "one"},
    ).json()
    second = app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={
            "artifact_id": first["artifact_id"],
            "visibility": "private",
            "payload": valid_payload("Second"),
            "idempotency_key": "two",
        },
    ).json()

    versions = app_client.get(f"/api/artifacts/{first['artifact_id']}/versions").json()

    assert second["version"] == 2
    assert [item["version_number"] for item in versions] == [1, 2]


def test_invalid_payload_returns_422(tmp_path):
    app_client = client(tmp_path)
    response = app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={
            "visibility": "private",
            "payload": {"schema_version": "0.1", "title": "Bad", "kind": "html", "blocks": []},
            "idempotency_key": "bad",
        },
    )

    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/server/test_api.py -v
```

Expected: FAIL with missing app implementation.

- [ ] **Step 3: Implement FastAPI app**

Create `server/open_artifacts_server/app.py`:

```python
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import Settings
from .db import init_db
from .store import ArtifactStore


class PublishRequest(BaseModel):
    artifact_id: str | None = None
    idempotency_key: str
    visibility: str = Field(pattern="^(private|workspace)$")
    payload: dict[str, Any]


class RestoreRequest(BaseModel):
    version_number: int
    created_by: str = "api"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    init_db(settings.database_path)
    store = ArtifactStore(settings.database_path, settings.public_base_url)
    app = FastAPI(title="Open Artifacts")
    templates = Jinja2Templates(directory="server/open_artifacts_server/templates")
    app.mount("/static", StaticFiles(directory="server/open_artifacts_server/static"), name="static")
    app.state.store = store
    app.state.settings = settings

    def require_publish_token(authorization: str | None) -> None:
        expected = f"Bearer {settings.publish_token}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="Invalid publish token")

    @app.post("/api/artifacts/publish")
    def publish(request: PublishRequest, authorization: str | None = Header(default=None)):
        require_publish_token(authorization)
        try:
            return store.publish(
                artifact_id=request.artifact_id,
                visibility=request.visibility,
                payload=request.payload,
                created_by=request.payload.get("source", {}).get("published_by", "agent"),
                organization=request.payload.get("source", {}).get("organization", "local-dev"),
                workspace=request.payload.get("workspace", {}).get("name", "default"),
                idempotency_key=request.idempotency_key,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/artifacts/{artifact_id}")
    def get_artifact(artifact_id: str):
        try:
            artifact = store.get_artifact(artifact_id)
            return {"artifact": artifact, "payload": store.get_current_payload(artifact_id)}
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/artifacts/{artifact_id}/versions")
    def versions(artifact_id: str):
        return store.list_versions(artifact_id)

    @app.post("/api/artifacts/{artifact_id}/restore")
    def restore(artifact_id: str, request: RestoreRequest):
        try:
            return store.restore(artifact_id, request.version_number, request.created_by)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/a/{artifact_id}", response_class=HTMLResponse)
    def viewer(request: Request, artifact_id: str):
        return templates.TemplateResponse(request, "viewer.html", {"artifact_id": artifact_id})

    @app.get("/gallery", response_class=HTMLResponse)
    def gallery(request: Request):
        return templates.TemplateResponse(request, "gallery.html", {})

    @app.get("/api/artifacts/{artifact_id}/events")
    async def events(artifact_id: str):
        async def stream():
            last_version = None
            while True:
                try:
                    artifact = store.get_artifact(artifact_id)
                    version = artifact["current_version"]
                    if version != last_version:
                        last_version = version
                        yield f"data: {json.dumps({'version': version})}\\n\\n"
                except KeyError:
                    yield "event: error\\ndata: not-found\\n\\n"
                    return
                await asyncio.sleep(1)

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("open_artifacts_server.app:app", host="127.0.0.1", port=8787)
```

- [ ] **Step 4: Add placeholder templates and static files for route mount**

Create `server/open_artifacts_server/templates/viewer.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Open Artifact</title>
    <link rel="stylesheet" href="/static/styles.css">
  </head>
  <body data-artifact-id="{{ artifact_id }}">
    <main id="app">Loading artifact...</main>
    <script src="/static/app.js"></script>
  </body>
</html>
```

Create `server/open_artifacts_server/templates/gallery.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Open Artifacts Gallery</title>
    <link rel="stylesheet" href="/static/styles.css">
  </head>
  <body data-gallery="true">
    <main id="app">Loading gallery...</main>
    <script src="/static/app.js"></script>
  </body>
</html>
```

Create `server/open_artifacts_server/static/app.js`:

```javascript
document.getElementById("app").textContent = "Open Artifacts";
```

Create `server/open_artifacts_server/static/styles.css`:

```css
body {
  margin: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f7f7f4;
  color: #1f2933;
}

main {
  max-width: 1080px;
  margin: 0 auto;
  padding: 32px;
}
```

- [ ] **Step 5: Run API tests**

Run:

```bash
uv run pytest tests/server/test_api.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Commit API**

```bash
git add server/open_artifacts_server/app.py server/open_artifacts_server/templates/viewer.html server/open_artifacts_server/templates/gallery.html server/open_artifacts_server/static/app.js server/open_artifacts_server/static/styles.css tests/server/test_api.py
git commit -m "feat: add artifact publish api"
```

### Task 5: Listing, Patch, Archive, And Restore Behavior

**Files:**
- Modify: `server/open_artifacts_server/store.py`
- Modify: `server/open_artifacts_server/app.py`
- Modify: `tests/server/test_api.py`

- [ ] **Step 1: Extend failing API tests**

Append to `tests/server/test_api.py`:

```python
def test_list_artifacts_filters_by_status(tmp_path):
    app_client = client(tmp_path)
    app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={"visibility": "private", "payload": valid_payload("One"), "idempotency_key": "one"},
    )

    response = app_client.get("/api/artifacts?status=draft")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "One"


def test_patch_artifact_changes_title_status_and_visibility(tmp_path):
    app_client = client(tmp_path)
    created = app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={"visibility": "private", "payload": valid_payload("One"), "idempotency_key": "one"},
    ).json()

    response = app_client.patch(
        f"/api/artifacts/{created['artifact_id']}",
        json={"title": "Renamed", "status": "ready", "visibility": "workspace"},
    )

    assert response.status_code == 200
    artifact = app_client.get(f"/api/artifacts/{created['artifact_id']}").json()["artifact"]
    assert artifact["title"] == "Renamed"
    assert artifact["status"] == "ready"
    assert artifact["visibility"] == "workspace"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/server/test_api.py::test_list_artifacts_filters_by_status tests/server/test_api.py::test_patch_artifact_changes_title_status_and_visibility -v
```

Expected: FAIL with 404 for missing routes or missing store methods.

- [ ] **Step 3: Add store list and patch methods**

Add to `ArtifactStore` in `server/open_artifacts_server/store.py`:

```python
    def list_artifacts(self, filters: dict[str, str | None]) -> list[dict[str, Any]]:
        clauses = ["archived_at IS NULL"]
        params: list[str] = []
        for key in ["workspace", "kind", "owner", "status", "visibility"]:
            if filters.get(key):
                clauses.append(f"{key} = ?")
                params.append(filters[key])
        if filters.get("title"):
            clauses.append("title LIKE ?")
            params.append(f"%{filters['title']}%")
        where = " AND ".join(clauses)
        with connect(self.database_path) as db:
            rows = db.execute(
                f"SELECT * FROM artifacts WHERE {where} ORDER BY updated_at DESC",
                params,
            ).fetchall()
        return [row_to_dict(row) for row in rows]

    def patch_artifact(self, artifact_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        allowed = {key: changes[key] for key in ["title", "status", "visibility"] if key in changes}
        if not allowed:
            return self.get_artifact(artifact_id)
        allowed["updated_at"] = now()
        assignments = ", ".join(f"{key} = ?" for key in allowed)
        values = list(allowed.values()) + [artifact_id]
        with transaction(self.database_path) as db:
            db.execute(f"UPDATE artifacts SET {assignments} WHERE id = ?", values)
        return self.get_artifact(artifact_id)
```

- [ ] **Step 4: Add list and patch routes**

Add imports and route model to `server/open_artifacts_server/app.py`:

```python
class PatchArtifactRequest(BaseModel):
    title: str | None = None
    status: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|workspace)$")
```

Add routes inside `create_app`:

```python
    @app.get("/api/artifacts")
    def list_artifacts(
        workspace: str | None = None,
        kind: str | None = None,
        owner: str | None = None,
        status: str | None = None,
        visibility: str | None = None,
        title: str | None = None,
    ):
        return store.list_artifacts(
            {
                "workspace": workspace,
                "kind": kind,
                "owner": owner,
                "status": status,
                "visibility": visibility,
                "title": title,
            }
        )

    @app.patch("/api/artifacts/{artifact_id}")
    def patch_artifact(artifact_id: str, request: PatchArtifactRequest):
        try:
            return store.patch_artifact(
                artifact_id,
                request.model_dump(exclude_none=True),
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
```

- [ ] **Step 5: Run API tests**

Run:

```bash
uv run pytest tests/server/test_api.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit list and patch**

```bash
git add server/open_artifacts_server/store.py server/open_artifacts_server/app.py tests/server/test_api.py
git commit -m "feat: manage artifacts in gallery api"
```

### Task 6: Viewer, Gallery, Safe Rendering, And Live Refresh

**Files:**
- Modify: `server/open_artifacts_server/templates/viewer.html`
- Modify: `server/open_artifacts_server/templates/gallery.html`
- Modify: `server/open_artifacts_server/static/app.js`
- Modify: `server/open_artifacts_server/static/styles.css`
- Create: `tests/server/test_viewer.py`

- [ ] **Step 1: Write failing viewer tests**

Create `tests/server/test_viewer.py`:

```python
from fastapi.testclient import TestClient

from open_artifacts_server.app import create_app
from open_artifacts_server.config import Settings


def make_client(tmp_path):
    settings = Settings(
        database_path=str(tmp_path / "viewer.sqlite3"),
        publish_token="secret",
        public_base_url="http://testserver",
    )
    return TestClient(create_app(settings))


def test_viewer_route_contains_artifact_bootstrap(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/a/art_123")

    assert response.status_code == 200
    assert 'data-artifact-id="art_123"' in response.text
    assert "/static/app.js" in response.text


def test_gallery_route_contains_gallery_bootstrap(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/gallery")

    assert response.status_code == 200
    assert 'data-gallery="true"' in response.text
```

- [ ] **Step 2: Run viewer tests**

Run:

```bash
uv run pytest tests/server/test_viewer.py -v
```

Expected: pass if placeholder routes exist. If they fail, fix template routing before continuing.

- [ ] **Step 3: Implement viewer HTML**

Replace `server/open_artifacts_server/templates/viewer.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Open Artifact</title>
    <link rel="stylesheet" href="/static/styles.css">
  </head>
  <body data-artifact-id="{{ artifact_id }}">
    <header class="topbar">
      <a class="brand" href="/gallery">Open Artifacts</a>
      <button id="copy-link" type="button">Copy link</button>
    </header>
    <main>
      <section id="artifact-root" class="surface">Loading artifact...</section>
      <aside id="versions-root" class="versions"></aside>
    </main>
    <script src="/static/app.js"></script>
  </body>
</html>
```

- [ ] **Step 4: Implement Gallery HTML**

Replace `server/open_artifacts_server/templates/gallery.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Open Artifacts Gallery</title>
    <link rel="stylesheet" href="/static/styles.css">
  </head>
  <body data-gallery="true">
    <header class="topbar">
      <a class="brand" href="/gallery">Open Artifacts</a>
    </header>
    <main>
      <section class="surface">
        <div class="section-header">
          <h1>Gallery</h1>
          <input id="gallery-filter" type="search" placeholder="Filter artifacts">
        </div>
        <div id="gallery-root">Loading gallery...</div>
      </section>
    </main>
    <script src="/static/app.js"></script>
  </body>
</html>
```

- [ ] **Step 5: Implement client rendering and SSE**

Replace `server/open_artifacts_server/static/app.js`:

```javascript
function text(value) {
  return value == null ? "" : String(value);
}

function escapeHtml(value) {
  return text(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(block) {
  return `<section class="block"><h2>${escapeHtml(block.title || "Notes")}</h2><p>${escapeHtml(block.content || "")}</p></section>`;
}

function renderBlock(block) {
  if (block.type === "markdown") return renderMarkdown(block);
  if (block.type === "timeline") {
    const items = (block.items || []).map((item) => `<li><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.time || "")}</span><p>${escapeHtml(item.detail || "")}</p></li>`).join("");
    return `<section class="block"><h2>${escapeHtml(block.title || "Timeline")}</h2><ol class="timeline">${items}</ol></section>`;
  }
  if (block.type === "code-reference") {
    const refs = (block.references || []).map((ref) => `<li><code>${escapeHtml(ref.path)}:${escapeHtml(ref.start_line)}-${escapeHtml(ref.end_line)}</code> ${escapeHtml(ref.label || "")}</li>`).join("");
    return `<section class="block"><h2>${escapeHtml(block.title || "Code")}</h2><ul>${refs}</ul></section>`;
  }
  if (block.type === "command-output" || block.type === "diff") {
    return `<section class="block"><h2>${escapeHtml(block.title || block.type)}</h2><pre>${escapeHtml(block.content || "")}</pre></section>`;
  }
  if (block.type === "checklist") {
    const items = (block.items || []).map((item) => `<li data-state="${escapeHtml(item.state || "todo")}">${escapeHtml(item.label || "")}<p>${escapeHtml(item.detail || "")}</p></li>`).join("");
    return `<section class="block"><h2>${escapeHtml(block.title || "Checklist")}</h2><ul class="checklist">${items}</ul></section>`;
  }
  if (block.type === "metric") {
    return `<section class="block metric"><h2>${escapeHtml(block.title || "Metric")}</h2><strong>${escapeHtml(block.value || "")}</strong><span>${escapeHtml(block.trend || "")}</span><p>${escapeHtml(block.detail || "")}</p></section>`;
  }
  if (block.type === "table") {
    const head = (block.columns || []).map((column) => `<th>${escapeHtml(column)}</th>`).join("");
    const rows = (block.rows || []).map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("");
    return `<section class="block"><h2>${escapeHtml(block.title || "Table")}</h2><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></section>`;
  }
  return "";
}

async function loadArtifact(artifactId) {
  const response = await fetch(`/api/artifacts/${artifactId}`);
  if (!response.ok) throw new Error("Artifact not found");
  const data = await response.json();
  const payload = data.payload;
  document.title = `${payload.title} - Open Artifact`;
  document.getElementById("artifact-root").innerHTML = `
    <div class="artifact-header">
      <div>
        <p class="eyebrow">${escapeHtml(payload.kind)}</p>
        <h1>${escapeHtml(payload.title)}</h1>
        <p>${escapeHtml(payload.summary || "")}</p>
      </div>
      <span class="status">${escapeHtml(payload.status || "draft")}</span>
    </div>
    ${(payload.blocks || []).map(renderBlock).join("")}
  `;
  const versions = await fetch(`/api/artifacts/${artifactId}/versions`).then((res) => res.json());
  document.getElementById("versions-root").innerHTML = `<h2>Versions</h2>${versions.map((version) => `<div class="version">v${version.version_number}<br><small>${escapeHtml(version.created_at)}</small></div>`).join("")}`;
}

async function loadGallery() {
  const artifacts = await fetch("/api/artifacts").then((res) => res.json());
  const filter = document.getElementById("gallery-filter");
  const root = document.getElementById("gallery-root");
  function render() {
    const query = (filter.value || "").toLowerCase();
    root.innerHTML = artifacts
      .filter((artifact) => artifact.title.toLowerCase().includes(query))
      .map((artifact) => `<a class="artifact-row" href="/a/${artifact.id}"><strong>${escapeHtml(artifact.title)}</strong><span>${escapeHtml(artifact.kind)}</span><span>v${artifact.current_version}</span></a>`)
      .join("") || "<p>No artifacts found.</p>";
  }
  filter.addEventListener("input", render);
  render();
}

const artifactId = document.body.dataset.artifactId;
if (artifactId) {
  loadArtifact(artifactId).catch((error) => {
    document.getElementById("artifact-root").textContent = error.message;
  });
  const events = new EventSource(`/api/artifacts/${artifactId}/events`);
  events.onmessage = () => loadArtifact(artifactId);
  const copy = document.getElementById("copy-link");
  copy.addEventListener("click", () => navigator.clipboard.writeText(window.location.href));
}

if (document.body.dataset.gallery) {
  loadGallery();
}
```

- [ ] **Step 6: Implement CSS**

Replace `server/open_artifacts_server/static/styles.css`:

```css
:root {
  color-scheme: light;
  --bg: #f6f5f0;
  --surface: #ffffff;
  --text: #20262d;
  --muted: #68717b;
  --line: #d8d4ca;
  --accent: #2f6f6d;
  --warn: #9a5b13;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
}

.topbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.9);
  position: sticky;
  top: 0;
}

.brand {
  color: var(--text);
  text-decoration: none;
  font-weight: 700;
}

main {
  width: min(1120px, calc(100vw - 32px));
  margin: 24px auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 20px;
}

.surface,
.versions {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 20px;
}

.artifact-header,
.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 16px;
  margin-bottom: 16px;
}

h1,
h2,
p {
  margin-top: 0;
}

.eyebrow,
.status,
.version,
.artifact-row span {
  color: var(--muted);
  font-size: 13px;
}

.status {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 10px;
}

.block {
  border-top: 1px solid var(--line);
  padding-top: 16px;
  margin-top: 16px;
}

pre {
  overflow: auto;
  padding: 12px;
  background: #182027;
  color: #f4f7f8;
  border-radius: 6px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  border-bottom: 1px solid var(--line);
  text-align: left;
  padding: 8px;
}

.artifact-row {
  display: grid;
  grid-template-columns: 1fr 140px 80px;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
  color: var(--text);
  text-decoration: none;
}

input,
button {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px 10px;
  background: white;
  color: var(--text);
}

@media (max-width: 800px) {
  main {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 7: Run viewer tests and full server tests**

Run:

```bash
uv run pytest tests/server -v
```

Expected: all server tests pass.

- [ ] **Step 8: Commit viewer and Gallery**

```bash
git add server/open_artifacts_server/templates/viewer.html server/open_artifacts_server/templates/gallery.html server/open_artifacts_server/static/app.js server/open_artifacts_server/static/styles.css tests/server/test_viewer.py
git commit -m "feat: render artifact viewer and gallery"
```

### Task 7: Skill Package And References

**Files:**
- Create: `skill/SKILL.md`
- Create: `skill/agents/openai.yaml`
- Create: `skill/config/open-artifacts.toml`
- Create: `skill/references/artifact-schema.md`
- Create: `skill/references/publishing-protocol.md`

- [ ] **Step 1: Create Skill instructions**

Create `skill/SKILL.md`:

```markdown
---
name: open-artifacts
description: Publish agent work as Open Artifacts. Use when the user asks to create, update, publish, share, visualize, or turn current agent work into an artifact, live page, investigation page, PR walkthrough, checklist, dashboard, or Gallery item.
---

# Open Artifacts

Use this Skill to publish the current agent-visible work context to a preconfigured Open Artifacts server.

## Workflow

1. Determine whether the user wants a new Artifact or an update to an existing Artifact.
2. If updating, reuse the visible `artifact_id` from the conversation.
3. Gather only context visible to the agent: user request, conversation summary, files read, diffs, command output, test results, and explicit user-provided material.
4. Choose `kind`: `work-summary`, `investigation`, `walkthrough`, `checklist`, or `dashboard`.
5. Build a payload using `references/artifact-schema.md`.
6. Publish using `scripts/publish_artifact.py` and `references/publishing-protocol.md`.
7. Report the returned URL, version, and `artifact_id`.
8. Keep the `artifact_id` in the response so future turns can update the same Artifact.

## Guardrails

- Do not claim access to hidden agent internals.
- Do not include secrets unless the user explicitly asks and the server is approved for that data.
- Do not put raw HTML or JavaScript in Markdown blocks.
- Prefer concise blocks over dumping full logs.
- Use code references for file locations instead of embedding large source files.
```

- [ ] **Step 2: Create Skill metadata**

Create `skill/agents/openai.yaml`:

```yaml
display_name: Open Artifacts
short_description: Publish current agent work to a live Open Artifacts page.
default_prompt: Publish the current work as an Open Artifact and return the URL.
```

- [ ] **Step 3: Create Skill config**

Create `skill/config/open-artifacts.toml`:

```toml
server_url = "http://localhost:8787"
api_base = "/api"
organization = "local-dev"
workspace = "default"
default_visibility = "private"
publish_token = "dev-token"
```

- [ ] **Step 4: Create schema reference**

Create `skill/references/artifact-schema.md`:

```markdown
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
```

- [ ] **Step 5: Create publishing protocol reference**

Create `skill/references/publishing-protocol.md`:

````markdown
# Publishing Protocol

Read `config/open-artifacts.toml` for server configuration.

Publish endpoint:

`POST {server_url}{api_base}/artifacts/publish`

Headers:

- `Authorization: Bearer <publish_token>`
- `Content-Type: application/json`

Request:

```json
{
  "artifact_id": "optional-existing-id",
  "idempotency_key": "unique-key",
  "visibility": "private",
  "payload": {}
}
```

Response:

```json
{
  "artifact_id": "art_123",
  "version": 1,
  "url": "http://localhost:8787/a/art_123",
  "gallery_url": "http://localhost:8787/gallery"
}
```

On `401`, report invalid Skill/server config. On `422`, revise the payload. On network failure, preserve the generated payload and report publish failure.
````

- [ ] **Step 6: Commit Skill docs**

```bash
git add skill/SKILL.md skill/agents/openai.yaml skill/config/open-artifacts.toml skill/references/artifact-schema.md skill/references/publishing-protocol.md
git commit -m "feat: add open artifacts skill package"
```

### Task 8: Skill Publish Helper

**Files:**
- Create: `skill/scripts/publish_artifact.py`
- Create: `tests/skill/test_publish_artifact.py`

- [ ] **Step 1: Write failing helper tests**

Create `tests/skill/test_publish_artifact.py`:

```python
import json

import pytest

from publish_artifact import load_config, build_publish_url, main


def test_load_config_reads_toml(tmp_path):
    config = tmp_path / "open-artifacts.toml"
    config.write_text(
        'server_url = "http://localhost:8787"\\napi_base = "/api"\\npublish_token = "dev-token"\\n',
        encoding="utf-8",
    )

    loaded = load_config(config)

    assert loaded["server_url"] == "http://localhost:8787"
    assert loaded["publish_token"] == "dev-token"


def test_build_publish_url_normalizes_slashes():
    assert build_publish_url("http://localhost:8787/", "/api") == "http://localhost:8787/api/artifacts/publish"


def test_main_rejects_missing_payload(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(["--config", str(tmp_path / "missing.toml")])

    assert error.value.code == 2
```

- [ ] **Step 2: Run helper tests to verify they fail**

Run:

```bash
uv run pytest tests/skill/test_publish_artifact.py -v
```

Expected: FAIL with missing `publish_artifact`.

- [ ] **Step 3: Implement publish helper**

Create `skill/scripts/publish_artifact.py`:

```python
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from urllib import request, error


def load_config(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def build_publish_url(server_url: str, api_base: str) -> str:
    return f"{server_url.rstrip('/')}/{api_base.strip('/')}/artifacts/publish"


def publish(config: dict, body: dict) -> dict:
    url = build_publish_url(config["server_url"], config.get("api_base", "/api"))
    data = json.dumps(body).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {config['publish_token']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise SystemExit(f"Publish failed with HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise SystemExit(f"Publish failed: {exc.reason}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--payload", required=True, help="Path to payload JSON file")
    parser.add_argument("--artifact-id")
    parser.add_argument("--visibility", default="private")
    parser.add_argument("--idempotency-key", required=True)
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    body = {
        "artifact_id": args.artifact_id,
        "idempotency_key": args.idempotency_key,
        "visibility": args.visibility,
        "payload": payload,
    }
    result = publish(config, body)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run helper tests**

Run:

```bash
uv run pytest tests/skill/test_publish_artifact.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit publish helper**

```bash
git add skill/scripts/publish_artifact.py tests/skill/test_publish_artifact.py
git commit -m "feat: add skill publish helper"
```

### Task 9: End-To-End Local Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a sample payload to README**

Append to `README.md`:

````markdown
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
uv run python skill/scripts/publish_artifact.py \
  --config skill/config/open-artifacts.toml \
  --payload /tmp/open-artifact-payload.json \
  --idempotency-key local-smoke-1
```

Open the returned URL and `/gallery`.
````

- [ ] **Step 2: Run full automated tests**

Run:

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Run the server for manual smoke test**

Run:

```bash
uv run uvicorn open_artifacts_server.app:app --app-dir server --host 127.0.0.1 --port 8787
```

Expected: server starts on `http://127.0.0.1:8787`.

- [ ] **Step 4: Publish sample payload**

Run:

```bash
uv run python skill/scripts/publish_artifact.py \
  --config skill/config/open-artifacts.toml \
  --payload /tmp/open-artifact-payload.json \
  --idempotency-key local-smoke-1
```

Expected: JSON response includes `artifact_id`, `version: 1`, `url`, and `gallery_url`.

- [ ] **Step 5: Verify browser flow**

Open the returned `/a/:artifact_id` URL and `/gallery`.

Expected:

- Viewer renders title, summary, status, and Markdown block.
- Gallery lists the Artifact.
- Publishing a second payload with `--artifact-id <id>` updates the same URL.
- The open viewer refreshes after the next SSE poll.

- [ ] **Step 6: Commit README verification docs**

```bash
git add README.md
git commit -m "docs: document local smoke test"
```

## Plan Self-Review Checklist

- Spec coverage: Skill package, publish helper, server API, SQLite versions, restore, viewer, Gallery, SSE, private/workspace visibility, and safe rendering are covered.
- Deferred scope: desktop app, public sharing, connector framework, full RBAC, compliance API, and arbitrary component plugins are not included.
- Type consistency: `artifact_id`, `version_number`, `visibility`, `payload`, `schema_version`, and block type names match the design spec.
- Verification: Each implementation task includes a failing test step, passing test step, and commit step.
