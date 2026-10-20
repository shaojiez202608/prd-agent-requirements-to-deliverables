# Contributing Guidelines

Thank you for your interest in contributing. This is a prototype; small, focused changes are easiest to review.
Please read this document before you open an issue or a pull request.

## Reporting bugs and feature requests

Use the issue templates in `.github/ISSUE_TEMPLATE/`. Check existing issues first. Include the commit you used,
the command you ran, what you expected and what happened. **Do not report security issues in public issues**; see
[SECURITY.md](SECURITY.md).

## Pull requests

1. Open an issue first for larger changes. One pull request does one thing; it is squash-merged.
2. Work on a branch from `main` (for example `fix/validate-html-comments`).
3. **Every change needs a test.** Bug fixes get a test that fails without the fix. Run the CI checks locally
   before you push:
   ```bash
   make lint test synth scan
   ```
4. Fill in the pull request template: which checks you ran, and what you did not test.
5. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
   `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `test: ...`, `chore: ...`, `ci: ...`, `refactor: ...`.
   The body says what changed, why, and how it was verified.

## Project-specific rules

- Keep the knowledge-base numbering: rules in the lowest fitting folder, cases only in `10-project-cases`.
- If you change `src/prd_agent/intake.py` or `src/prd_agent/prompt.py`, make the same change in
  `intake/compiler.js`; `tests/test_js_parity.py` must pass.
- If you change templates, the schema or `knowledge-base/00-project-rules/system-prompt.md`, regenerate the
  committed outputs:
  ```bash
  uv run prd-agent build-forms
  uv run prd-agent generate sample-data/smart-plug.pm.intake.json --out examples/smart-plug
  for v in pm frontline missing-fields; do
    uv run prd-agent compile-prompt sample-data/smart-plug.$v.intake.json --out examples/prompts/smart-plug.$v.prompt.txt
  done
  ```

## What must never be committed

- AWS account IDs, ARNs with real account IDs, access keys, profile names, or command output that contains them.
  Use `111122223333` as the account ID in examples and replace 12-digit numbers before you paste logs.
- Real configuration: `infra/config/*.json` is ignored; only `*.example.json` templates are committed.
- Real company, customer, product, person or module names. Use synthetic data only.
- Build output (`cdk.out/`, `cdk.context.json`, `out/`) and caches.

`make scan` runs gitleaks on the full history; `tests/test_docs.py` fails on 12-digit numbers outside a short
allow list.

## Using AI assistants

You may use AI coding assistants. You are responsible for every line you submit: **you must be able to explain
any line an AI wrote**, and you must have run the tests yourself. Do not paste secrets, account IDs or
non-public data into an AI tool. Repository-level instructions for AI assistants are in the
"Contributing to this repository" section of [AGENTS.md](AGENTS.md#contributing-to-this-repository).

## Licensing

See [LICENSE](LICENSE). By submitting a pull request you confirm that you have the right to submit the
contribution and that it can be distributed under the MIT-0 license of this project. New third-party
dependencies must be listed in [THIRD-PARTY-LICENSES](THIRD-PARTY-LICENSES) with the license taken from the
package metadata or the official repository.

## Code of Conduct

This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
