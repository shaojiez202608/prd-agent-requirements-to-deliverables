"""Optional S3 stack: synthesises with cdk-nag AwsSolutions and no unsuppressed findings."""

import pytest

cdk = pytest.importorskip("aws_cdk")

from aws_cdk import assertions  # noqa: E402
from cdk_nag import AwsSolutionsChecks  # noqa: E402

from conftest import ROOT  # noqa: E402
from prd_infra.artifact_stack import ArtifactStack  # noqa: E402
from prd_infra.config import FEATURE_FLAGS, load_config  # noqa: E402


def _synth(config="sandbox.json"):
    cfg = load_config(ROOT / "infra" / "config" / config)
    app = cdk.App(context=FEATURE_FLAGS)
    stack = ArtifactStack(app, "proto-prd-artifacts-test", cfg=cfg)  # environment-agnostic, no account ID
    for k, v in cfg.tags.items():
        cdk.Tags.of(app).add(k, v)
    cdk.Aspects.of(app).add(AwsSolutionsChecks())
    return stack


def test_no_unsuppressed_nag_findings():
    stack = _synth()
    errors = assertions.Annotations.from_stack(stack).find_error("*", assertions.Match.string_like_regexp("AwsSolutions-.*"))
    warnings = assertions.Annotations.from_stack(stack).find_warning("*", assertions.Match.string_like_regexp("AwsSolutions-.*"))
    assert errors == [] and warnings == []


def test_buckets_private_encrypted_tagged():
    t = assertions.Template.from_stack(_synth())
    t.resource_count_is("AWS::S3::Bucket", 2)
    t.resource_count_is("AWS::Lambda::Function", 0)
    t.resource_count_is("AWS::IAM::User", 0)
    t.all_resources_properties("AWS::S3::Bucket", {
        "PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "BlockPublicPolicy": True,
                                           "IgnorePublicAcls": True, "RestrictPublicBuckets": True},
        "BucketEncryption": assertions.Match.any_value(),
        "Tags": assertions.Match.array_with([{"Key": "Teardown", "Value": "after-test"}]),
    })
    t.has_resource("AWS::S3::Bucket", {"DeletionPolicy": "Delete"})


def test_bucket_policies_deny_insecure_transport():
    t = assertions.Template.from_stack(_synth())
    t.resource_count_is("AWS::S3::BucketPolicy", 2)
    t.all_resources_properties("AWS::S3::BucketPolicy", {"PolicyDocument": {"Statement": assertions.Match.array_with([
        assertions.Match.object_like({"Effect": "Deny", "Condition": {"Bool": {"aws:SecureTransport": "false"}}})])}})


def test_customer_config_retains_data():
    t = assertions.Template.from_stack(_synth("customer.json"))
    t.has_resource("AWS::S3::Bucket", {"DeletionPolicy": "Retain"})


def test_nag_harness_reports_findings():
    """Sanity check: the same harness reports S1/S10 for a bare bucket, so 'no findings' above is meaningful."""
    from aws_cdk import aws_s3 as s3

    app = cdk.App(context=FEATURE_FLAGS)
    stack = cdk.Stack(app, "bare")
    s3.Bucket(stack, "Bare")
    cdk.Aspects.of(app).add(AwsSolutionsChecks())
    msgs = assertions.Annotations.from_stack(stack).find_error("*", assertions.Match.string_like_regexp("AwsSolutions-S1.*"))
    assert msgs
