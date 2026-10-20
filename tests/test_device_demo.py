"""The device skeleton compiles as C99 with warnings as errors."""

import shutil
import subprocess

import pytest

CC = shutil.which("cc")


@pytest.mark.skipif(CC is None, reason="no C compiler")
def test_skeleton_compiles(generated, tmp_path):
    demo = generated / "device-demo"
    for src in ("app_main.c", "hal_port_host.c"):
        subprocess.run([CC, "-std=c99", "-Wall", "-Wextra", "-Werror", "-c", str(demo / src),
                        "-o", str(tmp_path / (src + ".o"))], check=True, capture_output=True)
