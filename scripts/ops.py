"""Operations for the optional AWS stack: preflight, destructive-diff guard, end-to-end verification,
cleanup, residue check and project-owned CDK bootstrap assets.

Called by the Makefile (see README.md). Every command prints masked output only: 12-digit numbers are
replaced by 111122223333 before anything is printed, and the caller's account is shown as its last four digits.

    uv run python scripts/ops.py preflight      --config infra/config/sandbox.json
    uv run python scripts/ops.py diff-guard     <cdk-diff-output.txt>
    uv run python scripts/ops.py verify         --config infra/config/sandbox.json [--expect-write-denied]
    uv run python scripts/ops.py cleanup        --config infra/config/sandbox.json --cdk-out <dir> [...]
    uv run python scripts/ops.py verify-cleanup --prefix proto-prd- --regions us-east-1 --cdk-out <dir> [...]
    uv run python scripts/ops.py asset-keys     --cdk-out <dir> [...]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "infra")]

_ACCOUNT = re.compile(r"(?<![0-9])[0-9]{12}(?![0-9])")
PLACEHOLDER_ACCOUNT = "111122223333"
REQUIRED_TOOLS = ("uv", "node", "npx", "aws")


def mask(text: object) -> str:
    return _ACCOUNT.sub(PLACEHOLDER_ACCOUNT, str(text))


def say(*parts: object) -> None:
    print(mask(" ".join(str(p) for p in parts)), flush=True)


def confirm(prompt: str, expected: str, env: str | None = None) -> bool:
    """Ask for an exact answer. *env* allows a non-interactive answer (CI); it must equal *expected*."""
    if env and os.environ.get(env) is not None:
        ok = os.environ[env] == expected
        say(f"{prompt} [{env} set: {'accepted' if ok else 'does not match'}]")
        return ok
    try:
        answer = input(mask(f"{prompt} Type '{expected}' to continue: "))
    except EOFError:
        answer = ""
    return answer.strip() == expected


def _config(path: str):
    from prd_infra.config import load_config

    cfg = load_config(path)
    region = cfg.region if not cfg.region.startswith("<") else os.environ.get("AWS_REGION") or \
        os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("CDK_DEFAULT_REGION")
    if not region:
        raise SystemExit("error: region is <REGION> in the config and AWS_REGION is not set")
    return cfg, region


def _boto(service: str, region: str):
    import boto3

    return boto3.client(service, region_name=region)


def _code(exc: Exception) -> str:
    return (getattr(exc, "response", None) or {}).get("Error", {}).get("Code", type(exc).__name__)


# ---------------------------------------------------------------------------------------------- preflight

def cmd_preflight(a) -> int:
    """Read-only checks. Changes nothing."""
    cfg, region = _config(a.config)
    failures = []
    ident = _boto("sts", region).get_caller_identity()
    account = ident["Account"]
    kind = ident["Arn"].split(":")[5].split("/")[0] if ident["Arn"].count(":") >= 5 else "?"
    say(f"account: ********{account[-4:]}  principal type: {kind}  region: {region}  stack: {cfg.stack_name}")
    say(f"removal policy: {cfg.removal_policy}  tags: {', '.join(f'{k}={v}' for k, v in cfg.tags.items())}")

    for tool in REQUIRED_TOOLS:
        path = shutil.which(tool)
        if not path:
            failures.append(f"tool missing: {tool}")
            continue
        out = subprocess.run([tool, "--version"], capture_output=True, text=True, check=False)  # noqa: S603 - fixed tool list
        say(f"tool {tool}: {(out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else 'ok'}")
    docker = shutil.which("docker")
    running = docker and subprocess.run([docker, "info"], capture_output=True,  # noqa: S603 - fixed args
                                        check=False).returncode == 0
    say(f"docker: {'running' if running else 'not running or not installed'} (not required: this stack has no "
        "container or Lambda assets)")

    ssm = _boto("ssm", region)
    for service in ("s3", "cloudformation"):
        try:
            ssm.get_parameter(Name=f"/aws/service/global-infrastructure/regions/{region}/services/{service}")
            say(f"service {service}: available in {region}")
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures.append(f"service {service} not confirmed in {region}: {_code(exc)}")

    cfn = _boto("cloudformation", region)
    try:
        boot = cfn.describe_stacks(StackName="CDKToolkit")["Stacks"][0]
        version = next((o["OutputValue"] for o in boot.get("Outputs", []) if o["OutputKey"] == "BootstrapVersion"), "?")
        say(f"CDK bootstrap: CDKToolkit {boot['StackStatus']}, version {version} (used, never modified)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"CDK bootstrap stack not found in {region} ({_code(exc)}); ask the account owner")
    try:
        stack = cfn.describe_stacks(StackName=cfg.stack_name)["Stacks"][0]
        say(f"stack {cfg.stack_name}: exists, {stack['StackStatus']} (deploy will update it)")
        if not stack["StackStatus"].endswith("_COMPLETE"):
            failures.append(f"stack {cfg.stack_name} is in state {stack['StackStatus']}")
    except Exception:  # noqa: BLE001
        say(f"stack {cfg.stack_name}: does not exist (deploy will create it)")

    s3 = _boto("s3", region)
    count = len(s3.list_buckets().get("Buckets", []))
    try:
        quota = _boto("service-quotas", region).get_service_quota(ServiceCode="s3", QuotaCode="L-DC2B2D3D")
        limit = int(quota["Quota"]["Value"])
        say(f"S3 buckets: {count} of {limit} used; this stack adds 2")
        if count + 2 > limit:
            failures.append("S3 bucket quota would be exceeded")
    except Exception as exc:  # noqa: BLE001
        say(f"S3 buckets: {count} in use; quota not readable ({_code(exc)}); this stack adds 2")

    if failures:
        for f in failures:
            say("FAIL:", f)
        return 1
    if not confirm("Is this the intended non-production account and region?", "yes", "PREFLIGHT_CONFIRM"):
        say("Stopped: not confirmed.")
        return 1
    say("Preflight: PASS")
    return 0


# ---------------------------------------------------------------------------------------------- diff guard

_REMOVAL = re.compile(r"^\s*\[-\]\s+(AWS::\S+)\s+(\S+)")
_REPLACE = re.compile(r"(requires replacement|may be replaced|replace)", re.IGNORECASE)
_RESOURCE = re.compile(r"^\s*\[[~+-]\]\s+(AWS::\S+)\s+(\S+)")


def destructive_changes(diff_text: str) -> list[str]:
    """Resources that `cdk diff` would delete or replace."""
    found, current = [], None
    for line in diff_text.splitlines():
        m = _RESOURCE.match(line)
        if m:
            current = f"{m.group(1)} {m.group(2)}"
        r = _REMOVAL.match(line)
        if r:
            found.append(f"delete {r.group(1)} {r.group(2)}")
        elif current and _REPLACE.search(line):
            found.append(f"replace {current}")
    return sorted(set(found))


def cmd_diff_guard(a) -> int:
    changes = destructive_changes(Path(a.diff).read_text(encoding="utf-8"))
    if not changes:
        say("Diff guard: no deletions or replacements")
        return 0
    for c in changes:
        say("destructive change:", c)
    if os.environ.get("ALLOW_DESTRUCTIVE") == "1":
        say("ALLOW_DESTRUCTIVE=1 set: continuing")
        return 0
    say("Refusing to deploy. Re-run with ALLOW_DESTRUCTIVE=1 if these deletions/replacements are intended.")
    return 1


# ---------------------------------------------------------------------------------------------- verify

def _outputs(cfn, stack: str) -> dict[str, str]:
    s = cfn.describe_stacks(StackName=stack)["Stacks"][0]
    return {o["OutputKey"]: o["OutputValue"] for o in s.get("Outputs", [])}


def _versions(s3, bucket: str, prefix: str) -> int:
    n = 0
    for page in s3.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=prefix):
        n += len(page.get("Versions", [])) + len(page.get("DeleteMarkers", []))
    return n


def cmd_verify(a) -> int:
    """End-to-end checks against the deployed stack, including deny paths."""
    from prd_agent.consistency import check_folder
    from prd_agent.progress import check_progress
    from prd_agent.publish import PublishRefused, fetch, publish

    cfg, region = _config(a.config)
    cfn, s3 = _boto("cloudformation", region), _boto("s3", region)
    out = _outputs(cfn, cfg.stack_name)
    bucket, logs = out["ArtifactBucketName"], out["AccessLogBucketName"]
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        say(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))

    for b, label in ((bucket, "artifact"), (logs, "log")):
        pab = s3.get_public_access_block(Bucket=b)["PublicAccessBlockConfiguration"]
        check(f"{label} bucket: Block Public Access all on", all(pab.values()))
        enc = s3.get_bucket_encryption(Bucket=b)["ServerSideEncryptionConfiguration"]["Rules"][0]
        check(f"{label} bucket: SSE-S3", enc["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256")
        own = s3.get_bucket_ownership_controls(Bucket=b)["OwnershipControls"]["Rules"][0]["ObjectOwnership"]
        check(f"{label} bucket: ACLs disabled", own == "BucketOwnerEnforced")
        tags = {t["Key"]: t["Value"] for t in s3.get_bucket_tagging(Bucket=b)["TagSet"]}
        check(f"{label} bucket: tags from config", all(tags.get(k) == v for k, v in cfg.tags.items()))
    check("artifact bucket: versioning", s3.get_bucket_versioning(Bucket=bucket).get("Status") == "Enabled")
    check("artifact bucket: access logging",
          s3.get_bucket_logging(Bucket=bucket).get("LoggingEnabled", {}).get("TargetPrefix") == "artifact-bucket/")
    policy = json.loads(s3.get_bucket_policy(Bucket=bucket)["Policy"])
    sids = {st.get("Sid") for st in policy["Statement"]}
    check("artifact bucket: account-boundary deny statement present", "DenyPrincipalsOutsideAccount" in sids)

    name = f"verify-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    work = Path(tempfile.mkdtemp(prefix="prd-verify-"))
    dest = f"s3://{bucket}/bundles"
    example = ROOT / "examples" / "smart-plug"
    if a.expect_write_denied:
        try:
            s3.put_object(Bucket=bucket, Key=f"bundles/{name}/probe.txt", Body=b"x")
            check("write by a principal outside writer_principal_arns is denied", False, "PutObject succeeded")
        except Exception as exc:  # noqa: BLE001
            check("write by a principal outside writer_principal_arns is denied", _code(exc) == "AccessDenied",
                  _code(exc))
        try:
            s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
            check("read/list by the same principal still allowed", True)
        except Exception as exc:  # noqa: BLE001
            check("read/list by the same principal still allowed", False, _code(exc))
        return _summary(results)

    m = publish(example, dest, name, s3_client=s3)
    check("publish example bundle", len(m["files"]) == 13, f"{len(m['files'])} files + MANIFEST.json")
    head = s3.head_object(Bucket=bucket, Key=f"bundles/{name}/PRD.md")
    check("published object encrypted (SSE-S3)", head.get("ServerSideEncryption") == "AES256")
    got = work / "fetched"
    fetch(dest, name, got, s3_client=s3)
    check("fetch verifies checksums; validate PASS", check_folder(got).ok)
    check("check-progress PASS on fetched copy", check_progress(got) == [])

    before = _versions(s3, bucket, f"bundles/{name}/")
    edited = work / "edited"
    shutil.copytree(example, edited)
    with (edited / "panel-spec.md").open("a", encoding="utf-8") as fh:
        fh.write("\nA later edit.\n")
    try:
        publish(edited, dest, name, s3_client=s3)
        check("re-publish under the same name refused", False, "publish succeeded")
    except PublishRefused as exc:
        check("re-publish under the same name refused", "already exists" in str(exc))
    try:
        s3.put_object(Bucket=bucket, Key=f"bundles/{name}/PRD.md", Body=b"x", IfNoneMatch="*")
        check("S3 conditional write on an existing key rejected", False, "PutObject succeeded")
    except Exception as exc:  # noqa: BLE001
        check("S3 conditional write on an existing key rejected", _code(exc) == "PreconditionFailed", _code(exc))
    check("no object version added by the refused writes", _versions(s3, bucket, f"bundles/{name}/") == before,
          f"{before} versions")

    http = _boto_http(region)
    try:
        http.list_objects_v2(Bucket=bucket, MaxKeys=1)
        check("plain HTTP request denied", False, "request succeeded")
    except Exception as exc:  # noqa: BLE001
        check("plain HTTP request denied", _code(exc) == "AccessDenied", _code(exc))
    url = f"https://{bucket}.s3.{region}.amazonaws.com/bundles/{name}/PRD.md"
    check("anonymous GET returns 403", _anonymous(url, "GET") == 403)
    check("anonymous PUT returns 403", _anonymous(url.replace("PRD.md", "anon.txt"), "PUT") == 403)
    shutil.rmtree(work, ignore_errors=True)
    return _summary(results)


def _boto_http(region: str):
    import boto3

    return boto3.client("s3", region_name=region, endpoint_url=f"http://s3.{region}.amazonaws.com")


def _anonymous(url: str, method: str) -> int:
    req = urllib.request.Request(url, method=method, data=b"x" if method == "PUT" else None)  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 - fixed https URL
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _summary(results: list[tuple[str, bool, str]]) -> int:
    failed = [r for r in results if not r[1]]
    say(f"Verify: {len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


# ---------------------------------------------------------------------------------------------- assets

def asset_keys(cdk_out_dirs: list[str]) -> list[str]:
    """S3 object keys of this project's file assets, read from cdk.out/*.assets.json."""
    keys = set()
    for d in cdk_out_dirs:
        for manifest in Path(d).glob("*.assets.json"):
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for asset in data.get("files", {}).values():
                for dest in asset.get("destinations", {}).values():
                    keys.add(dest["objectKey"])
            if data.get("dockerImages"):
                raise SystemExit("error: container assets found; extend asset cleanup for ECR first")
    return sorted(keys)


def cmd_asset_keys(a) -> int:
    for k in asset_keys(a.cdk_out):
        print(k)
    return 0


def _bootstrap_bucket(region: str) -> str | None:
    try:
        stack = _boto("cloudformation", region).describe_stacks(StackName="CDKToolkit")["Stacks"][0]
    except Exception:  # noqa: BLE001
        return None
    return next((o["OutputValue"] for o in stack.get("Outputs", []) if o["OutputKey"] == "BucketName"), None)


def _asset_versions(s3, bucket: str, keys: list[str]) -> list[dict]:
    items = []
    for key in keys:
        for page in s3.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=key):
            for v in page.get("Versions", []) + page.get("DeleteMarkers", []):
                if v["Key"] == key:
                    items.append({"Key": v["Key"], "VersionId": v["VersionId"]})
    return items


# ---------------------------------------------------------------------------------------------- cleanup

def _empty_bucket(s3, bucket: str) -> int:
    n = 0
    for page in s3.get_paginator("list_object_versions").paginate(Bucket=bucket):
        items = [{"Key": v["Key"], "VersionId": v["VersionId"]}
                 for v in page.get("Versions", []) + page.get("DeleteMarkers", [])]
        for i in range(0, len(items), 1000):
            s3.delete_objects(Bucket=bucket, Delete={"Objects": items[i:i + 1000], "Quiet": True})
        n += len(items)
    return n


def cmd_cleanup(a) -> int:
    """Two confirmations (stack, then data). A failed step prints a warning and the next step still runs."""
    cfg, region = _config(a.config)
    stack = cfg.stack_name
    if not stack.startswith(a.prefix):
        say(f"refusing: stack name must start with {a.prefix}")
        return 3
    cfn, s3 = _boto("cloudformation", region), _boto("s3", region)
    warnings: list[str] = []
    # Read the asset keys first: `cdk destroy` synthesizes again and must not overwrite the folders passed in.
    keys = asset_keys(a.cdk_out)
    say(f"Cleanup of stack {stack} in {region}")
    if not confirm(f"This deletes stack {stack} and its resources.", stack, "CLEANUP_CONFIRM_STACK"):
        say("Stopped: not confirmed.")
        return 1

    try:
        buckets = [r["PhysicalResourceId"] for r in cfn.describe_stack_resources(StackName=stack)["StackResources"]
                   if r["ResourceType"] == "AWS::S3::Bucket" and r.get("PhysicalResourceId")]
    except Exception as exc:  # noqa: BLE001
        buckets = []
        warnings.append(f"could not list stack resources ({_code(exc)}); is the stack already deleted?")
    counts = {}
    for b in buckets:
        try:
            counts[b] = _versions(s3, b, "")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"cannot list {b}: {_code(exc)}")
    for b, n in counts.items():
        say(f"bucket {b}: {n} object versions/delete markers")
    if counts and cfg.removal_policy == "retain":
        say("removal_policy is retain: buckets and data are kept; nothing is emptied.")
    elif any(counts.values()):
        if confirm(f"Delete all {sum(counts.values())} object versions in these buckets (data loss)?",
                   "DELETE DATA", "CLEANUP_CONFIRM_DATA"):
            for b in counts:
                try:
                    say(f"bucket {b}: {_empty_bucket(s3, b)} deleted")
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"emptying {b} failed: {_code(exc)}")
        else:
            warnings.append("data deletion not confirmed; cdk destroy will fail on non-empty buckets")

    scratch = tempfile.mkdtemp(prefix="prd-destroy-cdk.out-")
    cmd = a.cdk.split() + ["destroy", "--force", "-c", f"config={Path(a.config).resolve().relative_to(ROOT / 'infra')}",
                           "-o", scratch]
    say("running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT / "infra", capture_output=True, text=True, check=False)  # noqa: S603 - CDK CLI from --cdk
    say((proc.stdout + proc.stderr).strip().splitlines()[-1] if (proc.stdout + proc.stderr).strip() else "")
    if proc.returncode != 0:
        warnings.append(f"cdk destroy exited {proc.returncode}; empty the buckets again and re-run (late logs)")

    shutil.rmtree(scratch, ignore_errors=True)
    boot = _bootstrap_bucket(region)
    if boot and keys:
        try:
            items = _asset_versions(s3, boot, keys)
            say(f"bootstrap assets of this project: {len(keys)} key(s), {len(items)} version(s) in the CDK "
                "bootstrap bucket (other objects and the CDKToolkit stack are not touched)")
            if items and confirm("Delete these bootstrap asset versions?", "DELETE ASSETS", "CLEANUP_CONFIRM_ASSETS"):
                s3.delete_objects(Bucket=boot, Delete={"Objects": items, "Quiet": True})
                say(f"deleted {len(items)} bootstrap asset version(s)")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"bootstrap asset cleanup failed: {_code(exc)}; delete them by hand (keys above)")

    for w in warnings:
        say("WARNING:", w)
    say("Cleanup finished" + (" with warnings" if warnings else "") + ". Run make verify-cleanup.")
    return 1 if warnings else 0


# ---------------------------------------------------------------------------------------------- residue

def _count(fn) -> int | str:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return f"error {_code(exc)}"


def residue(prefix: str, region: str, keys: list[str], tags: dict[str, str]) -> dict[str, int | str]:
    lower = prefix.lower()
    cfn = _boto("cloudformation", region)
    s3 = _boto("s3", region)
    r: dict[str, int | str] = {}

    def stacks():
        n = 0
        for page in cfn.get_paginator("list_stacks").paginate():
            n += sum(1 for s in page["StackSummaries"]
                     if s["StackName"].startswith(prefix) and s["StackStatus"] != "DELETE_COMPLETE")
        return n

    def buckets():
        names = [b["Name"] for b in s3.list_buckets().get("Buckets", []) if b["Name"].startswith(lower)]
        n = 0
        for b in names:
            loc = s3.get_bucket_location(Bucket=b).get("LocationConstraint") or "us-east-1"
            n += loc == region
        return n

    def tagged():
        # The tagging index lags behind deletions: confirm that each listed resource still exists.
        tag = _boto("resourcegroupstaggingapi", region)
        filters = [{"Key": k, "Values": [v]} for k, v in tags.items()]
        n = 0
        for page in tag.get_paginator("get_resources").paginate(TagFilters=filters):
            for res in page["ResourceTagMappingList"]:
                arn = res["ResourceARN"]
                if arn.startswith("arn:aws:s3:::"):
                    try:
                        s3.head_bucket(Bucket=arn.split(":::", 1)[1])
                        n += 1
                    except Exception:  # noqa: BLE001 - gone; index not yet updated
                        say(f"  tag index lists a deleted bucket (index lag): {arn}")
                else:
                    say(f"  tagged resource not verified automatically: {arn}")
                    n += 1
        return n

    def pages(client, op, key, pred, **kw):
        n = 0
        for page in client.get_paginator(op).paginate(**kw):
            n += sum(1 for x in page.get(key, []) if pred(x))
        return n

    lam, logs, iam = _boto("lambda", region), _boto("logs", region), _boto("iam", region)
    ecr, kms = _boto("ecr", region), _boto("kms", region)
    apigw, apigw2 = _boto("apigateway", region), _boto("apigatewayv2", region)
    r["CloudFormation stacks (not DELETE_COMPLETE)"] = _count(stacks)
    r["S3 buckets with prefix in this region"] = _count(buckets)
    r["tagged resources that still exist (" + ", ".join(f"{k}={v}" for k, v in tags.items()) + ")"] = _count(tagged)
    r["log groups /aws/lambda/<prefix>"] = _count(lambda: pages(
        logs, "describe_log_groups", "logGroups", lambda x: True, logGroupNamePrefix=f"/aws/lambda/{prefix}"))
    r["Lambda functions"] = _count(lambda: pages(lam, "list_functions", "Functions",
                                                 lambda x: x["FunctionName"].startswith(prefix)))
    r["IAM roles"] = _count(lambda: pages(iam, "list_roles", "Roles", lambda x: x["RoleName"].startswith(prefix)))
    r["IAM customer managed policies"] = _count(lambda: pages(
        iam, "list_policies", "Policies", lambda x: x["PolicyName"].startswith(prefix), Scope="Local"))
    r["ECR repositories"] = _count(lambda: pages(ecr, "describe_repositories", "repositories",
                                                 lambda x: x["repositoryName"].startswith(lower)))
    r["KMS aliases"] = _count(lambda: pages(kms, "list_aliases", "Aliases",
                                            lambda x: x["AliasName"].startswith(f"alias/{prefix}")))
    r["API Gateway REST APIs"] = _count(lambda: pages(apigw, "get_rest_apis", "items",
                                                      lambda x: x["name"].startswith(prefix)))
    r["API Gateway HTTP APIs"] = _count(lambda: sum(1 for x in apigw2.get_apis().get("Items", [])
                                                    if x["Name"].startswith(prefix)))
    boot = _bootstrap_bucket(region)
    r["this project's objects in the CDK bootstrap bucket"] = (
        _count(lambda: len(_asset_versions(s3, boot, keys))) if boot and keys else 0)
    return r


def cmd_verify_cleanup(a) -> int:
    keys = asset_keys(a.cdk_out) if a.cdk_out else []
    tags = dict(t.split("=", 1) for t in a.tag)
    bad = 0
    for region in a.regions.split(","):
        say(f"region {region}, prefix {a.prefix}")
        for name, n in residue(a.prefix, region, keys, tags).items():
            say(f"  {name}: {n}")
            bad += n != 0
    say("Result: cleaned up, no residue" if not bad else f"Result: residue or unreadable categories: {bad}")
    return 1 if bad else 0


# ---------------------------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ops.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("preflight")
    s.add_argument("--config", required=True)
    s.set_defaults(fn=cmd_preflight)
    s = sub.add_parser("diff-guard")
    s.add_argument("diff")
    s.set_defaults(fn=cmd_diff_guard)
    s = sub.add_parser("verify")
    s.add_argument("--config", required=True)
    s.add_argument("--expect-write-denied", action="store_true",
                   help="the caller is not in writer_principal_arns: check that its writes are denied")
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("cleanup")
    s.add_argument("--config", required=True)
    s.add_argument("--prefix", default="proto-prd-")
    s.add_argument("--cdk", default="npx -y aws-cdk@2.1146.0")
    s.add_argument("--cdk-out", nargs="+", required=True, help="cdk.out folders whose assets belong to this project")
    s.set_defaults(fn=cmd_cleanup)
    s = sub.add_parser("verify-cleanup")
    s.add_argument("--prefix", default="proto-prd-")
    s.add_argument("--regions", default=os.environ.get("AWS_REGION", "us-east-1"))
    s.add_argument("--tag", nargs="*", default=["Project=prd-agent", "Teardown=after-test"])
    s.add_argument("--cdk-out", nargs="*", default=[])
    s.set_defaults(fn=cmd_verify_cleanup)
    s = sub.add_parser("asset-keys")
    s.add_argument("--cdk-out", nargs="+", required=True)
    s.set_defaults(fn=cmd_asset_keys)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
