---
name: open-artifacts
description: Publish agent work as Open Artifacts. Use when the user asks to create, update, publish, share, visualize, or turn current agent work into an artifact, live page, investigation page, PR walkthrough, checklist, dashboard, or Gallery item.
---

# Open Artifacts

Use this Skill to publish the current agent-visible work context to a preconfigured Open Artifacts server.

## Workflow

1. Determine whether the user wants a new Artifact or an update to an existing Artifact.
2. If updating, reuse the visible `artifact_id` from the conversation.
3. Gather only context visible to the agent: user request, conversation summary, files read, diffs, command output, test results, and explicit user-provided material.
4. Choose `kind`: `work-summary`, `investigation`, `walkthrough`, `checklist`, or `dashboard`.
5. Build a payload using `references/artifact-schema.md`. Prefer structured visual blocks when they improve comprehension: `chart` for numbers and trends, `flow` for processes and architecture, `stat-grid` for key figures, `image` for browser-visible screenshots or generated images, and `callout` for decisions, risks, outcomes, or next steps. Use `markdown` for narrative context, not as the default container for everything. Use `svg` only when a compact inline drawing is necessary and you can keep it inside the safe SVG whitelist.
6. Publish using `scripts/publish_artifact.py` and `references/publishing-protocol.md`.
7. Report the returned URL, version, and `artifact_id`.
8. Keep the `artifact_id` in the response so future turns can update the same Artifact.

## Guardrails

- Prefer piping payload JSON to `scripts/publish_artifact.py --payload -`. If a payload file is unavoidable, write it inside the current workspace or the runtime's ordinary temp directory. Never create or write payload files in privileged or sensitive root paths such as `C:\`, `C:\Temp`, `/`, `/root`, `/System`, or `/Windows`.
- Do not claim access to hidden agent internals.
- Do not include secrets unless the user explicitly asks and the server is approved for that data.
- Do not put raw HTML or JavaScript in Markdown blocks.
- Prefer concise blocks over dumping full logs.
- Use code references for file locations instead of embedding large source files.
- Do not use local filesystem image paths unless they are served by the Open Artifacts server; use browser-visible URLs or small safe raster `data:image/png`, `data:image/jpeg`, `data:image/gif`, or `data:image/webp` payloads.
- Avoid generating custom SVG unless the user explicitly needs an inline SVG. For process diagrams, use `flow`; for tabular comparisons, use `table`; for numbers, use `chart` or `stat-grid`; for decisions and risks, use `callout`. If an SVG publish fails with `Unsafe SVG`, read the specific disallowed tag or attribute from the error, remove every non-whitelisted construct, and retry at most once before switching to structured blocks.
- On `401` or `Invalid publish token`, stop. Do not retry without a token, do not guess common passwords, and do not probe environment variables. Ask the user for the correct publish token or for confirmation that `open-artifacts/config/open-artifacts.toml` has been updated.
- If environment overrides are needed, use only the documented keys: `OPEN_ARTIFACTS_SERVER_URL`, `OPEN_ARTIFACTS_API_BASE`, `OPEN_ARTIFACTS_ORGANIZATION`, `OPEN_ARTIFACTS_WORKSPACE`, `OPEN_ARTIFACTS_DEFAULT_VISIBILITY`, and `OPEN_ARTIFACTS_PUBLISH_TOKEN`.
- The URL returned by the server is based on the server's `OPEN_ARTIFACTS_PUBLIC_BASE_URL`, not only this Skill's `server_url`. If a deployed server runs behind nginx on a non-default port such as `8788`, the backend deployment must set `PUBLIC_BASE_URL` or `OPEN_ARTIFACTS_PUBLIC_BASE_URL` to include that port.
