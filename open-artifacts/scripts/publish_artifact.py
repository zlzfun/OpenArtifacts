from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from urllib import error, request


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
