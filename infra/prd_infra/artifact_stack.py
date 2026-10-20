"""Optional stack: private, versioned S3 bucket for published deliverable bundles.

Nothing else is deployed. There is no compute, no public endpoint and no IAM
user. Publishers use their own short-lived role credentials; see
docs/deployment-guide.md for a least-privilege policy example.
"""

from __future__ import annotations

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_s3 as s3
from cdk_nag import NagSuppressions
from constructs import Construct

from .config import DeployConfig


class ArtifactStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, cfg: DeployConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        removal = RemovalPolicy.DESTROY if cfg.removal_policy == "destroy" else RemovalPolicy.RETAIN

        logs = s3.Bucket(
            self, "AccessLogBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            minimum_tls_version=1.2,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(cfg.access_log_expiration_days))],
            removal_policy=removal,
        )
        NagSuppressions.add_resource_suppressions(logs, [{
            "id": "AwsSolutions-S1",
            "reason": "This bucket is the server access log target. Logging it into itself would loop; "
                      "a second log bucket would only move the finding.",
        }])

        bucket = s3.Bucket(
            self, "ArtifactBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            minimum_tls_version=1.2,
            versioned=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            server_access_logs_bucket=logs,
            server_access_logs_prefix="artifact-bucket/",
            lifecycle_rules=[s3.LifecycleRule(
                noncurrent_version_expiration=Duration.days(cfg.noncurrent_version_expiration_days),
                abort_incomplete_multipart_upload_after=Duration.days(1),
            )],
            removal_policy=removal,
        )

        CfnOutput(self, "ArtifactBucketName", value=bucket.bucket_name)
        CfnOutput(self, "AccessLogBucketName", value=logs.bucket_name)
        self.bucket = bucket
        self.log_bucket = logs
