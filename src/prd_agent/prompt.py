"""Deterministic prompt compiler (FR-1, FR-8).

Same intake in -> byte-identical text out. The agent instructions come from
knowledge-base/00-project-rules/system-prompt.md (FR-9). Multi-select values are emitted in
schema order, never in click order, so two people filling the same answers get
the same prompt. Mirrored in ``intake/compiler.js``; see tests/test_js_parity.py.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .intake import (
    REPO_ROOT,
    PendingItem,
    clean_lines,
    clean_text,
    find_pending,
    format_number,
    load_schema,
    option_values,
    parse_number,
)

NOT_PROVIDED = "(not provided)"

# FR-9: the agent instructions live in a versioned Markdown file, not in code.
SYSTEM_PROMPT_PATH = REPO_ROOT / "knowledge-base" / "00-project-rules" / "system-prompt.md"
_INSTRUCTION_SECTIONS = {"Always": "always", "GENERATE mode": "generate", "CLARIFY_ONLY mode": "clarify"}
_NUMBERED = re.compile(r"^[0-9]+\. \S")


def load_instructions(path: Path | None = None) -> dict[str, list[str]]:
    """Parse system-prompt.md into {"always", "generate", "clarify"} -> instruction lines (verbatim)."""
    path = path or SYSTEM_PROMPT_PATH
    out: dict[str, list[str]] = {key: [] for key in _INSTRUCTION_SECTIONS.values()}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = _INSTRUCTION_SECTIONS.get(line[3:].strip())
        elif current and _NUMBERED.match(line):
            out[current].append(line.rstrip())
    empty = [name for name, key in _INSTRUCTION_SECTIONS.items() if not out[key]]
    if empty:
        raise ValueError(f"{path.name}: no numbered instructions under: {', '.join(empty)}")
    return out

# Deliverable key -> files the agent must write (relative to the output folder).
DELIVERABLE_FILES: dict[str, list[str]] = {
    "thing_model": ["thing-model.json"],
    "architecture": ["architecture.mmd"],
    "quick_start": ["quick-start.md", "quick-start.pdf"],
    "prd": ["PRD.md"],
    "panel_spec": ["panel-spec.md", "panel-preview.html"],
    "device_demo": ["device-demo/dp_table.h", "device-demo/app_main.c", "device-demo/hal_port.h",
                    "device-demo/hal_port_host.c", "device-demo/README.md"],
}


_MARKER = re.compile(r"(intake)-", re.IGNORECASE | re.ASCII)


def _neutralise(text: str) -> str:
    # Person-supplied text must not be able to open or close the data block, in any letter case.
    return _MARKER.sub(r"\1_", text)


def _text(value: Any) -> str:
    if isinstance(value, str):
        return _neutralise(clean_text(value))
    if isinstance(value, bool):
        return "(invalid)"
    num = parse_number(value)
    return format_number(num) if num is not None else "(invalid)"


def _render_field(field: dict[str, Any], value: Any) -> str:
    ftype = field["type"]
    if ftype == "lines":
        lines = clean_lines(value)
        if not lines:
            return NOT_PROVIDED
        return "\n" + "\n".join(f"  {i}. {_neutralise(t)}" for i, t in enumerate(lines, 1))
    if value is None or (isinstance(value, str) and clean_text(value) == "") or (isinstance(value, list) and not value):
        return NOT_PROVIDED
    if ftype == "enum":
        labels = {o["value"]: o["en"] for o in field["options"]}
        if isinstance(value, str) and value in labels:
            return f"{value} ({labels[value]})"
        return f"{_text(value)} (invalid)"
    if ftype == "multi_enum":
        if not isinstance(value, list):
            return f"{_text(value)} (invalid)"
        labels = {o["value"]: o["en"] for o in field["options"]}
        chosen = [o for o in option_values(field) if o in value]
        invalid = [v for v in value if not (isinstance(v, str) and v in labels)]
        parts = [f"{v} ({labels[v]})" for v in chosen] + [f"{_text(v)} (invalid)" for v in invalid]
        return "; ".join(parts)
    return _text(value)


def _cell(value: Any) -> str:
    if value is None or (isinstance(value, str) and clean_text(value) == ""):
        return "-"
    return _text(value).replace("|", "\\|")


def compile_prompt(intake: Any, schema: dict[str, Any] | None = None,
                   instructions: dict[str, list[str]] | None = None) -> str:
    schema = schema or load_schema()
    instructions = instructions or load_instructions()
    pending: list[PendingItem] = find_pending(intake, schema)
    data = intake if isinstance(intake, dict) else {}
    mode = "GENERATE" if not pending else "CLARIFY_ONLY"
    lines: list[str] = []
    add = lines.append

    add("# PRD agent task")
    add("")
    # Only known values are echoed above the data block; anything else could carry instructions.
    version, variant = data.get("schema_version"), data.get("variant")
    add(f"schema_version: {version if version == schema['schema_version'] else '(invalid)'}")
    add(f"form: {variant if isinstance(variant, str) and variant in schema['variants'] else '(invalid)'}")
    add(f"mode: {mode}")
    add("")
    add("## Instructions for the agent")
    add("")
    for line in instructions["always"] + instructions["generate" if mode == "GENERATE" else "clarify"]:
        add(line)
    add("")
    add(f"## Pending confirmation items ({len(pending)})")
    add("")
    if pending:
        lines.extend(p.render() for p in pending)
    else:
        add("(none)")
    add("")
    add("## Intake")
    add("")
    add("INTAKE-BEGIN")
    for section in schema["sections"]:
        sec = data.get(section["key"])
        sec = sec if isinstance(sec, dict) else {}
        add("")
        add(f"### {section['title_en']}")
        add("")
        for field in section["fields"]:
            value = sec.get(field["key"])
            if field["type"] == "properties":
                cols = field["columns"]
                add("| # | " + " | ".join(c["key"] for c in cols) + " |")
                add("|---|" + "|".join("---" for _ in cols) + "|")
                props = value if isinstance(value, list) else []
                for i, prop in enumerate(props, 1):
                    prop = prop if isinstance(prop, dict) else {}
                    add(f"| {i} | " + " | ".join(_cell(prop.get(c["key"])) for c in cols) + " |")
                if not props:
                    add("| - | " + " | ".join("-" for _ in cols) + " |")
                continue
            rendered = _render_field(field, value)
            sep = ":" if rendered.startswith("\n") else ": "
            add(f"- {field['label_en']} [{section['key']}.{field['key']}]{sep}{rendered}")
    add("")
    add("INTAKE-END")
    add("")
    add("## Requested deliverables")
    add("")
    outputs = (data.get("deliverables") or {}).get("outputs") if isinstance(data.get("deliverables"), dict) else None
    chosen = [k for k in DELIVERABLE_FILES if isinstance(outputs, list) and k in outputs]
    if mode == "GENERATE":
        for key in chosen:
            add(f"- {key}: " + ", ".join(DELIVERABLE_FILES[key]))
        add("- always: PROGRESS.md")
    else:
        add("(none until the pending items are confirmed)")
    add("")
    return "\n".join(lines)
