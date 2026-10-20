# Deployment log

Account: `111122223333` (placeholder; the real sandbox account is never recorded). Region: us-east-1 (from
`AWS_REGION`). Earlier deployments of the same stack were destroyed earlier on the same day; their bootstrap template
objects were removed in this run (see "Bootstrap assets").

## Run of 2026-10-20 (UTC), commit `1eb4af5`

| Item | Value |
|---|---|
| Commit | `1eb4af5` (`fix(deps): place exclude-newer first in [tool.uv]`). Uncommitted changes at run time: documentation only (this file, VERIFICATION.md, CHANGELOG.md, docs/) |
| Stack / config | `proto-prd-artifacts`, `infra/config/sandbox.json` copied by `make init` from `sandbox.example.json` (unchanged) |
| Tools | CDK CLI 2.1146.0 (pinned in Makefile), aws-cdk-lib 2.273.0, cdk-nag 2.38.2, jsii 1.141.0 (from `uv.lock` with the 7-day cooldown), uv 0.10.10, Node.js 24.14.0, AWS CLI 2.33.17 |
| Credentials | IAM user credentials from the environment (preflight shows principal type `user`) |

### Steps

| # | Command | Result |
|---|---|---|
| 1 | `make deploy CDK_OUT=<scratch>/r4-a` with `PREFLIGHT_CONFIRM=yes` (17:22:43 to 17:24:47) | Preflight PASS: account shown as last four digits and confirmed, region us-east-1, uv/node/npx/aws present, Docker not running (not required), S3 and CloudFormation available in the region (SSM public parameters), `CDKToolkit` UPDATE_COMPLETE version 30, stack did not exist, S3 bucket quota 153 of 10000 used. Synth with cdk-nag OK. Diff guard: no deletions or replacements. Deploy: "Deployment time: 47.35s", "Total time: 66.53s" (the CDK figures exclude preflight and synth) |
| 2 | `make verify` | **21 passed, 0 failed**: Block Public Access, SSE-S3, ACLs disabled and tags on both buckets; versioning and access logging on the artifact bucket; `DenyPrincipalsOutsideAccount` present; publish of the example (13 files + manifest); object encrypted; fetch with checksum verification, `validate` and `check-progress` PASS; re-publish under the same name refused; S3 conditional write on an existing key `PreconditionFailed`; no version added by the refused writes (14); plain HTTP `AccessDenied`; anonymous GET 403; anonymous PUT 403 |
| 3 | `make deploy CDK_OUT=<scratch>/r4-b WRITERS=arn:aws:iam::111122223333:role/proto-prd-nonexistent-publisher` (account taken from the credentials at run time; 17:25:39 to 17:27:01) | Diff: adds statement `DenyWritesExceptPublishers` only; diff guard: no deletions or replacements; update "Deployment time: 11.74s" |
| 4 | `uv run python scripts/ops.py verify --config infra/config/sandbox.json --expect-write-denied` | **13 passed, 0 failed**: the caller (not in the writer list) gets `AccessDenied` on PutObject; list/read still allowed |
| 5 | `uv run python scripts/ops.py cleanup --config infra/config/sandbox.json --cdk-out <scratch>/r4-a <scratch>/r4-b` with the three confirmation variables set (17:27:09 to 17:27:32) | Stack name confirmed; 14 object versions in the artifact bucket, 0 in the log bucket, data deletion confirmed, 14 deleted; `cdk destroy`: destroyed; 2 project asset keys, 2 versions deleted from the bootstrap bucket after confirmation; exit 0, no warnings |
| 6 | `uv run python scripts/ops.py verify-cleanup --prefix proto-prd- --regions us-east-1 --cdk-out <scratch>/r4-a <scratch>/r4-b <synth of e799662>` (17:27), then `make verify-cleanup` | Every category 0 (table below); exit 0 for both. `head-bucket` on both bucket names: 404. `CDKToolkit` still UPDATE_COMPLETE |

### Residue check

| Category (us-east-1, prefix `proto-prd-`) | Count |
|---|---|
| CloudFormation stacks not DELETE_COMPLETE | 0 |
| S3 buckets with the prefix in the region | 0 |
| Resources tagged `Project=prd-agent` + `Teardown=after-test` that still exist | 0 |
| Log groups `/aws/lambda/proto-prd-*`, Lambda functions | 0, 0 |
| IAM roles, customer managed policies | 0, 0 |
| ECR repositories, KMS aliases | 0, 0 |
| API Gateway REST / HTTP APIs | 0 / 0 |
| This project's objects in the CDK bootstrap bucket | 0 |

Result: **cleaned up, no residue**. Only `us-east-1` was used. Only the `proto-prd-artifacts` stack and this
project's asset objects were touched; the `CDKToolkit` stack and other users' resources were not changed.

### Bootstrap assets

The bootstrap bucket is shared and versioned. This project's objects were identified by the asset keys in
`cdk.out/*.assets.json` (content hashes of the synthesized template):

| Asset key (prefix) | Synthesized from | Deployed in | Deleted |
|---|---|---|---|
| `4f5b0552…` | commits `e799662` and `fd49754` (identical template) | the two earlier runs | 16:58 UTC (first run of this round) |
| `85094a8d…` | `9618f4a`, `9dee339` and `1eb4af5`, no writer context | step 1 of each run in this round | after each run (16:58, 17:05, 17:27 UTC) |
| `3b9e5ddb…` | `9618f4a`, `9dee339` and `1eb4af5`, with the writer context of step 3 | step 3 of each run in this round | after each run (16:59, 17:05, 17:27 UTC) |

### Earlier runs in this round and the failure they found

| Commit | Time (UTC) | Result |
|---|---|---|
| `9618f4a` | 16:51 to 16:59 | Deploy, verify (21/21) and writer-deny verify (13/13) passed. **Cleanup missed one bootstrap object**: `cdk destroy -o <first folder>` re-synthesized without the writer context and overwrote that folder's `assets.json` before the keys were read. A second cleanup call removed the object. Fixed in `9dee339` (keys read first, destroy writes to a temporary folder, with a test) |
| `9dee339` | 17:00 to 17:05 | Full run passed, cleanup removed both objects, no residue |
| `1eb4af5` | 17:22 to 17:27 | Repeated after the ASH fixes changed `uv.lock` and `scripts/ops.py`; this is the run recorded above |

### What this run does not prove

- It does not prove behaviour in other regions or partitions, with role credentials (the run used IAM user
  credentials), or under `removal_policy: retain` (customer config, not deployed).
- Cross-account denial was not exercised with a second account; the account-boundary statement was verified to be
  present and anonymous requests were denied.
- Server access log delivery was not observed (logs arrive after hours; the log bucket held 0 objects).
- The destructive-diff guard was only exercised with non-destructive diffs in AWS; its refusal path is covered by
  unit tests with recorded diff text.
- The GitHub workflows (`ci.yml`, `deploy-verify.yml`) were not run on GitHub.
