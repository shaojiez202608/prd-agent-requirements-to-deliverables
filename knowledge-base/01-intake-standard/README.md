# 01 Intake standard

Questions are asked in a fixed order. The order is also the order of sections in the intake JSON, the prompt
and the PRD:

1. Business scenario: scene category, one-sentence scenario, pain points, end users.
2. Hardware and device side: category, working name, connectivity, power supply, device architecture,
   module selection status, firmware standard or custom, channels.
3. Functions and thing model: one row per function point (control name, ID, identifier, data type, access,
   unit/range/step, enum values, max length, panel control, interaction).
4. Cloud panel and application side: client app types, provisioning, login, panel style, data presentation.
5. Constraints and acceptance: offline behaviour, acceptance criteria, security/privacy notes, other notes.
6. Deliverables to produce.

The machine-readable definition of every field (required flag, allowed values, example) is
`intake/schema.json`. The two forms differ only in which fields they show:

| Form | Who fills it | Shows |
|---|---|---|
| Frontline (`intake/frontline.html`) | Field engineers, first contact | Business, product basics, functions in plain words, app side, acceptance |
| PM (`intake/pm.html`) | Product manager | Everything, including ID, identifier, data type, ranges, architecture, offline behaviour |

A frontline intake is expected to produce pending items (for example missing IDs). That is intended: its prompt
asks the AI to turn them into questions for the PM, not to fill them in.

## Pending item rules

A pending item has the form `- [code] path: message`. Codes:

| Code | Meaning |
|---|---|
| missing | A required field is empty, or a field required by the data type is empty |
| invalid | A value is outside its allowed options, pattern or range |
| conflict | Values contradict each other (duplicate ID, min not below max, control that cannot work with the access) |

Conditional rules:
- int/float: unit, min, max, step are required; min < max; step > 0; int ranges are integers.
- enum: at least two distinct enum values.
- string: max_length is required.
- Control compatibility: toggle needs bool + RW/W; slider needs int/float + RW/W; value_display needs int/float + R;
  alarm_indicator needs bool/enum + R; selector needs enum + RW/W; list_editor needs string + RW/W;
  text_display needs string/enum + R.
- IDs and identifiers are unique. Identifiers match `^[a-z][a-z0-9_]{0,31}$`.
- Deliverables must include `thing_model`: it is the reference for every consistency check.
- Free text (text fields, lines and text columns) must not contain `<!--`, `-->` or `*/`. These strings are
  reserved for the machine-readable markers in Markdown/HTML and for C comments in the device skeleton.
- When `quick_start` is requested, text that reaches the quick-start PDF must be Latin-1: product name, offline
  behaviour, and the property columns name, unit, enum_values and interaction. The built-in PDF font cannot render
  other characters (DECISIONS.md D-25). Without `quick_start`, Chinese text is accepted.
