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
