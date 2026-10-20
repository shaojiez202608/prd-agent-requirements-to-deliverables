"""Reference generator (local mock of the agent).

The real workflow is: intake form -> prompt -> a person pastes it into an AI
coding agent that reads AGENTS.md and the knowledge base. This module produces
the same six deliverables deterministically from the knowledge-base templates,
so the whole flow (generation, progress log, validation) runs offline and the
example output in ``examples/`` is reproducible. It is also the "golden"
output that agent-produced files can be compared against.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .intake import REPO_ROOT, PendingItem, clean_lines, clean_text, find_pending, format_number, load_schema
from .pdf import render_markdown_pdf
from .progress import MILESTONES, render_progress
from .prompt import DELIVERABLE_FILES
from .thing_model import build_thing_model, dump_thing_model

KB = REPO_ROOT / "knowledge-base"
_PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")


class InsufficientInput(Exception):
    def __init__(self, pending: list[PendingItem]):
        super().__init__(f"{len(pending)} pending confirmation item(s)")
        self.pending = pending


@dataclass(frozen=True)
class GenerationResult:
    files: list[str]
    validation: str  # "PASS" or "FAIL"

    @property
    def ok(self) -> bool:
        return self.validation == "PASS"


def fill(template: str, values: dict[str, str]) -> str:
    missing = sorted({m for m in _PLACEHOLDER.findall(template) if m not in values})
    if missing:
        raise KeyError(f"template placeholders without value: {', '.join(missing)}")
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def _tpl(rel: str) -> str:
    return (KB / rel).read_text(encoding="utf-8")


def _labels(schema: dict[str, Any]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for section in schema["sections"]:
        for field in section["fields"]:
            if "options" in field:
                out[f"{section['key']}.{field['key']}"] = {o["value"]: o["en"] for o in field["options"]}
            for col in field.get("columns", []):
                if "options" in col:
                    out[f"properties.{col['key']}"] = {o["value"]: o["en"] for o in col["options"]}
    return out


def _bullets(items: list[str]) -> str:
    return "\n".join(f"  - {i}" for i in items) if items else "  - (none)"


def _md_cell(text: str) -> str:
    return text.replace("|", "\\|")


def dp_table_md(model: dict[str, Any]) -> str:
    rows = ["| Control | Identifier | ID | Access | Interaction |", "|---|---|---|---|---|"]
    for p in model["properties"]:
        rows.append(f"| {_md_cell(p['name'])} | `{p['identifier']}` | {p['id']} | {p['access']} | "
                    f"{_md_cell(p['panel']['interaction'])} |")
    return "\n".join(rows)


def _type_text(p: dict[str, Any]) -> str:
    dt = p["data_type"]
    t = dt["type"]
    if t in ("int", "float"):
        return (f"{t}, range {format_number(dt['min'])} to {format_number(dt['max'])}, "
                f"step {format_number(dt['step'])}, unit {dt['unit']}")
    if t == "enum":
        return "enum: " + ", ".join(dt["values"])
    if t == "string":
        return f"string, max length {dt['max_length']}"
    return "bool (true/false)"


def property_details(model: dict[str, Any]) -> str:
    return "\n".join(f"- ID {p['id']} `{p['identifier']}` ({p['name']}): {_type_text(p)}" for p in model["properties"])


def _example_value(p: dict[str, Any]) -> str:
    t = p["data_type"]["type"]
    if t == "bool":
        return "true"
    if t in ("int", "float"):
        return format_number(p["data_type"]["min"])
    if t == "enum":
        return '"' + p["data_type"]["values"][0] + '"'
    return '"..."'


def _c_macro(ident: str) -> str:
    return "DP_ID_" + ident.upper()


_C_TYPE = {"bool": "DP_TYPE_BOOL", "int": "DP_TYPE_INT", "float": "DP_TYPE_FLOAT", "enum": "DP_TYPE_ENUM",
           "string": "DP_TYPE_STRING"}


def _c_value(p: dict[str, Any]) -> str:
    t = p["data_type"]["type"]
    if t == "bool":
        return ".kind = DP_VAL_BOOL, .b = false"
    if t in ("int", "float"):
        return f".kind = DP_VAL_NUM, .num = {format_number(p['data_type']['min'])}"
    return '.kind = DP_VAL_STR, .str = ""'


def _interaction_flow(intake: dict[str, Any], labels: dict[str, dict[str, str]], offline_ref: str) -> str:
    prov = [labels["app.provisioning"][v] for v in labels["app.provisioning"] if v in intake["app"]["provisioning"]]
    login = [labels["app.login"][v] for v in labels["app.login"] if v in intake["app"]["login"]]
    steps = [
        f"Sign in ({' or '.join(login)}).",
        f"Add device: provisioning by {' or '.join(prov)}. On failure show the reason and a retry action.",
        "Device appears in the device list with its online state.",
        "Open the panel: controls load the last reported values; writable controls are disabled until the first report.",
        "Change a writable control: send the command, show the pending state, update only when the device reports.",
        f"Device goes offline: apply the offline behaviour ({offline_ref}); re-enable controls on the next report.",
    ]
    return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))


def _context(intake: dict[str, Any], model: dict[str, Any], schema: dict[str, Any]) -> dict[str, str]:
    labels = _labels(schema)
    biz, hw, app, con = intake["business"], intake["hardware"], intake["app"], intake["constraints"]

    def one(key: str, value: Any) -> str:
        return labels[key][value] if value in labels.get(key, {}) else "(not provided)"

    def many(key: str, values: list[str]) -> list[str]:
        return [labels[key][v] for v in labels[key] if v in values]

    outputs = intake["deliverables"]["outputs"]
    out_labels = many("deliverables.outputs", outputs)
    open_items = []
    if hw.get("module_selection") == "to_be_decided":
        open_items.append("Module selection is to be decided. The device skeleton uses a host stub until then.")
    note = clean_text(con.get("open_notes"))
    if note:
        open_items.append(f"Note from intake: {note}")
    for p in model["properties"]:
        if p["data_type"]["type"] == "string" and p["access"] != "R":
            open_items.append(f"Encoding of string property ID {p['id']} `{p['identifier']}` (for example a list "
                              "format) is not in the intake; confirm before device and app work start.")
    open_items.append("Command timeout and retry policy of the app are not part of the intake; confirm with the app team.")

    index = []
    for key in DELIVERABLE_FILES:
        if key in outputs:
            index.append(f"- {one('deliverables.outputs', key)}: " + ", ".join(f"`{f}`" for f in DELIVERABLE_FILES[key]))

    props = model["properties"]
    layout = "\n".join(f"{i}. Card `{p['identifier']}` (ID {p['id']}): {one('properties.control', p['panel']['control'])}"
                       for i, p in enumerate(props, 1))
    behaviour = "\n".join(
        f"- ID {p['id']} `{p['identifier']}` ({p['access']}), {one('properties.control', p['panel']['control'])}: "
        f"{p['panel']['interaction']}." + ("" if p["access"] == "R" else " Uses the command/report loop.")
        for p in props)
    cards = "\n".join(
        f'<div class="card" data-dp-id="{p["id"]}" data-dp-identifier="{p["identifier"]}" data-dp-access="{p["access"]}">\n'
        f'  <strong>{html.escape(p["name"])}</strong> <span class="dp">ID {p["id"]} | {p["identifier"]} | {p["access"]}</span>\n'
        f'  <div class="ctl">{html.escape(one("properties.control", p["panel"]["control"]))}: '
        f'{html.escape(p["panel"]["interaction"])}</div>\n</div>'
        for p in props)
    readable = [p for p in props if p["access"] in ("R", "RW")]
    writable = [p for p in props if p["access"] in ("RW", "W")]
    report_example = "{\n" + ",\n".join(f'  "{p["id"]}": {_example_value(p)}' for p in readable[:3]) + "\n}"
    command_example = ("{\n" + ",\n".join(f'  "{p["id"]}": {_example_value(p)}' for p in writable[:1]) + "\n}") if writable else "(no writable properties)"
    bool_writable = [p for p in writable if p["data_type"]["type"] == "bool"]
    demo_target = bool_writable[0] if bool_writable else (writable[0] if writable else props[0])

    channels = hw.get("channels")
    return {
        "product_name": clean_text(hw["product_name"]),
        "schema_version": intake["schema_version"],
        "variant": intake["variant"],
        "scene_category": one("business.scene_category", biz["scene_category"]),
        "scene_description": clean_text(biz["scene_description"]),
        "pain_points": _bullets(many("business.pain_points", biz["pain_points"])),
        "end_users": _bullets(many("business.end_users", biz["end_users"])),
        "deliverables": "\n".join(f"- {d}" for d in out_labels),
        "product_category": one("hardware.product_category", hw["product_category"]),
        "connectivity": one("hardware.connectivity", hw["connectivity"]),
        "power_supply": one("hardware.power_supply", hw["power_supply"]),
        "architecture_mode": one("hardware.architecture_mode", hw.get("architecture_mode")),
        "module_selection": one("hardware.module_selection", hw.get("module_selection")),
        "firmware_custom": one("hardware.firmware_custom", hw["firmware_custom"]),
        "channels": str(channels) if channels not in (None, "") else "(not provided)",
        "dp_table": dp_table_md(model),
        "property_details": property_details(model),
        "app_types": _bullets(many("app.app_types", app["app_types"])),
        "provisioning": _bullets(many("app.provisioning", app["provisioning"])),
        "login": _bullets(many("app.login", app["login"])),
        "panel_style": one("app.panel_style", app["panel_style"]),
        "data_presentation": _bullets(many("app.data_presentation", app["data_presentation"])),
        "data_presentation_inline": ", ".join(many("app.data_presentation", app["data_presentation"])),
        "interaction_flow": _interaction_flow(intake, labels, "section 7"),
        "panel_interaction_flow": _interaction_flow(intake, labels, "offline state in section 3"),
        "offline_behavior": clean_text(con.get("offline_behavior")) or "(not provided)",
        "security_privacy_notes": clean_text(con.get("security_privacy_notes")) or "(not provided)",
        "acceptance_criteria": "\n".join(f"{i}. {t}" for i, t in enumerate(clean_lines(con["acceptance_criteria"]), 1)),
        "open_items": "\n".join(f"- {t}" for t in open_items),
        "deliverable_index": "\n".join(index),
        "layout": layout,
        "control_behaviour": behaviour,
        "cards": cards,
        "report_example": report_example,
        "command_example": command_example,
        "dp_nodes": "\n".join(f'    dp{p["id"]}["DP {p["id"]} {p["identifier"]} {p["access"]}"]' for p in props),
        "app_nodes": "\n".join(f'    app_{v}["{labels["app.app_types"][v]}"]'
                               for v in labels["app.app_types"] if v in app["app_types"]),
        "id_defines": "\n".join(f"#define {_c_macro(p['identifier'])} {p['id']}" for p in props),
        "dp_count": str(len(props)),
        "dp_defines": "\n".join(
            f'    DP_DEFINE({p["id"]}, "{p["identifier"]}", DP_{p["access"]}, {_C_TYPE[p["data_type"]["type"]]}),'
            for p in props),
        "command_cases": "\n".join(
            f"    case {_c_macro(p['identifier'])}: /* {p['identifier']}, {p['data_type']['type']}, {p['access']} */\n"
            f"        /* TODO: apply the value to the hardware */\n        break;"
            for p in writable),
        "report_calls": "\n".join(
            f"    {{ dp_value_t v = {{ .id = {_c_macro(p['identifier'])}, {_c_value(p)} }}; hal_dp_report(&v); }}"
            for p in readable) or "    /* no readable properties */",
        "demo_command_id": _c_macro(demo_target["identifier"]),
    }


def _writers(ctx: dict[str, str], model: dict[str, Any]) -> dict[str, Callable[[Path], None]]:
    def text(rel_tpl: str) -> Callable[[Path], None]:
        return lambda path: path.write_text(fill(_tpl(rel_tpl), ctx), encoding="utf-8")

    def static(rel: str) -> Callable[[Path], None]:
        return lambda path: path.write_text(_tpl(rel), encoding="utf-8")

    return {
        "thing-model.json": lambda path: path.write_text(dump_thing_model(model), encoding="utf-8"),
        "PRD.md": text("04-prd-template/PRD.template.md"),
        "architecture.mmd": text("03-architecture-diagram-conventions/architecture.template.mmd"),
        "quick-start.md": text("05-quick-start-template/quick-start.template.md"),
        "panel-spec.md": text("06-panel-spec-template/panel-spec.template.md"),
        "panel-preview.html": text("06-panel-spec-template/panel-preview.template.html"),
        "device-demo/dp_table.h": text("07-device-demo-template/dp_table.h.tpl"),
        "device-demo/app_main.c": text("07-device-demo-template/app_main.c.tpl"),
        "device-demo/hal_port.h": static("07-device-demo-template/hal_port.h"),
        "device-demo/hal_port_host.c": static("07-device-demo-template/hal_port_host.c"),
        "device-demo/README.md": text("07-device-demo-template/README.md.tpl"),
    }


def planned_files(outputs: list[str]) -> list[str]:
    files: list[str] = []
    for key in DELIVERABLE_FILES:
        if key in outputs:
            files.extend(DELIVERABLE_FILES[key])
    return files


def _install(tmp: Path, out_dir: Path) -> None:
    """Move a completely generated folder into place. Nothing is touched before this point."""
    if not out_dir.exists():
        os.replace(tmp, out_dir)
        return
    if not out_dir.is_dir():
        raise NotADirectoryError(f"{out_dir} exists and is not a directory")
    for path in sorted(p for p in tmp.rglob("*") if p.is_file()):
        target = out_dir / path.relative_to(tmp)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(path, target)


def generate(intake: Any, out_dir: Path, schema: dict[str, Any] | None = None,
             log: Callable[[str], None] | None = None) -> GenerationResult:
    """Generate deliverables.

    Raises InsufficientInput (and writes nothing) if any item is pending. All files are first written to a
    temporary folder next to *out_dir* and moved into place only after every step succeeded, so a failure
    leaves *out_dir* untouched.
    """
    schema = schema or load_schema()
    pending = find_pending(intake, schema)
    if pending:
        raise InsufficientInput(pending)

    model = build_thing_model(intake)
    ctx = _context(intake, model, schema)
    writers = _writers(ctx, model)
    planned = planned_files(intake["deliverables"]["outputs"])
    out_dir = Path(out_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.tmp-", dir=out_dir.parent))
    try:
        status, done = _generate_into(work, planned, writers, ctx, log)
        _install(work, out_dir)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return GenerationResult(done, status)


def _generate_into(out_dir: Path, planned: list[str], writers: dict[str, Callable[[Path], None]],
                   ctx: dict[str, str], log: Callable[[str], None] | None) -> tuple[str, list[str]]:
    done: list[str] = []
    reports: list[tuple[int, str, list[str]]] = []

    def milestone(pct: int, note: str) -> None:
        reports.append((pct, note, list(done)))
        if log:
            log(f"[PROGRESS {pct}%] {note} | files so far: {', '.join(done) or '(none)'}")

    milestone(10, "Intake checked: 0 pending items. Plan ready.")
    for pct, files in MILESTONES:
        if pct in (10, 100):
            continue
        for rel in files:
            if rel in planned and rel != "quick-start.pdf":
                path = out_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                writers[rel](path)
                done.append(rel)
        milestone(pct, {25: "Thing model written.", 45: "PRD and architecture diagram written.",
                        70: "Quick-start guide and panel specification written.",
                        90: "Device demo skeleton written."}[pct])

    if "quick-start.pdf" in planned:
        render_markdown_pdf((out_dir / "quick-start.md").read_text(encoding="utf-8"), out_dir / "quick-start.pdf",
                            title=f"{ctx['product_name']} quick-start guide")
        done.append("quick-start.pdf")

    from .consistency import check_folder  # local import to avoid a cycle

    report = check_folder(out_dir, required=planned)
    status = "PASS" if report.ok else "FAIL"
    reports.append((100, f"All deliverables written. Validation: {status}", list(done)))
    if log:
        log(f"[PROGRESS 100%] Validation: {status} | files so far: {', '.join(done)}")
        if not report.ok:
            log(report.render_text().rstrip("\n"))
    (out_dir / "PROGRESS.md").write_text(render_progress(planned, reports, validation=status), encoding="utf-8")
    return status, done
