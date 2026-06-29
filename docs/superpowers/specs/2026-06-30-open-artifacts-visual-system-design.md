# Open Artifacts Visual System Design

Date: 2026-06-30

## Goal

Open Artifacts already has a working MVP flow, but the current viewer and gallery read as a plain text renderer. This design upgrades the product into a consistent, visually credible artifact system while preserving the MVP's security and simplicity.

The default visual direction is **Editorial Lab Notebook**: a warm paper canvas, high-contrast ink typography, hairline structure, restrained orange accents, and selective dark technical modules. It is inspired by developer-tool references from `awesome-design-md`, especially the readable lab-notebook feel of Replicate and the structured technical restraint of OpenCode.

Two alternate directions are archived for future theme work:

- **Dark Control Room**: a near-black product-console surface for dense dashboards and operational artifacts.
- **Bright Visual Canvas**: a lighter, image-forward gallery style for more creative or presentation-heavy artifacts.

The current implementation will not add runtime theme switching. It will structure the CSS and documentation so future themes can be added without rewriting the renderer.

## Scope

In scope:

- Redesign the gallery and artifact viewer with a shared design system.
- Extend the structured artifact schema with safe visual block types.
- Update client rendering so artifacts can include charts, images, SVG illustrations, callouts, stat grids, and flows.
- Update the Open Artifacts skill documentation so agents are encouraged to choose visual blocks when they improve comprehension.
- Add tests for schema validation and stable rendering behavior.

Out of scope for this pass:

- Arbitrary raw HTML or JavaScript in artifacts.
- A full theme picker or per-artifact theme selection.
- Server-side image generation.
- Remote asset fetching or full file upload management.

## Design Language

### Tokens

The CSS should centralize design tokens in `:root`:

- Canvas: warm off-white paper tone.
- Surface: clean white and bone panels.
- Ink: near-black text.
- Muted text: neutral gray-brown.
- Accent: restrained orange for active or highlighted moments.
- Technical dark: near-black module background for code, diffs, command output, and dense charts.
- Hairline: low-contrast border for page structure.

Border radii stay restrained at 4px to 8px. Cards should feel precise rather than bubbly. Shadows should be minimal and used only when they improve hierarchy.

### Typography

Use locally available font stacks without adding network font dependencies:

- Display/headings: a readable serif-forward stack for editorial weight, with safe fallbacks.
- UI/body: a clean system sans stack for predictable rendering and CJK compatibility.
- Technical text: `ui-monospace`, `SFMono-Regular`, `Menlo`, `Monaco`, `Consolas`, monospace.

Long artifacts must remain easy to scan. Headings, meta labels, captions, and code should each have distinct rhythm.

### Layout

The viewer remains a two-column shell on desktop:

- Main artifact surface: title, summary, source metadata, and content blocks.
- Version rail: compact version history with status and timestamps.

On mobile, the version rail stacks below the artifact.

The gallery becomes a card grid:

- Search stays at the top.
- Each card shows title, kind, status, version, summary, and updated time when available.
- Cards use the same token system as the viewer.

## Artifact Viewer

The viewer header should become a richer artifact masthead:

- Eyebrow row: kind, workspace, source agent, current version.
- Title and summary.
- Status pill.
- Optional visual summary strip when visual blocks are present.

Existing blocks get stronger presentation:

- `markdown`: editorial text block with improved typography.
- `timeline`: vertical event rail with time, label, and detail.
- `code-reference`: compact file-reference rows with path and line range.
- `command-output`, `diff`: dark technical modules.
- `checklist`: state-aware checklist rows.
- `metric`: metric tile with value, trend, and detail.
- `table`: readable table wrapper with horizontal overflow on small screens.

## Visual Blocks

The schema should add structured, safe block types.

### `chart`

Purpose: make data comparisons and trends visible without external libraries.

Shape:

```json
{
  "type": "chart",
  "title": "Test trend",
  "chart_type": "bar",
  "series": [
    {"label": "Unit", "value": 42},
    {"label": "Integration", "value": 9}
  ],
  "caption": "Tests passing by category."
}
```

Supported chart types for this pass:

- `bar`
- `line`
- `donut`

Rendering should use generated SVG strings from escaped structured data. No script execution is needed.

### `image`

Purpose: show relevant screenshots, diagrams, product images, or user-supplied reference material.

Shape:

```json
{
  "type": "image",
  "title": "Reference screenshot",
  "src": "data:image/png;base64,...",
  "alt": "Artifact reference screenshot",
  "caption": "User-provided visual reference."
}
```

Validation should reject `javascript:` and `data:text/html` style sources. Normal `http`/`https` URLs, relative URLs already served by the Open Artifacts server, and `data:image/png`, `data:image/jpeg`, `data:image/gif`, `data:image/webp`, or `data:image/svg+xml` sources are acceptable for this MVP.

Conversation-local image paths are not automatically browser-visible from an HTTP artifact page. The publishing helper can later add asset materialization that copies a local file into server-managed artifact assets. Until then, agents should use browser-visible URLs, generated SVG blocks, or small `data:image` payloads for local/generated images.

### `svg`

Purpose: support lightweight generated diagrams and illustrations.

Shape:

```json
{
  "type": "svg",
  "title": "System flow",
  "svg": "<svg viewBox=\"0 0 400 160\" role=\"img\" aria-label=\"System flow\">...</svg>",
  "caption": "Skill publishes to server, server renders artifact."
}
```

This is the only block that stores markup-like content. It must be restricted to an allowlist:

- Root must be `<svg>`.
- Disallow `<script>`, `<foreignObject>`, event handler attributes, external references, and unsafe URL protocols.
- Allow basic shape/text/path elements needed for diagrams.

### `callout`

Purpose: visually separate conclusions, warnings, decisions, or next steps.

Shape:

```json
{
  "type": "callout",
  "tone": "decision",
  "title": "Selected direction",
  "content": "Use the Editorial Lab Notebook style as the default."
}
```

Tones: `note`, `decision`, `warning`, `success`.

### `stat-grid`

Purpose: group several key numbers into a visual summary.

Shape:

```json
{
  "type": "stat-grid",
  "title": "Run summary",
  "stats": [
    {"label": "Tests", "value": "24", "detail": "all passing"},
    {"label": "Files changed", "value": "5"}
  ]
}
```

### `flow`

Purpose: represent steps or system relationships without raw SVG.

Shape:

```json
{
  "type": "flow",
  "title": "Publishing loop",
  "items": [
    {"label": "Agent", "detail": "Builds payload"},
    {"label": "Server", "detail": "Stores version"},
    {"label": "Viewer", "detail": "Renders live artifact"}
  ]
}
```

The renderer can draw this as connected cards using CSS and simple SVG connector lines.

## Generation Guidance

The Open Artifacts skill should instruct agents to choose the most expressive block type:

- Use `chart` for quantitative comparisons, trends, counts, or distributions.
- Use `flow` for architecture, process, or lifecycle explanations.
- Use `image` when the conversation includes screenshots, generated images, or relevant local visual files.
- Use `svg` for compact generated diagrams when `flow` is too limited.
- Use `stat-grid` for summaries with multiple key figures.
- Use `callout` for decisions, risks, outcomes, or next steps.
- Keep `markdown` for narrative context, not as the default container for everything.

The skill should still prefer concise artifacts and avoid dumping long logs or full source files.

## Security

The current raw HTML ban remains. New visual capability must be structured and sanitized:

- Escape all text before rendering.
- Validate block types server-side.
- Validate image URLs and SVG content server-side.
- Render chart and flow SVG from structured JSON in the client.
- Do not allow arbitrary JavaScript, inline event handlers, or remote script references.

## Testing

Schema tests:

- Accept all new block types with minimal valid payloads.
- Reject unknown block types.
- Reject raw HTML inside markdown.
- Reject unsafe image sources.
- Reject SVG with script, event handlers, `foreignObject`, or unsafe URLs.

Viewer tests:

- Confirm `/a/{artifact_id}` and `/gallery` still include bootstraps.
- Add renderer-oriented tests for `renderBlock` behavior if the JavaScript is made testable, or add stable DOM/class assertions through a lightweight browser smoke test.

Manual verification:

- Run `uv run pytest`.
- Start the FastAPI server.
- Publish or seed an artifact containing markdown, chart, image, callout, stat-grid, and flow blocks.
- Check desktop and mobile widths in browser.

## Implementation Notes

Keep changes in the existing MVP architecture:

- `server/open_artifacts_server/schema.py`: add block validation helpers.
- `open-artifacts/references/artifact-schema.md`: document new blocks.
- `open-artifacts/SKILL.md`: update generation guidance.
- `server/open_artifacts_server/static/app.js`: add structured renderers.
- `server/open_artifacts_server/static/styles.css`: implement the design system and block visuals.
- `server/open_artifacts_server/templates/*.html`: only adjust shell classes or small markup hooks as needed.
- `tests/server/test_schema.py` and viewer tests: cover validation and rendering expectations.

The implementation should avoid introducing a frontend build step. Plain CSS and JavaScript are sufficient for the MVP.
