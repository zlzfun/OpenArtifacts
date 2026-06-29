# Open Artifacts Visual System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Open Artifacts from a plain text renderer into a consistent Editorial Lab Notebook visual system with safe visual artifact blocks.

**Architecture:** Keep the existing FastAPI plus plain HTML/CSS/JS MVP architecture. Server-side schema validation controls which structured blocks can be stored; the browser renderer converts escaped structured JSON into visual HTML and generated SVG for charts and flows. The gallery and viewer share one CSS token system and one visual language.

**Tech Stack:** FastAPI, Pydantic request models, SQLite store, Jinja templates, plain JavaScript, plain CSS, pytest, FastAPI TestClient.

---

## File Map

- Modify `server/open_artifacts_server/schema.py`: add supported visual block types and validation helpers for image sources, SVG allowlisting, chart types, callout tones, and structured lists.
- Modify `server/open_artifacts_server/static/app.js`: add renderers for `chart`, `image`, `svg`, `callout`, `stat-grid`, and `flow`; improve existing block markup; improve gallery card rendering.
- Modify `server/open_artifacts_server/static/styles.css`: replace the thin MVP styling with shared Editorial Lab Notebook tokens, viewer shell styles, gallery cards, and visual block styles.
- Modify `server/open_artifacts_server/templates/viewer.html`: add shell classes and accessible loading markup.
- Modify `server/open_artifacts_server/templates/gallery.html`: add shell classes and gallery masthead markup.
- Modify `open-artifacts/references/artifact-schema.md`: document new block shapes and safety rules.
- Modify `open-artifacts/SKILL.md`: instruct agents to use visual blocks when they improve comprehension.
- Modify `tests/server/test_schema.py`: cover valid and invalid visual blocks.
- Modify `tests/server/test_viewer.py`: cover template hooks for the updated shell.
- Add `tests/server/test_static_renderer.py`: lightweight static regression tests that confirm client renderers and CSS hooks exist without adding a JS build step.

---

### Task 1: Add Visual Block Schema Tests

**Files:**
- Modify: `tests/server/test_schema.py`

- [ ] **Step 1: Add visual payload test helpers**

Append these helpers after `base_payload()` in `tests/server/test_schema.py`:

```python
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
```

- [ ] **Step 2: Add acceptance and rejection tests**

Append these tests to `tests/server/test_schema.py`:

```python
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
    ],
)
def test_rejects_unsafe_svg(svg):
    payload = visual_payload()
    payload["blocks"] = [{"type": "svg", "svg": svg}]

    with pytest.raises(ValueError, match="Unsafe SVG"):
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
```

- [ ] **Step 3: Run schema tests and confirm failures**

Run:

```bash
uv run pytest tests/server/test_schema.py -v
```

Expected: the new tests fail with `Unsupported block type` and missing validation errors because the implementation has not been added yet.

- [ ] **Step 4: Commit failing tests**

Run:

```bash
git add tests/server/test_schema.py
git commit -m "test: cover visual artifact schema blocks"
```

Expected: commit succeeds.

---

### Task 2: Implement Visual Block Schema Validation

**Files:**
- Modify: `server/open_artifacts_server/schema.py`
- Test: `tests/server/test_schema.py`

- [ ] **Step 1: Add imports and constants**

In `server/open_artifacts_server/schema.py`, add this import near the existing imports:

```python
from xml.etree import ElementTree
```

Replace `SUPPORTED_BLOCKS` with:

```python
SUPPORTED_BLOCKS = {
    "markdown",
    "timeline",
    "code-reference",
    "command-output",
    "diff",
    "checklist",
    "metric",
    "table",
    "chart",
    "image",
    "svg",
    "callout",
    "stat-grid",
    "flow",
}
SUPPORTED_CHART_TYPES = {"bar", "line", "donut"}
SUPPORTED_CALLOUT_TONES = {"note", "decision", "warning", "success"}
SAFE_DATA_IMAGE_PREFIXES = (
    "data:image/png;",
    "data:image/jpeg;",
    "data:image/gif;",
    "data:image/webp;",
    "data:image/svg+xml;",
)
SAFE_SVG_TAGS = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "title",
    "desc",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
}
SAFE_SVG_ATTRS = {
    "aria-label",
    "class",
    "cx",
    "cy",
    "d",
    "fill",
    "height",
    "id",
    "offset",
    "opacity",
    "points",
    "r",
    "role",
    "rx",
    "ry",
    "stroke",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-width",
    "transform",
    "viewBox",
    "width",
    "x",
    "x1",
    "x2",
    "y",
    "y1",
    "y2",
}
```

- [ ] **Step 2: Add validation helpers**

Add these helpers above `validate_payload`:

```python
def _is_safe_image_src(src: str) -> bool:
    normalized = src.strip().lower()
    if not normalized:
        return False
    if normalized.startswith(("http://", "https://", "/", "./", "../")):
        return True
    if normalized.startswith(SAFE_DATA_IMAGE_PREFIXES):
        return True
    return False


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _validate_svg(svg: str) -> None:
    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as error:
        raise ValueError("Unsafe SVG") from error

    if _local_name(root.tag) != "svg":
        raise ValueError("Unsafe SVG")

    for element in root.iter():
        tag = _local_name(element.tag)
        if tag not in SAFE_SVG_TAGS:
            raise ValueError("Unsafe SVG")
        for attr, value in element.attrib.items():
            attr_name = _local_name(attr)
            if attr_name.startswith("on") or attr_name not in SAFE_SVG_ATTRS:
                raise ValueError("Unsafe SVG")
            if isinstance(value, str) and value.strip().lower().startswith(
                ("javascript:", "vbscript:", "data:text/html")
            ):
                raise ValueError("Unsafe SVG")


def _validate_visual_block(block: dict[str, Any]) -> None:
    block_type = block.get("type")
    if block_type == "chart" and block.get("chart_type", "bar") not in SUPPORTED_CHART_TYPES:
        raise ValueError("Unsupported chart type")
    if block_type == "image" and not _is_safe_image_src(str(block.get("src", ""))):
        raise ValueError("Unsafe image source")
    if block_type == "svg":
        _validate_svg(str(block.get("svg", "")))
    if block_type == "callout" and block.get("tone", "note") not in SUPPORTED_CALLOUT_TONES:
        raise ValueError("Unsupported callout tone")
```

- [ ] **Step 3: Call visual validation from `validate_payload`**

Inside the `for` loop in `validate_payload`, after the existing markdown raw HTML check, add:

```python
        _validate_visual_block(block)
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
uv run pytest tests/server/test_schema.py -v
```

Expected: all tests in `tests/server/test_schema.py` pass.

- [ ] **Step 5: Run full server test suite**

Run:

```bash
uv run pytest tests/server -v
```

Expected: all server tests pass.

- [ ] **Step 6: Commit schema implementation**

Run:

```bash
git add server/open_artifacts_server/schema.py tests/server/test_schema.py
git commit -m "feat: validate visual artifact blocks"
```

Expected: commit succeeds.

---

### Task 3: Add Static Renderer Regression Tests

**Files:**
- Create: `tests/server/test_static_renderer.py`
- Test: `server/open_artifacts_server/static/app.js`
- Test: `server/open_artifacts_server/static/styles.css`

- [ ] **Step 1: Create static renderer tests**

Create `tests/server/test_static_renderer.py`:

```python
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
```

- [ ] **Step 2: Run static renderer tests and confirm failures**

Run:

```bash
uv run pytest tests/server/test_static_renderer.py -v
```

Expected: tests fail because the renderers and CSS hooks do not exist yet.

- [ ] **Step 3: Commit failing static tests**

Run:

```bash
git add tests/server/test_static_renderer.py
git commit -m "test: cover visual renderer hooks"
```

Expected: commit succeeds.

---

### Task 4: Implement Visual Block Renderers and Gallery Cards

**Files:**
- Modify: `server/open_artifacts_server/static/app.js`
- Test: `tests/server/test_static_renderer.py`

- [ ] **Step 1: Replace `renderMarkdown` and add shared block helpers**

In `server/open_artifacts_server/static/app.js`, replace `renderMarkdown` with:

```javascript
function renderBlockShell(block, body, className = "") {
  const title = block.title ? `<h2>${escapeHtml(block.title)}</h2>` : "";
  const caption = block.caption ? `<p class="caption">${escapeHtml(block.caption)}</p>` : "";
  return `<section class="block ${className}">${title}${body}${caption}</section>`;
}

function renderMarkdown(block) {
  const paragraphs = text(block.content || "")
    .split(/\n{2,}/)
    .filter(Boolean)
    .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
    .join("");
  return renderBlockShell(block, paragraphs || "<p></p>", "block-markdown");
}
```

- [ ] **Step 2: Add chart renderers**

Add these functions after `renderMarkdown`:

```javascript
function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function renderBarChart(block, series) {
  const max = Math.max(...series.map((item) => numberValue(item.value)), 1);
  const bars = series
    .map((item, index) => {
      const value = numberValue(item.value);
      const width = Math.max((value / max) * 100, 2);
      return `<div class="bar-row" style="--bar-width:${width}%"><span>${escapeHtml(item.label)}</span><div><i></i></div><strong>${escapeHtml(item.value)}</strong></div>`;
    })
    .join("");
  return `<div class="bar-chart">${bars}</div>`;
}

function renderLineChart(block, series) {
  const values = series.map((item) => numberValue(item.value));
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const spread = Math.max(max - min, 1);
  const points = values
    .map((value, index) => {
      const x = series.length === 1 ? 50 : (index / (series.length - 1)) * 100;
      const y = 90 - ((value - min) / spread) * 80;
      return `${x},${y}`;
    })
    .join(" ");
  const labels = series
    .map((item, index) => {
      const x = series.length === 1 ? 50 : (index / (series.length - 1)) * 100;
      return `<text x="${x}" y="116">${escapeHtml(item.label)}</text>`;
    })
    .join("");
  return `<svg class="line-chart" viewBox="0 0 100 124" role="img" aria-label="${escapeHtml(block.title || "Line chart")}"><polyline points="${points}"></polyline>${labels}</svg>`;
}

function renderDonutChart(block, series) {
  const total = Math.max(series.reduce((sum, item) => sum + numberValue(item.value), 0), 1);
  let offset = 25;
  const rings = series
    .map((item, index) => {
      const value = numberValue(item.value);
      const length = (value / total) * 100;
      const strokeOffset = offset;
      offset -= length;
      return `<circle class="donut-segment segment-${index % 6}" cx="50" cy="50" r="36" pathLength="100" stroke-dasharray="${length} ${100 - length}" stroke-dashoffset="${strokeOffset}"></circle>`;
    })
    .join("");
  const legend = series
    .map((item, index) => `<li><span class="segment-dot segment-${index % 6}"></span>${escapeHtml(item.label)} <strong>${escapeHtml(item.value)}</strong></li>`)
    .join("");
  return `<div class="donut-wrap"><svg class="donut-chart" viewBox="0 0 100 100" role="img" aria-label="${escapeHtml(block.title || "Donut chart")}"><circle class="donut-track" cx="50" cy="50" r="36"></circle>${rings}</svg><ul>${legend}</ul></div>`;
}

function renderChart(block) {
  const series = Array.isArray(block.series) ? block.series : [];
  const chartType = block.chart_type || "bar";
  let body = "";
  if (chartType === "line") body = renderLineChart(block, series);
  else if (chartType === "donut") body = renderDonutChart(block, series);
  else body = renderBarChart(block, series);
  return renderBlockShell(block, body, `block-chart block-chart-${escapeHtml(chartType)}`);
}
```

- [ ] **Step 3: Add image, SVG, callout, stat-grid, and flow renderers**

Add these functions after `renderChart`:

```javascript
function renderImage(block) {
  const alt = escapeHtml(block.alt || block.title || "Artifact image");
  const src = escapeHtml(block.src || "");
  const body = `<figure><img src="${src}" alt="${alt}"></figure>`;
  return renderBlockShell(block, body, "block-image");
}

function renderSvg(block) {
  const body = `<div class="svg-frame">${block.svg || ""}</div>`;
  return renderBlockShell(block, body, "block-svg");
}

function renderCallout(block) {
  const tone = escapeHtml(block.tone || "note");
  const body = `<div class="callout-body"><p>${escapeHtml(block.content || "")}</p></div>`;
  return renderBlockShell(block, body, `block-callout callout-${tone}`);
}

function renderStatGrid(block) {
  const stats = (block.stats || [])
    .map((stat) => `<li><span>${escapeHtml(stat.label || "")}</span><strong>${escapeHtml(stat.value || "")}</strong><p>${escapeHtml(stat.detail || "")}</p></li>`)
    .join("");
  return renderBlockShell(block, `<ul class="stat-grid">${stats}</ul>`, "block-stat-grid");
}

function renderFlow(block) {
  const items = (block.items || [])
    .map((item, index) => `<li><span>${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(item.label || "")}</strong><p>${escapeHtml(item.detail || "")}</p></li>`)
    .join("");
  return renderBlockShell(block, `<ol class="flow-list">${items}</ol>`, "block-flow");
}
```

- [ ] **Step 4: Update `renderBlock` cases**

In `renderBlock`, add these cases before the fallback return:

```javascript
  if (block.type === "chart") return renderChart(block);
  if (block.type === "image") return renderImage(block);
  if (block.type === "svg") return renderSvg(block);
  if (block.type === "callout") return renderCallout(block);
  if (block.type === "stat-grid") return renderStatGrid(block);
  if (block.type === "flow") return renderFlow(block);
```

Also update existing block renderers to use `renderBlockShell` where practical:

```javascript
  if (block.type === "command-output" || block.type === "diff") {
    return renderBlockShell(
      block,
      `<pre>${escapeHtml(block.content || "")}</pre>`,
      `block-technical block-${escapeHtml(block.type)}`
    );
  }
```

- [ ] **Step 5: Update artifact header rendering**

In `loadArtifact`, replace the `artifact-root` template with:

```javascript
  const artifact = data.artifact || {};
  const source = payload.source || {};
  const workspace = payload.workspace || {};
  document.getElementById("artifact-root").innerHTML = `
    <article class="artifact-card">
      <div class="artifact-header">
        <div>
          <p class="eyebrow">${escapeHtml(payload.kind)} · ${escapeHtml(workspace.name || "default")} · v${escapeHtml(artifact.current_version || "")}</p>
          <h1>${escapeHtml(payload.title)}</h1>
          <p class="summary">${escapeHtml(payload.summary || "")}</p>
          <p class="meta-line">Published by ${escapeHtml(source.agent || "agent")}</p>
        </div>
        <span class="status">${escapeHtml(payload.status || "draft")}</span>
      </div>
      <div class="artifact-blocks">
        ${(payload.blocks || []).map(renderBlock).join("")}
      </div>
    </article>
  `;
```

- [ ] **Step 6: Update version rail rendering**

In `loadArtifact`, replace the `versions-root` assignment with:

```javascript
  document.getElementById("versions-root").innerHTML = `<h2>Versions</h2><div class="version-list">${versions.map((version) => `<div class="version"><strong>v${version.version_number}</strong><small>${escapeHtml(version.created_at)}</small></div>`).join("")}</div>`;
```

- [ ] **Step 7: Update gallery rendering**

In `loadGallery`, replace the `root.innerHTML = artifacts...` expression with:

```javascript
    root.innerHTML = `<div class="gallery-grid">${
      artifacts
        .filter((artifact) => artifact.title.toLowerCase().includes(query))
        .map((artifact) => `<a class="artifact-row" href="/a/${artifact.id}">
          <span class="artifact-kind">${escapeHtml(artifact.kind)}</span>
          <strong>${escapeHtml(artifact.title)}</strong>
          <p>${escapeHtml(artifact.summary || "")}</p>
          <span class="artifact-row-meta">${escapeHtml(artifact.status || "draft")} · v${artifact.current_version}</span>
        </a>`)
        .join("") || "<p>No artifacts found.</p>"
    }</div>`;
```

- [ ] **Step 8: Run static renderer tests and confirm JavaScript hooks pass**

Run:

```bash
uv run pytest tests/server/test_static_renderer.py -v
```

Expected: JavaScript renderer assertions pass. CSS hook assertions still fail until Task 5.

- [ ] **Step 9: Commit JavaScript renderers**

Run:

```bash
git add server/open_artifacts_server/static/app.js tests/server/test_static_renderer.py
git commit -m "feat: render visual artifact blocks"
```

Expected: commit succeeds.

---

### Task 5: Implement Editorial Lab Notebook Shell and Block Styling

**Files:**
- Modify: `server/open_artifacts_server/static/styles.css`
- Modify: `server/open_artifacts_server/templates/viewer.html`
- Modify: `server/open_artifacts_server/templates/gallery.html`
- Modify: `tests/server/test_viewer.py`
- Test: `tests/server/test_static_renderer.py`

- [ ] **Step 1: Update viewer and gallery template classes**

In `server/open_artifacts_server/templates/viewer.html`, change:

```html
    <main>
      <section id="artifact-root" class="surface">Loading artifact...</section>
      <aside id="versions-root" class="versions"></aside>
    </main>
```

to:

```html
    <main class="artifact-shell">
      <section id="artifact-root" class="surface" aria-live="polite">Loading artifact...</section>
      <aside id="versions-root" class="versions"></aside>
    </main>
```

In `server/open_artifacts_server/templates/gallery.html`, change:

```html
    <main>
      <section class="surface">
```

to:

```html
    <main class="gallery-shell">
      <section class="surface gallery-surface">
```

- [ ] **Step 2: Update viewer tests for shell hooks**

In `tests/server/test_viewer.py`, add assertions:

```python
    assert 'class="artifact-shell"' in response.text
    assert 'aria-live="polite"' in response.text
```

inside `test_viewer_route_contains_artifact_bootstrap`, and:

```python
    assert 'class="gallery-shell"' in response.text
    assert 'class="surface gallery-surface"' in response.text
```

inside `test_gallery_route_contains_gallery_bootstrap`.

- [ ] **Step 3: Replace CSS with the shared visual system**

Replace `server/open_artifacts_server/static/styles.css` with a complete stylesheet that defines:

```css
:root {
  color-scheme: light;
  --canvas: #f8f4ec;
  --canvas-ink: #211d19;
  --surface: #fffdf8;
  --surface-bone: #f0eadf;
  --surface-dark: #1f1d1a;
  --surface-dark-2: #2b2925;
  --muted: #716b61;
  --muted-2: #9b9286;
  --line: rgba(33, 29, 25, 0.16);
  --line-strong: rgba(33, 29, 25, 0.34);
  --accent: #df5b2f;
  --accent-deep: #a93d21;
  --success: #417d57;
  --warning: #a8671c;
  --danger: #a94438;
  --shadow: 0 18px 48px rgba(64, 49, 29, 0.12);
  --radius: 8px;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --body: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --display: Georgia, "Times New Roman", serif;
}
```

The stylesheet must include selectors checked by `tests/server/test_static_renderer.py`: `.artifact-shell`, `.artifact-card`, `.block-chart`, `.block-image`, `.block-svg`, `.block-callout`, `.stat-grid`, `.flow-list`, and `.gallery-grid`.

It must also include responsive rules:

```css
@media (max-width: 900px) {
  .artifact-shell,
  .gallery-shell {
    grid-template-columns: 1fr;
    width: min(100% - 24px, 1120px);
  }

  .artifact-header,
  .section-header {
    grid-template-columns: 1fr;
  }

  .gallery-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 4: Run viewer and static tests**

Run:

```bash
uv run pytest tests/server/test_viewer.py tests/server/test_static_renderer.py -v
```

Expected: both test files pass.

- [ ] **Step 5: Commit shell and CSS**

Run:

```bash
git add server/open_artifacts_server/static/styles.css server/open_artifacts_server/templates/viewer.html server/open_artifacts_server/templates/gallery.html tests/server/test_viewer.py tests/server/test_static_renderer.py
git commit -m "feat: apply artifact visual system"
```

Expected: commit succeeds.

---

### Task 6: Update Artifact Schema and Skill Guidance

**Files:**
- Modify: `open-artifacts/references/artifact-schema.md`
- Modify: `open-artifacts/SKILL.md`

- [ ] **Step 1: Update schema reference**

In `open-artifacts/references/artifact-schema.md`, add the new supported blocks after the existing `table` entry:

```markdown
- `chart`: `{ "type": "chart", "title": "Test trend", "chart_type": "bar", "series": [{"label": "Unit", "value": 42}], "caption": "Tests passing by category." }`
- `image`: `{ "type": "image", "title": "Reference screenshot", "src": "https://example.com/screenshot.png", "alt": "Reference screenshot", "caption": "User-provided visual reference." }`
- `svg`: `{ "type": "svg", "title": "System flow", "svg": "<svg viewBox=\"0 0 120 40\" role=\"img\" aria-label=\"System flow\"><rect x=\"4\" y=\"4\" width=\"40\" height=\"20\"></rect></svg>", "caption": "Generated diagram." }`
- `callout`: `{ "type": "callout", "tone": "decision", "title": "Decision", "content": "Use the Editorial Lab Notebook style." }`
- `stat-grid`: `{ "type": "stat-grid", "title": "Run summary", "stats": [{"label": "Tests", "value": "24", "detail": "all passing"}] }`
- `flow`: `{ "type": "flow", "title": "Publishing loop", "items": [{"label": "Agent", "detail": "Builds payload"}] }`
```

Add this safety paragraph before `Do not include raw HTML or JavaScript.`:

```markdown
Prefer visual blocks when they make the artifact easier to understand: use `chart` for quantitative comparisons, `flow` for processes or architecture, `stat-grid` for key figures, `image` for browser-visible screenshots or generated images, `svg` for compact generated diagrams, and `callout` for decisions, risks, outcomes, or next steps.

`image.src` must be browser-visible: use `http`/`https`, a relative URL already served by the Open Artifacts server, or a small `data:image/png`, `data:image/jpeg`, `data:image/gif`, `data:image/webp`, or `data:image/svg+xml` payload. Local filesystem paths from a conversation are not automatically visible in the browser.

`svg` is restricted to safe inline SVG only. Do not include scripts, event handlers, `foreignObject`, external references, or unsafe URL protocols.
```

- [ ] **Step 2: Update skill workflow guidance**

In `open-artifacts/SKILL.md`, replace step 5:

```markdown
5. Build a payload using `references/artifact-schema.md`.
```

with:

```markdown
5. Build a payload using `references/artifact-schema.md`. Prefer structured visual blocks when they improve comprehension: `chart` for numbers and trends, `flow` for processes and architecture, `stat-grid` for key figures, `image` for browser-visible screenshots or generated images, `svg` for compact diagrams, and `callout` for decisions, risks, outcomes, or next steps. Use `markdown` for narrative context, not as the default container for everything.
```

Add this guardrail:

```markdown
- Do not use local filesystem image paths unless they are served by the Open Artifacts server; use browser-visible URLs, generated SVG, or small safe `data:image` payloads.
```

- [ ] **Step 3: Run full tests**

Run:

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit documentation updates**

Run:

```bash
git add open-artifacts/references/artifact-schema.md open-artifacts/SKILL.md
git commit -m "docs: guide visual artifact generation"
```

Expected: commit succeeds.

---

### Task 7: Manual Visual Verification

**Files:**
- No committed files required unless verification finds a defect.

- [ ] **Step 1: Start the development server**

Run:

```bash
uv run uvicorn open_artifacts_server.app:app --app-dir server --host 127.0.0.1 --port 8787
```

Expected: server listens on `http://127.0.0.1:8787`.

- [ ] **Step 2: Publish a visual smoke artifact**

Create `/private/tmp/open-artifacts-visual-smoke.json` with:

```json
{
  "schema_version": "0.1",
  "title": "Visual smoke artifact",
  "kind": "dashboard",
  "summary": "A smoke test covering the Editorial Lab Notebook shell and visual blocks.",
  "status": "ready",
  "workspace": {"name": "visual-system"},
  "source": {"agent": "codex", "skill_version": "0.1.0", "published_by": "developer"},
  "blocks": [
    {"type": "callout", "tone": "decision", "title": "Selected direction", "content": "Use the Editorial Lab Notebook style as the default."},
    {"type": "stat-grid", "title": "Run summary", "stats": [{"label": "Tests", "value": "24", "detail": "all passing"}, {"label": "Blocks", "value": "6", "detail": "visual types"}]},
    {"type": "chart", "title": "Block coverage", "chart_type": "bar", "series": [{"label": "Text", "value": 2}, {"label": "Visual", "value": 6}, {"label": "Technical", "value": 3}], "caption": "Structured blocks can carry visual weight."},
    {"type": "flow", "title": "Publishing loop", "items": [{"label": "Agent", "detail": "Builds payload"}, {"label": "Server", "detail": "Stores version"}, {"label": "Viewer", "detail": "Renders live artifact"}]},
    {"type": "svg", "title": "Simple system diagram", "svg": "<svg viewBox=\"0 0 360 120\" role=\"img\" aria-label=\"System diagram\"><rect x=\"16\" y=\"32\" width=\"88\" height=\"48\" rx=\"6\"></rect><text x=\"36\" y=\"61\">Agent</text><line x1=\"104\" y1=\"56\" x2=\"156\" y2=\"56\"></line><rect x=\"156\" y=\"32\" width=\"88\" height=\"48\" rx=\"6\"></rect><text x=\"176\" y=\"61\">Server</text><line x1=\"244\" y1=\"56\" x2=\"296\" y2=\"56\"></line><rect x=\"296\" y=\"32\" width=\"48\" height=\"48\" rx=\"6\"></rect><text x=\"306\" y=\"61\">UI</text></svg>", "caption": "Safe inline SVG diagram."}
  ]
}
```

Publish it:

```bash
uv run python open-artifacts/scripts/publish_artifact.py --config open-artifacts/config/open-artifacts.toml --payload /private/tmp/open-artifacts-visual-smoke.json --idempotency-key visual-smoke-1
```

Expected: command prints a JSON response with a URL under `http://127.0.0.1:8787/a/`.

- [ ] **Step 3: Verify in browser**

Open:

```text
http://127.0.0.1:8787/gallery
```

Expected:

- Gallery uses a card grid, not a plain row list.
- Artifact detail uses the Editorial Lab Notebook shell.
- Chart, stat-grid, flow, callout, and SVG blocks render without console errors.
- At mobile width, the version rail stacks below the artifact and text does not overlap.

- [ ] **Step 4: Run final tests**

Run:

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Confirm verification did not leave uncommitted changes**

Run:

```bash
git status --short
```

Expected: no tracked files are modified. Known unrelated untracked files may still appear: `.DS_Store`, `.idea/`, `.superpowers/`, and `server/open_artifacts_server/__pycache__/`.

---

## Self-Review Notes

- Spec coverage: Tasks 1-2 cover schema and safety; Tasks 3-5 cover renderer, gallery, viewer, and shared CSS; Task 6 covers generation guidance; Task 7 covers manual browser verification.
- Scope check: runtime theme switching, arbitrary HTML/JS, server-side image generation, and full file upload management remain out of scope.
- Type consistency: block names match the spec exactly: `chart`, `image`, `svg`, `callout`, `stat-grid`, and `flow`.
