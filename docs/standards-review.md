# Standards review (prototype repository checklist A–F)

Review of this repository against the project's checklist for AWS prototype repositories (sections A–F).
Status values: **Meets**, **Needs change**, **Not applicable** (with reason). "Initial" is the state at the start
of the review (commit `91afdc6`); "Final" is filled in after the changes.

| # | Item | Initial | Evidence (initial) | Action | Final |
|---|---|---|---|---|---|
| A1 | README first screen: disclaimer (non-production, user responsible, security/legal review, shared responsibility) with link to hardening list | Needs change | README.md:3 says "Prototype, not for production" only | Rewrite disclaimer with the three points and the link | _pending_ |
| A2 | No customer, person, domain, 12-digit numbers, personal profile names, `[INSERT` remnants | Meets (to re-check) | tests/test_docs.py:27 checks internal names and local paths; git grep for 12-digit numbers finds only 2^53 constants | Re-run greps; add account-ID test | _pending_ |
| A3 | Placeholders `<UPPER_SNAKE>`, `example.com`, `111122223333`; screenshots have provenance; data synthetic | Needs change | DEPLOYMENT-LOG.md:3 uses `<ACCOUNT_ID>`; LICENSE:3 `<COPYRIGHT_HOLDER>`; no screenshots; sample-data synthetic | Replace with `111122223333`; LICENSE copyright line | _pending_ |
| B1 | LICENSE with copyright line, SECURITY (full form), CoC, CONTRIBUTING (tests, commit convention, no account IDs) | Needs change | LICENSE:3 placeholder holder; SECURITY.md:5 platform-private reporting only; CODE_OF_CONDUCT.md generic text; CONTRIBUTING.md has no commit convention or account-ID rule | Rewrite all four | _pending_ |
| B2 | THIRD-PARTY-LICENSES (distributed / downloaded); CHANGELOG + VERSION | Needs change | Files missing | Add, verified from package metadata | _pending_ |
| B3 | Issue/PR templates, AGENTS.md + CLAUDE.md, Makefile, .gitignore/.dockerignore | Needs change | No `.github/`, no CLAUDE.md, no Makefile; AGENTS.md is the product's FR-3 reading order (no contributor section) | Add files; AGENTS.md exception (see DECISIONS) | _pending_ |
| B4 | DECISIONS / OPEN-QUESTIONS / SECURITY-NOTES / THREAT_MODEL (DRAFT) / VERIFICATION / DEPLOYMENT-LOG | Needs change | All present; THREAT_MODEL.md:1 not marked DRAFT | Mark DRAFT | _pending_ |
| C1 | Config as templates, input validation, removal policy as parameter, consistent tags | Needs change | infra/config/sandbox.json committed as real config; infra/prd_infra/config.py:36 validates removal policy only | Example templates + `make init`; regex and cross-field validation failing synth | _pending_ |
| C2 | Preflight (account, region, toolchain, quotas), destructive-change guard, smoke/e2e verification | Needs change | No preflight, no diff guard; e2e only as manual steps in DEPLOYMENT-LOG.md | `make preflight`, guarded `make deploy`, `make verify` | _pending_ |
| C3 | Verification records: date, region, config, commit hash, failures, limits | Needs change | VERIFICATION.md has date and region, no commit hash and no "what this does not prove" | Add | _pending_ |
| D1 | Static checks zero unhandled findings, suppressions justified; trust policies with SourceAccount+SourceArn; resource policies on sensitive resources | Needs change | cdk-nag 0 findings, 0 suppressions (SECURITY-NOTES.md:22); no service roles; bucket policy only denies non-TLS (infra/prd_infra/artifact_stack.py:36) | Add account-boundary and optional writer-restriction statements | _pending_ |
| D2 | CI: lint, tests, synth, secret scan; Actions pinned by SHA; least permissions; Dependabot; gitleaks exemptions justified | Needs change | No CI files | Add ci.yml, deploy-verify.yml, dependabot.yml, .gitleaks.toml, canary | _pending_ |
| D3 | No account-level settings changed | Meets | Stack creates buckets and bucket policies only (DEPLOYMENT-LOG.md resources table) | - | _pending_ |
| E1 | Cleanup script with confirmations; residue script; README lists resources not deleted automatically | Needs change | scripts/empty_stack_buckets.py:22 has `--yes` only; scripts/residue_check.sh always exits 0; README has no list | Interactive cleanup, failing residue check, list in README | _pending_ |
| E2 | All used regions checked, clear conclusion | Meets (single region) | DEPLOYMENT-LOG.md residue table, us-east-1 only | Script takes a region list; bootstrap assets of this project included | _pending_ |
| F1 | Fact-check rows with official link and date; cost only as dimensions; README section order | Needs change | docs/architecture.md fact-check has dates; README order differs (README.md:21–140) | Restructure both READMEs | _pending_ |
| F2 | Conventional Commits with verification in the body; not pushed | Needs change | Subjects were imperative sentences | Subjects rewritten once with git-filter-repo before this round; new commits follow the convention | _pending_ |
