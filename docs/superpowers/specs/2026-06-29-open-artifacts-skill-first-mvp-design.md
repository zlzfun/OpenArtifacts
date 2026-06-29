# Open Artifacts Skill-First MVP Design

## Context

Open Artifacts is an open-source implementation direction inspired by Anthropic's "Artifacts in Claude Code" announcement published on June 18, 2026. The reference product turns an agent session into a live, shareable, interactive web artifact built from session context, updates the same link over time, keeps version history, exposes a gallery, and defaults to private organization-bounded sharing.

The Gemini-generated requirements analysis supplied at project start was useful as a broad roadmap, but it overstated MVP scope and is intentionally not kept in the repository source tree. The MVP must focus on the core loop: an agent publishes current work context into a structured artifact, the server renders it at a stable URL, and later publishes update the same page with version history.

## Product Direction

Use a Skill-first architecture for MVP.

The first deployable user-facing surface is an `open-artifacts` Skill that runs inside an agent environment such as Codex, Claude Code, or another Skill-compatible agent. The Skill is responsible for converting the agent-visible context into an Artifact payload and publishing that payload to a preconfigured Open Artifacts server.

The server is a separate backend product. It is not bundled into the Skill and is not started by the Skill. The Skill assumes the server has already been deployed for a specific domain, department, or local development environment.

## Goals

- Let a user ask an agent to create or update an Artifact from current work.
- Let the Skill collect agent-visible context, summarize it, and shape it into a controlled payload.
- Publish the payload to a preconfigured server without per-user setup.
- Return a stable Artifact URL.
- Keep all subsequent updates under the same URL.
- Store version history and support restore.
- Render a safe, useful viewer and a Gallery.
- Support live in-place viewer refresh when an Artifact is republished.

## Non-Goals For MVP

- Do not build a desktop app.
- Do not package the server inside the Skill.
- Do not require users to configure environment variables during Skill install.
- Do not support public anonymous sharing.
- Do not execute arbitrary HTML or JavaScript from Artifact payloads.
- Do not build deep integrations for Prometheus, Jira, GitHub, GitLab, Terraform, or cloud providers.
- Do not build a plugin marketplace or arbitrary component extension system.
- Do not implement full enterprise RBAC, retention policies, or compliance APIs.

## Architecture Overview

The system has two main parts.

```text
Agent session
  -> open-artifacts Skill
  -> publish HTTP API
  -> open-artifacts-server
  -> Artifact viewer / Gallery
```

The Skill is the publishing adapter. The server is the product runtime.

### Skill Responsibilities

- Trigger when the user asks for an artifact, shareable visual page, work summary, investigation page, PR walkthrough, checklist, or dashboard.
- Inspect the agent-visible context: conversation, files the agent has read, diffs, command outputs, test results, and explicit user-provided material.
- Decide whether to create a new Artifact or update an existing one.
- Build a schema-compliant Artifact payload.
- Read bundled configuration.
- Call the server publish API.
- Return the stable URL and the current version number.
- Keep the `artifact_id` visible in the conversation so future updates reuse the same Artifact.
- In MVP, do not write local state files for `artifact_id`; same-session updates rely on the visible conversation context.

The Skill does not claim access to hidden agent internals. It can use context available to the current agent runtime and any files or tool outputs the agent can legitimately inspect.

### Server Responsibilities

- Authenticate publish requests.
- Validate payloads.
- Create Artifacts and append versions.
- Maintain the stable Artifact URL.
- Render Artifact pages from safe structured blocks.
- Provide Gallery, version history, and restore.
- Push update events to open viewer pages.
- Enforce read access and sharing rules.

## Repository Shape

The repo should separate Skill and server source clearly.

```text
<repo-root>/
  open-artifacts/
    SKILL.md
    agents/openai.yaml
    config/open-artifacts.toml
    references/artifact-schema.md
    references/publishing-protocol.md
    scripts/publish_artifact.py
  server/
    backend source
    viewer source
  tests/
```

`scripts/publish_artifact.py` is a lightweight HTTP client helper, not a server. Its purpose is to make publish requests deterministic across agent runtimes and avoid brittle hand-written HTTP calls by the model.

## MVP Technology Choices

Use Python for both the Skill helper and server in MVP.

- Backend: FastAPI.
- Storage: SQLite through Python's standard `sqlite3` module or a small migration helper.
- Viewer and Gallery: server-rendered HTML templates plus vanilla JavaScript for fetch and SSE.
- Styling: plain CSS served by the backend.
- Tests: pytest for server behavior and helper script behavior.

Do not introduce a frontend build pipeline in MVP. The viewer needs predictable rendering and live refresh, not a complex client application.

## Configuration Model

Use domain-preconfigured Skill configuration as the default path.

Configuration priority:

1. Skill bundled config: default server URL, API base path, organization, workspace, default visibility, and publish token.
2. Optional user local override config for debugging or temporary switching.
3. Optional environment variable override as an advanced escape hatch.

The GitHub version must not contain internal server information. It should use localhost defaults or placeholder values. Department-distributed Skill builds can replace `open-artifacts/config/open-artifacts.toml` with real server information. When deployment changes, the Skill distribution is updated.

Example open-source config:

```toml
server_url = "http://localhost:8787"
api_base = "/api"
organization = "local-dev"
workspace = "default"
default_visibility = "private"
publish_token = "dev-token"
```

MVP uses a static publish token in the Skill config for domain-distributed builds. This is acceptable only for the initial department-scoped prototype. Later versions should support per-user or per-workspace tokens issued by an identity layer.

## Artifact Payload Schema

MVP uses a controlled JSON schema. The server stores raw payload JSON but the viewer only renders known block types.

Top-level payload:

```json
{
  "schema_version": "0.1",
  "artifact_id": "optional-existing-id",
  "title": "Auth bug investigation",
  "kind": "investigation",
  "summary": "Short human-readable summary.",
  "status": "draft",
  "workspace": {
    "name": "payments-service",
    "repository": "git@github.com:org/repo.git",
    "branch": "feature/auth-fix",
    "commit": "abc123"
  },
  "source": {
    "agent": "codex",
    "skill_version": "0.1.0",
    "published_by": "user-or-agent-name"
  },
  "blocks": []
}
```

Supported `kind` values:

- `work-summary`
- `investigation`
- `walkthrough`
- `checklist`
- `dashboard`

Supported block types:

- `markdown`: sanitized Markdown with raw HTML disabled.
- `timeline`: ordered event list with time, label, and detail.
- `code-reference`: file path and line range references.
- `command-output`: command, exit code, and trimmed output.
- `diff`: unified diff text.
- `checklist`: checklist items with `todo`, `doing`, `done`, or `blocked` state.
- `metric`: simple metric value, trend, and detail.
- `table`: small tabular data.

Security constraints:

- No arbitrary JavaScript in payloads.
- No raw HTML rendering from Markdown.
- Links use safe protocols only.
- Code references do not cause the public viewer to read repository files.
- Payload size limits are enforced by the server.

## Publishing Protocol

Publish endpoint:

```http
POST /api/artifacts/publish
Authorization: Bearer <publish_token>
Content-Type: application/json
```

Request body:

```json
{
  "artifact_id": "optional-existing-id",
  "idempotency_key": "agent-generated-unique-key",
  "visibility": "private",
  "payload": {
    "schema_version": "0.1",
    "title": "Example",
    "kind": "investigation",
    "blocks": []
  }
}
```

Response body:

```json
{
  "artifact_id": "art_123",
  "version": 3,
  "url": "https://artifacts.example.com/a/art_123",
  "gallery_url": "https://artifacts.example.com/gallery"
}
```

Error behavior:

- `401`: report invalid Skill/server configuration.
- `422`: report schema validation errors and revise the payload before retrying.
- `409`: report idempotency conflict and fetch current state before retrying.
- Network failure: preserve the generated payload in the conversation or a temporary file and tell the user publishing failed.

## Server Data Model

Core records:

```text
Artifact
- id
- title
- kind
- owner
- organization
- workspace
- visibility
- status
- current_version
- archived_at
- created_at
- updated_at

ArtifactVersion
- id
- artifact_id
- version_number
- payload
- summary
- created_by
- created_at

PublishEvent
- id
- artifact_id
- version_number
- event_type
- created_at
```

MVP storage should use SQLite for simple deployment. The data model should avoid SQLite-specific API assumptions so a later Postgres migration does not change API semantics.

## Server API

Required MVP endpoints:

```text
POST /api/artifacts/publish
GET /api/artifacts
GET /api/artifacts/:id
GET /api/artifacts/:id/versions
POST /api/artifacts/:id/restore
PATCH /api/artifacts/:id
GET /api/artifacts/:id/events
GET /a/:artifact_id
GET /gallery
```

`GET /api/artifacts/:id/events` should use Server-Sent Events for MVP. Artifact updates are one-way server-to-browser notifications, so SSE is simpler than WebSocket while still satisfying in-place refresh.

## Viewer And Gallery

The viewer is a server-hosted page at `/a/:artifact_id`. It fetches the current Artifact payload and renders controlled blocks. When it receives an SSE update event, it refetches the current version and updates in place.

The Gallery is a workspace-level page at `/gallery`. MVP Gallery supports:

- List Artifacts.
- Filter by title, kind, owner, status, visibility, and updated time.
- Open Artifact.
- Copy link.
- Archive Artifact.
- Change title or status.
- Switch `private` and `workspace` visibility.
- View versions.
- Restore a version.

## Permissions And Sharing

MVP uses two visibility values:

- `private`: only the author or an administrator can view.
- `workspace`: authenticated users in the same workspace can view.

The open-source local development mode can degrade to token or local-network access, but the schema and server model still keep `owner`, `organization`, `workspace`, and `visibility` fields.

The server must not provide public anonymous sharing in MVP. If deployed behind an existing department gateway or OIDC proxy, the server can trust upstream identity headers after explicit configuration.

## MVP User Flow

1. A department user installs the preconfigured `open-artifacts` Skill.
2. The user asks the agent to create an Artifact from current work.
3. The Skill gathers available context and produces a payload.
4. The Skill publishes to the preconfigured server.
5. The server creates an Artifact and version 1.
6. The Skill returns a fixed URL.
7. The user opens the URL in a browser.
8. The user asks the agent to update the Artifact as work progresses.
9. The Skill republishes using the same `artifact_id`.
10. The open viewer refreshes in place.
11. The Gallery lists the Artifact.
12. The user can inspect and restore previous versions.

## MVP Completion Criteria

The MVP is complete when the following work end-to-end:

- Install a preconfigured Skill.
- Publish a new Artifact from an agent session.
- Render the Artifact at a stable URL.
- Update the same Artifact from the same session.
- Refresh an already open viewer without manual page reload.
- Show the Artifact in Gallery.
- Show version history.
- Restore a previous version.
- Reject malformed payloads with useful validation errors.
- Avoid rendering arbitrary HTML or JavaScript from payloads.

## Roadmap After MVP

Beta:

- Dedicated templates for PR walkthrough and incident investigation.
- Postgres storage option.
- OIDC integration.
- Better search and filtering.
- Artifact export.
- Retention policy.
- Basic audit log.

Later:

- Connector framework.
- Template/plugin ecosystem.
- Compliance API.
- Organization admin console.
- Role-based scoping.
- Dedicated templates for license audit, privacy data flow, cloud resource maps, security findings, UX variants, and engineering delivery dashboards.
- Desktop app integration if there is a compelling user flow.
