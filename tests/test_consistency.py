"""FR-7 and acceptance 2: a changed ID is reported with file and line."""

import json
import re
import shutil

import pytest

from prd_agent.consistency import check_folder


def edit(path, old, new, count=1):
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def line_of(path, needle):
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if needle in line:
            return no
    raise AssertionError(needle)


def test_changed_id_in_prd_points_to_file_and_line(generated):
    prd = generated / "PRD.md"
    edit(prd, "| `timer_task` | 5 |", "| `timer_task` | 7 |")
    report = check_folder(generated)
    assert not report.ok
    assert len(report.differences) == 1
    d = report.differences[0]
    assert (d.file, d.kind) == ("PRD.md", "id_mismatch")
    assert d.line == line_of(prd, "`timer_task` | 7")
    assert "ID 7 here, ID 5 in thing model" in d.message
    assert f"PRD.md:{d.line}: id_mismatch" in report.render_text()


def test_changed_id_in_quick_start(generated):
    qs = generated / "quick-start.md"
    edit(qs, "| `report_interval` | 6 |", "| `report_interval` | 60 |")
    kinds = {(d.file, d.kind, d.line) for d in check_folder(generated).differences}
    assert ("quick-start.md", "id_mismatch", line_of(qs, "`report_interval` | 60")) in kinds
    # quick-start.md changed, so the PDF no longer matches its source
    assert any(k[1] == "stale_pdf" for k in kinds)


def test_changed_id_in_demo_header(generated):
    h = generated / "device-demo" / "dp_table.h"
    edit(h, "#define DP_ID_OVERLOAD_PROTECT 4", "#define DP_ID_OVERLOAD_PROTECT 9")
    diffs = check_folder(generated).differences
    assert [(d.file, d.kind, d.line) for d in diffs] == [
        ("device-demo/dp_table.h", "id_mismatch", line_of(h, "DP_ID_OVERLOAD_PROTECT 9"))]


def test_access_mismatch_in_demo_table(generated):
    h = generated / "device-demo" / "dp_table.h"
    edit(h, 'DP_DEFINE(2, "active_power", DP_R,', 'DP_DEFINE(2, "active_power", DP_RW,')
    diffs = check_folder(generated).differences
    assert [(d.file, d.kind) for d in diffs] == [("device-demo/dp_table.h", "access_mismatch")]


def test_identifier_mismatch_in_html_and_mermaid(generated):
    edit(generated / "panel-preview.html", 'data-dp-identifier="overload_alarm"', 'data-dp-identifier="overload_alert"')
    edit(generated / "architecture.mmd", '"DP 3 overload_alarm R"', '"DP 3 overload_alarm RW"')
    kinds = sorted((d.file, d.kind) for d in check_folder(generated).differences)
    assert kinds == [("architecture.mmd", "access_mismatch"), ("panel-preview.html", "identifier_mismatch")]


def test_missing_row_and_unknown_row(generated):
    ps = generated / "panel-spec.md"
    text = ps.read_text(encoding="utf-8")
    text = re.sub(r"^\| Overload alarm .*\n", "", text, flags=re.M)
    text = text.replace("<!-- dp-table:end -->", "| Extra | `extra_dp` | 42 | R | x |\n<!-- dp-table:end -->")
    ps.write_text(text, encoding="utf-8")
    kinds = sorted(d.kind for d in check_folder(generated).differences if d.file == "panel-spec.md")
    assert kinds == ["missing", "unknown_entry"]


def test_swapped_ids_report_duplicate(generated):
    edit(generated / "PRD.md", "| `timer_task` | 5 |", "| `timer_task` | 6 |")
    kinds = sorted(d.kind for d in check_folder(generated).differences)
    assert kinds == ["duplicate_id", "id_mismatch"]


def test_edited_thing_model_gets_hint(generated):
    tm = generated / "thing-model.json"
    model = json.loads(tm.read_text(encoding="utf-8"))
    model["properties"][4]["id"] = 50
    tm.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    report = check_folder(generated)
    assert not report.ok
    assert set(d.file for d in report.differences) == set(report.checked)
    assert report.hints and "thing model itself may be the file that was edited" in report.hints[0]


def test_missing_markers_and_missing_required_file(generated):
    edit(generated / "quick-start.md", "<!-- dp-table:begin -->", "")
    (generated / "PRD.md").unlink()
    kinds = {(d.file, d.kind) for d in check_folder(generated).differences}
    assert ("quick-start.md", "unreadable") in kinds
    assert ("PRD.md", "missing_file") in kinds


def test_without_progress_log_only_core_files_required(generated):
    (generated / "PROGRESS.md").unlink()
    (generated / "panel-spec.md").unlink()
    shutil.rmtree(generated / "device-demo")
    report = check_folder(generated)
    assert [(d.file, d.kind) for d in report.differences] == [("device-demo/dp_table.h", "missing_file")]
    assert "panel-spec.md" in report.skipped


def test_json_report(generated):
    edit(generated / "PRD.md", "| `power_switch` | 1 | RW |", "| `power_switch` | 1 | R |")
    data = json.loads(check_folder(generated).to_json())
    assert data["ok"] is False
    assert data["differences"][0]["kind"] == "access_mismatch"
    assert data["differences"][0]["reference_line"] > 0


def test_duplicate_id_in_thing_model(generated):
    tm = generated / "thing-model.json"
    model = json.loads(tm.read_text(encoding="utf-8"))
    model["properties"][1]["id"] = 1
    tm.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    kinds = [d.kind for d in check_folder(generated).differences if d.file == "thing-model.json"]
    assert "duplicate_id" in kinds


def _drop_from_plan(folder, names):
    log = folder / "PROGRESS.md"
    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln[2:] not in names]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_core_files_cannot_be_planned_away(generated):
    """Deleting the FR-7 files and removing them from PROGRESS.md must not pass any gate."""
    from prd_agent.progress import check_progress
    from prd_agent.publish import PublishRefused, publish

    for rel in ("PRD.md", "quick-start.md", "quick-start.pdf"):
        (generated / rel).unlink()
    shutil.rmtree(generated / "device-demo")
    _drop_from_plan(generated, {"PRD.md", "quick-start.md", "quick-start.pdf", "device-demo/dp_table.h",
                                "device-demo/app_main.c", "device-demo/hal_port.h", "device-demo/hal_port_host.c",
                                "device-demo/README.md"})
    report = check_folder(generated)
    missing = {d.file for d in report.differences if d.kind == "missing_file"}
    assert missing == {"PRD.md", "quick-start.md", "quick-start.pdf", "device-demo/dp_table.h"}
    assert sum("FR-7 core deliverable" in p.message for p in check_progress(generated)) == 4
    with pytest.raises(PublishRefused):
        publish(generated, str(generated.parent / "dist"), "v1")


def test_intake_outputs_define_required_files(generated, pm_intake):
    (generated / "panel-spec.md").unlink()
    outputs = pm_intake["deliverables"]["outputs"]
    assert [(d.file, d.kind) for d in check_folder(generated, outputs=outputs).differences] == [
        ("panel-spec.md", "missing_file")]
    assert check_folder(generated, outputs=["thing_model", "prd", "quick_start", "device_demo"]).ok


def test_header_without_dp_define_lines_fails(generated):
    h = generated / "device-demo" / "dp_table.h"
    h.write_text("".join(ln for ln in h.read_text(encoding="utf-8").splitlines(keepends=True)
                         if "DP_DEFINE(" not in ln or "#define DP_DEFINE" in ln), encoding="utf-8")
    diffs = [d for d in check_folder(generated).differences if d.file == "device-demo/dp_table.h"]
    assert len(diffs) == 6 and {d.kind for d in diffs} == {"missing"}
    assert all("access-bearing entry" in d.message for d in diffs)


def test_header_without_id_defines_fails(generated):
    h = generated / "device-demo" / "dp_table.h"
    h.write_text(re.sub(r"^#define DP_ID_.*\n", "", h.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8")
    diffs = [d for d in check_folder(generated).differences if d.file == "device-demo/dp_table.h"]
    assert len(diffs) == 6 and all("#define" in d.message for d in diffs)


def test_visible_ids_are_checked(generated):
    edit(generated / "PRD.md", "- ID 5 `timer_task` (Timer tasks)", "- ID 7 `timer_task` (Timer tasks)")
    edit(generated / "panel-spec.md", "Card `overload_alarm` (ID 3)", "Card `overload_alarm` (ID 4)")
    edit(generated / "panel-spec.md", "- ID 2 `active_power` (R)", "- ID 2 `active_power` (RW)")
    edit(generated / "panel-preview.html", '<span class="dp">ID 1 | power_switch | RW</span>',
         '<span class="dp">ID 1 | power_toggle | RW</span>')
    edit(generated / "quick-start.md", '  "2": ', '  "12": ')
    diffs = [(d.file, d.kind) for d in check_folder(generated).differences if d.kind != "stale_pdf"]
    assert sorted(diffs) == [("PRD.md", "text_mismatch"), ("panel-preview.html", "text_mismatch"),
                             ("panel-spec.md", "text_mismatch"), ("panel-spec.md", "text_mismatch"),
                             ("quick-start.md", "text_mismatch")]


def test_commented_out_html_is_ignored(generated):
    page = generated / "panel-preview.html"
    edit(page, "</body>", '<!-- <div data-dp-id="99" data-dp-identifier="ghost" data-dp-access="R">\n'
         '<span class="dp">ID 99 | ghost | R</span></div> -->\n</body>')
    assert check_folder(generated).ok


def test_reference_lines_ignore_nested_ids(generated):
    tm = generated / "thing-model.json"
    model = json.loads(tm.read_text(encoding="utf-8"))
    model["product"]["id"] = "nested, not a property"
    model["properties"][0]["panel"]["id"] = 0
    tm.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    edit(generated / "PRD.md", "| `timer_task` | 5 |", "| `timer_task` | 7 |")
    d = next(d for d in check_folder(generated).differences if d.kind == "id_mismatch")
    lines = tm.read_text(encoding="utf-8").splitlines()
    assert lines[d.reference_line - 1].strip() == '"id": 5,'


def test_reference_lines_compact_json(generated):
    from prd_agent.consistency import reference_entries

    tm = generated / "thing-model.json"
    model = json.loads(tm.read_text(encoding="utf-8"))
    tm.write_text(json.dumps(model, separators=(",", ":")) + "\n", encoding="utf-8")
    entries, diffs = reference_entries(tm)
    assert diffs == [] and [e.line for e in entries] == [1] * 6
