#!/usr/bin/env bash
# Residue check after `cdk destroy`. Prints counts only, never account IDs.
# Usage: scripts/residue_check.sh <stack-name-prefix> [region]
set -uo pipefail
PREFIX="${1:-proto-prd-}"
REGION="${2:-${AWS_REGION:-us-east-1}}"
LOWER=$(echo "$PREFIX" | tr '[:upper:]' '[:lower:]')

# The CLI paginates some list calls and prints one count per page; sum them.
sum() { awk '{for(i=1;i<=NF;i++) if ($i ~ /^[0-9]+$/) t+=$i} END {print t+0}'; }

echo "region: $REGION, prefix: $PREFIX"
echo -n "CloudFormation stacks (not DELETE_COMPLETE): "
aws cloudformation list-stacks --region "$REGION" \
  --query "length(StackSummaries[?starts_with(StackName, '$PREFIX') && StackStatus!='DELETE_COMPLETE'])" --output text
echo -n "S3 buckets with prefix: "
aws s3api list-buckets --query "length(Buckets[?starts_with(Name, '$LOWER')])" --output text
echo -n "Resources tagged Project=prd-agent (tagging API): "
aws resourcegroupstaggingapi get-resources --region "$REGION" --tag-filters Key=Project,Values=prd-agent \
  --query "length(ResourceTagMappingList)" --output text
echo -n "Resources tagged Teardown=after-test and Project=prd-agent: "
aws resourcegroupstaggingapi get-resources --region "$REGION" \
  --tag-filters Key=Project,Values=prd-agent Key=Teardown,Values=after-test \
  --query "length(ResourceTagMappingList)" --output text
echo -n "Log groups with prefix /aws/lambda/$PREFIX: "
aws logs describe-log-groups --region "$REGION" --log-group-name-prefix "/aws/lambda/$PREFIX" \
  --query "length(logGroups)" --output text
echo -n "Lambda functions with prefix: "
aws lambda list-functions --region "$REGION" --query "length(Functions[?starts_with(FunctionName, '$PREFIX')])" --output text | sum
echo -n "IAM roles with prefix: "
aws iam list-roles --query "length(Roles[?starts_with(RoleName, '$PREFIX')])" --output text | sum
echo -n "IAM customer policies with prefix: "
aws iam list-policies --scope Local --query "length(Policies[?starts_with(PolicyName, '$PREFIX')])" --output text | sum
echo -n "ECR repositories with prefix: "
aws ecr describe-repositories --region "$REGION" --query "length(repositories[?starts_with(repositoryName, '$LOWER')])" --output text 2>/dev/null || echo "n/a"
echo -n "API Gateway REST APIs with prefix: "
aws apigateway get-rest-apis --region "$REGION" --query "length(items[?starts_with(name, '$PREFIX')])" --output text
echo -n "API Gateway HTTP APIs with prefix: "
aws apigatewayv2 get-apis --region "$REGION" --query "length(Items[?starts_with(Name, '$PREFIX')])" --output text
echo -n "KMS aliases with prefix alias/$PREFIX: "
aws kms list-aliases --region "$REGION" --query "length(Aliases[?starts_with(AliasName, 'alias/$PREFIX')])" --output text
echo -n "AgentCore runtimes with prefix: "
aws bedrock-agentcore-control list-agent-runtimes --region "$REGION" \
  --query "length(agentRuntimes[?starts_with(agentRuntimeName, '$(echo "$PREFIX" | tr '-' '_')')])" --output text 2>/dev/null || echo "n/a (CLI command not available)"
