"""Build the two offline intake pages (FR-1) from intake/schema.json.

Output: intake/frontline.html and intake/pm.html. Each page is a single file
with the schema, the agent instructions (knowledge-base/00-project-rules/system-prompt.md),
the compiler and the UI script inlined, so it opens from disk
with no network access. A Content-Security-Policy blocks all network requests.
"""

from __future__ import annotations

import json
from pathlib import Path

from .intake import REPO_ROOT, load_schema
from .prompt import load_instructions

INTAKE_DIR = REPO_ROOT / "intake"


def build_form(variant: str) -> str:
    schema = load_schema()
    meta = schema["variants"][variant]
    tpl = (INTAKE_DIR / "form.template.html").read_text(encoding="utf-8")
    schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    instructions_json = json.dumps(load_instructions(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    values = {
        "{{INSTRUCTIONS_JSON}}": instructions_json,
        "{{TITLE}}": f"{meta['title_zh']} / {meta['title_en']}",
        "{{VARIANT}}": variant,
        "{{SCHEMA_JSON}}": schema_json,
        "{{COMPILER_JS}}": (INTAKE_DIR / "compiler.js").read_text(encoding="utf-8"),
        "{{FORM_UI_JS}}": (INTAKE_DIR / "form-ui.js").read_text(encoding="utf-8"),
    }
    for key, val in values.items():
        tpl = tpl.replace(key, val)
    return tpl


def build_all(out_dir: Path | None = None) -> list[Path]:
    out_dir = Path(out_dir or INTAKE_DIR)
    written = []
    for variant in load_schema()["variants"]:
        path = out_dir / f"{variant}.html"
        path.write_text(build_form(variant), encoding="utf-8")
        written.append(path)
    return written
