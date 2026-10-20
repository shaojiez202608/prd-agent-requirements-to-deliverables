"""Acceptance 1 and 3: six deliverables from the sample; nothing generated when input is insufficient."""

import filecmp

import pytest

from conftest import ROOT, load_sample
from prd_agent.consistency import check_folder
from prd_agent.generate import InsufficientInput, fill, generate
from prd_agent.progress import check_progress

SIX = ["thing-model.json", "architecture.mmd", "quick-start.pdf", "PRD.md", "panel-spec.md", "device-demo/app_main.c"]


def test_sample_generates_six_deliverables_and_validates(generated):
    for rel in SIX + ["quick-start.md", "panel-preview.html", "device-demo/dp_table.h", "PROGRESS.md"]:
        assert (generated / rel).is_file(), rel
    report = check_folder(generated)
    assert report.ok, report.render_text()
    assert report.reference_count == 6
    assert check_progress(generated) == []


def test_insufficient_input_generates_nothing(tmp_path):
    out = tmp_path / "out"
    with pytest.raises(InsufficientInput) as exc:
        generate(load_sample("smart-plug.missing-fields.intake.json"), out)
    assert len(exc.value.pending) == 4
    assert not out.exists()


def test_frontline_intake_generates_nothing(tmp_path):
    with pytest.raises(InsufficientInput):
        generate(load_sample("smart-plug.frontline.intake.json"), tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_generation_is_deterministic(tmp_path, pm_intake):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(pm_intake, a)
    generate(pm_intake, b)
    cmp = filecmp.dircmp(a, b)
    assert not cmp.diff_files and not cmp.left_only and not cmp.right_only
    assert (a / "quick-start.pdf").read_bytes() == (b / "quick-start.pdf").read_bytes()


def test_committed_example_matches_generator(generated):
    example = ROOT / "examples" / "smart-plug"
    for path in sorted(p for p in generated.rglob("*") if p.is_file()):
        rel = path.relative_to(generated)
        assert (example / rel).read_bytes() == path.read_bytes(), f"examples/smart-plug/{rel} is stale"


def test_subset_of_deliverables(tmp_path, pm_intake):
    pm_intake["deliverables"]["outputs"] = ["thing_model", "prd"]
    out = tmp_path / "out"
    generate(pm_intake, out)
    assert sorted(p.name for p in out.iterdir()) == ["PRD.md", "PROGRESS.md", "thing-model.json"]
    assert check_folder(out).ok
    assert check_progress(out) == []


def test_open_items_instead_of_guesses(generated):
    prd = (generated / "PRD.md").read_text(encoding="utf-8")
    assert "Module selection is to be decided" in prd
    assert "Encoding of string property ID 5 `timer_task`" in prd


def test_template_placeholder_without_value_fails():
    with pytest.raises(KeyError):
        fill("{{known}} {{unknown}}", {"known": "x"})


def test_ids_annotated_on_panel_preview(generated):
    html = (generated / "panel-preview.html").read_text(encoding="utf-8")
    for i in range(1, 7):
        assert f'data-dp-id="{i}"' in html
        assert f'<span class="dp">ID {i} |' in html
