# Publishing Protocol

Read `config/open-artifacts.toml` for server configuration.

Publish endpoint:

`POST {server_url}{api_base}/artifacts/publish`

Headers:

- `Authorization: Bearer <publish_token>`
- `Content-Type: application/json`

Request:

```json
{
  "artifact_id": "optional-existing-id",
  "idempotency_key": "unique-key",
  "visibility": "private",
  "payload": {}
}
```

Response:

```json
{
  "artifact_id": "art_123",
  "version": 1,
  "url": "http://localhost:8787/a/art_123",
  "gallery_url": "http://localhost:8787/gallery"
}
```

On `401`, report invalid Skill/server config. On `422`, revise the payload. On network failure, preserve the generated payload and report publish failure.
