import pytest

from publish_artifact import (
    build_publish_url,
    load_config,
    main,
    normalize_response_urls,
    read_payload,
)


def test_load_config_reads_toml(tmp_path):
    config = tmp_path / "open-artifacts.toml"
    config.write_text(
        'server_url = "http://localhost:8787"\napi_base = "/api"\npublish_token = "dev-token"\n',
        encoding="utf-8",
    )

    loaded = load_config(config)

    assert loaded["server_url"] == "http://localhost:8787"
    assert loaded["publish_token"] == "dev-token"


def test_load_config_applies_known_environment_overrides(tmp_path, monkeypatch):
    config = tmp_path / "open-artifacts.toml"
    config.write_text(
        'server_url = "http://localhost:8787"\napi_base = "/api"\npublish_token = "dev-token"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("OPEN_ARTIFACTS_SERVER_URL", "http://203.0.113.10:8788")
    monkeypatch.setenv("OPEN_ARTIFACTS_PUBLISH_TOKEN", "secret")

    loaded = load_config(config)

    assert loaded["server_url"] == "http://203.0.113.10:8788"
    assert loaded["publish_token"] == "secret"


def test_build_publish_url_normalizes_slashes():
    assert (
        build_publish_url("http://localhost:8787/", "/api")
        == "http://localhost:8787/api/artifacts/publish"
    )


def test_read_payload_accepts_stdin_marker(monkeypatch):
    class Stdin:
        def read(self):
            return '{"schema_version": "0.1", "blocks": []}'

    monkeypatch.setattr("sys.stdin", Stdin())

    payload = read_payload("-")

    assert payload["schema_version"] == "0.1"


def test_normalize_response_urls_uses_configured_port_for_same_host():
    result = {
        "artifact_id": "art_123",
        "version": 1,
        "url": "http://203.0.113.10/a/art_123",
        "gallery_url": "http://203.0.113.10/gallery",
    }

    normalized = normalize_response_urls(result, "http://203.0.113.10:8788")

    assert normalized["url"] == "http://203.0.113.10:8788/a/art_123"
    assert normalized["gallery_url"] == "http://203.0.113.10:8788/gallery"
    assert "warnings" in normalized


def test_normalize_response_urls_keeps_different_public_host():
    result = {
        "url": "https://artifacts.example.com/a/art_123",
        "gallery_url": "https://artifacts.example.com/gallery",
    }

    normalized = normalize_response_urls(result, "http://10.0.0.5:8788")

    assert normalized == result


def test_main_rejects_missing_payload(tmp_path):
    with pytest.raises(SystemExit) as error:
        main(["--config", str(tmp_path / "missing.toml")])

    assert error.value.code == 2
