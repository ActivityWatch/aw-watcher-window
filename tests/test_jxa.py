"""Exercise JXA control flow with stubs; native macOS API checks remain manual."""

from pathlib import Path
import shutil
import subprocess

import pytest


def test_jxa_fallbacks():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the JXA control-flow harness")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            node,
            str(root / "tests" / "jxa_harness.js"),
            str(root / "aw_watcher_window" / "printAppStatus.jxa"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
