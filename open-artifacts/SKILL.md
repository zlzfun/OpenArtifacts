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
5. Build a payload using `references/artifact-schema.md`.
6. Publish using `scripts/publish_artifact.py` and `references/publishing-protocol.md`.
7. Report the returned URL, version, and `artifact_id`.
8. Keep the `artifact_id` in the response so future turns can update the same Artifact.

## Guardrails

- Do not claim access to hidden agent internals.
- Do not include secrets unless the user explicitly asks and the server is approved for that data.
- Do not put raw HTML or JavaScript in Markdown blocks.
- Prefer concise blocks over dumping full logs.
- Use code references for file locations instead of embedding large source files.
