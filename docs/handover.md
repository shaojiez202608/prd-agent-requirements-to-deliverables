# Handover

## What you receive
- Intake forms (frontline, PM) and the schema they are built from.
- A numbered knowledge base with `AGENTS.md`, six deliverable templates and a synthetic worked example.
- CLI: prompt compiler, local reference generator, consistency checker, progress checker, PDF renderer, change log,
  publish/fetch.
- An optional CDK stack (private S3 bucket for bundles).

## How to adapt
1. Edit `intake/schema.json` (fields, options, required flags) and run `prd-agent build-forms`. If you add rules,
   mirror them in `intake/compiler.js` and `src/prd_agent/intake.py`; the parity test enforces this.
2. Put team rules in `knowledge-base/00-project-rules` and the template folders, and real (sanitised) cases in
   `10-project-cases`.
3. Keep the machine-readable markers (dp-table, data attributes, mermaid label format, C macros) in any template
   you change, or update `src/prd_agent/consistency.py` and its tests.

## Removal policy parameter
`removal_policy` in `infra/config/*.json`:
- `sandbox.json`: `destroy`. The buckets are deleted with the stack after they have been emptied (see cleanup.md).
- `customer.json`: `retain`. This is the default for a customer prototype. Buckets and data stay after
  `cdk destroy` and must be deleted by hand with the data owner's agreement.

## Hardening before production
- Review the knowledge-base rules and the pending-item rules with the real teams. The current content is a
  generic starting point.
- Put `prd-agent validate` and `prd-agent check-progress` into CI as required checks for any change to deliverables.
- Add a human review and an approval record before any external document (quick-start guide) is published.
- Bundle and review a Unicode font if deliverables must contain non-Latin text.
- Restrict bucket access to named publisher and reader roles. Consider SSE-KMS with a customer managed key for the
  artifact bucket (the log bucket must stay on SSE-S3), Object Lock for released bundles, and CloudTrail data events.
- Set retention for noncurrent versions and access logs according to policy, and use `retain` outside sandboxes.
- Decide on a struct or array type for structured properties instead of encoded strings.
- Treat AI-produced deliverables as drafts. The checker proves ID consistency, not correctness.
