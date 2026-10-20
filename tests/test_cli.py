from conftest import SAMPLES
from prd_agent.cli import main


def test_check_intake_exit_codes(capsys):
    assert main(["check-intake", str(SAMPLES / "smart-plug.pm.intake.json")]) == 0
    assert main(["check-intake", str(SAMPLES / "smart-plug.missing-fields.intake.json")]) == 2
    assert "[missing] hardware.connectivity" in capsys.readouterr().out


def test_generate_refuses_and_validate(tmp_path, capsys):
    out = tmp_path / "o"
    assert main(["generate", str(SAMPLES / "smart-plug.missing-fields.intake.json"), "--out", str(out)]) == 2
    assert not out.exists()
    assert main(["generate", str(SAMPLES / "smart-plug.pm.intake.json"), "--out", str(out)]) == 0
    assert "[PROGRESS 100%] Validation: PASS" in capsys.readouterr().out
    assert main(["validate", str(out)]) == 0
    assert main(["check-progress", str(out)]) == 0


def test_bad_intake_path(tmp_path):
    import pytest

    with pytest.raises(SystemExit) as exc:
        main(["check-intake", str(tmp_path / "nope.json")])
    assert exc.value.code == 3


def test_generate_exit_1_when_validation_fails(tmp_path, monkeypatch):
    import prd_agent.consistency as consistency

    real = consistency.check_folder

    def failing(folder, *a, **k):
        report = real(folder, *a, **k)
        report.differences.append(consistency.Difference("PRD.md", 1, "id_mismatch", "simulated"))
        return report

    monkeypatch.setattr(consistency, "check_folder", failing)
    out = tmp_path / "o"
    assert main(["generate", str(SAMPLES / "smart-plug.pm.intake.json"), "--out", str(out)]) == 1
    assert "Validation: FAIL" in (out / "PROGRESS.md").read_text(encoding="utf-8")


def test_generate_exit_3_on_io_error(tmp_path, monkeypatch, capsys):
    import prd_agent.generate as gen

    def fail_pdf(md, out, title=""):
        from prd_agent.pdf import PdfTextError

        raise PdfTextError("simulated")

    monkeypatch.setattr(gen, "render_markdown_pdf", fail_pdf)
    out = tmp_path / "o"
    assert main(["generate", str(SAMPLES / "smart-plug.pm.intake.json"), "--out", str(out)]) == 3
    assert not out.exists()
    assert "was not changed" in capsys.readouterr().err


def test_chinese_product_name_is_a_pending_item_not_a_crash(tmp_path, capsys):
    import json

    data = json.loads((SAMPLES / "smart-plug.pm.intake.json").read_text(encoding="utf-8"))
    data["hardware"]["product_name"] = "智能插座"
    src = tmp_path / "zh.json"
    src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert main(["check-intake", str(src)]) == 2
    assert main(["generate", str(src), "--out", str(tmp_path / "o")]) == 2
    assert "outside Latin-1" in capsys.readouterr().out
    assert not (tmp_path / "o").exists()
