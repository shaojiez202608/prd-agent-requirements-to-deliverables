# Demo script (about 15 minutes, local only)

Setup: `uv sync`, a browser, a terminal in the repository root.

## 1. The problem (1 min)
Intake requests come in many forms. The deliverables are written by different people, so IDs drift between the PRD,
the integration guide and the device code. The fix here is standard input, fixed rules and a checker. No model
is tuned.

## 2. Intake forms (3 min)
1. Open `intake/frontline.html` from disk. Show that it works offline and that the page's security policy blocks
   all network requests.
2. Click "Import" and load `sample-data/smart-plug.frontline.intake.json`, then "Generate". The status line reports
   pending items and `mode: CLARIFY_ONLY`. The frontline form has no ID or identifier fields, so the prompt asks
   the AI to turn the gaps into questions for the PM.
3. Open `intake/pm.html` and import `sample-data/smart-plug.pm.intake.json`. Click Generate: 0 pending items and
   `mode: GENERATE`. Change the order of the ticked login methods and generate again. The text is identical.

## 3. Insufficient input (2 min)
```bash
uv run prd-agent check-intake sample-data/smart-plug.missing-fields.intake.json
uv run prd-agent generate sample-data/smart-plug.missing-fields.intake.json --out out/missing; echo "exit $?"; ls out/missing
```
The run lists four items (missing connectivity, missing unit, duplicate ID, missing provisioning), exits with
code 2, and creates no folder.

## 4. Knowledge base and generation (3 min)
1. Show `AGENTS.md`: the reading order is 00 rules → 10 cases.
2. Run the local reference generator, which plays the agent:
   ```bash
   uv run prd-agent generate sample-data/smart-plug.pm.intake.json --out out/smart-plug
   ```
   Point out the six `[PROGRESS n%]` lines, each with its file list.
3. Open `out/smart-plug/panel-preview.html`. Each card shows its ID badge.
4. Open `out/smart-plug/quick-start.pdf`.

## 5. Consistency check (3 min)
```bash
uv run prd-agent validate out/smart-plug                  # PASS
sed -i.bak 's/| `timer_task` | 5 |/| `timer_task` | 7 |/' out/smart-plug/PRD.md
uv run prd-agent validate out/smart-plug                  # FAIL: PRD.md:<line>: id_mismatch ...
mv out/smart-plug/PRD.md.bak out/smart-plug/PRD.md
```
Then edit the ID of `timer_task` in `thing-model.json` instead. Every file now differs, and the hint names the
thing model as the likely edit.

## 6. Progress protocol (1 min)
```bash
printf '# PRD\n\nTODO\n' > out/smart-plug/PRD.md
uv run prd-agent check-progress out/smart-plug            # PRD.md looks like a skeleton
```

## 7. Iteration and distribution (2 min)
```bash
uv run prd-agent generate sample-data/smart-plug.pm.v2.intake.json --out out/v2
uv run prd-agent diff-model examples/smart-plug/thing-model.json out/v2/thing-model.json
uv run prd-agent publish out/v2 --dest out/dist --name demo-smart-plug-v2
```

## Closing
State the limits plainly: the manual copy step is deliberate; the checker compares ID, identifier and access only;
panel output is structure, not visual design; there is no effect data.
