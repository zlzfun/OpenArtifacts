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
    assert 'class="artifact-shell"' in response.text
    assert 'aria-live="polite"' in response.text
    assert 'id="copy-link"' in response.text
    assert 'id="versions-root"' in response.text
    assert "/static/app.js" in response.text


def test_gallery_route_contains_gallery_bootstrap(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/gallery")

    assert response.status_code == 200
    assert 'data-gallery="true"' in response.text
    assert 'class="gallery-shell"' in response.text
    assert 'class="surface gallery-surface"' in response.text
    assert 'id="gallery-filter"' in response.text
