"""FR-1: two offline intake pages, built from the schema, no network access."""

import re

from conftest import ROOT
from prd_agent.forms import build_form


def test_committed_forms_are_current():
    for variant in ("frontline", "pm"):
        assert (ROOT / "intake" / f"{variant}.html").read_text(encoding="utf-8") == build_form(variant)


def test_forms_are_self_contained():
    for variant in ("frontline", "pm"):
        html = build_form(variant)
        assert "default-src 'none'" in html
        assert not re.search(r"""(src|href)\s*=\s*["']https?:""", html)
        assert "fetch(" not in html and "XMLHttpRequest" not in html
        assert "{{" not in html.replace("{{name}}", "")
        assert f'var VARIANT = "{variant}";' in html


def test_forms_differ_by_variant():
    assert build_form("frontline") != build_form("pm")
