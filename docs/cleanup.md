# Cleanup

The commands are in [README.md](../README.md#cleanup): `make destroy`, then `make verify-cleanup`. This page explains
what they do.

## Local

Delete `out/` (generated folders), `/tmp/prd-agent-cdk.out` (synth output) and, if you no longer need them,
`infra/config/*.json` (your real configuration; the templates stay).

## `make destroy` (scripts/ops.py cleanup)

1. Refuses stack names that do not start with `--prefix` (default `proto-prd-`, the sandbox prefix). For another
   stack, call `uv run python scripts/ops.py cleanup --config infra/config/customer.json --prefix prd-agent- --cdk-out <dir>`.
2. Asks you to type the stack name.
3. Lists the stack's buckets with their number of object versions and asks again (`DELETE DATA`) before it deletes
   all versions and delete markers. With `removal_policy: retain` nothing is emptied and the buckets stay.
4. Runs `cdk destroy`. No auto-delete custom resource is deployed (it would add a Lambda function and an IAM role),
   which is why the buckets are emptied first.
5. Deletes this project's template objects (all versions) from the CDK bootstrap bucket after a third confirmation
   (`DELETE ASSETS`). They are found by the object keys in `cdk.out/*.assets.json` of the folders passed with
   `--cdk-out`. Objects of other projects, CDK's shared provider assets and the `CDKToolkit` stack are not touched.
   To include the template of an earlier deployment, synth that commit into another folder and pass both folders.

A failed step prints a warning and the next steps still run; the command then exits with status 1. Non-interactive
use (CI) sets `CLEANUP_CONFIRM_STACK=<stack name>`, `CLEANUP_CONFIRM_DATA="DELETE DATA"` and
`CLEANUP_CONFIRM_ASSETS="DELETE ASSETS"`.

The access log bucket can receive late log deliveries after step 3. If `cdk destroy` fails because a bucket is not
empty, run `make destroy` again.

## `make verify-cleanup` (scripts/ops.py verify-cleanup)

Checks every region in `REGIONS` (default `AWS_REGION`, else us-east-1) and exits non-zero if any count is not 0 or
a category could not be read:

CloudFormation stacks with the prefix (not `DELETE_COMPLETE`), S3 buckets with the prefix in that region,
resources tagged `Project=prd-agent` and `Teardown=after-test` that still exist (the tagging index lags behind
deletions, so each listed bucket is confirmed with `head-bucket`), Lambda log groups and functions, IAM roles and
customer managed policies, ECR repositories, KMS aliases, API Gateway REST and HTTP APIs, and this project's objects
in the CDK bootstrap bucket. This stack creates only the two buckets and their policies; the other categories
confirm that nothing else was left behind.

The result is either "cleaned up, no residue" or a list of what remains.
