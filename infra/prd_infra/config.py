"""Deployment parameters: one JSON file per environment.

Templates are committed as ``infra/config/*.example.json``; the real files (``infra/config/*.json``) are
ignored by git and created by ``make init``. Every value is validated here, so a wrong parameter fails at
``cdk synth`` before anything is deployed. Account IDs never appear in these files: the account comes from the
caller's credentials, and principal ARNs (which contain an account ID) are passed with ``--context``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

REMOVAL = ("destroy", "retain")
SANDBOX_PREFIX = "proto-"

# CDK feature flags this app relies on. Server access logs are granted through a bucket
# policy instead of the legacy LogDeliveryWrite ACL, so ACLs can stay disabled.
FEATURE_FLAGS = {"@aws-cdk/aws-s3:serverAccessLogsUseBucketPolicy": True}

_STACK_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,127}$")
_REGION = re.compile(r"^[a-z]{2}(-[a-z]+)+-[0-9]$")
_TAG_KEY = re.compile(r"^[A-Za-z0-9 _.:/=+@-]{1,128}$")
_TAG_VALUE = re.compile(r"^[A-Za-z0-9 _.:/=+@-]{0,256}$")
_ACCOUNT_LIKE = re.compile(r"(?<![0-9])[0-9]{12}(?![0-9])")
_PRINCIPAL_ARN = re.compile(r"^arn:aws[a-z-]*:iam::[0-9]{12}:(role|user)/[A-Za-z0-9+=,.@_/-]{1,512}$")
KEYS = {"stack_name", "region", "removal_policy", "noncurrent_version_expiration_days",
        "access_log_expiration_days", "tags"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class DeployConfig:
    stack_name: str
    region: str
    removal_policy: str
    noncurrent_version_expiration_days: int
    access_log_expiration_days: int
    tags: dict[str, str]
    # From --context writer_principal_arns=arn1,arn2 (never from the file). Empty: any principal of the
    # account that IAM allows may write; non-empty: s3:PutObject is denied to every other principal.
    writer_principal_arns: tuple[str, ...] = field(default=())


def _days(raw: dict, key: str, problems: list[str]) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 3650:
        problems.append(f"{key} must be an integer from 1 to 3650")
        return 1
    return value


def validate(raw: object, writer_principal_arns: tuple[str, ...] = ()) -> DeployConfig:
    """Validate a parsed config file. Raises ConfigError listing every problem."""
    if not isinstance(raw, dict):
        raise ConfigError("config must be a JSON object")
    problems: list[str] = []
    unknown = sorted(set(raw) - KEYS)
    missing = sorted(KEYS - set(raw))
    if unknown:
        problems.append("unknown keys: " + ", ".join(unknown))
    if missing:
        problems.append("missing keys: " + ", ".join(missing))
    if _ACCOUNT_LIKE.search(json.dumps(raw)):
        problems.append("a 12-digit number was found; account IDs must not be written into config files")

    stack_name = raw.get("stack_name")
    if not isinstance(stack_name, str) or not _STACK_NAME.match(stack_name):
        problems.append("stack_name must match " + _STACK_NAME.pattern)
    region = raw.get("region")
    if not isinstance(region, str) or not (region == "<REGION>" or _REGION.match(region)):
        problems.append("region must be an AWS region code such as us-east-1, or <REGION> to use the environment")
    removal = raw.get("removal_policy")
    if removal not in REMOVAL:
        problems.append(f"removal_policy must be one of {', '.join(REMOVAL)}")
    noncurrent = _days(raw, "noncurrent_version_expiration_days", problems)
    logs = _days(raw, "access_log_expiration_days", problems)
    tags = raw.get("tags")
    if not isinstance(tags, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in tags.items()):
        problems.append("tags must be an object of string to string")
        tags = {}
    for key, value in tags.items():
        if not _TAG_KEY.match(key) or key.lower().startswith("aws:"):
            problems.append(f"tag key {key!r} is not allowed")
        if not _TAG_VALUE.match(value):
            problems.append(f"tag value for {key!r} is not allowed")
    if "Project" not in tags:
        problems.append("tags must include Project")

    # Cross-field rules.
    if removal == "destroy":
        if isinstance(stack_name, str) and not stack_name.startswith(SANDBOX_PREFIX):
            problems.append(f"removal_policy destroy is only allowed for sandbox stacks named {SANDBOX_PREFIX}*")
        if "Teardown" not in tags:
            problems.append("removal_policy destroy requires a Teardown tag")
    if removal == "retain" and noncurrent < 30:
        problems.append("removal_policy retain requires noncurrent_version_expiration_days >= 30")

    for arn in writer_principal_arns:
        if not _PRINCIPAL_ARN.match(arn):
            problems.append(f"writer principal is not an IAM role or user ARN: {_mask(arn)}")

    if problems:
        raise ConfigError("invalid deployment config:\n- " + "\n- ".join(problems))
    return DeployConfig(stack_name=stack_name, region=region, removal_policy=removal,
                        noncurrent_version_expiration_days=noncurrent, access_log_expiration_days=logs,
                        tags=dict(tags), writer_principal_arns=tuple(writer_principal_arns))


def _mask(text: str) -> str:
    return _ACCOUNT_LIKE.sub("111122223333", text)


def parse_principals(value: object) -> tuple[str, ...]:
    """--context writer_principal_arns: a comma-separated string (or a JSON list from cdk.json)."""
    if value in (None, ""):
        return ()
    items = value if isinstance(value, list) else str(value).split(",")
    return tuple(str(i).strip() for i in items if str(i).strip())


def load_config(path: str | Path, writer_principal_arns: tuple[str, ...] = ()) -> DeployConfig:
    path = Path(path)
    if not path.is_file():
        example = path.with_name(path.stem + ".example.json")
        hint = f"; run `make init` to copy {example.name}" if example.is_file() else ""
        raise ConfigError(f"config file {path} not found{hint}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ConfigError(f"{path.name} is not valid JSON: {exc}") from exc
    return validate(raw, writer_principal_arns)
