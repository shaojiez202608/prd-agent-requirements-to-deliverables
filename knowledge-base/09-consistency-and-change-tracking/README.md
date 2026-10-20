# 09 Consistency, change tracking and segmented generation

## Consistency check (`prd-agent validate <folder>`)

Reference: `thing-model.json`. Compared files and the exact place the checker reads:

| File | Where ID, identifier, access are read |
|---|---|
| PRD.md, quick-start.md, panel-spec.md | Table between `<!-- dp-table:begin -->` and `<!-- dp-table:end -->`; header must contain Identifier, ID, Access |
| panel-preview.html | `data-dp-id`, `data-dp-identifier`, `data-dp-access` attributes |
| architecture.mmd | Node labels `"DP <id> <identifier> <access>"` |
| device-demo/dp_table.h | `#define DP_ID_<IDENTIFIER> <id>` (ID and identifier) and `DP_DEFINE(<id>, "<identifier>", DP_<access>, ...)` |
| quick-start.pdf | Not parsed; the PDF stores the SHA-256 of quick-start.md and must match the current Markdown |

Difference report: one line per difference, `file:line: kind: message (thing-model.json:line)`.
Kinds: `id_mismatch`, `identifier_mismatch`, `access_mismatch`, `missing`, `unknown_entry`, `duplicate_id`,
`invalid_id`, `unreadable`, `no_entries`, `missing_file`, `stale_pdf`, and for the reference itself
`invalid_reference`, `duplicate_identifier`, `invalid_access`.
If every checked file disagrees with the same thing model line, a hint says the thing model itself was probably edited.
Exit code 0 means consistent, 1 means differences. `--format json` gives the same data as JSON.

Required files: the planned list in PROGRESS.md if present, otherwise PRD.md, quick-start.md and
device-demo/dp_table.h (the three documents named in FR-7).

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
