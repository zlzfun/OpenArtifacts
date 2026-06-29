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
            row = db.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
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

    def restore(
        self, artifact_id: str, version_number: int, created_by: str
    ) -> dict[str, Any]:
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
