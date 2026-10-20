# Prior-art search

Search date: 2026-10-20. Sources: the GitHub organisations aws-samples, aws-solutions-library-samples and awslabs
(searched by repository name and description), AWS documentation, and AWS blogs. Every link below returned
HTTP 200 on the search date. Several searches found nothing: "prd" in aws-samples and in
aws-solutions-library-samples, "iot genai" in aws-solutions-library-samples, "iot code generation" in aws-samples,
and "document generation bedrock" in aws-samples.

Community repositories owned by individual accounts were found as well (conversational PRD-writing plugins, and an
IoT PRD skill that maps data points to features). They are left out by name on purpose, because the repository
must not contain personal identifiers. Their coverage is summarised in the last row of the table. See DECISIONS.md D-14.

## Close assets

| # | Asset | Link | Covers | Does not cover |
|---|---|---|---|---|
| 1 | AI-DLC workflows | https://github.com/awslabs/aidlc-workflows (blogs: https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/, https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc/) | Steering rules for coding agents across several tools. A staged workflow that asks for missing decisions and stops at approval gates. | IoT content and a thing model. No checks keyed on IDs across artifacts. No percentage milestones with file lists. Not the six IoT deliverables. |
| 2 | Kiro CLI prompts for product teams | https://github.com/aws-samples/sample-kiro-cli-prompts-for-product-teams | Kiro steering files and hooks for the flow discovery → research → PRFAQ → PRD (EARS requirements) → offline HTML prototype. Ordered workflow with quality gates. | IoT and a thing model. Device code and the quick-start PDF. No check keyed on property IDs, no percentage progress protocol, no explicit "refuse and list pending items". |
| 3 | Voice-driven development | https://github.com/aws-samples/sample-voice-driven-development | Speech → transcription → LLM → Kiro-format requirements.md/tasks.md or an issue. | All four differentiators. Nothing IoT-specific. |
| 4 | SpecShip | https://github.com/aws-samples/sample-specship | Kiro Power pipeline that produces requirements/design/tasks. Hard gates per milestone, and adversarial validators that include one for spec-code alignment. | IoT and a thing model. No consistency keyed on property IDs and no percentage protocol with file lists. Not document deliverables for several audiences. |
| 5 | Kiro Steering Studio | https://github.com/aws-samples/sample-kiro-steering-studio | Voice conversation that generates Kiro steering files. | PRD and IoT deliverables. No reading-order design, no validation. |
| 6 | AWS IoT Core learning path (basics) | https://github.com/aws-samples/sample-aws-iot-core-learning-path-basics | Interactive scripts for IoT Core device management, security, MQTT and shadows. | No LLM and no document generation. |
| 7 | IoT SiteWise conversational agent | https://github.com/aws-samples/aws-iot-sitewise-conversational-agent | An agent that answers questions about asset state at run time. | Run-time operations, not design-time deliverables. |
| 8 | AWS IoT device shadow docs (reference) | https://docs.aws.amazon.com/iot/latest/developerguide/iot-device-shadows.html | The state model that a device and an app exchange. | Reference material only; it generates nothing. |
| 9 | Community PRD and IoT-PRD plugins (not named, see above) | - | Conversational PRD writing. One maps IoT data points to features; another reconciles documents with code. | No validation across artifacts keyed on IDs, no reading-order knowledge base, no progress protocol, no refusal on insufficient input. |

## Differences from the closest assets

The project's four differentiators (spec section 7), checked against the table:

| Differentiator | Closest existing coverage | What this project adds |
|---|---|---|
| (a) Consistency across artifacts keyed on thing model ID | Generic spec-code alignment in #4; a data-point to feature mapping in #9 | A deterministic checker. It reads ID, identifier and access from fixed places in six deliverables (Markdown tables, HTML attributes, mermaid labels, a C header) and reports `file:line` differences against thing-model.json. It is unit-tested. |
| (b) Numbered knowledge base and reading order | Ordered steering and workflows in #1 and #2 | The folder number is the reading order (00 rules → 10 cases), declared in AGENTS.md. The deliverable templates live in the same knowledge base and the reference generator uses them, so rules, templates and example cannot drift. |
| (c) Staged progress protocol | Milestone gates in #4 | Fixed reports at 10/25/45/70/90/100 percent, each with a cumulative file list. A checker verifies the claims against the disk, including skeleton detection. |
| (d) Warn on insufficient input before generating | #1 asks for missing decisions | The intake is checked against a schema with conditional and cross-field rules. The prompt compiler switches to `CLARIFY_ONLY` mode, and the local generator refuses to write files. The browser (JS) and the CLI (Python) produce byte-identical output. |

## Conclusion

No asset found covers all four points, and none covers (a) or (c) in the form above. The project overlaps partly
with #1, #2 and #4 on (b) and (d) only. Development continued. The README states the difference in one paragraph and
points here.
