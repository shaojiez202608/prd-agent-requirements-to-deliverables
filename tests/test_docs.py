"""Documentation and repository hygiene checks."""

import re
import subprocess

from conftest import ROOT


def _sections(name):
    return [ln for ln in (ROOT / name).read_text(encoding="utf-8").splitlines() if ln.startswith("## ")]


def test_readmes_have_the_same_sections():
    assert len(_sections("README.md")) == len(_sections("README.zh-CN.md"))


def test_readmes_list_the_same_commands():
    from prd_agent.cli import build_parser

    sub = next(a for a in build_parser()._actions if a.dest == "cmd")
    cli = set(sub.choices)

    def commands(name):
        rows = re.findall(r"^\| `([a-z-]+)[ `]", (ROOT / name).read_text(encoding="utf-8"), flags=re.M)
        return [r for r in rows if r in cli]

    en = commands("README.md")
    assert en == commands("README.zh-CN.md")
    assert set(en) == cli


def test_no_internal_names_or_local_paths_in_tracked_files():
    pattern = re.compile(r"\b[Tt][Ll][Ii]\b|[Tt][Ll][Ii][-_]|T" + r"LI|/" + r"Users/")
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    hits = []
    for rel in files:
        path = ROOT / rel
        if path.suffix == ".pdf" or not path.is_file():
            continue
        for no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{rel}:{no}")
    assert hits == []


def test_no_account_ids_in_tracked_files():
    """12-digit numbers are only allowed as the documentation placeholder 111122223333."""
    allowed = {"111122223333"}
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    hits = []
    for rel in files:
        path = ROOT / rel
        if path.suffix == ".pdf" or rel == "uv.lock" or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"(?<![0-9])[0-9]{12}(?![0-9])", text):
            if m.group(0) not in allowed:
                hits.append(f"{rel}: {m.group(0)[:2]}...")
    assert hits == []
