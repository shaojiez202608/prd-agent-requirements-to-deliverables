# Distribution interface

The project does not depend on any instant-messaging tool. Distribution is a file bundle with a manifest,
published to a folder or to the optional S3 bucket. Notification is left to whatever the team already uses.

## Bundle

```
<bundle-name>/
  thing-model.json, PRD.md, architecture.mmd, quick-start.md, quick-start.pdf,
  panel-spec.md, panel-preview.html, device-demo/..., PROGRESS.md
  MANIFEST.json
```

`MANIFEST.json`:

```json
{"bundle": "<bundle-name>", "files": [{"path": "PRD.md", "sha256": "<hex>", "bytes": 1234}]}
```

Rules:
- `publish` refuses to publish unless `validate` and `check-progress` both pass.
- Bundle names are immutable. Publish a new version under a new name (for example `-v2`) and attach the
  `diff-model` output.
- `fetch` verifies every file against the manifest and rejects absolute paths and `..` in the manifest.

## Local command-line example

```bash
uv run prd-agent publish examples/smart-plug --dest out/dist --name demo-smart-plug-v1
uv run prd-agent fetch out/dist --name demo-smart-plug-v1 --out out/received
uv run prd-agent validate out/received
```

## Adapter contract (for teams that want notifications)

An adapter is any script that runs after `publish` succeeds. It receives the destination URI, the bundle name and
the path of `MANIFEST.json`. It may post a link and a short summary (the file count and the `validate` result) to a
channel. It must not attach the files themselves, and it must not include credentials in the message. No adapter
is included.
