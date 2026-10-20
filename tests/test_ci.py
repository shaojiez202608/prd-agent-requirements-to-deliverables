"""CI hygiene: actions pinned by commit SHA with a version comment, minimal permissions, manual deploys."""

import re

from conftest import ROOT

WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def test_actions_are_pinned_by_sha_with_version_comment():
    uses = [ln.strip() for wf in WORKFLOWS for ln in wf.read_text(encoding="utf-8").splitlines() if "uses:" in ln]
    assert uses
    for line in uses:
        assert re.search(r"uses: [\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+$", line), line


def test_workflows_default_to_read_only_permissions():
    for wf in WORKFLOWS:
        assert "\npermissions:\n  contents: read\n" in wf.read_text(encoding="utf-8"), wf.name


def test_deploy_workflow_is_manual_behind_an_environment_with_oidc():
    text = (ROOT / ".github" / "workflows" / "deploy-verify.yml").read_text(encoding="utf-8")
    assert re.search(r"^on:\n  workflow_dispatch:\n\n", text, re.M)
    assert "environment: sandbox-aws" in text and "id-token: write" in text
    assert "role-to-assume: arn:aws:iam::111122223333:role/<DEPLOY_ROLE_NAME>" in text
