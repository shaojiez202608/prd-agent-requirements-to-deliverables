"""Distribution step: publish a validated deliverable folder as a bundle.

Interface (docs/distribution.md): a bundle is the deliverable folder plus
MANIFEST.json (file list with SHA-256). Destinations:

- a local directory (default, no AWS needed; this is the mock mode), or
- ``s3://<bucket>/<prefix>`` on the optional private bucket from infra/.

Publishing is refused unless the consistency check and the progress check pass.
No instant-messaging integration is included on purpose.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .consistency import check_folder
from .progress import check_progress

MANIFEST = "MANIFEST.json"


class PublishRefused(Exception):
    pass


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.name != MANIFEST)


def build_manifest(folder: Path, bundle_name: str) -> dict[str, Any]:
    return {
        "bundle": bundle_name,
        "files": [{"path": p.relative_to(folder).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                   "bytes": p.stat().st_size} for p in _files(folder)],
    }


def _gate(folder: Path) -> None:
    report = check_folder(folder)
    problems = check_progress(folder)
    if not report.ok or problems:
        msg = report.render_text() + "".join(p.render() + "\n" for p in problems)
        raise PublishRefused("bundle is not consistent; fix and re-run validate\n" + msg)


def _split_s3(uri: str) -> tuple[str, str]:
    rest = uri[len("s3://"):]
    bucket, _, prefix = rest.partition("/")
    if not bucket:
        raise ValueError("s3 destination must be s3://<bucket>/<prefix>")
    return bucket, prefix.strip("/")


def publish(folder: Path, dest: str, bundle_name: str, s3_client: Any = None) -> dict[str, Any]:
    folder = Path(folder)
    _gate(folder)
    manifest = build_manifest(folder, bundle_name)
    body = json.dumps(manifest, indent=2) + "\n"
    if dest.startswith("s3://"):
        bucket, prefix = _split_s3(dest)
        if s3_client is None:
            import boto3  # optional dependency group "publish"

            s3_client = boto3.client("s3")
        base = f"{prefix}/{bundle_name}" if prefix else bundle_name
        for f in _files(folder):
            s3_client.put_object(Bucket=bucket, Key=f"{base}/{f.relative_to(folder).as_posix()}", Body=f.read_bytes())
        s3_client.put_object(Bucket=bucket, Key=f"{base}/{MANIFEST}", Body=body.encode())
    else:
        target = Path(dest) / bundle_name
        if target.exists():
            raise PublishRefused(f"{target} already exists; bundles are immutable, choose a new bundle name")
        shutil.copytree(folder, target)
        (target / MANIFEST).write_text(body, encoding="utf-8")
    return manifest


def fetch(source: str, bundle_name: str, out: Path, s3_client: Any = None) -> dict[str, Any]:
    """Download a bundle and verify every file against MANIFEST.json."""
    out = Path(out)
    if source.startswith("s3://"):
        bucket, prefix = _split_s3(source)
        if s3_client is None:
            import boto3

            s3_client = boto3.client("s3")
        base = f"{prefix}/{bundle_name}" if prefix else bundle_name

        def read(rel: str) -> bytes:
            return s3_client.get_object(Bucket=bucket, Key=f"{base}/{rel}")["Body"].read()
    else:
        root = Path(source) / bundle_name

        def read(rel: str) -> bytes:
            return (root / rel).read_bytes()

    manifest = json.loads(read(MANIFEST))
    for entry in manifest["files"]:
        rel = entry["path"]
        if rel.startswith("/") or ".." in Path(rel).parts:
            raise ValueError(f"unsafe path in manifest: {rel}")
        data = read(rel)
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"checksum mismatch: {rel}")
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
