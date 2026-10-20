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
