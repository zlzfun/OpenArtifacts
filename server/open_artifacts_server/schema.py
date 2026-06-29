from copy import deepcopy
import re
from typing import Any


SUPPORTED_KINDS = {
    "work-summary",
    "investigation",
    "walkthrough",
    "checklist",
    "dashboard",
}
SUPPORTED_BLOCKS = {
    "markdown",
    "timeline",
    "code-reference",
    "command-output",
    "diff",
    "checklist",
    "metric",
    "table",
}
BLOCKED_HTML = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def validate_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(raw)

    if payload.get("schema_version") != "0.1":
        raise ValueError("Unsupported schema_version")
    if not payload.get("title"):
        raise ValueError("Artifact title is required")
    if payload.get("kind") not in SUPPORTED_KINDS:
        raise ValueError("Unsupported artifact kind")
    if not isinstance(payload.get("blocks"), list):
        raise ValueError("Artifact blocks must be a list")

    for index, block in enumerate(payload["blocks"]):
        if not isinstance(block, dict):
            raise ValueError(f"Block {index} must be an object")
        block_type = block.get("type")
        if block_type not in SUPPORTED_BLOCKS:
            raise ValueError("Unsupported block type")
        if block_type == "markdown" and BLOCKED_HTML.search(block.get("content", "")):
            raise ValueError("Raw HTML is not allowed")

    return payload
