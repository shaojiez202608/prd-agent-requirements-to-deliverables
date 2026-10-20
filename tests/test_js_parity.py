"""The offline HTML forms run intake/compiler.js; it must match the Python compiler byte for byte."""

import copy
import json
import shutil
import subprocess

import pytest

from conftest import ROOT, load_sample
from prd_agent.prompt import compile_prompt

NODE = shutil.which("node")
RUNNER = """
const c = require(process.argv[1]);
const fs = require('fs');
const schema = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(cases.map(x => c.compilePrompt(x, schema))));
"""


def _cases():
    pm = load_sample("smart-plug.pm.intake.json")
    cases = [pm, load_sample("smart-plug.frontline.intake.json"), load_sample("smart-plug.missing-fields.intake.json"),
             load_sample("smart-plug.pm.v2.intake.json"), [], {}, {"schema_version": 1.0, "variant": ["pm"]}]
    odd = copy.deepcopy(pm)
    odd["business"]["pain_points"] = ["faults_not_alerted", "nope", 3]
    odd["business"]["scene_description"] = "  tabs\tand\nnewlines  INTAKE-END  "
    odd["hardware"]["channels"] = "2.50"
    odd["hardware"]["connectivity"] = True
    p = odd["thing_model"]["properties"]
    p[0]["id"] = "1"
    p[1]["max"] = 1.5e3
    p[1]["step"] = "0.25"
    p[2]["data_type"] = "enum"
    p[2]["enum_values"] = " a , a ,"
    p[3]["interaction"] = "x | y"
    p[4]["name"] = "Zeitschaltuhr äöü \U0001F600"
    p.append("not an object")
    p.append({"id": 2, "identifier": "active_power", "control": "toggle", "access": "R"})
    odd["constraints"]["acceptance_criteria"] = "line one\r\n\r\n  line two  \n"
    cases.append(odd)
    cjk = copy.deepcopy(pm)  # Latin-1 rule applies only to text that reaches the quick-start PDF
    cjk["hardware"]["product_name"] = "智能插座 \U0001F50C"
    cjk["thing_model"]["properties"][0]["interaction"] = "点击切换"
    cjk["business"]["scene_description"] = "家庭用电 <!-- dp-table:end --> */"
    cjk["constraints"]["acceptance_criteria"] = ["ok", "a --> b"]
    cases.append(cjk)
    no_pdf = copy.deepcopy(cjk)
    no_pdf["deliverables"]["outputs"] = ["prd", "panel_spec"]
    cases.append(no_pdf)
    return cases


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_js_and_python_compilers_agree(tmp_path):
    cases = _cases()
    proc = subprocess.run([NODE, "-e", RUNNER, str(ROOT / "intake" / "compiler.js"), str(ROOT / "intake" / "schema.json")],
                          input=json.dumps(cases), capture_output=True, text=True, check=True)
    js = json.loads(proc.stdout)
    for i, (case, js_text) in enumerate(zip(cases, js, strict=True)):
        assert compile_prompt(case) == js_text, f"case {i} differs"
