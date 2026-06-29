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

    first = store.publish(
        None, "private", payload("First"), "tester", "local-dev", "default", "first"
    )
    second = store.publish(
        first["artifact_id"],
        "private",
        payload("Second"),
        "tester",
        "local-dev",
        "default",
        "second",
    )

    versions = store.list_versions(first["artifact_id"])
    current = store.get_current_payload(first["artifact_id"])

    assert second["version"] == 2
    assert [version["version_number"] for version in versions] == [1, 2]
    assert current["title"] == "Second"


def test_restore_creates_new_current_version_from_old_payload(tmp_path):
    db_path = tmp_path / "artifacts.sqlite3"
    init_db(str(db_path))
    store = ArtifactStore(str(db_path), public_base_url="http://localhost:8787")

    first = store.publish(
        None, "private", payload("First"), "tester", "local-dev", "default", "first"
    )
    store.publish(
        first["artifact_id"],
        "private",
        payload("Second"),
        "tester",
        "local-dev",
        "default",
        "second",
    )
    restored = store.restore(first["artifact_id"], version_number=1, created_by="tester")

    assert restored["version"] == 3
    assert store.get_current_payload(first["artifact_id"])["title"] == "First"
