"""Deployment parameters: one JSON file per environment (infra/config/*.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REMOVAL = ("destroy", "retain")


@dataclass(frozen=True)
class DeployConfig:
    stack_name: str
    region: str
    removal_policy: str
    noncurrent_version_expiration_days: int
    access_log_expiration_days: int
    tags: dict[str, str]


def load_config(path: str | Path) -> DeployConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg = DeployConfig(
        stack_name=raw["stack_name"],
        region=raw["region"],
        removal_policy=raw["removal_policy"],
        noncurrent_version_expiration_days=int(raw["noncurrent_version_expiration_days"]),
        access_log_expiration_days=int(raw["access_log_expiration_days"]),
        tags=dict(raw["tags"]),
    )
    if cfg.removal_policy not in REMOVAL:
        raise ValueError(f"removal_policy must be one of {REMOVAL}")
    if cfg.noncurrent_version_expiration_days < 1 or cfg.access_log_expiration_days < 1:
        raise ValueError("expiration days must be >= 1")
    if "Project" not in cfg.tags:
        raise ValueError("tags must include Project")
    return cfg
