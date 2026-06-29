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
