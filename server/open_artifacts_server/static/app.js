function text(value) {
  return value == null ? "" : String(value);
}

function escapeHtml(value) {
  return text(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

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

function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function renderBarChart(block, series) {
  const max = Math.max(...series.map((item) => numberValue(item.value)), 1);
  const bars = series
    .map((item) => {
      const value = numberValue(item.value);
      const width = Math.max((value / max) * 100, 2);
      return `<div class="bar-row" style="--bar-width:${width}%"><span>${escapeHtml(item.label ?? "")}</span><div><i></i></div><strong>${escapeHtml(item.value ?? "")}</strong></div>`;
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
      return `<text x="${x}" y="116">${escapeHtml(item.label ?? "")}</text>`;
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
    .map((item, index) => `<li><span class="segment-dot segment-${index % 6}"></span>${escapeHtml(item.label ?? "")} <strong>${escapeHtml(item.value ?? "")}</strong></li>`)
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
    .map((stat) => `<li><span>${escapeHtml(stat.label ?? "")}</span><strong>${escapeHtml(stat.value ?? "")}</strong><p>${escapeHtml(stat.detail ?? "")}</p></li>`)
    .join("");
  return renderBlockShell(block, `<ul class="stat-grid">${stats}</ul>`, "block-stat-grid");
}

function renderFlow(block) {
  const items = (block.items || [])
    .map((item, index) => `<li><span>${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(item.label ?? "")}</strong><p>${escapeHtml(item.detail ?? "")}</p></li>`)
    .join("");
  return renderBlockShell(block, `<ol class="flow-list">${items}</ol>`, "block-flow");
}

function renderBlock(block) {
  if (block.type === "markdown") return renderMarkdown(block);
  if (block.type === "timeline") {
    const items = (block.items || []).map((item) => `<li><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.time || "")}</span><p>${escapeHtml(item.detail || "")}</p></li>`).join("");
    return `<section class="block"><h2>${escapeHtml(block.title || "Timeline")}</h2><ol class="timeline">${items}</ol></section>`;
  }
  if (block.type === "code-reference") {
    const refs = (block.references || []).map((ref) => `<li><code>${escapeHtml(ref.path)}:${escapeHtml(ref.start_line)}-${escapeHtml(ref.end_line)}</code> ${escapeHtml(ref.label || "")}</li>`).join("");
    return `<section class="block"><h2>${escapeHtml(block.title || "Code")}</h2><ul>${refs}</ul></section>`;
  }
  if (block.type === "command-output" || block.type === "diff") {
    return renderBlockShell(
      block,
      `<pre>${escapeHtml(block.content || "")}</pre>`,
      `block-technical block-${escapeHtml(block.type)}`
    );
  }
  if (block.type === "checklist") {
    const items = (block.items || []).map((item) => `<li data-state="${escapeHtml(item.state || "todo")}">${escapeHtml(item.label || "")}<p>${escapeHtml(item.detail || "")}</p></li>`).join("");
    return `<section class="block"><h2>${escapeHtml(block.title || "Checklist")}</h2><ul class="checklist">${items}</ul></section>`;
  }
  if (block.type === "metric") {
    return `<section class="block metric"><h2>${escapeHtml(block.title || "Metric")}</h2><strong>${escapeHtml(block.value || "")}</strong><span>${escapeHtml(block.trend || "")}</span><p>${escapeHtml(block.detail || "")}</p></section>`;
  }
  if (block.type === "table") {
    const head = (block.columns || []).map((column) => `<th>${escapeHtml(column)}</th>`).join("");
    const rows = (block.rows || []).map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("");
    return `<section class="block"><h2>${escapeHtml(block.title || "Table")}</h2><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></section>`;
  }
  if (block.type === "chart") return renderChart(block);
  if (block.type === "image") return renderImage(block);
  if (block.type === "svg") return renderSvg(block);
  if (block.type === "callout") return renderCallout(block);
  if (block.type === "stat-grid") return renderStatGrid(block);
  if (block.type === "flow") return renderFlow(block);
  return "";
}

async function loadArtifact(artifactId) {
  const response = await fetch(`/api/artifacts/${artifactId}`);
  if (!response.ok) throw new Error("Artifact not found");
  const data = await response.json();
  const payload = data.payload || {};
  const artifact = data.artifact || {};
  const source = payload.source || {};
  const workspace = payload.workspace || {};
  document.title = `${payload.title} - Open Artifact`;
  document.getElementById("artifact-root").innerHTML = `
    <article class="artifact-card">
      <div class="artifact-header">
        <div>
          <p class="eyebrow">${escapeHtml(payload.kind)} &middot; ${escapeHtml(workspace.name || "default")} &middot; v${escapeHtml(artifact.current_version || "")}</p>
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
  const versions = await fetch(`/api/artifacts/${artifactId}/versions`).then((res) => res.json());
  document.getElementById("versions-root").innerHTML = `<h2>Versions</h2><div class="version-list">${versions.map((version) => `<div class="version"><strong>v${escapeHtml(version.version_number)}</strong><small>${escapeHtml(version.created_at)}</small></div>`).join("")}</div>`;
}

async function loadGallery() {
  const artifacts = await fetch("/api/artifacts").then((res) => res.json());
  const filter = document.getElementById("gallery-filter");
  const root = document.getElementById("gallery-root");
  function render() {
    const query = (filter.value || "").toLowerCase();
    root.innerHTML = `<div class="gallery-grid">${
      artifacts
        .filter((artifact) => text(artifact.title).toLowerCase().includes(query))
        .map((artifact) => {
          const summary = artifact.summary ? `<p>${escapeHtml(artifact.summary)}</p>` : "";
          return `<a class="artifact-row" href="/a/${escapeHtml(artifact.id)}">
            <span class="artifact-kind">${escapeHtml(artifact.kind)}</span>
            <strong>${escapeHtml(artifact.title)}</strong>
            ${summary}
            <span class="artifact-row-meta">${escapeHtml(artifact.status || "draft")} &middot; v${escapeHtml(artifact.current_version)}</span>
          </a>`;
        })
        .join("") || "<p>No artifacts found.</p>"
    }</div>`;
  }
  filter.addEventListener("input", render);
  render();
}

const artifactId = document.body.dataset.artifactId;
if (artifactId) {
  loadArtifact(artifactId).catch((error) => {
    document.getElementById("artifact-root").textContent = error.message;
  });
  const events = new EventSource(`/api/artifacts/${artifactId}/events`);
  events.onmessage = () => loadArtifact(artifactId);
  const copy = document.getElementById("copy-link");
  copy.addEventListener("click", () => navigator.clipboard.writeText(window.location.href));
}

if (document.body.dataset.gallery) {
  loadGallery();
}
