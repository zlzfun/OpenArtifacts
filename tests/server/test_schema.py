import pytest

from open_artifacts_server.schema import validate_payload


def base_payload():
    return {
        "schema_version": "0.1",
        "title": "Auth investigation",
        "kind": "investigation",
        "summary": "Short summary",
        "status": "draft",
        "workspace": {"name": "payments", "branch": "main"},
        "source": {"agent": "codex", "skill_version": "0.1.0"},
        "blocks": [
            {"type": "markdown", "title": "Summary", "content": "No raw HTML"},
            {
                "type": "timeline",
                "title": "Timeline",
                "items": [{"time": "2026-06-29T10:00:00Z", "label": "Started"}],
            },
            {
                "type": "code-reference",
                "title": "Relevant code",
                "references": [
                    {"path": "src/auth.py", "start_line": 1, "end_line": 5}
                ],
            },
        ],
    }


def test_valid_payload_round_trips():
    payload = validate_payload(base_payload())

    assert payload["title"] == "Auth investigation"
    assert payload["blocks"][0]["type"] == "markdown"


def test_rejects_unknown_kind():
    payload = base_payload()
    payload["kind"] = "incident-postmortem"

    with pytest.raises(ValueError, match="Unsupported artifact kind"):
        validate_payload(payload)


def test_rejects_raw_html_in_markdown():
    payload = base_payload()
    payload["blocks"][0]["content"] = "<script>alert(1)</script>"

    with pytest.raises(ValueError, match="Raw HTML is not allowed"):
        validate_payload(payload)


def test_rejects_unknown_block_type():
    payload = base_payload()
    payload["blocks"] = [{"type": "html", "content": "<b>bad</b>"}]

    with pytest.raises(ValueError, match="Unsupported block type"):
        validate_payload(payload)
