from pathlib import Path


STATIC_DIR = Path("server/open_artifacts_server/static")


def read_static(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def test_app_js_contains_visual_block_renderers():
    script = read_static("app.js")

    for renderer in [
        "renderChart",
        "renderImage",
        "renderSvg",
        "renderCallout",
        "renderStatGrid",
        "renderFlow",
    ]:
        assert f"function {renderer}" in script

    for block_type in [
        '"chart"',
        '"image"',
        '"svg"',
        '"callout"',
        '"stat-grid"',
        '"flow"',
    ]:
        assert block_type in script


def test_styles_css_contains_visual_system_hooks():
    styles = read_static("styles.css")

    for selector in [
        ".artifact-shell",
        ".artifact-card",
        ".block-chart",
        ".block-image",
        ".block-svg",
        ".block-callout",
        ".stat-grid",
        ".flow-list",
        ".gallery-grid",
    ]:
        assert selector in styles
