"""Intake schema loading, normalisation and the "insufficient input" check (FR-8).

The same rules are implemented in ``intake/compiler.js`` for the offline HTML
forms. ``tests/test_js_parity.py`` runs both on the same fixtures and requires
byte-identical prompt text, so any change here must be mirrored there.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "intake" / "schema.json"

_WS = re.compile(r"[ \t\r\n]+")
_NUM = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
# Largest integer that JavaScript (the offline forms) represents exactly. Larger integers are rejected so that
# both compilers see the same value.
MAX_SAFE_INTEGER = 2**53 - 1


@dataclass(frozen=True)
class PendingItem:
    """One item that must be confirmed before deliverables may be generated."""

    code: str
    path: str
    message: str

    def render(self) -> str:
        return f"- [{self.code}] {self.path}: {self.message}"


def load_schema(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or SCHEMA_PATH).read_text(encoding="utf-8"))


def clean_text(value: Any) -> str:
    """Trim and collapse ASCII whitespace. Non-strings become ''."""
    if not isinstance(value, str):
        return ""
    return _WS.sub(" ", value).strip(" ")


def clean_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = value.replace("\r\n", "\n").split("\n")
    elif isinstance(value, list):
        raw = [v for v in value if isinstance(v, str)]
    else:
        return []
    return [t for t in (clean_text(r) for r in raw) if t]


def parse_number(value: Any) -> int | float | None:
    """Return an int/float, or None if the value is not a plain decimal number."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if abs(value) <= MAX_SAFE_INTEGER else None
    if isinstance(value, str):
        s = value.strip(" \t\r\n")
        if not _NUM.match(s):
            return None
        value = float(s)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        if value.is_integer():
            return int(value) if abs(value) <= MAX_SAFE_INTEGER else None
        return value
    return None


def format_number(value: int | float) -> str:
    """Plain decimal text without exponent, identical to formatNumber in intake/compiler.js.

    Both languages print the shortest digits that round-trip the double; only the exponent notation
    differs (Python ``1e-05``, JavaScript ``1e-7``), so it is expanded here.
    """
    if isinstance(value, int):
        return str(value)
    text = repr(value)
    return format(Decimal(text), "f") if "e" in text else text


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return clean_text(value) == ""
    if isinstance(value, list):
        return len(value) == 0
    return False


def option_values(field: dict[str, Any]) -> list[str]:
    return [o["value"] for o in field.get("options", [])]


def _check_scalar(field: dict[str, Any], value: Any, path: str, out: list[PendingItem]) -> None:
    """Validate a non-empty scalar / list value against its field definition."""
    ftype = field["type"]
    if ftype == "enum":
        if not isinstance(value, str) or value not in option_values(field):
            out.append(PendingItem("invalid", path, "value is not one of the allowed options"))
    elif ftype == "multi_enum":
        allowed = option_values(field)
        if not isinstance(value, list) or any((not isinstance(v, str)) or v not in allowed for v in value):
            out.append(PendingItem("invalid", path, "contains a value that is not an allowed option"))
    elif ftype == "text":
        text = clean_text(value)
        if not isinstance(value, str):
            out.append(PendingItem("invalid", path, "must be text"))
            return
        if "max_length" in field and len(text) > field["max_length"]:
            out.append(PendingItem("invalid", path, f"longer than {field['max_length']} characters"))
        if "pattern" in field and not re.match(field["pattern"], text):
            out.append(PendingItem("invalid", path, f"does not match pattern {field['pattern']}"))
    elif ftype == "lines":
        lines = clean_lines(value)
        if "max_items" in field and len(lines) > field["max_items"]:
            out.append(PendingItem("invalid", path, f"more than {field['max_items']} lines"))
        if "max_length" in field and any(len(t) > field["max_length"] for t in lines):
            out.append(PendingItem("invalid", path, f"a line is longer than {field['max_length']} characters"))
    elif ftype in ("integer", "number"):
        num = parse_number(value)
        if num is None or (ftype == "integer" and not isinstance(num, int)):
            out.append(PendingItem("invalid", path, "must be an integer" if ftype == "integer" else "must be a number"))
            return
        if "min" in field and num < field["min"]:
            out.append(PendingItem("invalid", path, f"must be >= {field['min']}"))
        if "max" in field and num > field["max"]:
            out.append(PendingItem("invalid", path, f"must be <= {field['max']}"))


def _text_values(field: dict[str, Any], value: Any) -> list[str]:
    if field["type"] == "text" and isinstance(value, str):
        return [clean_text(value)]
    if field["type"] == "lines":
        return clean_lines(value)
    return []


LATIN1_MESSAGE = ("contains characters outside Latin-1, which the quick-start PDF cannot render; "
                  "use Latin-1 text or do not request quick_start")


def _check_text_rules(schema: dict[str, Any], field: dict[str, Any], value: Any, path: str, latin1: bool,
                      out: list[PendingItem]) -> None:
    """Reserved markers (all free text) and Latin-1 (text that reaches the quick-start PDF)."""
    texts = _text_values(field, value)
    if not texts:
        return
    for marker in schema["rules"].get("reserved_text", []):
        if any(marker in t for t in texts):
            out.append(PendingItem("invalid", path, f"must not contain {marker} (reserved for markers in the deliverables)"))
            break
    if latin1 and any(ord(ch) > 0xFF for t in texts for ch in t):
        out.append(PendingItem("invalid", path, LATIN1_MESSAGE))


def _pdf_requested(intake: dict[str, Any], schema: dict[str, Any]) -> bool:
    rule = schema["rules"].get("latin1_text")
    deliverables = intake.get("deliverables")
    outputs = deliverables.get("outputs") if isinstance(deliverables, dict) else None
    return bool(rule) and isinstance(outputs, list) and rule["when_output"] in outputs


def _present(field: dict[str, Any], value: Any) -> bool:
    if field["type"] == "lines":
        return len(clean_lines(value)) > 0
    return not is_empty(value)


def _check_property(schema: dict[str, Any], columns: list[dict[str, Any]], prop: Any, idx: int,
                    out: list[PendingItem], pdf: bool = False) -> None:
    base = f"thing_model.properties[{idx}]"
    if not isinstance(prop, dict):
        out.append(PendingItem("invalid", base, "must be an object"))
        return
    for col in columns:
        val = prop.get(col["key"])
        path = f"{base}.{col['key']}"
        if not _present(col, val):
            if col["required"]:
                out.append(PendingItem("missing", path, "required field is empty"))
            continue
        _check_scalar(col, val, path, out)
        latin1 = pdf and col["key"] in schema["rules"].get("latin1_text", {}).get("columns", [])
        _check_text_rules(schema, col, val, path, latin1, out)

    dtype = prop.get("data_type")
    numeric = schema["rules"]["numeric_types"]
    if dtype in numeric:
        for key in ("unit", "min", "max", "step"):
            if is_empty(prop.get(key)):
                out.append(PendingItem("missing", f"{base}.{key}", f"required when data_type is {dtype}"))
        lo, hi, step = (parse_number(prop.get(k)) for k in ("min", "max", "step"))
        if lo is not None and hi is not None and not lo < hi:
            out.append(PendingItem("conflict", f"{base}.max", "max must be greater than min"))
        if step is not None and step <= 0:
            out.append(PendingItem("conflict", f"{base}.step", "step must be greater than 0"))
        if dtype == "int":
            for key, num in (("min", lo), ("max", hi), ("step", step)):
                if num is not None and not isinstance(num, int):
                    out.append(PendingItem("conflict", f"{base}.{key}", "must be an integer when data_type is int"))
    elif dtype == "enum":
        raw_enum = prop.get("enum_values") if isinstance(prop.get("enum_values"), str) else ""
        values = [v for v in (clean_text(x) for x in raw_enum.split(",")) if v]
        if len(values) < 2:
            out.append(PendingItem("missing", f"{base}.enum_values", "at least two values required when data_type is enum"))
        elif len(set(values)) != len(values):
            out.append(PendingItem("conflict", f"{base}.enum_values", "duplicate enum values"))
    elif dtype == "string":
        if is_empty(prop.get("max_length")):
            out.append(PendingItem("missing", f"{base}.max_length", "required when data_type is string"))

    control = prop.get("control")
    access = prop.get("access")
    req = schema["rules"]["control_requirements"].get(control) if isinstance(control, str) else None
    if req:
        if isinstance(dtype, str) and dtype in option_values(_col(columns, "data_type")) and dtype not in req["data_types"]:
            out.append(PendingItem("conflict", f"{base}.control",
                                   f"control {control} expects data_type {'/'.join(req['data_types'])}"))
        if isinstance(access, str) and access in option_values(_col(columns, "access")) and access not in req["access"]:
            out.append(PendingItem("conflict", f"{base}.control",
                                   f"control {control} expects access {'/'.join(req['access'])}"))


def _col(columns: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return next(c for c in columns if c["key"] == key)


def find_pending(intake: Any, schema: dict[str, Any] | None = None) -> list[PendingItem]:
    """Return every item that blocks generation, in deterministic schema order."""
    schema = schema or load_schema()
    out: list[PendingItem] = []
    if not isinstance(intake, dict):
        return [PendingItem("invalid", "(root)", "intake must be a JSON object")]
    if intake.get("schema_version") != schema["schema_version"]:
        out.append(PendingItem("invalid", "schema_version", f"expected {schema['schema_version']}"))
    if not isinstance(intake.get("variant"), str) or intake.get("variant") not in schema["variants"]:
        out.append(PendingItem("invalid", "variant", "expected one of " + ", ".join(schema["variants"])))
    pdf = _pdf_requested(intake, schema)
    latin1_fields = schema["rules"].get("latin1_text", {}).get("fields", [])
    for section in schema["sections"]:
        sec = intake.get(section["key"])
        sec = sec if isinstance(sec, dict) else {}
        for field in section["fields"]:
            path = f"{section['key']}.{field['key']}"
            val = sec.get(field["key"])
            if field["type"] == "properties":
                props = val if isinstance(val, list) else []
                if not props:
                    out.append(PendingItem("missing", path, "at least one property is required"))
                    continue
                for i, prop in enumerate(props):
                    _check_property(schema, field["columns"], prop, i, out, pdf)
                _check_unique(props, out)
                continue
            if not _present(field, val):
                if field["required"]:
                    out.append(PendingItem("missing", path, "required field is empty"))
                continue
            _check_scalar(field, val, path, out)
            _check_text_rules(schema, field, val, path, pdf and path in latin1_fields, out)
            if path == "deliverables.outputs" and isinstance(val, list):
                need = [o for o in schema["rules"].get("required_outputs", []) if o not in val]
                if need:
                    out.append(PendingItem("missing", path, "must include " + ", ".join(need)
                                           + " (the reference for every consistency check)"))
    return out


def _check_unique(props: list[Any], out: list[PendingItem]) -> None:
    seen_id: dict[Any, int] = {}
    seen_ident: dict[str, int] = {}
    for i, prop in enumerate(props):
        if not isinstance(prop, dict):
            continue
        pid = parse_number(prop.get("id"))
        if isinstance(pid, int):
            if pid in seen_id:
                out.append(PendingItem("conflict", f"thing_model.properties[{i}].id",
                                       f"duplicate id {pid} (also at properties[{seen_id[pid]}])"))
            else:
                seen_id[pid] = i
        ident = clean_text(prop.get("identifier"))
        if ident:
            if ident in seen_ident:
                out.append(PendingItem("conflict", f"thing_model.properties[{i}].identifier",
                                       f"duplicate identifier {ident} (also at properties[{seen_ident[ident]}])"))
            else:
                seen_ident[ident] = i


def load_intake(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
