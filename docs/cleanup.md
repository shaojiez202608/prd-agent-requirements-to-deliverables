# Cleanup

## Local

```bash
rm -rf out/                 # generated folders
```

## AWS (optional stack)

With the sandbox config the buckets have removal policy `destroy`. They must be empty, including every object
version, before CloudFormation can delete them. No auto-delete custom resource is deployed (it would add a Lambda
function and an IAM role), so empty them first:

```bash
# 1. dry run, then delete all object versions and delete markers in the stack's own buckets
uv run python scripts/empty_stack_buckets.py proto-prd-artifacts --region us-east-1
uv run python scripts/empty_stack_buckets.py proto-prd-artifacts --region us-east-1 --yes

# 2. destroy the stack
cd infra && npx -y aws-cdk@2 destroy -c config=config/sandbox.json --force && cd ..

# 3. residue check: every count must be 0
scripts/residue_check.sh proto-prd- us-east-1
```

The access log bucket can receive late log deliveries after step 1. If `destroy` fails because a bucket is not
empty, run step 1 again and repeat step 2.

With the customer config (`retain`), `cdk destroy` removes the stack but keeps both buckets and their data. Delete
them by hand only when the data owner agrees.

The residue check covers CloudFormation stacks, S3 buckets, resources tagged `Project=prd-agent` (and
`Teardown=after-test`), Lambda log groups and functions, IAM roles and customer policies, ECR repositories, API
Gateway APIs, KMS aliases and AgentCore runtimes. This stack creates only the two buckets and their bucket policies.
The other categories are checked to confirm that nothing else was left behind.
