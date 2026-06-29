import pytest

from publish_artifact import build_publish_url, load_config, main


def test_load_config_reads_toml(tmp_path):
    config = tmp_path / "open-artifacts.toml"
    config.write_text(
        'server_url = "http://localhost:8787"\napi_base = "/api"\npublish_token = "dev-token"\n',
        encoding="utf-8",
    )

    loaded = load_config(config)

    assert loaded["server_url"] == "http://localhost:8787"
    assert loaded["publish_token"] == "dev-token"


def test_build_publish_url_normalizes_slashes():
    assert (
        build_publish_url("http://localhost:8787/", "/api")
        == "http://localhost:8787/api/artifacts/publish"
    )


def test_main_rejects_missing_payload(tmp_path):
    with pytest.raises(SystemExit) as error:
        main(["--config", str(tmp_path / "missing.toml")])

    assert error.value.code == 2
