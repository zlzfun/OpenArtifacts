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

function renderMarkdown(block) {
  return `<section class="block"><h2>${escapeHtml(block.title || "Notes")}</h2><p>${escapeHtml(block.content || "")}</p></section>`;
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
    return `<section class="block"><h2>${escapeHtml(block.title || block.type)}</h2><pre>${escapeHtml(block.content || "")}</pre></section>`;
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
  return "";
}

async function loadArtifact(artifactId) {
  const response = await fetch(`/api/artifacts/${artifactId}`);
  if (!response.ok) throw new Error("Artifact not found");
  const data = await response.json();
  const payload = data.payload;
  document.title = `${payload.title} - Open Artifact`;
  document.getElementById("artifact-root").innerHTML = `
    <div class="artifact-header">
      <div>
        <p class="eyebrow">${escapeHtml(payload.kind)}</p>
        <h1>${escapeHtml(payload.title)}</h1>
        <p>${escapeHtml(payload.summary || "")}</p>
      </div>
      <span class="status">${escapeHtml(payload.status || "draft")}</span>
    </div>
    ${(payload.blocks || []).map(renderBlock).join("")}
  `;
  const versions = await fetch(`/api/artifacts/${artifactId}/versions`).then((res) => res.json());
  document.getElementById("versions-root").innerHTML = `<h2>Versions</h2>${versions.map((version) => `<div class="version">v${version.version_number}<br><small>${escapeHtml(version.created_at)}</small></div>`).join("")}`;
}

async function loadGallery() {
  const artifacts = await fetch("/api/artifacts").then((res) => res.json());
  const filter = document.getElementById("gallery-filter");
  const root = document.getElementById("gallery-root");
  function render() {
    const query = (filter.value || "").toLowerCase();
    root.innerHTML = artifacts
      .filter((artifact) => artifact.title.toLowerCase().includes(query))
      .map((artifact) => `<a class="artifact-row" href="/a/${artifact.id}"><strong>${escapeHtml(artifact.title)}</strong><span>${escapeHtml(artifact.kind)}</span><span>v${artifact.current_version}</span></a>`)
      .join("") || "<p>No artifacts found.</p>";
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
