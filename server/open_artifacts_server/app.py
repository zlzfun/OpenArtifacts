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


class PatchArtifactRequest(BaseModel):
    title: str | None = None
    status: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|workspace)$")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    init_db(settings.database_path)
    store = ArtifactStore(settings.database_path, settings.public_base_url)
    app = FastAPI(title="Open Artifacts")
    templates = Jinja2Templates(directory="server/open_artifacts_server/templates")
    app.mount(
        "/static",
        StaticFiles(directory="server/open_artifacts_server/static"),
        name="static",
    )
    app.state.store = store
    app.state.settings = settings

    def require_publish_token(authorization: str | None) -> None:
        expected = f"Bearer {settings.publish_token}"
        if authorization != expected:
            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid publish token. Do not retry with guessed tokens, omit "
                    "the Authorization header, or brute-force common passwords. "
                    "Ask the user for the correct publish token, then update the "
                    "Skill config publish_token or server OPEN_ARTIFACTS_PUBLISH_TOKEN."
                ),
            )

    @app.post("/api/artifacts/publish")
    def publish(
        request: PublishRequest, authorization: str | None = Header(default=None)
    ):
        require_publish_token(authorization)
        try:
            return store.publish(
                artifact_id=request.artifact_id,
                visibility=request.visibility,
                payload=request.payload,
                created_by=request.payload.get("source", {}).get(
                    "published_by", "agent"
                ),
                organization=request.payload.get("source", {}).get(
                    "organization", "local-dev"
                ),
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
        return templates.TemplateResponse(
            request, "viewer.html", {"artifact_id": artifact_id}
        )

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
                        yield f"data: {json.dumps({'version': version})}\n\n"
                except KeyError:
                    yield "event: error\ndata: not-found\n\n"
                    return
                await asyncio.sleep(1)

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("open_artifacts_server.app:app", host="127.0.0.1", port=8787)
