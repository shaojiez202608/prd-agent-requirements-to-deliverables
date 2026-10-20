# Numbered knowledge base

The number in each folder name is the reading order defined in `AGENTS.md`. All content is written for this
prototype and uses generic IoT practice; no vendor manual or customer material is included.

| Folder | Content | Used by the reference generator |
|---|---|---|
| 00-project-rules | Hard rules | - |
| 01-intake-standard | Intake sections and pending-item rules | - |
| 02-thing-model-spec | thing-model.json format | yes (format) |
| 03-architecture-diagram-conventions | mermaid annotation rules and template | yes |
| 04-prd-template | PRD template | yes |
| 05-quick-start-template | Quick-start guide template | yes |
| 06-panel-spec-template | Panel spec and preview templates | yes |
| 07-device-demo-template | Device demo skeleton templates | yes |
| 08-progress-protocol | Progress report format and checks | yes (PROGRESS.md) |
| 09-consistency-and-change-tracking | Validation, change log, segmented generation | - |
| 10-project-cases | Worked example (synthetic smart plug) | - |

To add a rule, edit the lowest-numbered folder where it belongs. To add a case, add a file in `10-project-cases`.
Do not put rules in case files; cases are read last and must not override rules.
