# 09 Consistency, change tracking and segmented generation

## Consistency check (`prd-agent validate <folder>`)

Reference: `thing-model.json`. Compared files and the exact place the checker reads:

| File | Where ID, identifier, access are read |
|---|---|
| PRD.md, quick-start.md, panel-spec.md | Table between `<!-- dp-table:begin -->` and `<!-- dp-table:end -->`; header must contain Identifier, ID, Access |
| panel-preview.html | `data-dp-id`, `data-dp-identifier`, `data-dp-access` attributes (HTML comments are ignored) |
| architecture.mmd | Node labels `"DP <id> <identifier> <access>"` |
| device-demo/dp_table.h | `#define DP_ID_<IDENTIFIER> <id>` (ID and identifier) and `DP_DEFINE(<id>, "<identifier>", DP_<access>, ...)`; both kinds must list every property |
| quick-start.pdf | Not parsed; the PDF stores the SHA-256 of quick-start.md and must match the current Markdown |

Visible text is also checked where it uses one of these fixed patterns ("mentions"). A mention must agree with
the thing model, but it is not required to exist:

| Pattern | Where it appears |
|---|---|
| ``ID <id> `<identifier>` `` optionally followed by ` (<access>)` | Property details, open items, control behaviour |
| ``Card `<identifier>` (ID <id>)`` | Panel layout |
| `"<id>":` at the start of a line inside a fenced code block | Report and command examples (ID must exist) |
| `<span class="dp">ID <id> \| <identifier> \| <access></span>` | Badge on the panel preview |

Prose in any other form is not checked.

Difference report: one line per difference, `file:line: kind: message (thing-model.json:line)`.
Kinds: `id_mismatch`, `identifier_mismatch`, `access_mismatch`, `missing`, `unknown_entry`, `duplicate_id`, `text_mismatch`,
`invalid_id`, `unreadable`, `no_entries`, `missing_file`, `stale_pdf`, and for the reference itself
`invalid_reference`, `duplicate_identifier`, `invalid_access`.
If every checked file disagrees with the same thing model line, a hint says the thing model itself was probably edited.
Exit code 0 means consistent, 1 means differences. `--format json` gives the same data as JSON.

Required files: by default PRD.md, quick-start.md, quick-start.pdf and device-demo/dp_table.h (the documents
named in FR-7) plus every file planned in PROGRESS.md. The progress log can add files but never remove these.
For an intake that requests fewer deliverables, pass `--intake <intake.json>` to `validate`, `check-progress` and
`publish`; the required files are then exactly those of its `deliverables.outputs`.
`check-progress` applies the same rule to the planned list.

## Change tracking (`prd-agent diff-model old.json new.json`)

Compares two thing models by ID. Breaking changes: removed ID, ID reused with a new identifier, data type change,
narrowed range or enum, access narrowed, unit or step change. Rules for iterations:
- Never reuse an ID for a different meaning. Retire it and add a new ID.
- Record the diff output in the PRD change log of the new version.
- `--fail-on-breaking` exits 1 when a breaking change is present, for use in review scripts.

## Segmented generation

Write one deliverable per step in the milestone order of 08. For long files write section by section. After each
file, re-read its last lines to make sure it is complete, then report progress. This keeps any single output short
enough not to be cut off and makes a cut-off visible in the progress check.
