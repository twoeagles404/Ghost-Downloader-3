"""Shared pytest fixtures for the whole test suite.

A single session-scoped QApplication lives here and is reused by every test.
Creating more than one QApplication in a process aborts on macOS, which is what
happened when each test module defined its own fixture and QApplication was
recreated across modules. Keeping it here guarantees exactly one instance.
"""
from __future__ import annotations

import os

import pytest

# Render headlessly by default so the suite runs without a display or GUI.
# An explicit QT_QPA_PLATFORM in the environment still wins.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
