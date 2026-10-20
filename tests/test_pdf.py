import pytest

from prd_agent.pdf import PdfTextError, read_source_hash, render_markdown_pdf


def test_pdf_has_source_hash(tmp_path):
    import hashlib

    md = "# Title\n\nText line.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```\ncode\n```\n- item\n"
    out = tmp_path / "x.pdf"
    render_markdown_pdf(md, out, title="t")
    assert out.read_bytes().startswith(b"%PDF-")
    assert read_source_hash(out) == hashlib.sha256(md.encode()).hexdigest()


def test_non_latin1_text_is_rejected_with_line(tmp_path):
    with pytest.raises(PdfTextError, match="quick-start.md:3"):
        render_markdown_pdf("# T\n\n智能插座\n", tmp_path / "x.pdf")


def test_pdf_without_hash(tmp_path):
    p = tmp_path / "y.pdf"
    p.write_bytes(b"%PDF-1.4\n%%EOF\n")
    assert read_source_hash(p) is None
