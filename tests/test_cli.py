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
