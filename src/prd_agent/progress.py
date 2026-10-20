"""Staged progress protocol (FR-4).

An agent writes PROGRESS.md with six reports (10/25/45/70/90/100 %). Each report
lists every file produced so far. ``check_progress`` verifies the log against
the files on disk so that "framework only, then stop" is detected.
Format: knowledge-base/08-progress-protocol/README.md
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .prompt import CORE_FILES, planned_files

PERCENTS = [10, 25, 45, 70, 90, 100]

# Milestone -> files that must be listed no later than this milestone (if planned).
MILESTONES: list[tuple[int, list[str]]] = [
    (10, []),
    (25, ["thing-model.json"]),
    (45, ["PRD.md", "architecture.mmd"]),
    (70, ["quick-start.md", "panel-spec.md", "panel-preview.html"]),
    (90, ["device-demo/dp_table.h", "device-demo/app_main.c", "device-demo/hal_port.h",
          "device-demo/hal_port_host.c", "device-demo/README.md"]),
    (100, ["quick-start.pdf"]),
]
DUE: dict[str, int] = {f: pct for pct, files in MILESTONES for f in files}

_HEAD = re.compile(r"^## \[PROGRESS (\d+)%\] (.+)$")
_BULLET = re.compile(r"^- (.+)$")


def render_progress(planned: list[str], reports: list[tuple[int, str, list[str]]], validation: str) -> str:
    out = ["# Progress log", "", "Format: knowledge-base/08-progress-protocol.", "", "Planned files:"]
    out += [f"- {f}" for f in planned]
    for pct, note, files in reports:
        out += ["", f"## [PROGRESS {pct}%] {note}", "", "Files so far:"]
        out += [f"- {f}" for f in files] or ["- (none)"]
    out += ["", f"Validation: {validation}", ""]
    return "\n".join(out)


@dataclass(frozen=True)
class ProgressProblem:
    line: int
    message: str

    def render(self, name: str = "PROGRESS.md") -> str:
        return f"{name}:{self.line}: {self.message}"


def stub_reason(path: Path) -> str | None:
    """Return why a deliverable looks like an empty framework, or None if it looks real."""
    if not path.is_file():
        return "file does not exist"
    data = path.read_bytes()
    if not data.strip():
        return "file is empty"
    if path.suffix == ".pdf":
        return None if data.startswith(b"%PDF-") else "not a PDF file"
    text = data.decode("utf-8", errors="replace")
    if path.suffix == ".json":
        try:
            json.loads(text)
        except ValueError:
            return "invalid JSON"
        return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if path.suffix == ".md":
        body = [ln for ln in lines if not ln.startswith("#") and ln.upper() not in ("TODO", "TBD", "...")]
        return None if len(body) >= 5 else "markdown has fewer than 5 content lines (looks like a skeleton)"
    return None if len(lines) >= 3 else "fewer than 3 non-empty lines (looks like a skeleton)"


def check_progress(folder: Path, outputs: list[str] | None = None) -> list[ProgressProblem]:
    """Check PROGRESS.md against the files on disk.

    The planned list must contain the FR-7 core files, or with *outputs* (the intake's deliverables) every
    file those outputs produce, so that removing a file from the plan cannot hide a missing deliverable.
    """
    folder = Path(folder)
    path = folder / "PROGRESS.md"
    if not path.is_file():
        return [ProgressProblem(0, "PROGRESS.md not found")]
    lines = path.read_text(encoding="utf-8").splitlines()
    problems: list[ProgressProblem] = []

    planned: list[str] = []
    sections: list[dict] = []
    current: dict | None = None
    mode = None
    validation_line = None
    for no, raw in enumerate(lines, 1):
        line = raw.rstrip()
        m = _HEAD.match(line)
        if m:
            current = {"pct": int(m.group(1)), "line": no, "files": [], "has_list": False}
            sections.append(current)
            mode = None
            continue
        if line == "Planned files:":
            mode = "planned"
            continue
        if line == "Files so far:":
            if current is None:
                problems.append(ProgressProblem(no, "'Files so far:' outside a progress report"))
            else:
                current["has_list"] = True
            mode = "files"
            continue
        if line.startswith("Validation:"):
            validation_line = (no, line)
            mode = None
            continue
        b = _BULLET.match(line)
        if b and mode == "planned":
            planned.append(b.group(1).strip())
        elif b and mode == "files" and current is not None:
            if b.group(1).strip() != "(none)":
                current["files"].append((b.group(1).strip(), no))
        elif line and mode in ("planned", "files"):
            mode = None

    if not planned:
        problems.append(ProgressProblem(0, "no 'Planned files:' list"))
    elif outputs is not None:
        for f in planned_files(outputs):
            if f not in planned:
                problems.append(ProgressProblem(0, f"planned files omit {f}, which the intake requests"))
    else:
        for f in CORE_FILES:
            if f not in planned:
                problems.append(ProgressProblem(0, f"planned files omit {f}, an FR-7 core deliverable "
                                                   "(pass --intake for a smaller deliverable set)"))
    got = [s["pct"] for s in sections]
    if got != PERCENTS:
        problems.append(ProgressProblem(sections[0]["line"] if sections else 0,
                                        f"expected reports at {PERCENTS}, found {got}"))
    prev: set[str] = set()
    for s in sections:
        names = [f for f, _ in s["files"]]
        if not s["has_list"]:
            problems.append(ProgressProblem(s["line"], f"{s['pct']}% report has no 'Files so far:' list"))
        missing_prev = sorted(prev - set(names))
        if missing_prev:
            problems.append(ProgressProblem(s["line"], f"{s['pct']}% report drops files listed earlier: "
                                            + ", ".join(missing_prev)))
        for f in planned:
            due = DUE.get(f, 100)
            if due <= s["pct"] and f not in names:
                problems.append(ProgressProblem(s["line"], f"{f} is due by {due}% but not listed at {s['pct']}%"))
        for f, no in s["files"]:
            reason = stub_reason(folder / f)
            if reason:
                problems.append(ProgressProblem(no, f"{f}: {reason}"))
        prev = set(names)
    if validation_line is None:
        problems.append(ProgressProblem(0, "no 'Validation:' line after the 100% report"))
    elif validation_line[1].strip() != "Validation: PASS":
        problems.append(ProgressProblem(validation_line[0], "validation did not pass"))
    # de-duplicate stub messages that repeat for every later report
    seen: set[str] = set()
    unique = []
    for p in problems:
        key = p.message
        if key in seen and ":" in key:
            continue
        seen.add(key)
        unique.append(p)
    return unique
