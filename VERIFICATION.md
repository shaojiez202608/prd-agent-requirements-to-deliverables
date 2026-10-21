# Verification

Run on 2026-10-20 (UTC) on a macOS arm64 machine: Python 3.12.13 (project venv via uv 0.10.10), Node.js 24.14.0,
Apple clang 21, AWS CLI 2.33.17. Code commit: `b4bf9dd` (the documentation commit that records these results
follows it; tag `v0.1.0`). Configuration: `infra/config/sandbox.example.json` copied by `make init`, region
us-east-1. Anything not listed was not run. No model or AI service is involved in any check.

## Unit tests

`make test` (`uv run pytest`) → **140 passed, 0 failed, 0 skipped**.

| File | Tests | Covers |
|---|---|---|
| tests/test_intake_pending.py | 16 | FR-8 pending-item rules, Latin-1 rule for PDF text, reserved markers, required thing_model output |
| tests/test_prompt_compiler.py | 13 | Determinism, CLARIFY_ONLY mode, header echo, marker neutralisation, number formatting, FR-9 system prompt file |
| tests/test_js_parity.py | 1 | JS and Python compilers byte-identical on 12 fixtures (instructions from system-prompt.md) |
| tests/test_generate.py | 11 | Acceptance 1 and 3, determinism incl. PDF bytes, committed example current, atomic generation |
| tests/test_consistency.py | 20 | Acceptance 2 variants with file and line, FR-7 core files, both C header kinds, visible-text patterns, HTML comments, reference lines |
| tests/test_progress.py | 7 | FR-4 progress protocol |
| tests/test_pdf.py | 3 | PDF output, source hash, non-Latin-1 rejected |
| tests/test_changes.py | 5 | FR-10 change log; enum order; duplicate IDs |
| tests/test_forms.py | 3 | Committed forms current, no network APIs, CSP |
| tests/test_publish.py | 6 | Local and S3 (fake client) publish/fetch, immutability, tamper detection |
| tests/test_device_demo.py | 1 | C skeleton compiles with `-std=c99 -Wall -Wextra -Werror` |
| tests/test_cli.py | 7 | Exit codes 0/1/2/3, `--intake` |
| tests/test_infra.py | 7 | cdk-nag zero findings with and without writer context, bucket properties, TLS-only, retain config, account-boundary deny, writer deny follows context, harness negative case (bare bucket → S1) |
| tests/test_config.py | 12 | Config templates valid; regex, range and cross-field rules; account IDs rejected; writer ARNs; missing file points to `make init` |
| tests/test_scripts.py | 21 | ops.py: masking, diff guard (deletion/replacement, `ALLOW_DESTRUCTIVE`), asset keys, confirmations, cleanup prefix guard and key order before destroy, Stubber-based asset matching, residue exit codes, https-only probe, Makefile targets |
| tests/test_ci.py | 3 | Actions pinned by SHA with version comments, read-only default permissions, manual deploy workflow with environment and OIDC |
| tests/test_docs.py | 4 | README section and command parity, no internal names or local paths, no 12-digit numbers except `111122223333` |

Negative checks: the nag harness test shows that a bare bucket produces AwsSolutions-S1, so "zero findings" is
meaningful; `make synth` with an invalid config (destroy policy on a non-`proto-` stack without Teardown tag) fails
with both problems listed.

## Acceptance criteria

| # | Criterion | How it was checked | Result |
|---|---|---|---|
| 1 | Sample intake generates six deliverables, checker reports them consistent | `prd-agent generate sample-data/smart-plug.pm.intake.json --out <scratch>/a1`, `validate`, `check-progress` | Exit 0; `Consistency check: PASS`; `Progress log: PASS` |
| 2 | A changed ID is reported with file and line | `timer_task` 5→7 in the PRD table | `PRD.md:57: id_mismatch: identifier timer_task: ID 7 here, ID 5 in thing model (thing-model.json:66)` |
| 3 | Missing key fields: pending items, no deliverables | `generate` with `smart-plug.missing-fields.intake.json` | 4 pending items, exit 2, no output folder |
| 4 | Checker and prompt compiler have unit tests that ran | See above | 140 passed |
| 5 | Chinese and English README with deployment, usage, cleanup, limitations | README.md, README.zh-CN.md (parity tests) | Present, same section order |

## Other checks

| Check | Command | Result |
|---|---|---|
| Lint | `make lint` (ruff 0.17.0 from `uv.lock`) and `uvx ruff check .` (0.17.1) | No findings |
| CDK synth with cdk-nag, no AWS credentials needed | `make synth` (CDK CLI 2.1146.0, aws-cdk-lib 2.273.0, cdk-nag 2.38.2) | Exit 0; NagReport 10 rows, all Compliant, 0 suppressed |
| Form behaviour in jsdom 24.1.3 (installed outside the repository) | `scripts/form_smoke_test.js` for pm, frontline, missing-fields | Byte-identical to `examples/prompts/*.prompt.txt` (`cmp`) |
| Workflow lint | `uvx zizmor --persona=auditor .github/workflows` (zizmor 1.31.1, offline mode), `uvx --from actionlint-py actionlint` (1.7.12) | No findings (2 informational job-name findings were fixed) |
| AWS deployment, end-to-end, teardown | See DEPLOYMENT-LOG.md (commit `b4bf9dd`) | Preflight PASS; verify 21/21 and writer-deny 13/13; cleanup without warnings; residue check: cleaned up, no residue |

## Security scans

| Tool | Scope | Result |
|---|---|---|
| gitleaks 8.30.1 (`make scan`) | Full git history (all commits), default rules, no exemptions | No leaks found |
| gitleaks canary (`make scan`) | Generated fake AWS key in a temporary folder | Detected (scan fails if it is not) |
| detect-secrets 1.5.0 | Working tree | 0 findings (one false positive in `scripts/scan.sh` was removed by code change, not by exemption) |
| osv-scanner 2.7.0 (release binary in a scratch folder) | `uv.lock`, 31 packages | No issues found |
| ASH v3.7.1, `--mode local`, output in `_scan_out/PRD_agent/` outside the repository | Repository working tree | bandit PASSED (0 medium+, 242 low: asserts and fixed-argument subprocess calls in tests and scripts), checkov PASSED, detect-secrets PASSED, npm-audit PASSED, semgrep PASSED. **cdk-nag, cfn-nag, grype, syft, opengrep: MISSING** (not installed; no Docker on this machine) |

**The local ASH run is incomplete** (5 of 10 scanners MISSING), which the standard counts as not passed. The
missing scanners are left to a CI run on GitHub; they were not run anywhere in this round. cdk-nag itself did run
outside ASH (`make synth`, tests). Two actionable ASH findings from the first run were fixed in code: bandit B310
(`scripts/ops.py`, https-only check) and semgrep `uv-missing-dependency-cooldown` (`pyproject.toml`).

CI: run on GitHub after the repository was pushed (private); see "GitHub CI" below.

## Not run, and why

- Linking and running the device demo: compile passes; linking fails on this machine (`ld: tapi error` in the
  installed SDK, re-checked in an earlier round of the same day).
- Rendering the mermaid diagrams: no renderer installed; labels are checked by regular expressions.
- A real browser session for the forms (clipboard, file export/import): only jsdom.
- A real AI agent run on the prompt: the project constraints forbid online AI calls; the local generator stands in.

## What these results do not prove

- That AI-produced deliverables are correct: the checker proves ID, identifier and access consistency only.
- Behaviour in other regions, partitions or with role credentials, or with the `retain` (customer) config.
- That the GitHub workflows run as written: they were linted, not executed on GitHub.
- That the scanners MISSING in ASH would report nothing.

## GitHub CI (2026-10-21)

Workflow `ci` on GitHub-hosted runners (ubuntu-24.04), push to `main`, run 39526056186 at commit `a64e26d`:
all jobs succeeded (lint, test, synth, secret scan; ASH).

ASH v3.7.1 in container mode (image built from the Docker Hub copy of its base image, see the `ash` job):
10 of 10 scanners passed, 0 failed, 0 missing; 242 findings in total, 0 actionable, 0 suppressed.
This replaces the incomplete local ASH run above (five scanners missing for lack of Docker).

What this does not show: the `deploy-verify` workflow has not run on GitHub (it needs an OIDC role and an
environment with reviewers in the target account).
