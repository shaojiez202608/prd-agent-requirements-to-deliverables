#!/usr/bin/env python3
"""CDK entry point. Usage (from infra/):

    npx -y aws-cdk@2 deploy -c config=config/sandbox.json

The account comes from the caller's credentials (CDK_DEFAULT_ACCOUNT); it is
never written into the repository.
"""

from __future__ import annotations

import os

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from prd_infra.artifact_stack import ArtifactStack
from prd_infra.config import load_config

app = cdk.App()
cfg = load_config(app.node.try_get_context("config") or "config/sandbox.json")
region = cfg.region if not cfg.region.startswith("<") else os.environ.get("CDK_DEFAULT_REGION")
ArtifactStack(app, cfg.stack_name, cfg=cfg,
              env=cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=region),
              description="PRD agent prototype: private bucket for deliverable bundles (not for production)")
for key, value in cfg.tags.items():
    cdk.Tags.of(app).add(key, value)
cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))
app.synth()
