# PRD agent: from structured intake to consistent deliverables

> **Prototype, not for production.** This is a reference implementation for prototype and non-production use.
> See [Hardening before production](#hardening-before-production).

Suggested repository name for publishing: `prd-agent-requirements-to-deliverables`.

Field engineers and product managers fill in a fixed intake template. The template produces a deterministic prompt.
An AI coding agent reads a numbered knowledge base and writes six IoT product deliverables. A checker then
confirms that all of them use the same thing model IDs.

| Deliverable | Format | Consumer |
|---|---|---|
| Thing model | `thing-model.json` | Cloud platform, device developers |
| Product architecture | `architecture.mmd` (mermaid) | Reviewers |
| Quick-start integration guide | `quick-start.md` → `quick-start.pdf` | External developers |
| Requirements specification / PRD | `PRD.md` | Product, engineering |
| Panel interaction spec | `panel-spec.md` + `panel-preview.html` | Panel UI design |
| Device demo skeleton | `device-demo/` (C99) | Device developers |

## What is different

Many assets already generate PRDs with an LLM ([prior-art search](docs/prior-art.md)). This one adds four things:

1. **Consistency keyed on the thing model ID.** `prd-agent validate` reads ID, identifier and access from fixed
   places in every deliverable and reports each difference as `file:line`.
2. **A numbered knowledge base with a reading order.** `AGENTS.md` makes the agent read `knowledge-base/00` to `10`
   in order: rules first, then templates, then the case.
3. **A staged progress protocol.** The agent reports at 10/25/45/70/90/100 percent and lists the files it has
   produced each time. `prd-agent check-progress` compares those lists with what is on disk, so a run that only
   builds the skeleton is caught.
4. **A warning before generating on insufficient input.** Missing or contradictory fields become a list of items to
   confirm, and the prompt switches to `CLARIFY_ONLY`. Nothing is guessed.

## Quick start (local, no AWS)

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/). Node.js is optional; it is needed only for the
JS/Python parity test. A C compiler is optional; it is needed only for the device skeleton compile test.

```bash
uv sync
uv run pytest                                    # unit tests

# 1. Intake: open intake/pm.html or intake/frontline.html in a browser (works offline),
#    or use the synthetic sample:
uv run prd-agent check-intake sample-data/smart-plug.pm.intake.json
uv run prd-agent compile-prompt sample-data/smart-plug.pm.intake.json      # paste into your AI tool

# 2. Insufficient input: lists pending items, exit code 2, writes nothing
uv run prd-agent generate sample-data/smart-plug.missing-fields.intake.json --out out/missing

# 3. Local reference generator (mock of the agent): six deliverables + PROGRESS.md
uv run prd-agent generate sample-data/smart-plug.pm.intake.json --out out/smart-plug

# 4. Checks (also run these on folders written by an AI agent)
uv run prd-agent validate out/smart-plug
uv run prd-agent check-progress out/smart-plug
```

A full generated example is committed in [`examples/smart-plug/`](examples/smart-plug/), and the compiled prompts
are in [`examples/prompts/`](examples/prompts/). The walkthrough is in [docs/demo-script.md](docs/demo-script.md).

### Using it with an AI coding agent

Open this repository as the workspace of an agent that reads `AGENTS.md`, for example Kiro, which picks up a root
`AGENTS.md` automatically (see the fact check in [docs/architecture.md](docs/architecture.md#fact-check)). Paste
the compiled prompt and name an output folder. Then run `prd-agent validate` and `prd-agent check-progress` on
that folder.

## Commands

| Command | Purpose |
|---|---|
| `check-intake <intake.json>` | List pending items (exit 2 if any) |
| `compile-prompt <intake.json> [--out f]` | Deterministic prompt text |
| `generate <intake.json> --out <dir>` | Local reference generator; refuses on pending items (exit 2), exit 1 if its own validation fails, exit 3 on I/O or PDF errors (the target folder is then unchanged) |
| `validate <dir> [--format json] [--intake f]` | Consistency check keyed on ID. Without `--intake` the FR-7 files are required |
| `check-progress <dir> [--intake f]` | Progress protocol check |
| `render-pdf <quick-start.md>` | Markdown to PDF |
| `diff-model <old.json> <new.json> [--fail-on-breaking]` | Thing model change log |
| `build-forms` | Rebuild the two HTML forms from the schema and the system prompt |
| `publish <dir> --dest <dir or s3://bucket/prefix> --name <bundle> [--intake f]` | Publish a bundle that passes validation; an existing bundle name is refused |
| `fetch <src> --name <bundle> --out <dir>` | Download a bundle and verify checksums |

Exit codes: 0 ok, 1 check failed, 2 insufficient input, 3 usage or I/O error. Pass `--intake` when the intake
requested fewer deliverables than the FR-7 set (PRD, quick-start guide, device skeleton).

## Optional AWS deployment

The core needs no AWS. As an option, one CDK stack creates a private, versioned S3 bucket for published bundles
(plus its access log bucket). It has no compute and no public endpoint.

```bash
cd infra
npx -y aws-cdk@2 deploy -c config=config/sandbox.json
```

See [docs/deployment-guide.md](docs/deployment-guide.md) and [docs/cleanup.md](docs/cleanup.md). For pricing, see
the official [Amazon S3 pricing](https://aws.amazon.com/s3/pricing/) page; the billing dimensions are storage,
requests and data transfer.

## Cleanup

Local: delete the `out/` folder. AWS: follow [docs/cleanup.md](docs/cleanup.md). Empty both buckets, including all
object versions, then run `cdk destroy`, then run the residue check.

## Limitations

- No online AI call. Copying the prompt from the form into the AI tool is a deliberate manual step.
- The checker compares ID, identifier and access only, not ranges or prose. Visible text is checked only where it
  uses the fixed patterns listed in `knowledge-base/09` (for example ``ID 5 `timer_task` `` and the panel badges);
  other visible text, such as free prose, is not checked.
- Deliverables are in English, because the built-in PDF font covers Latin-1 only. When the quick-start guide is
  requested, non-Latin-1 text in the fields that reach the PDF is a pending item.
- Panel output guarantees structure and ID mapping, not visual design.
- The agent follows the reading order because AGENTS.md instructs it to. The tool does not enforce it.
- The knowledge base contains one synthetic case (`knowledge-base/10-project-cases`). Other product classes need
  their own cases before the outputs can be relied on.
- No effect data exists for this approach. The repository makes no claim about time saved.

More detail: [docs/architecture.md](docs/architecture.md#limitations).

## Hardening before production

See [docs/handover.md](docs/handover.md). In short:
- Review the knowledge-base rules with the real teams.
- Add a Unicode font and review its licence.
- Put `validate` and `check-progress` into CI as merge gates.
- Restrict bucket access to named roles, turn on retention, and consider SSE-KMS for the artifact bucket.
- Add a review step before any external document is published.

## Documents

[Architecture](docs/architecture.md) · [Prior art](docs/prior-art.md) · [Deployment](docs/deployment-guide.md) ·
[Demo script](docs/demo-script.md) · [Handover](docs/handover.md) · [Cleanup](docs/cleanup.md) ·
[Distribution interface](docs/distribution.md) · [Threat model](THREAT_MODEL.md) · [Security notes](SECURITY-NOTES.md) ·
[Verification](VERIFICATION.md) · [Deployment log](DEPLOYMENT-LOG.md) · [Decisions](DECISIONS.md) ·
[Open questions](OPEN-QUESTIONS.md)

## License

MIT-0. See [LICENSE](LICENSE).
