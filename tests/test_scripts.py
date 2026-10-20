"""Operations script (scripts/ops.py): guards and parsers that run without AWS."""

import importlib.util
import json
import sys

import pytest
from botocore.stub import Stubber

from conftest import ROOT

spec = importlib.util.spec_from_file_location("ops", ROOT / "scripts" / "ops.py")
ops = importlib.util.module_from_spec(spec)
sys.modules["ops"] = ops
spec.loader.exec_module(ops)


def test_mask_replaces_account_ids():
    fake = "9876543210" + "98"  # built at run time: no account-like literal in the repository
    assert ops.mask(f"arn:aws:iam::{fake}:role/x {fake}3") == f"arn:aws:iam::111122223333:role/x {fake}3"


DIFF = """Stack proto-prd-artifacts
Resources
[~] AWS::S3::BucketPolicy ArtifactBucketPolicy ArtifactBucketPolicy4B4B7752
 └─ [~] PolicyDocument
[-] AWS::S3::Bucket AccessLogBucket AccessLogBucketDA470295 orphan
[~] AWS::S3::Bucket ArtifactBucket ArtifactBucket7410C9EF replace
 └─ [~] BucketName (requires replacement)
[+] AWS::S3::Bucket NewBucket NewBucketABC
"""


def test_diff_guard_finds_deletions_and_replacements():
    assert ops.destructive_changes(DIFF) == ["delete AWS::S3::Bucket AccessLogBucket",
                                             "replace AWS::S3::Bucket ArtifactBucket"]
    assert ops.destructive_changes("[+] AWS::S3::Bucket A A1\n[~] AWS::S3::BucketPolicy P P1\n") == []


def test_diff_guard_refuses_without_allow_destructive(tmp_path, monkeypatch):
    f = tmp_path / "diff.txt"
    f.write_text(DIFF, encoding="utf-8")
    monkeypatch.delenv("ALLOW_DESTRUCTIVE", raising=False)
    assert ops.main(["diff-guard", str(f)]) == 1
    monkeypatch.setenv("ALLOW_DESTRUCTIVE", "1")
    assert ops.main(["diff-guard", str(f)]) == 0


def test_asset_keys_from_cdk_out(tmp_path):
    (tmp_path / "s.assets.json").write_text(json.dumps({"files": {"h1": {"destinations": {
        "d": {"bucketName": "b", "objectKey": "h1.json"}}}}, "dockerImages": {}}), encoding="utf-8")
    assert ops.asset_keys([str(tmp_path)]) == ["h1.json"]


def test_confirm_from_environment(monkeypatch):
    monkeypatch.setenv("X_CONFIRM", "proto-prd-artifacts")
    assert ops.confirm("?", "proto-prd-artifacts", "X_CONFIRM")
    monkeypatch.setenv("X_CONFIRM", "yes")
    assert not ops.confirm("?", "proto-prd-artifacts", "X_CONFIRM")


def test_cleanup_refuses_foreign_stack_before_any_aws_call(tmp_path, capsys):
    cfg = json.loads((ROOT / "infra" / "config" / "customer.example.json").read_text(encoding="utf-8"))
    cfg["region"] = "us-east-1"
    path = tmp_path / "customer.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    assert ops.main(["cleanup", "--config", str(path), "--cdk-out", str(tmp_path)]) == 3
    assert "must start with proto-prd-" in capsys.readouterr().out


def test_asset_versions_only_match_exact_keys():
    import boto3

    s3 = boto3.client("s3", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
    with Stubber(s3) as st:
        st.add_response("list_object_versions", {"Versions": [
            {"Key": "h1.json", "VersionId": "v1"}, {"Key": "h1.json.extra", "VersionId": "v2"}]},
            {"Bucket": "boot", "Prefix": "h1.json"})
        assert ops._asset_versions(s3, "boot", ["h1.json"]) == [{"Key": "h1.json", "VersionId": "v1"}]


def test_verify_cleanup_fails_on_residue(monkeypatch):
    monkeypatch.setattr(ops, "residue", lambda *a: {"stacks": 0, "S3 buckets": 1})
    assert ops.main(["verify-cleanup", "--regions", "us-east-1"]) == 1
    monkeypatch.setattr(ops, "residue", lambda *a: {"stacks": 0, "S3 buckets": 0})
    assert ops.main(["verify-cleanup", "--regions", "us-east-1"]) == 0
    monkeypatch.setattr(ops, "residue", lambda *a: {"stacks": "error AccessDenied"})
    assert ops.main(["verify-cleanup", "--regions", "us-east-1"]) == 1


def test_sandbox_stack_uses_project_prefix():
    cfg = json.loads((ROOT / "infra" / "config" / "sandbox.example.json").read_text(encoding="utf-8"))
    assert cfg["stack_name"].startswith("proto-prd-")


@pytest.mark.parametrize("target", ["preflight", "lint", "test", "synth", "deploy", "verify", "destroy",
                                    "verify-cleanup", "scan", "init"])
def test_makefile_has_standard_targets(target):
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert f"\n{target}:" in text


def test_cleanup_reads_asset_keys_before_cdk_destroy(tmp_path, monkeypatch):
    """cdk destroy re-synthesizes; the asset keys must come from the folders as passed in."""
    cfg = tmp_path / "sandbox.json"
    cfg.write_text((ROOT / "infra" / "config" / "sandbox.example.json").read_text(encoding="utf-8"), encoding="utf-8")
    calls = []
    monkeypatch.setattr(ops, "asset_keys", lambda dirs: calls.append(("keys", list(dirs))) or ["k.json"])

    class Proc:
        returncode, stdout, stderr = 0, "destroyed", ""

    def run(cmd, **kw):
        calls.append(("destroy", cmd[cmd.index("-o") + 1]))
        return Proc()

    class Cfn:
        def describe_stack_resources(self, StackName):
            return {"StackResources": []}

    monkeypatch.setattr(ops.subprocess, "run", run)
    monkeypatch.setattr(ops, "_boto", lambda service, region: Cfn())
    monkeypatch.setattr(ops, "_bootstrap_bucket", lambda region: None)
    monkeypatch.setattr(ops, "ROOT", tmp_path.parent)
    monkeypatch.setenv("CLEANUP_CONFIRM_STACK", "proto-prd-artifacts")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    (tmp_path.parent / "infra").mkdir(exist_ok=True)
    real_cfg = tmp_path.parent / "infra" / "sandbox.json"
    real_cfg.write_text(cfg.read_text(encoding="utf-8"), encoding="utf-8")
    ops.main(["cleanup", "--config", str(real_cfg), "--cdk-out", str(tmp_path)])
    assert calls[0] == ("keys", [str(tmp_path)])
    assert calls[1][0] == "destroy" and calls[1][1] != str(tmp_path)


def test_anonymous_probe_refuses_non_https():
    with pytest.raises(ValueError, match="non-https"):
        ops._anonymous("file:///etc/hosts", "GET")
