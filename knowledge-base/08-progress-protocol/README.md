# 08 Staged progress protocol

Purpose: in long tasks an agent may set up a structure and stop. The protocol makes every stage name the files that
exist, and a checker compares the claims with the disk.

## Format (PROGRESS.md in the output folder)

```
# Progress log

Planned files:
- thing-model.json
- ...

## [PROGRESS 10%] <one-line note>

Files so far:
- (none)

## [PROGRESS 25%] <note>

Files so far:
- thing-model.json

...

## [PROGRESS 100%] <note>

Files so far:
- ...

Validation: PASS
```

The same line `[PROGRESS n%] ...` is also printed in the chat after each stage.

## Milestones

| Report | Files that must be listed by then (if planned) |
|---|---|
| 10% | none; the intake check passed and the planned file list is written |
| 25% | thing-model.json |
| 45% | PRD.md, architecture.mmd |
| 70% | quick-start.md, panel-spec.md, panel-preview.html |
| 90% | device-demo/dp_table.h, app_main.c, hal_port.h, hal_port_host.c, README.md |
| 100% | quick-start.pdf, every other planned file, and `Validation: PASS` |

## Checks (`prd-agent check-progress <folder>`)

1. Exactly six reports at 10, 25, 45, 70, 90, 100, in that order.
2. Every report has a `Files so far:` list.
3. Lists are cumulative: a file listed once must be listed in every later report.
4. Each planned file is listed by its milestone.
5. Every listed file exists and is not a skeleton: non-empty; JSON parses; Markdown has at least five content lines;
   other text files have at least three non-empty lines; PDFs start with `%PDF-`.
6. The log ends with `Validation: PASS` (from `prd-agent validate`).
