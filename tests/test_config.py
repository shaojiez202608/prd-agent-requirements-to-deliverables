"""Deployment config templates and validation (fails at synth time)."""

import copy
import json

import pytest

from conftest import ROOT
from prd_infra.config import ConfigError, load_config, parse_principals, validate

CONFIG = ROOT / "infra" / "config"


def _sandbox():
    return json.loads((CONFIG / "sandbox.example.json").read_text(encoding="utf-8"))


def test_templates_are_valid():
    assert load_config(CONFIG / "sandbox.example.json").removal_policy == "destroy"
    assert load_config(CONFIG / "customer.example.json").removal_policy == "retain"


@pytest.mark.parametrize("key,value,message", [
    ("stack_name", "1-bad name", "stack_name must match"),
    ("region", "us_east_1", "region must be"),
    ("removal_policy", "snapshot", "removal_policy must be one of"),
    ("noncurrent_version_expiration_days", 0, "from 1 to 3650"),
    ("access_log_expiration_days", "90", "from 1 to 3650"),
    ("tags", {"aws:owner": "x", "Project": "p", "Teardown": "t"}, "tag key 'aws:owner' is not allowed"),
])
def test_single_field_rules(key, value, message):
    raw = _sandbox()
    raw[key] = value
    with pytest.raises(ConfigError, match=message):
        validate(raw)


def test_cross_field_rules():
    raw = _sandbox()
    raw["stack_name"] = "prd-agent-artifacts"
    del raw["tags"]["Teardown"]
    with pytest.raises(ConfigError) as exc:
        validate(raw)
    assert "only allowed for sandbox stacks named proto-*" in str(exc.value)
    assert "requires a Teardown tag" in str(exc.value)
    retain = _sandbox()
    retain["removal_policy"], retain["noncurrent_version_expiration_days"] = "retain", 7
    with pytest.raises(ConfigError, match="retain requires"):
        validate(retain)


def test_account_ids_are_rejected_in_config_files():
    raw = _sandbox()
    raw["tags"]["Owner"] = "1234567890" + "12"
    with pytest.raises(ConfigError, match="12-digit number"):
        validate(raw)


def test_unknown_and_missing_keys():
    raw = copy.deepcopy(_sandbox())
    raw["account"] = "x"
    del raw["region"]
    with pytest.raises(ConfigError) as exc:
        validate(raw)
    assert "unknown keys: account" in str(exc.value) and "missing keys: region" in str(exc.value)


def test_writer_principals_come_from_context_and_are_checked():
    assert parse_principals(None) == ()
    arns = parse_principals("arn:aws:iam::111122223333:role/a, arn:aws:iam::111122223333:user/b")
    assert validate(_sandbox(), arns).writer_principal_arns == arns
    with pytest.raises(ConfigError, match="not an IAM role or user ARN: arn:aws:s3:::bucket"):
        validate(_sandbox(), ("arn:aws:s3:::bucket",))


def test_missing_real_config_points_to_make_init(tmp_path):
    (tmp_path / "sandbox.example.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError, match="run `make init`"):
        load_config(tmp_path / "sandbox.json")
