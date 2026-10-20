# Deployment log

Account: `<ACCOUNT_ID>` (sandbox, not recorded). Region: us-east-1 (from the environment; S3 is available there).
An earlier deployment of the same stack was destroyed on the same day; this file records only the run below.

## Run (2026-10-21)

| Item | Value |
|---|---|
| Stack | `proto-prd-artifacts` (config `infra/config/sandbox.json`) |
| Tool | `npx -y aws-cdk@2` (CLI 2.1146.0), aws-cdk-lib 2.273.0, cdk-nag 2.38.2 |
| Synth with cdk-nag | 0 AwsSolutions errors and 0 warnings. The NagReport has 10 rows, all Compliant, none suppressed: S1, S2, S5 and S10 for both buckets, S10 for both bucket policies |
| Deploy (UTC) | Command started 16:00:34, returned 16:02:30 (116 s wall clock, including synth, asset publishing and change set). CDK reported "Deployment time: 50.9s" (CloudFormation stack deployment only) and "Total time: 112.34s" |
| Bootstrap | Existing `CDKToolkit` stack used as is (not changed; status `UPDATE_COMPLETE` before and after) |
| Synth/deploy output | `-o` pointed to a folder outside the repository; nothing from it is committed |

### Resources created

| Logical ID | Type | Notes |
|---|---|---|
| ArtifactBucket | AWS::S3::Bucket | name `proto-prd-artifacts-artifactbucket…` (generated) |
| ArtifactBucketPolicy | AWS::S3::BucketPolicy | Denies non-TLS and TLS < 1.2 |
| AccessLogBucket | AWS::S3::Bucket | name `proto-prd-artifacts-accesslogbucket…` (generated) |
| AccessLogBucketPolicy | AWS::S3::BucketPolicy | Denies non-TLS and TLS < 1.2; allows the S3 logging service principal to write `artifact-bucket/*`, limited to the source bucket and account |
| CDKMetadata | AWS::CDK::Metadata | - |

No Lambda function, IAM role, IAM user, KMS key, log group, ECR repository, API or AgentCore resource was created.
CDK uploaded the synthesized template to the existing bootstrap staging bucket, which belongs to `CDKToolkit` and
was not modified otherwise.

### Verification steps and results

| # | Step | Result |
|---|---|---|
| 1 | `get-public-access-block` on both buckets | All four settings `true` |
| 2 | `get-bucket-encryption` | `AES256` (SSE-S3) on both |
| 3 | `get-bucket-versioning` | Artifact bucket `Enabled`; log bucket not versioned (as designed) |
| 4 | `get-bucket-ownership-controls` | `BucketOwnerEnforced` on both (ACLs disabled) |
| 5 | `get-bucket-logging` on the artifact bucket | Target prefix `artifact-bucket/` |
| 6 | `get-bucket-tagging` | `Project=prd-agent`, `Purpose=prototype`, `Teardown=after-test` on both |
| 7 | `prd-agent publish examples/smart-plug --dest s3://<bucket>/bundles --name demo-smart-plug-v1` | Exit 0. 13 files (12 deliverables and PROGRESS.md) plus MANIFEST.json: 14 objects, 14 versions |
| 8 | `head-object` on a published file | `ServerSideEncryption: AES256` |
| 9 | `prd-agent fetch …`, then `validate` and `check-progress` on the fetched copy | 13 files, all checksums verified; Consistency check PASS; Progress log PASS |
| 10 | `list-objects-v2` over plain HTTP (`--endpoint-url http://s3.us-east-1.amazonaws.com`) | `AccessDenied … with an explicit deny in a resource-based policy` (TLS-only policy works) |
| 11 | Unauthenticated HTTPS GET of a published object (`curl`) | HTTP 403 |
| 12 | Immutability: publish an edited copy under the same name `demo-smart-plug-v1` | Exit 1: `refused: s3://<bucket>/bundles/demo-smart-plug-v1/PRD.md already exists; bundles are immutable, choose a new bundle name`. Object versions under `bundles/` still 14 (nothing overwritten) |
| 13 | Immutability at the S3 level: `aws s3api put-object … --if-none-match '*'` on an existing key | `PreconditionFailed` (HTTP 412); versions still 14 |
| 14 | Fetch `demo-smart-plug-v1` again and `diff -r` against `examples/smart-plug` | Identical (published content unchanged) |
| 15 | Publish under a new name `demo-smart-plug-v1b` | Exit 0; 28 object versions in the bucket |

### Destroy

| Step | Command | Result |
|---|---|---|
| 1 | `uv run python scripts/empty_stack_buckets.py proto-prd-artifacts --region us-east-1` (dry run, then `--yes`, then dry run again) | Artifact bucket: 28 object versions found, 28 deleted, then 0. Log bucket: 0 (no logs delivered yet) |
| 1a | Prefix guard: the same script with stack name `prd-agent-artifacts` (no `proto-prd-` prefix) | `refusing: stack name must start with proto-prd-`, exit 3 |
| 2 | `npx -y aws-cdk@2 destroy -c config=config/sandbox.json --force` (16:06:14 to 16:06:37 UTC, 23 s) | `proto-prd-artifacts: destroyed` on first attempt |

### Residue check (16:06 UTC, `scripts/residue_check.sh proto-prd- us-east-1`)

| Category | Count |
|---|---|
| CloudFormation stacks `proto-prd-*` not DELETE_COMPLETE | 0 (the stack shows as `DELETE_COMPLETE`) |
| S3 buckets `proto-prd-*` (also `head-bucket` on both names: 404) | 0 |
| Resources tagged `Project=prd-agent` | 0 |
| Resources tagged `Project=prd-agent` + `Teardown=after-test` | 0 |
| Log groups `/aws/lambda/proto-prd-*` | 0 |
| Lambda functions | 0 |
| IAM roles / customer policies | 0 / 0 |
| ECR repositories | 0 |
| API Gateway REST / HTTP APIs | 0 / 0 |
| KMS aliases (no key was created, so no key in pending deletion) | 0 |
| AgentCore runtimes | 0 |

Result: **cleaned up, no residue**. Only the `proto-prd-artifacts` stack created in this run was touched; the
`CDKToolkit` stack and stacks of other users were not changed.
