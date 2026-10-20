"""FR-4: staged progress protocol checks."""

from prd_agent.progress import check_progress


def msgs(folder):
    return [p.message for p in check_progress(folder)]


def test_generated_log_passes(generated):
    assert check_progress(generated) == []


def test_missing_report_is_detected(generated):
    log = generated / "PROGRESS.md"
    text = log.read_text(encoding="utf-8")
    start = text.index("## [PROGRESS 70%]")
    end = text.index("## [PROGRESS 90%]")
    log.write_text(text[:start] + text[end:], encoding="utf-8")
    assert any("expected reports at" in m for m in msgs(generated))


def test_skeleton_file_is_detected(generated):
    (generated / "PRD.md").write_text("# PRD\n\n## 1. Background\n\nTODO\n", encoding="utf-8")
    assert any(m.startswith("PRD.md: markdown has fewer than 5 content lines") for m in msgs(generated))


def test_claimed_file_that_does_not_exist(generated):
    (generated / "panel-preview.html").unlink()
    assert "panel-preview.html: file does not exist" in msgs(generated)


def test_file_due_but_not_listed(generated):
    log = generated / "PROGRESS.md"
    text = log.read_text(encoding="utf-8")
    head, tail = text.split("## [PROGRESS 45%]", 1)
    tail = tail.replace("- architecture.mmd\n", "", 1)
    log.write_text(head + "## [PROGRESS 45%]" + tail, encoding="utf-8")
    assert any("architecture.mmd is due by 45% but not listed at 45%" in m for m in msgs(generated))


def test_dropped_file_and_failed_validation(generated):
    log = generated / "PROGRESS.md"
    text = log.read_text(encoding="utf-8")
    i = text.index("## [PROGRESS 100%]")
    tail = text[i:].replace("- thing-model.json\n", "", 1).replace("Validation: PASS", "Validation: FAIL")
    log.write_text(text[:i] + tail, encoding="utf-8")
    m = msgs(generated)
    assert any("drops files listed earlier: thing-model.json" in x for x in m)
    assert "validation did not pass" in m


def test_no_log(tmp_path):
    assert msgs(tmp_path) == ["PROGRESS.md not found"]
