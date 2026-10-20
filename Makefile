# Single entry point. CI uses only the checking targets (lint, test, synth, scan); they never modify files.
# Targets that touch AWS (preflight, deploy, verify, destroy, verify-cleanup) use the credentials in your shell.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
CONFIG ?= config/sandbox.json
CDK ?= npx -y aws-cdk@2.1146.0
CDK_OUT ?= /tmp/prd-agent-cdk.out
REGIONS ?= $(or $(AWS_REGION),us-east-1)
# Optional: comma-separated IAM role/user ARNs that may write bundles (passed as context, never stored).
WRITERS ?=
CTX := -c config=$(CONFIG) $(if $(WRITERS),-c writer_principal_arns=$(WRITERS),)
OPS := uv run python scripts/ops.py

.PHONY: help init lint test synth preflight deploy verify destroy verify-cleanup scan ci
help:
	@echo "init lint test synth scan | preflight deploy verify destroy verify-cleanup (AWS) | ci"

init:
	uv sync
	@for f in infra/config/*.example.json; do t="$${f%.example.json}.json"; \
	  if [ ! -f "$$t" ]; then cp "$$f" "$$t"; echo "created $$t from $$f (edit it, it is not committed)"; fi; done

lint:
	uv run ruff check .

test:
	uv run pytest

synth: init
	cd infra && $(CDK) synth $(CTX) -o $(CDK_OUT) --quiet
	@echo "synth OK (cdk-nag AwsSolutions report in $(CDK_OUT))"

preflight: init
	$(OPS) preflight --config infra/$(CONFIG)

deploy: preflight synth
	cd infra && $(CDK) diff $(CTX) -o $(CDK_OUT) > $(CDK_OUT)/diff.txt 2>&1
	sed -E 's/[0-9]{12}/111122223333/g' $(CDK_OUT)/diff.txt
	$(OPS) diff-guard $(CDK_OUT)/diff.txt
	cd infra && $(CDK) deploy $(CTX) -o $(CDK_OUT) --require-approval never 2>&1 | sed -E 's/[0-9]{12}/111122223333/g'

verify:
	$(OPS) verify --config infra/$(CONFIG)

destroy:
	$(OPS) cleanup --config infra/$(CONFIG) --cdk-out $(CDK_OUT)

verify-cleanup:
	$(OPS) verify-cleanup --prefix proto-prd- --regions $(REGIONS) --cdk-out $(CDK_OUT)

scan:
	scripts/scan.sh

ci: lint test synth scan
