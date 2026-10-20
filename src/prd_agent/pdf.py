"""Minimal Markdown -> PDF renderer for the quick-start guide.

Pure Python (fpdf2), no browser, no LaTeX, no network. Supports the Markdown
subset used by the template: headings, paragraphs, bullet and numbered lists,
pipe tables, fenced code blocks and HTML comments (dropped). The SHA-256 of the
source Markdown is stored in the PDF Keywords field so the consistency checker
can tell whether the PDF is stale.

Built-in PDF fonts only cover Latin-1. Text outside Latin-1 raises PdfTextError
instead of silently dropping characters; see docs/architecture.md (limitations).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from pathlib import Path

from fpdf import FPDF

FIXED_DATE = dt.datetime(2000, 1, 1, tzinfo=dt.UTC)  # deterministic output
KEY_PREFIX = "source-sha256:"


class PdfTextError(ValueError):
    pass


def _inline(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    return text.replace("\\|", "|")


def _check_latin1(md: str) -> None:
    for no, line in enumerate(md.splitlines(), 1):
        for ch in line:
            if ord(ch) > 0xFF:
                raise PdfTextError(f"quick-start.md:{no}: character {ch!r} is outside Latin-1; "
                                   "the built-in PDF font cannot render it")


def _cells(line: str) -> list[str]:
    s = line.strip().strip("|")
    return [_inline(c.strip()) for c in re.split(r"(?<!\\)\|", s)]


def render_markdown_pdf(md: str, out: Path, title: str = "") -> None:
    _check_latin1(md)
    pdf = FPDF(format="A4")
    pdf.set_creation_date(FIXED_DATE)
    pdf.set_title(title)
    pdf.set_keywords(KEY_PREFIX + hashlib.sha256(md.encode("utf-8")).hexdigest())
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    lines = re.sub(r"<!--.*?-->", "", md, flags=re.S).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            i += 1
            pdf.set_font("Courier", size=9)
            while i < len(lines) and not lines[i].strip().startswith("```"):
                pdf.multi_cell(width, 4.5, lines[i] or " ", new_x="LMARGIN", new_y="NEXT")
                i += 1
            i += 1
            pdf.ln(2)
            continue
        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.fullmatch(r"\|?[\s:|-]+\|?", lines[i].strip()):
                    rows.append(_cells(lines[i]))
                i += 1
            ncol = max(len(r) for r in rows)
            pdf.set_font("Helvetica", size=8)
            with pdf.table(width=width, first_row_as_headings=True, line_height=4.5, text_align="LEFT") as table:
                for row in rows:
                    trow = table.row()
                    for c in row + [""] * (ncol - len(row)):
                        trow.cell(c)
            pdf.ln(2)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            pdf.ln(2)
            pdf.set_font("Helvetica", style="B", size={1: 16, 2: 13}.get(level, 11))
            pdf.multi_cell(width, 7, _inline(m.group(2)), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            i += 1
            continue
        pdf.set_font("Helvetica", size=10)
        if not stripped:
            pdf.ln(2)
        elif re.match(r"^(\s*)[-*]\s+", line):
            indent = len(re.match(r"^(\s*)", line).group(1))
            pdf.set_x(pdf.l_margin + 4 + indent * 2)
            pdf.multi_cell(width - 4 - indent * 2, 5, "- " + _inline(re.sub(r"^\s*[-*]\s+", "", line)),
                           new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.multi_cell(width, 5, _inline(stripped), new_x="LMARGIN", new_y="NEXT")
        i += 1
    Path(out).write_bytes(bytes(pdf.output()))


def read_source_hash(pdf_path: Path) -> str | None:
    """Return the source-sha256 stored in the PDF Keywords field, if any."""
    data = Path(pdf_path).read_bytes()
    m = re.search(rb"/Keywords\s*\(" + re.escape(KEY_PREFIX.encode()) + rb"([0-9a-f]{64})\)", data)
    if m:
        return m.group(1).decode()
    m = re.search(rb"/Keywords\s*<([0-9A-Fa-f]+)>", data)
    if m:
        raw = bytes.fromhex(m.group(1).decode())
        text = raw[2:].decode("utf-16-be") if raw.startswith(b"\xfe\xff") else raw.decode("latin-1")
        if text.startswith(KEY_PREFIX):
            return text[len(KEY_PREFIX):]
    return None
