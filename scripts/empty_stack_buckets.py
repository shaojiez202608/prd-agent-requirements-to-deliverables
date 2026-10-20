"""Empty the buckets of one of *our* stacks (all object versions and delete markers) before `cdk destroy`.

Usage: uv run python scripts/empty_stack_buckets.py <stack-name> [--region us-east-1] [--yes]

Safety: only buckets that are physical resources of the named stack are touched, and the stack name
must start with the prefix in --prefix (default "proto-prd-"). Without --yes it only lists what it would delete.
"""

from __future__ import annotations

import argparse
import sys

import boto3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stack")
    ap.add_argument("--region", default=None)
    ap.add_argument("--prefix", default="proto-prd-")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    if not a.stack.startswith(a.prefix):
        print(f"refusing: stack name must start with {a.prefix}", file=sys.stderr)
        return 3
    cfn = boto3.client("cloudformation", region_name=a.region)
    s3 = boto3.client("s3", region_name=a.region)
    buckets = [r["PhysicalResourceId"] for r in
               cfn.describe_stack_resources(StackName=a.stack)["StackResources"]
               if r["ResourceType"] == "AWS::S3::Bucket" and r.get("PhysicalResourceId")]
    for bucket in buckets:
        n = 0
        for page in s3.get_paginator("list_object_versions").paginate(Bucket=bucket):
            items = [{"Key": v["Key"], "VersionId": v["VersionId"]}
                     for v in page.get("Versions", []) + page.get("DeleteMarkers", [])]
            n += len(items)
            if items and a.yes:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": items, "Quiet": True})
        print(f"{bucket}: {n} object versions/delete markers {'deleted' if a.yes else 'found (dry run)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
