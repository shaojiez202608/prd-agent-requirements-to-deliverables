# Verification

Everything below was run on 2026-10-20 on a macOS arm64 machine with Python 3.12.13 (project venv via uv),
Node.js 24, Apple clang 21 and AWS CLI 2. Anything not listed was not run.

## Unit tests

Command: `uv run pytest` → **71 passed, 0 failed, 0 skipped**.

| File | Tests | Covers |
|---|---|---|
| tests/test_intake_pending.py | 12 | FR-8 pending-item rules: missing, invalid, conflict, conditional and cross-field rules |
| tests/test_prompt_compiler.py | 8 | FR-1 determinism, click-order independence, whitespace normalisation, CLARIFY_ONLY mode, injection marker neutralised, committed prompts up to date |
| tests/test_js_parity.py | 1 | `intake/compiler.js` (run with Node) and the Python compiler give byte-identical text for 8 fixtures, edge cases included |
| tests/test_generate.py | 9 | Acceptance 1 (six deliverables, validation PASS), acceptance 3 (insufficient input: no output folder), determinism including PDF bytes, committed example up to date, open items instead of guesses, IDs on the panel sketch |
| tests/test_consistency.py | 12 | Acceptance 2: changed ID, identifier or access in PRD, quick-start, panel spec, HTML, mermaid or C header, reported with the file and the exact line. Also missing/unknown rows, swapped IDs, edited thing model (hint), missing markers, missing files, JSON report, stale PDF |
| tests/test_progress.py | 7 | FR-4: missing report, skeleton file, claimed but missing file, file due but not listed, dropped file, failed validation |
| tests/test_pdf.py | 3 | PDF output, embedded source hash, non-Latin-1 rejected with the line number |
| tests/test_changes.py | 3 | FR-10 change log, breaking-change classification |
| tests/test_forms.py | 3 | Committed forms match the builder; no external URLs or network APIs; CSP present |
| tests/test_publish.py | 4 | Local and S3 (fake client) publish/fetch, refused when inconsistent, tamper detection, immutable bundle names |
| tests/test_device_demo.py | 1 | Generated C skeleton compiles with `-std=c99 -Wall -Wextra -Werror` (compile only, see below) |
| tests/test_cli.py | 3 | Exit codes 0/2/3, generate refuses, then validate and check-progress pass |
| tests/test_infra.py | 5 | CDK stack with cdk-nag AwsSolutions: no unsuppressed errors or warnings; buckets private, encrypted and tagged; TLS-only policies; `retain` with the customer config; a harness sanity test (a bare bucket does produce AwsSolutions-S1) |

Negative check of the nag test: with the harness sanity test in place, a bare bucket produces an S1 error, so the
"no findings" assertion for the real stack is meaningful.

## Acceptance criteria (spec section 9)

| # | Criterion | How it was checked | Result |
|---|---|---|---|
| 1 | The sample intake generates six deliverables and the checker reports them consistent | `prd-agent generate sample-data/smart-plug.pm.intake.json --out …` then `validate` and `check-progress`; tests in test_generate.py | PASS: 12 files plus PROGRESS.md; `Consistency check: PASS`; `Progress log: PASS` |
| 2 | One changed ID in a deliverable is reported with its file and line | Changed `timer_task` 5→7 in PRD.md | `PRD.md:57: id_mismatch: identifier timer_task: ID 7 here, ID 5 in thing model (thing-model.json:66)`; more variants in test_consistency.py |
| 3 | Missing key fields: list of items to confirm, no deliverables | `prd-agent generate sample-data/smart-plug.missing-fields.intake.json --out …` | Exit 2, 4 pending items listed, output folder not created |
| 4 | Checker and prompt compilation have unit tests that ran | See above | 71 passed |
| 5 | Chinese and English README with deployment, usage, cleanup and limitations | README.md, README.zh-CN.md | Present |

## Other checks that ran

| Check | Command | Result |
|---|---|---|
| Form behaviour in a DOM (jsdom 24, installed in a scratch folder outside the repo) | `NODE_PATH=… node scripts/form_smoke_test.js intake/<form>.html sample-data/<intake>.json` for pm, frontline and missing-fields | Prompt text from filling the form fields and clicking Generate is byte-identical to `examples/prompts/*.prompt.txt` for all three. Status line: 0, 20 and 4 pending items |
| Lint | `uvx ruff check .` | No findings |
| CDK synth with cdk-nag | `npx -y aws-cdk@2 synth -c config=config/sandbox.json` | Success; NagReport: all AwsSolutions rules Compliant, no suppressions |
| AWS deployment and teardown | See DEPLOYMENT-LOG.md | Deploy, end-to-end check, destroy and residue check all done; no residue |
| PDF visual check | Opened examples/smart-plug/quick-start.pdf | Headings, lists, table and code blocks rendered on 2 pages |

## Security scans

| Tool | Scope | Result | Handling |
|---|---|---|---|
| detect-secrets 1.5.0 (`uvx detect-secrets scan --all-files`) | Working tree, excluding .venv and caches | 0 findings | Run before each commit |
| gitleaks 8.30.1 (`gitleaks git .`, `gitleaks dir .`) | Full git history (all commits) and working tree | No leaks found | - |
| ASH v3.7.1, local mode (`ash --mode local`, output in a folder outside the project, no zip files in the project) | 105 files | bandit: 127 Low (123 × B101 `assert` in tests, 2 × B404 and 2 × B603 for `subprocess` with fixed arguments in tests), below the MEDIUM threshold, PASSED. detect-secrets PASSED. npm-audit PASSED | Accepted: all findings are in tests (asserts are how pytest works; subprocess runs `node`/`cc` with fixed argument lists) |
| ASH scanners not run | cdk-nag, cfn-nag, checkov, grype, syft, semgrep, opengrep | MISSING in ASH local mode. The tool installs timed out on this machine's network, or the scanners need Docker or binaries that are not installed | cdk-nag ran separately (synth and tests). The others were **not run** |
| Holmes | - | **Not run: Holmes is not available on this machine** | - |

## Not run, and why

- **Linking and running the device demo.** The compile step passes. Linking fails on this machine because of a
  local toolchain problem (`ld: tapi error: malformed file` in the installed SDK) that is unrelated to the code.
  The test therefore compiles only.
- **Rendering the mermaid diagram.** No mermaid renderer was installed (it needs a headless browser download).
  The labels are checked by regular expressions only.
- **Manual testing in a real browser.** The forms were exercised in jsdom, not in an interactive browser session.
  Clipboard copy and file download/upload (export/import) were not exercised.
- **A real AI agent run (for example Kiro) on the prompt.** Not run; the spec forbids online AI calls in this
  project. The local reference generator stands in for the agent.
- **ASH scanners marked MISSING** (see above) and **Holmes**.
