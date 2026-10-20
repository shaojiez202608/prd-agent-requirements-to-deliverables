"""FR-10: version change tracking between thing model versions."""

import copy

from conftest import load_sample
from prd_agent.changes import diff_models, render_changes
from prd_agent.thing_model import build_thing_model


def test_v1_to_v2_changes():
    v1 = build_thing_model(load_sample("smart-plug.pm.intake.json"))
    v2 = build_thing_model(load_sample("smart-plug.pm.v2.intake.json"))
    changes = diff_models(v1, v2)
    assert [(c.id, c.kind, c.breaking) for c in changes] == [(6, "changed", False), (7, "added", False)]
    assert "max 60 -> 120" in changes[0].detail
    assert "0 breaking" in render_changes(changes)


def test_breaking_changes():
    v1 = build_thing_model(load_sample("smart-plug.pm.intake.json"))
    v2 = copy.deepcopy(v1)
    v2["properties"] = [p for p in v2["properties"] if p["id"] != 3]
    v2["properties"][0]["identifier"] = "relay"
    v2["properties"][1]["access"] = "W"
    v2["properties"][-1]["data_type"]["min"] = 5
    by = {(c.id, c.detail.split()[0]): c.breaking for c in diff_models(v1, v2)}
    assert by[(3, "overload_alarm")] is True
    assert by[(1, "identifier")] is True
    assert by[(2, "access")] is True
    assert by[(6, "min")] is True


def test_no_changes():
    v1 = build_thing_model(load_sample("smart-plug.pm.intake.json"))
    assert diff_models(v1, copy.deepcopy(v1)) == []
    assert "No changes" in render_changes([])


def _enum_model(values):
    return {"properties": [{"id": 1, "identifier": "mode", "access": "RW", "name": "Mode",
                            "data_type": {"type": "enum", "values": values}, "panel": {}}]}


def test_enum_order_is_part_of_the_contract():
    assert diff_models(_enum_model(["a", "b"]), _enum_model(["b", "a"]))[0].breaking is True
    assert diff_models(_enum_model(["a", "b"]), _enum_model(["a", "c", "b"]))[0].breaking is True
    assert diff_models(_enum_model(["a", "b"]), _enum_model(["a", "b", "c"]))[0].breaking is False


def test_duplicate_ids_are_rejected(tmp_path):
    import json

    import pytest

    from prd_agent.cli import main

    dup = _enum_model(["a", "b"])
    dup["properties"].append(dict(dup["properties"][0], identifier="other"))
    with pytest.raises(ValueError, match="duplicate property ID 1"):
        diff_models(dup, _enum_model(["a", "b"]))
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    old.write_text(json.dumps(dup), encoding="utf-8")
    new.write_text(json.dumps(_enum_model(["a", "b"])), encoding="utf-8")
    assert main(["diff-model", str(old), str(new)]) == 3
