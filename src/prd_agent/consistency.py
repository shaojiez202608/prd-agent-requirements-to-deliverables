"""Cross-deliverable consistency check keyed on thing model property ID (FR-6, FR-7).

Reference: thing-model.json. Every other deliverable carries a machine-readable
copy of (ID, identifier, access) in a fixed place:

- Markdown (PRD.md, quick-start.md, panel-spec.md): table between
  ``<!-- dp-table:begin -->`` and ``<!-- dp-table:end -->`` with columns
  Identifier, ID, Access (other columns are ignored).
- panel-preview.html: ``data-dp-id`` / ``data-dp-identifier`` / ``data-dp-access`` attributes.
- architecture.mmd: node labels ``"DP <id> <identifier> <access>"``.
- device-demo/dp_table.h: ``#define DP_ID_<IDENTIFIER> <id>`` and
  ``DP_DEFINE(<id>, "<identifier>", DP_<access>, ...)``.

Rules are in knowledge-base/09-consistency-and-change-tracking/README.md.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

ACCESS = ("R", "RW", "W")

# file -> extractor name. Order is the report order.
SOURCES: list[tuple[str, str]] = [
    ("PRD.md", "markdown"),
    ("quick-start.md", "markdown"),
    ("panel-spec.md", "markdown"),
    ("panel-preview.html", "html"),
    ("architecture.mmd", "mermaid"),
    ("device-demo/dp_table.h", "c_header"),
]
# FR-7: these three must always be present.
CORE_FILES = ["PRD.md", "quick-start.md", "device-demo/dp_table.h"]


@dataclass(frozen=True)
class Entry:
    file: str
    line: int
    id: int | None
    identifier: str | None
    access: str | None  # None when the source does not carry access (C #define)


@dataclass(frozen=True)
class Difference:
    file: str
    line: int
    kind: str
    message: str
    reference_line: int | None = None

    def render(self) -> str:
        ref = f" (thing-model.json:{self.reference_line})" if self.reference_line else ""
        return f"{self.file}:{self.line}: {self.kind}: {self.message}{ref}"


@dataclass
class Report:
    reference_count: int = 0
    checked: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    differences: list[Difference] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.differences

    def render_text(self) -> str:
        status = "PASS" if self.ok else f"FAIL ({len(self.differences)} difference(s))"
        out = [f"Consistency check: {status}",
               f"reference: thing-model.json ({self.reference_count} properties)"]
        if self.checked:
            out.append("checked: " + ", ".join(f"{k} ({v} entries)" for k, v in self.checked.items()))
        if self.skipped:
            out.append("skipped (not present): " + ", ".join(self.skipped))
        if self.differences:
            out.append("")
            out.extend(d.render() for d in self.differences)
        if self.hints:
            out.append("")
            out.extend(f"hint: {h}" for h in self.hints)
        return "\n".join(out) + "\n"

    def to_json(self) -> str:
        return json.dumps({"ok": self.ok, "reference_count": self.reference_count, "checked": self.checked,
                           "skipped": self.skipped, "differences": [asdict(d) for d in self.differences],
                           "hints": self.hints}, indent=2) + "\n"


class ExtractError(Exception):
    def __init__(self, file: str, line: int, message: str):
        super().__init__(message)
        self.file, self.line, self.message = file, line, message


def _int(text: str) -> int | None:
    text = text.strip()
    return int(text) if re.fullmatch(r"[0-9]+", text) else None


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells = re.split(r"(?<!\\)\|", s)
    return [c.strip().replace("\\|", "|") for c in cells]


def extract_markdown(name: str, text: str) -> list[Entry]:
    lines = text.splitlines()
    begin = [i for i, ln in enumerate(lines) if ln.strip() == "<!-- dp-table:begin -->"]
    end = [i for i, ln in enumerate(lines) if ln.strip() == "<!-- dp-table:end -->"]
    if len(begin) != 1 or len(end) != 1 or end[0] < begin[0]:
        raise ExtractError(name, 0, "expected exactly one <!-- dp-table:begin --> ... <!-- dp-table:end --> block")
    rows = [(i + 1, ln) for i, ln in enumerate(lines[begin[0] + 1:end[0]], begin[0] + 1) if ln.strip()]
    if len(rows) < 2:
        raise ExtractError(name, begin[0] + 1, "dp-table block has no table")
    head_no, head = rows[0]
    cols = [c.lower() for c in _split_row(head)]
    try:
        i_id, i_ident, i_acc = cols.index("id"), cols.index("identifier"), cols.index("access")
    except ValueError as exc:
        raise ExtractError(name, head_no, "dp-table header must contain Identifier, ID and Access columns") from exc
    out = []
    for no, row in rows[2:]:
        cells = _split_row(row)
        if len(cells) != len(cols):
            raise ExtractError(name, no, f"row has {len(cells)} cells, header has {len(cols)}")
        ident = cells[i_ident].strip("`").strip()
        out.append(Entry(name, no, _int(cells[i_id]), ident or None, cells[i_acc] or None))
    return out


_HTML_TAG = re.compile(r"<[^>]*\bdata-dp-id\s*=[^>]*>", re.S)


def _attr(tag: str, attr: str) -> str | None:
    m = re.search(rf'\b{attr}\s*=\s*"([^"]*)"', tag)
    return m.group(1) if m else None


def extract_html(name: str, text: str) -> list[Entry]:
    out = []
    for m in _HTML_TAG.finditer(text):
        tag = m.group(0)
        no = text.count("\n", 0, m.start()) + 1
        out.append(Entry(name, no, _int(_attr(tag, "data-dp-id") or ""), _attr(tag, "data-dp-identifier"),
                         _attr(tag, "data-dp-access")))
    return out


_MMD = re.compile(r'"DP\s+([0-9]+)\s+([A-Za-z0-9_]+)\s+([A-Z]+)"')


def extract_mermaid(name: str, text: str) -> list[Entry]:
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        for m in _MMD.finditer(line):
            out.append(Entry(name, no, int(m.group(1)), m.group(2), m.group(3)))
    return out


_C_DEFINE = re.compile(r"^\s*#define\s+DP_ID_([A-Z0-9_]+)\s+([0-9]+)\b")
_C_TABLE = re.compile(r'DP_DEFINE\(\s*([0-9]+)\s*,\s*"([^"]*)"\s*,\s*DP_([A-Z]+)\s*,')


def extract_c_header(name: str, text: str) -> list[Entry]:
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        m = _C_DEFINE.match(line)
        if m:
            out.append(Entry(name, no, int(m.group(2)), m.group(1).lower(), None))
            continue
        m = _C_TABLE.search(line)
        if m:
            out.append(Entry(name, no, int(m.group(1)), m.group(2), m.group(3)))
    return out


EXTRACTORS = {"markdown": extract_markdown, "html": extract_html, "mermaid": extract_mermaid,
              "c_header": extract_c_header}


def reference_entries(path: Path) -> tuple[list[Entry], list[Difference]]:
    """Read thing-model.json and locate the line of each property's "id"."""
    text = path.read_text(encoding="utf-8")
    try:
        model = json.loads(text)
    except ValueError as exc:
        return [], [Difference("thing-model.json", 0, "invalid_reference", f"not valid JSON: {exc}")]
    props = model.get("properties") if isinstance(model, dict) else None
    if not isinstance(props, list) or not props:
        return [], [Difference("thing-model.json", 0, "invalid_reference", "no properties list")]
    id_lines = [no for no, ln in enumerate(text.splitlines(), 1) if re.match(r'^\s*"id"\s*:', ln)]
    entries, diffs = [], []
    for i, p in enumerate(props):
        line = id_lines[i] if i < len(id_lines) else 0
        pid = p.get("id") if isinstance(p, dict) else None
        if not isinstance(pid, int) or isinstance(pid, bool):
            diffs.append(Difference("thing-model.json", line, "invalid_reference", f"property {i} has no integer id"))
            continue
        entries.append(Entry("thing-model.json", line, pid, p.get("identifier"), p.get("access")))
    seen: dict[int, Entry] = {}
    seen_ident: dict[str, Entry] = {}
    for e in entries:
        if e.id in seen:
            diffs.append(Difference("thing-model.json", e.line, "duplicate_id",
                                    f"ID {e.id} is also used at line {seen[e.id].line}"))
        seen.setdefault(e.id, e)
        if e.identifier in seen_ident:
            diffs.append(Difference("thing-model.json", e.line, "duplicate_identifier",
                                    f"identifier {e.identifier} is also used at line {seen_ident[e.identifier].line}"))
        if isinstance(e.identifier, str):
            seen_ident.setdefault(e.identifier, e)
        if e.access not in ACCESS:
            diffs.append(Difference("thing-model.json", e.line, "invalid_access", f"access {e.access!r} for ID {e.id}"))
    return entries, diffs


def compare(ref: list[Entry], entries: list[Entry], name: str, anchor_line: int) -> list[Difference]:
    by_id = {e.id: e for e in ref}
    by_ident = {e.identifier: e for e in ref}
    diffs: list[Difference] = []
    covered: set[tuple[int | None, bool]] = set()  # (ref id, has_access) pairs seen in this file
    seen_ids: dict[tuple[int | None, bool], int] = {}
    for e in entries:
        kind_key = (e.id, e.access is not None)
        if e.id is None:
            diffs.append(Difference(name, e.line, "invalid_id", f"ID is not an integer (identifier {e.identifier})"))
            continue
        if kind_key in seen_ids:
            diffs.append(Difference(name, e.line, "duplicate_id", f"ID {e.id} already listed at line {seen_ids[kind_key]}"))
        else:
            seen_ids[kind_key] = e.line
        r = by_id.get(e.id)
        if r is not None and r.identifier == e.identifier:
            covered.add((r.id, e.access is not None))
            if e.access is not None and e.access != r.access:
                diffs.append(Difference(name, e.line, "access_mismatch",
                                        f"ID {e.id} {e.identifier}: access {e.access} here, {r.access} in thing model",
                                        r.line))
            continue
        alt = by_ident.get(e.identifier)
        if alt is not None:
            covered.add((alt.id, e.access is not None))
            diffs.append(Difference(name, e.line, "id_mismatch",
                                    f"identifier {e.identifier}: ID {e.id} here, ID {alt.id} in thing model", alt.line))
            if e.access is not None and e.access != alt.access:
                diffs.append(Difference(name, e.line, "access_mismatch",
                                        f"identifier {e.identifier}: access {e.access} here, {alt.access} in thing model",
                                        alt.line))
            continue
        if r is not None:
            covered.add((r.id, e.access is not None))
            diffs.append(Difference(name, e.line, "identifier_mismatch",
                                    f"ID {e.id}: identifier {e.identifier} here, {r.identifier} in thing model", r.line))
            if e.access is not None and e.access != r.access:
                diffs.append(Difference(name, e.line, "access_mismatch",
                                        f"ID {e.id}: access {e.access} here, {r.access} in thing model", r.line))
            continue
        diffs.append(Difference(name, e.line, "unknown_entry",
                                f"ID {e.id} {e.identifier} is not in the thing model"))
    kinds = {has_acc for (_, has_acc) in seen_ids} or {True}
    for has_acc in sorted(kinds):
        for r in ref:
            if (r.id, has_acc) not in covered:
                what = "access-bearing entry" if has_acc else "#define"
                diffs.append(Difference(name, anchor_line, "missing",
                                        f"ID {r.id} {r.identifier} has no {what} in this file", r.line))
    return diffs


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_folder(folder: Path, required: list[str] | None = None) -> Report:
    """Check every known deliverable in *folder* against thing-model.json.

    *required*: files that must exist. ``None`` means the planned files from
    PROGRESS.md if present, otherwise the three FR-7 files.
    """
    folder = Path(folder)
    report = Report()
    tm = folder / "thing-model.json"
    if not tm.is_file():
        report.differences.append(Difference("thing-model.json", 0, "missing_file", "reference file not found"))
        return report
    ref, ref_diffs = reference_entries(tm)
    report.reference_count = len(ref)
    report.differences.extend(ref_diffs)

    if required is None:
        required = _planned_from_progress(folder) or CORE_FILES
    all_diffs: list[Difference] = []
    for name, kind in SOURCES:
        path = folder / name
        if not path.is_file():
            if name in required:
                report.differences.append(Difference(name, 0, "missing_file", "required deliverable not found"))
            else:
                report.skipped.append(name)
            continue
        text = path.read_text(encoding="utf-8")
        try:
            entries = EXTRACTORS[kind](name, text)
        except ExtractError as exc:
            report.differences.append(Difference(exc.file, exc.line, "unreadable", exc.message))
            continue
        report.checked[name] = len(entries)
        if not entries:
            report.differences.append(Difference(name, 0, "no_entries", "no thing model entries found"))
            continue
        all_diffs.extend(compare(ref, entries, name, entries[0].line))

    report.differences.extend(all_diffs)
    _pdf_freshness(folder, required, report)
    _reference_hint(report, all_diffs)
    return report


def _planned_from_progress(folder: Path) -> list[str]:
    path = folder / "PROGRESS.md"
    if not path.is_file():
        return []
    planned, on = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "Planned files:":
            on = True
            continue
        if on:
            if line.startswith("- "):
                planned.append(line[2:].strip())
            else:
                break
    return planned


def _pdf_freshness(folder: Path, required: list[str], report: Report) -> None:
    from .pdf import read_source_hash

    pdf, md = folder / "quick-start.pdf", folder / "quick-start.md"
    if not pdf.is_file():
        if "quick-start.pdf" in required:
            report.differences.append(Difference("quick-start.pdf", 0, "missing_file", "required deliverable not found"))
        return
    embedded = read_source_hash(pdf)
    if md.is_file() and embedded != _sha256(md):
        report.differences.append(Difference("quick-start.pdf", 0, "stale_pdf",
                                             "PDF was not rendered from the current quick-start.md; run prd-agent render-pdf"))


def _reference_hint(report: Report, diffs: list[Difference]) -> None:
    """If every checked file disagrees with the same reference line, the thing model is the likely edit."""
    if len(report.checked) < 2:
        return
    by_ref: dict[int, set[str]] = {}
    for d in diffs:
        if d.reference_line and d.kind in ("id_mismatch", "identifier_mismatch", "access_mismatch", "missing"):
            by_ref.setdefault(d.reference_line, set()).add(d.file)
    for line, files in sorted(by_ref.items()):
        if files == set(report.checked):
            report.hints.append(f"all {len(files)} checked files disagree with thing-model.json:{line}; "
                                "the thing model itself may be the file that was edited")
