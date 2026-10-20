# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-20

First tagged version of the prototype.

### Added
- Offline intake forms (frontline, PM) built from `intake/schema.json`; deterministic prompt compiler in JS and
  Python with a byte-parity test; agent instructions in `knowledge-base/00-project-rules/system-prompt.md` (FR-9).
- Numbered knowledge base with the `AGENTS.md` reading order (FR-3), deliverable templates and a synthetic case.
- CLI `prd-agent`: check-intake, compile-prompt, local reference generator, validate (consistency keyed on the
  thing model ID, including fixed visible-text patterns), check-progress, render-pdf, diff-model, build-forms,
  publish (immutable bundles, S3 conditional writes) and fetch.
- Optional CDK stack: private versioned S3 artifact bucket with access log bucket; bucket policy with an
  account-boundary deny and an optional writer list; config templates with validation that fails synth.
- Operations: `Makefile` (init, lint, test, synth, preflight, deploy, verify, destroy, verify-cleanup, scan),
  `scripts/ops.py` (read-only preflight, destructive-diff guard, end-to-end verification including deny paths,
  confirmed cleanup that also removes this project's bootstrap assets, residue check), `scripts/scan.sh`
  (gitleaks full history plus canary).
- CI workflow, manual deploy-verify workflow (OIDC, environment approval), Dependabot, issue and PR templates,
  CODEOWNERS.
- Repository files: LICENSE (MIT-0, Amazon copyright line), SECURITY, CODE_OF_CONDUCT, CONTRIBUTING,
  THIRD-PARTY-LICENSES, VERSION, CLAUDE.md, and the documents DECISIONS, OPEN-QUESTIONS, SECURITY-NOTES,
  THREAT_MODEL (draft), VERIFICATION, DEPLOYMENT-LOG and docs/standards-review.md.

### Fixed (during review rounds before the tag)
- Core FR-7 files can no longer be planned away in PROGRESS.md; dp_table.h must cover both entry kinds.
- Non-Latin-1 text for the PDF and reserved markers are pending items instead of crashes; generation is atomic.
- Prompt header echoes only known values; number formatting is identical in both compilers.
- Cleanup reads asset keys before `cdk destroy` re-synthesizes.

[Unreleased]: https://example.com/prd-agent-requirements-to-deliverables/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/prd-agent-requirements-to-deliverables/releases/tag/v0.1.0
