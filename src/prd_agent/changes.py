"""Thing model version change tracking (FR-10).

Compares two thing-model.json files by property ID and classifies each change
as breaking or compatible for device firmware and app clients.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Change:
    id: int
    kind: str  # added | removed | changed
    detail: str
    breaking: bool

    def render(self) -> str:
        flag = "BREAKING" if self.breaking else "compatible"
        return f"- ID {self.id} {self.kind} [{flag}]: {self.detail}"


def _by_id(model: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {p["id"]: p for p in model.get("properties", [])}


def diff_models(old: dict[str, Any], new: dict[str, Any]) -> list[Change]:
    a, b = _by_id(old), _by_id(new)
    out: list[Change] = []
    for pid in sorted(set(a) | set(b)):
        pa, pb = a.get(pid), b.get(pid)
        if pa is None:
            out.append(Change(pid, "added", f"{pb['identifier']} ({pb['access']}, {pb['data_type']['type']})", False))
            continue
        if pb is None:
            out.append(Change(pid, "removed", f"{pa['identifier']} removed; old firmware/app still send this ID", True))
            continue
        if pa["identifier"] != pb["identifier"]:
            out.append(Change(pid, "changed", f"identifier {pa['identifier']} -> {pb['identifier']} (ID reused)", True))
        if pa["access"] != pb["access"]:
            narrowed = not set(pb["access"]) >= set(pa["access"])
            out.append(Change(pid, "changed", f"access {pa['access']} -> {pb['access']}", narrowed))
        ta, tb = pa["data_type"], pb["data_type"]
        if ta.get("type") != tb.get("type"):
            out.append(Change(pid, "changed", f"data type {ta.get('type')} -> {tb.get('type')}", True))
            continue
        for key in ("min", "max", "step", "unit", "max_length", "values"):
            if ta.get(key) != tb.get(key):
                breaking = _breaking_spec(key, ta.get(key), tb.get(key))
                out.append(Change(pid, "changed", f"{key} {ta.get(key)} -> {tb.get(key)}", breaking))
        if pa.get("name") != pb.get("name"):
            out.append(Change(pid, "changed", f"name {pa.get('name')} -> {pb.get('name')}", False))
        if pa.get("panel") != pb.get("panel"):
            out.append(Change(pid, "changed", "panel control or interaction changed", False))
    return out


def _breaking_spec(key: str, old: Any, new: Any) -> bool:
    if old is None or new is None:
        return True
    if key == "min":
        return new > old  # narrowed
    if key in ("max", "max_length"):
        return new < old  # narrowed
    if key == "values":
        return not set(new) >= set(old)
    return True  # step or unit change alters meaning of existing values


def render_changes(changes: list[Change]) -> str:
    if not changes:
        return "# Thing model changes\n\nNo changes.\n"
    breaking = sum(c.breaking for c in changes)
    lines = ["# Thing model changes", "", f"{len(changes)} change(s), {breaking} breaking.", ""]
    lines += [c.render() for c in changes]
    return "\n".join(lines) + "\n"
