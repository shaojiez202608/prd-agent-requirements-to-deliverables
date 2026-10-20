# Verification

Everything below was run on 2026-10-20/21 (UTC) on a macOS arm64 machine with Python 3.12.13 (project venv via uv),
Node.js 24.14.0, Apple clang 21 and AWS CLI 2, after the review fixes in this round. Anything not listed was not run.

## Unit tests

Command: `uv run pytest` → **103 passed, 0 failed, 0 skipped** (4.2 s).

| File | Tests | Covers |
|---|---|---|
| tests/test_intake_pending.py | 16 | FR-8 pending-item rules: missing, invalid, conflict, conditional and cross-field rules; Latin-1 only for text that reaches the PDF (and only when quick_start is requested); reserved markers `<!--`, `-->`, `*/`; outputs must include thing_model |
| tests/test_prompt_compiler.py | 13 | FR-1 determinism, click-order independence, whitespace, CLARIFY_ONLY mode, committed prompts up to date; header echoes only known schema_version/variant; case-insensitive marker neutralisation; plain-decimal numbers and the 2^53 limit; FR-9 instructions read from `system-prompt.md` (edit changes the prompt, text not duplicated in either compiler, malformed file rejected) |
| tests/test_js_parity.py | 1 | `intake/compiler.js` (Node) and the Python compiler give byte-identical text for 12 fixtures: the 4 samples, 3 malformed roots, odd values, CJK/reserved text with and without quick_start, small decimals/`-0`/range limits, header injection. The instructions are passed in from `system-prompt.md` |
| tests/test_generate.py | 11 | Acceptance 1 and 3, determinism including PDF bytes, committed example up to date, subset of deliverables (with and without the intake), open items, panel IDs; a failure in the PDF step leaves no output folder and no temporary folder; regenerating into an existing folder |
| tests/test_consistency.py | 20 | Acceptance 2 variants (file and exact line), missing/unknown rows, swapped IDs, hint for an edited thing model, missing markers/files, JSON report, stale PDF; FR-7 core files cannot be planned away (validate, check-progress and publish all refuse); `outputs` defines required files; dp_table.h without `DP_DEFINE` or without `#define` lines fails; visible IDs (`text_mismatch`); HTML comments ignored; reference lines ignore nested `id` keys and work on compact JSON |
| tests/test_progress.py | 7 | FR-4: missing report, skeleton file, claimed but missing file, file due but not listed, dropped file, failed validation |
| tests/test_pdf.py | 3 | PDF output, embedded source hash, non-Latin-1 rejected with the line number |
| tests/test_changes.py | 5 | FR-10 change log and breaking-change classification; enum reorder/insert breaking, append compatible; duplicate IDs rejected (CLI exit 3) |
| tests/test_forms.py | 3 | Committed forms match the builder (schema, compiler and system prompt embedded); no external URLs or network APIs; CSP present |
| tests/test_publish.py | 6 | Local and S3 (fake client with conditional-write semantics) publish/fetch, refused when inconsistent, tamper detection, immutable names locally and on S3 (nothing overwritten), other S3 errors propagate |
| tests/test_device_demo.py | 1 | Generated C skeleton compiles with `-std=c99 -Wall -Wextra -Werror` (compile only, see below) |
| tests/test_cli.py | 7 | Exit codes 0/1/2/3: generate refuses on pending items, exits 1 when its validation fails, 3 on PDF/I/O errors with the folder unchanged; Chinese product name is a pending item, not a crash; `--intake` on validate, check-progress and publish |
| tests/test_infra.py | 5 | CDK stack with cdk-nag AwsSolutions: no unsuppressed errors or warnings; buckets private, encrypted, tagged; TLS-only policies; `retain` with the customer config; harness sanity test (a bare bucket produces AwsSolutions-S1) |
| tests/test_scripts.py | 2 | Cleanup script refuses stack names without `proto-prd-` before any AWS call; sandbox stack and residue check use the prefix |
| tests/test_docs.py | 3 | README.md and README.zh-CN.md have the same number of sections and the same command table; no internal names or local absolute paths in tracked files |

## Acceptance criteria

| # | Criterion | How it was checked | Result |
|---|---|---|---|
| 1 | The sample intake generates six deliverables and the checker reports them consistent | `prd-agent generate sample-data/smart-plug.pm.intake.json --out /tmp/…/a1`, then `validate` and `check-progress` | Exit 0, 12 files plus PROGRESS.md; `Consistency check: PASS` (PRD, quick-start, panel-spec, HTML, mermaid 6 entries each, dp_table.h 12); `Progress log: PASS` |
| 2 | One changed ID in a deliverable is reported with its file and line | Changed `timer_task` 5→7 in the PRD table of that folder | Exit 1, exactly one difference: `PRD.md:57: id_mismatch: identifier timer_task: ID 7 here, ID 5 in thing model (thing-model.json:66)` |
| 3 | Missing key fields: list of items to confirm, no deliverables | `prd-agent generate sample-data/smart-plug.missing-fields.intake.json --out /tmp/…/a3` | Exit 2, 4 pending items listed, output folder not created |
| 4 | Checker and prompt compilation have unit tests that ran | See above | 103 passed |
| 5 | Chinese and English README with deployment, usage, cleanup and limitations | README.md, README.zh-CN.md (same sections, checked by test_docs.py) | Present |

## Review findings re-checked from the command line

| Finding | Command | Result after the fix |
|---|---|---|
| Core files planned away | Generated folder, removed PRD.md, quick-start.md/.pdf, device-demo/ and their lines in PROGRESS.md; `validate`, `check-progress`, `publish` | validate exit 1 with 4 × `missing_file`; check-progress FAIL (4 × "planned files omit … FR-7 core deliverable"); publish `refused` |
| Chinese product name | `check-intake` and `generate` with `hardware.product_name` = Chinese text | Both exit 2 with `[invalid] hardware.product_name: contains characters outside Latin-1 …`; no output folder |

## Other checks that ran

| Check | Command | Result |
|---|---|---|
| Form behaviour in a DOM (jsdom 24.1.3, installed in a scratch folder outside the repo) | `NODE_PATH=… node scripts/form_smoke_test.js intake/<form>.html sample-data/<intake>.json` for pm, frontline and missing-fields | Prompt text from filling the fields and clicking Generate is byte-identical (`cmp`) to `examples/prompts/*.prompt.txt` for all three. Status line: 0, 20 and 4 pending items |
| Lint | `uvx ruff check .` (ruff 0.17.1) | No findings |
| CDK synth with cdk-nag | `npx -y aws-cdk@2 synth -c config=config/sandbox.json -o <folder outside the repo>` (CLI 2.1146.0, aws-cdk-lib 2.273.0, cdk-nag 2.38.2) | Exit 0, no errors or warnings; NagReport 10 rows, all Compliant, 0 suppressed |
| AWS deployment and teardown | See DEPLOYMENT-LOG.md | Deploy, end-to-end check (publish, fetch, HTTP denied, anonymous 403, immutable re-publish refused, S3 conditional write 412), emptying all versions, destroy and residue check all done; no residue |
| PDF visual check | Opened examples/smart-plug/quick-start.pdf in an earlier round; the file is byte-identical now (test_generate.py) | Headings, lists, table and code blocks rendered on 2 pages |

## Security scans

| Tool | Scope | Result | Handling |
|---|---|---|---|
| detect-secrets 1.5.0 (`uvx detect-secrets scan --all-files`, excluding .venv, caches and .git) | Working tree | 0 findings | - |
| gitleaks 8.30.1 (`gitleaks git .`, `gitleaks dir .`) | Full git history and working tree | No leaks found | Re-run after the history rewrite; see the maintainer report |
| ASH v3.7.1, local mode | 105 files | Run in an earlier round only, **not re-run in this round**. Then: bandit 127 Low (asserts and fixed-argument subprocess calls in tests), detect-secrets and npm-audit PASSED | - |
| ASH scanners not run | cdk-nag, cfn-nag, checkov, grype, syft, semgrep, opengrep | MISSING in ASH local mode in that earlier round (installs timed out or need Docker) | cdk-nag ran separately (synth and tests). The others were **not run** |
| Holmes | - | **Not run: Holmes is not available on this machine** | - |

## Not run, and why

- **Linking and running the device demo.** The compile step passes. Linking fails on this machine because of a
  local toolchain problem (`ld: tapi error: malformed file` in the installed SDK, re-checked in this round) that
  is unrelated to the code.
  The test therefore compiles only.
- **Rendering the mermaid diagram.** No mermaid renderer was installed (it needs a headless browser download).
  The labels are checked by regular expressions only.
- **Manual testing in a real browser.** The forms were exercised in jsdom, not in an interactive browser session.
  Clipboard copy and file download/upload (export/import) were not exercised.
- **A real AI agent run (for example Kiro) on the prompt.** Not run; the project constraints forbid online AI
  calls. The local reference generator stands in for the agent.
- **ASH in this round, the scanners marked MISSING**, and **Holmes** (see above).
