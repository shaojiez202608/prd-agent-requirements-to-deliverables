import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "sample-data"


def load_sample(name: str) -> dict:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture
def pm_intake() -> dict:
    return copy.deepcopy(load_sample("smart-plug.pm.intake.json"))


@pytest.fixture
def generated(tmp_path, pm_intake) -> Path:
    from prd_agent.generate import generate

    out = tmp_path / "out"
    generate(pm_intake, out)
    return out
