"""Thing model construction and loading.

The thing model (``thing-model.json``) is the single source of truth for
property ID, identifier and access. Every other deliverable copies these three
values and the consistency checker compares them back to this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .intake import clean_text, parse_number

THING_MODEL_FORMAT = "prd-agent/thing-model@1"


def _num(v: Any) -> int | float | None:
    return parse_number(v)


def build_thing_model(intake: dict[str, Any]) -> dict[str, Any]:
    """Build the thing model from a validated intake (call find_pending first)."""
    hw = intake["hardware"]
    props = []
    for p in intake["thing_model"]["properties"]:
        dtype = p["data_type"]
        spec: dict[str, Any] = {"type": dtype}
        if dtype in ("int", "float"):
            spec.update({"min": _num(p["min"]), "max": _num(p["max"]), "step": _num(p["step"]),
                         "unit": clean_text(p["unit"])})
        elif dtype == "enum":
            spec["values"] = [v for v in (clean_text(x) for x in p["enum_values"].split(",")) if v]
        elif dtype == "string":
            spec["max_length"] = _num(p["max_length"])
        props.append({
            "id": _num(p["id"]),
            "identifier": clean_text(p["identifier"]),
            "name": clean_text(p["name"]),
            "access": p["access"],
            "data_type": spec,
            "panel": {"control": p["control"], "interaction": clean_text(p["interaction"])},
        })
    props.sort(key=lambda x: x["id"])
    return {
        "format": THING_MODEL_FORMAT,
        "product": {
            "name": clean_text(hw["product_name"]),
            "category": hw["product_category"],
            "connectivity": hw["connectivity"],
        },
        "properties": props,
    }


def dump_thing_model(model: dict[str, Any]) -> str:
    """Stable serialisation: one key per line so the checker can report line numbers."""
    return json.dumps(model, indent=2, ensure_ascii=False) + "\n"


def load_thing_model(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
