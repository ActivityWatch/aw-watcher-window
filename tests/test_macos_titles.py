"""Compile and run the production Swift title path against offline AX fixtures."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS Accessibility frameworks required")
def test_swift_title_enrichment(tmp_path):
    # On macOS, missing swiftc is a failure, not a skipped regression suite.
    compiler = shutil.which("swiftc")
    assert compiler, "Install Xcode Command Line Tools to test the macOS helper"
    root = Path(__file__).resolve().parents[1]
    source = tmp_path / "main.swift"
    source.write_text(
        (root / "aw_watcher_window/macos.swift").read_text()
        + "\n" + (root / "tests/swift/macos_title_tests.swift").read_text(),
        encoding="utf-8",
    )
    binary = tmp_path / "title-tests"
    build = subprocess.run(
        [compiler, "-D", "AW_TITLE_TESTS", "-target",
         f"{platform.machine()}-apple-macosx12.0", str(source), "-o", str(binary)],
        capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run(
        [str(binary), str(root / "tests/fixtures/macos_titles.json")],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "LOG_LEVEL": "ERROR"},
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "Swift title tests passed" in run.stdout, run.stdout
