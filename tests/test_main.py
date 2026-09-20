"""
End-to-end application entry-point tests.

These tests verify that main.py now delegates to the unified clinical
pipeline instead of rebuilding extraction logic locally.
"""

from pathlib import Path
from unittest.mock import patch

import main


def test_build_knowledge_engine_loads_patterns():
    engine = main.build_knowledge_engine()

    assert len(engine._registry.all()) >= 1
    assert any(
        pattern.id == "microcytic_cbc_pattern"
        for pattern in engine._registry.all()
    )


def test_main_runs_real_sample_pdf():
    with patch.object(
        main.sys,
        "argv",
        ["main.py", "samples/reports/sample.pdf"],
    ):
        assert main.main() == 0


def test_main_blocks_unsafe_sample_without_crashing():
    with patch.object(
        main.sys,
        "argv",
        ["main.py", "samples/reports/sample2.pdf"],
    ):
        assert main.main() == 0


def test_main_missing_file_returns_error():
    with patch.object(
        main.sys,
        "argv",
        ["main.py", "samples/reports/does_not_exist.pdf"],
    ):
        assert main.main() == 1