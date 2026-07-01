from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path
from urllib import error, request
from urllib.parse import urlsplit, urlunsplit


def load_config(path: Path) -> dict:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    env_overrides = {
        "server_url": "OPEN_ARTIFACTS_SERVER_URL",
        "api_base": "OPEN_ARTIFACTS_API_BASE",
        "organization": "OPEN_ARTIFACTS_ORGANIZATION",
        "workspace": "OPEN_ARTIFACTS_WORKSPACE",
        "default_visibility": "OPEN_ARTIFACTS_DEFAULT_VISIBILITY",
        "publish_token": "OPEN_ARTIFACTS_PUBLISH_TOKEN",
    }
    for key, env_name in env_overrides.items():
        value = os.environ.get(env_name)
        if value:
            config[key] = value
    return config


def build_publish_url(server_url: str, api_base: str) -> str:
    return f"{server_url.rstrip('/')}/{api_base.strip('/')}/artifacts/publish"


def read_payload(path: str) -> dict:
    if path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _origin(parts):
    return (parts.scheme, parts.hostname, parts.port)


def normalize_response_urls(result: dict, server_url: str) -> dict:
    normalized = dict(result)
    server_parts = urlsplit(server_url)
    warnings = list(normalized.get("warnings", []))

    for key in ("url", "gallery_url"):
        value = normalized.get(key)
        if not isinstance(value, str):
            continue
        value_parts = urlsplit(value)
        same_host = value_parts.hostname == server_parts.hostname
        different_origin = _origin(value_parts) != _origin(server_parts)
        if same_host and different_origin and server_parts.scheme and server_parts.netloc:
            normalized[key] = urlunsplit(
                (
                    server_parts.scheme,
                    server_parts.netloc,
                    value_parts.path,
                    value_parts.query,
                    value_parts.fragment,
                )
            )

    if normalized != result:
        warnings.append(
            "Returned artifact URL origin differed from configured server_url; "
            "using server_url origin. Check backend OPEN_ARTIFACTS_PUBLIC_BASE_URL "
            "if this is unexpected."
        )
        normalized["warnings"] = warnings

    return normalized


def _http_error_message(exc: error.HTTPError) -> str:
    detail = exc.read().decode("utf-8")
    if exc.code == 401:
        return (
            "Publish failed with HTTP 401: invalid publish token. "
            "Do not retry with guessed tokens, omit the token, or brute-force common "
            "passwords. Ask the user for the correct publish_token, then update "
            "open-artifacts/config/open-artifacts.toml or OPEN_ARTIFACTS_PUBLISH_TOKEN. "
            f"Server detail: {detail}"
        )
    if exc.code == 422:
        return (
            "Publish failed with HTTP 422: payload validation failed. "
            "Revise the payload according to references/artifact-schema.md. "
            f"Server detail: {detail}"
        )
    return f"Publish failed with HTTP {exc.code}: {detail}"


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
            result = json.loads(response.read().decode("utf-8"))
            return normalize_response_urls(result, config["server_url"])
    except error.HTTPError as exc:
        raise SystemExit(_http_error_message(exc)) from exc
    except error.URLError as exc:
        raise SystemExit(f"Publish failed: {exc.reason}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--payload",
        required=True,
        help="Path to payload JSON file, or '-' to read JSON from stdin",
    )
    parser.add_argument("--artifact-id")
    parser.add_argument("--visibility", default="private")
    parser.add_argument("--idempotency-key", required=True)
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    payload = read_payload(args.payload)
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
