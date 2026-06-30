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

    for token in [
        "color-scheme: light;",
        "--canvas: #f8f4ec;",
        "--canvas-ink: #211d19;",
        "--surface: #fffdf8;",
        "--surface-bone: #f0eadf;",
        "--surface-dark: #1f1d1a;",
        "--surface-dark-2: #2b2925;",
        "--muted: #716b61;",
        "--muted-2: #9b9286;",
        "--line: rgba(33, 29, 25, 0.16);",
        "--line-strong: rgba(33, 29, 25, 0.34);",
        "--accent: #df5b2f;",
        "--accent-deep: #a93d21;",
        "--success: #417d57;",
        "--warning: #a8671c;",
        "--danger: #a94438;",
        "--shadow: 0 18px 48px rgba(64, 49, 29, 0.12);",
        "--radius: 8px;",
        '--mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;',
        '--body: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;',
        '--display: Georgia, "Times New Roman", serif;',
    ]:
        assert token in styles

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

    assert "@media (max-width: 900px)" in styles
    assert ".gallery-shell" in styles
