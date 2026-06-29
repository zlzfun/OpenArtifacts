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


def visual_payload():
    payload = base_payload()
    payload["kind"] = "dashboard"
    payload["blocks"] = [
        {
            "type": "chart",
            "title": "Test trend",
            "chart_type": "bar",
            "series": [
                {"label": "Unit", "value": 42},
                {"label": "Integration", "value": 9},
            ],
            "caption": "Tests passing by category.",
        },
        {
            "type": "image",
            "title": "Reference screenshot",
            "src": "data:image/png;base64,iVBORw0KGgo=",
            "alt": "Reference screenshot",
            "caption": "User-provided visual reference.",
        },
        {
            "type": "svg",
            "title": "System flow",
            "svg": (
                '<svg viewBox="0 0 120 40" role="img" aria-label="System flow">'
                '<rect x="4" y="4" width="40" height="20"></rect>'
                '<text x="8" y="18">Agent</text>'
                "</svg>"
            ),
            "caption": "Skill publishes to server.",
        },
        {
            "type": "callout",
            "tone": "decision",
            "title": "Selected direction",
            "content": "Use the Editorial Lab Notebook style.",
        },
        {
            "type": "stat-grid",
            "title": "Run summary",
            "stats": [
                {"label": "Tests", "value": "24", "detail": "all passing"},
                {"label": "Files changed", "value": "5"},
            ],
        },
        {
            "type": "flow",
            "title": "Publishing loop",
            "items": [
                {"label": "Agent", "detail": "Builds payload"},
                {"label": "Server", "detail": "Stores version"},
                {"label": "Viewer", "detail": "Renders live artifact"},
            ],
        },
    ]
    return payload


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


def test_accepts_visual_blocks():
    payload = validate_payload(visual_payload())

    assert [block["type"] for block in payload["blocks"]] == [
        "chart",
        "image",
        "svg",
        "callout",
        "stat-grid",
        "flow",
    ]


@pytest.mark.parametrize(
    "src",
    [
        "javascript:alert(1)",
        "data:text/html;base64,PGgxPmJhZDwvaDE+",
        "vbscript:msgbox(1)",
    ],
)
def test_rejects_unsafe_image_sources(src):
    payload = visual_payload()
    payload["blocks"] = [{"type": "image", "src": src}]

    with pytest.raises(ValueError, match="Unsafe image source"):
        validate_payload(payload)


@pytest.mark.parametrize(
    "svg",
    [
        "<script>alert(1)</script>",
        '<svg><script>alert(1)</script></svg>',
        '<svg><foreignObject><p>bad</p></foreignObject></svg>',
        '<svg onclick="alert(1)"><rect /></svg>',
        '<svg><image href="javascript:alert(1)" /></svg>',
        '<svg><rect fill="url(https://example.com/pattern.svg#p)" /></svg>',
        '<svg><rect stroke="url(javascript:alert(1))" /></svg>',
    ],
)
def test_rejects_unsafe_svg(svg):
    payload = visual_payload()
    payload["blocks"] = [{"type": "svg", "svg": svg}]

    with pytest.raises(ValueError, match="Unsafe SVG"):
        validate_payload(payload)


def test_accepts_svg_internal_url_reference():
    payload = visual_payload()
    payload["blocks"] = [
        {
            "type": "svg",
            "svg": (
                '<svg viewBox="0 0 20 20">'
                "<defs>"
                '<linearGradient id="gradient">'
                '<stop offset="0%" />'
                "</linearGradient>"
                "</defs>"
                '<rect fill="url(#gradient)" width="20" height="20" />'
                "</svg>"
            ),
        }
    ]

    validate_payload(payload)


def test_rejects_unknown_chart_type():
    payload = visual_payload()
    payload["blocks"] = [{"type": "chart", "chart_type": "scatter", "series": []}]

    with pytest.raises(ValueError, match="Unsupported chart type"):
        validate_payload(payload)


def test_rejects_unknown_callout_tone():
    payload = visual_payload()
    payload["blocks"] = [
        {"type": "callout", "tone": "celebration", "content": "Unsupported"}
    ]

    with pytest.raises(ValueError, match="Unsupported callout tone"):
        validate_payload(payload)
