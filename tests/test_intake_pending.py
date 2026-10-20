"""FR-8: insufficient input is detected and listed before generation."""

from conftest import load_sample
from prd_agent.intake import find_pending


def paths(items):
    return [(p.code, p.path) for p in items]


def test_complete_pm_intake_has_no_pending_items(pm_intake):
    assert find_pending(pm_intake) == []


def test_missing_fields_sample_lists_each_problem():
    got = paths(find_pending(load_sample("smart-plug.missing-fields.intake.json")))
    assert got == [
        ("missing", "hardware.connectivity"),
        ("missing", "thing_model.properties[1].unit"),
        ("conflict", "thing_model.properties[5].id"),
        ("missing", "app.provisioning"),
    ]


def test_frontline_intake_is_insufficient_by_design():
    got = paths(find_pending(load_sample("smart-plug.frontline.intake.json")))
    assert ("missing", "hardware.architecture_mode") in got
    assert ("missing", "thing_model.properties[0].id") in got
    assert ("missing", "thing_model.properties[0].identifier") in got
    assert ("missing", "constraints.offline_behavior") in got


def test_invalid_enum_and_pattern(pm_intake):
    pm_intake["business"]["scene_category"] = "space_station"
    pm_intake["thing_model"]["properties"][0]["identifier"] = "Power-Switch"
    got = paths(find_pending(pm_intake))
    assert ("invalid", "business.scene_category") in got
    assert ("invalid", "thing_model.properties[0].identifier") in got


def test_numeric_rules(pm_intake):
    p = pm_intake["thing_model"]["properties"][5]
    p["min"], p["max"], p["step"] = 10, 5, 0
    got = paths(find_pending(pm_intake))
    assert ("conflict", "thing_model.properties[5].max") in got
    assert ("conflict", "thing_model.properties[5].step") in got


def test_int_range_must_be_integer(pm_intake):
    pm_intake["thing_model"]["properties"][5]["step"] = 0.5
    assert ("conflict", "thing_model.properties[5].step") in paths(find_pending(pm_intake))


def test_enum_and_string_conditional_fields(pm_intake):
    props = pm_intake["thing_model"]["properties"]
    props[2]["data_type"] = "enum"  # alarm_indicator accepts enum
    props[4].pop("max_length")
    got = paths(find_pending(pm_intake))
    assert ("missing", "thing_model.properties[2].enum_values") in got
    assert ("missing", "thing_model.properties[4].max_length") in got


def test_control_access_conflict(pm_intake):
    pm_intake["thing_model"]["properties"][0]["access"] = "R"  # toggle needs RW/W
    items = find_pending(pm_intake)
    assert ("conflict", "thing_model.properties[0].control") in paths(items)
    assert "expects access RW/W" in items[0].message


def test_duplicate_identifier(pm_intake):
    pm_intake["thing_model"]["properties"][1]["identifier"] = "power_switch"
    assert ("conflict", "thing_model.properties[1].identifier") in paths(find_pending(pm_intake))


def test_numbers_as_strings_are_accepted(pm_intake):
    p = pm_intake["thing_model"]["properties"][5]
    p["id"], p["min"], p["max"] = "6", "1", "60"
    assert find_pending(pm_intake) == []


def test_non_object_and_wrong_version():
    assert paths(find_pending([])) == [("invalid", "(root)")]
    got = paths(find_pending({"schema_version": "0.9", "variant": "x"}))
    assert got[:2] == [("invalid", "schema_version"), ("invalid", "variant")]


def test_empty_property_list(pm_intake):
    pm_intake["thing_model"]["properties"] = []
    assert ("missing", "thing_model.properties") in paths(find_pending(pm_intake))


def test_non_latin1_text_blocks_generation_when_pdf_requested(pm_intake):
    pm_intake["hardware"]["product_name"] = "智能插座"
    pm_intake["thing_model"]["properties"][4]["name"] = "定时"
    got = paths(find_pending(pm_intake))
    assert ("invalid", "hardware.product_name") in got
    assert ("invalid", "thing_model.properties[4].name") in got
    # Without the quick-start PDF the same text is allowed.
    pm_intake["deliverables"]["outputs"] = ["thing_model", "prd"]
    assert find_pending(pm_intake) == []


def test_latin1_accented_text_is_fine(pm_intake):
    pm_intake["hardware"]["product_name"] = "Steckdose Größe"
    assert find_pending(pm_intake) == []


def test_reserved_markers_are_rejected(pm_intake):
    pm_intake["business"]["scene_description"] = "text <!-- dp-table:begin --> more"
    pm_intake["hardware"]["product_name"] = "Plug */ int x;"
    pm_intake["constraints"]["acceptance_criteria"] = ["fine", "a --> b"]
    items = find_pending(pm_intake)
    got = paths(items)
    assert ("invalid", "business.scene_description") in got
    assert ("invalid", "hardware.product_name") in got
    assert ("invalid", "constraints.acceptance_criteria") in got
    assert any("must not contain */" in p.message for p in items)


def test_outputs_must_include_thing_model(pm_intake):
    pm_intake["deliverables"]["outputs"] = ["prd", "quick_start"]
    items = find_pending(pm_intake)
    assert paths(items) == [("missing", "deliverables.outputs")]
    assert "must include thing_model" in items[0].message
