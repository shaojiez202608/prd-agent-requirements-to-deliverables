"""Safety guard of the cleanup script and the sandbox naming convention."""

import json
import subprocess
import sys

from conftest import ROOT


def test_empty_buckets_script_refuses_foreign_stack_names():
    # Refuses before any AWS call: the name does not start with the default sandbox prefix.
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "empty_stack_buckets.py"), "someone-elses-stack"],
                          capture_output=True, text=True)
    assert proc.returncode == 3
    assert "must start with proto-prd-" in proc.stderr


def test_sandbox_stack_uses_project_prefix():
    cfg = json.loads((ROOT / "infra" / "config" / "sandbox.json").read_text(encoding="utf-8"))
    assert cfg["stack_name"].startswith("proto-prd-")
    script = (ROOT / "scripts" / "residue_check.sh").read_text(encoding="utf-8")
    assert 'PREFIX="${1:-proto-prd-}"' in script
