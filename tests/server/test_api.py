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
        json={
            "visibility": "private",
            "payload": valid_payload(),
            "idempotency_key": "one",
        },
    )

    assert response.status_code == 401


def test_publish_creates_and_reads_artifact(tmp_path):
    app_client = client(tmp_path)
    response = app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={
            "visibility": "private",
            "payload": valid_payload(),
            "idempotency_key": "one",
        },
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
        json={
            "visibility": "private",
            "payload": valid_payload("First"),
            "idempotency_key": "one",
        },
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
            "payload": {
                "schema_version": "0.1",
                "title": "Bad",
                "kind": "html",
                "blocks": [],
            },
            "idempotency_key": "bad",
        },
    )

    assert response.status_code == 422


def test_list_artifacts_filters_by_status(tmp_path):
    app_client = client(tmp_path)
    app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={
            "visibility": "private",
            "payload": valid_payload("One"),
            "idempotency_key": "one",
        },
    )

    response = app_client.get("/api/artifacts?status=draft")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "One"


def test_patch_artifact_changes_title_status_and_visibility(tmp_path):
    app_client = client(tmp_path)
    created = app_client.post(
        "/api/artifacts/publish",
        headers={"Authorization": "Bearer secret"},
        json={
            "visibility": "private",
            "payload": valid_payload("One"),
            "idempotency_key": "one",
        },
    ).json()

    response = app_client.patch(
        f"/api/artifacts/{created['artifact_id']}",
        json={"title": "Renamed", "status": "ready", "visibility": "workspace"},
    )

    assert response.status_code == 200
    artifact = app_client.get(f"/api/artifacts/{created['artifact_id']}").json()[
        "artifact"
    ]
    assert artifact["title"] == "Renamed"
    assert artifact["status"] == "ready"
    assert artifact["visibility"] == "workspace"
