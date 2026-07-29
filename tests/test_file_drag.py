"""Branch-by-branch tests for startFileDrag platform dispatch and fallback.

Covers:
  - Windows native path success does not trigger the Qt fallback
  - Windows prep-phase failure falls back to Qt (original args passed through)
  - Non-Windows platforms go straight through the Qt path
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.platform import desktop


@pytest.fixture()
def drag(monkeypatch):
    win32 = MagicMock()
    qt = MagicMock()
    monkeypatch.setattr(desktop, "_startFileDragWin32", win32)
    monkeypatch.setattr(desktop, "_startFileDragQt", qt)
    source = MagicMock()
    source.window.return_value.winId.return_value = 42
    return win32, qt, source


class TestStartFileDrag:

    def test_win32_success_skips_qt(self, drag, monkeypatch):
        win32, qt, source = drag
        monkeypatch.setattr(sys, "platform", "win32")
        paths = [Path("C:/dl/a.txt"), Path("C:/dl/b.txt")]

        desktop.startFileDrag(paths, source)

        win32.assert_called_once_with([str(p) for p in paths], 42)
        qt.assert_not_called()

    def test_win32_failure_falls_back_to_qt(self, drag, monkeypatch):
        win32, qt, source = drag
        monkeypatch.setattr(sys, "platform", "win32")
        win32.side_effect = OSError("SHParseDisplayName failed")
        paths = [Path("C:/dl/a.txt")]

        desktop.startFileDrag(paths, source)

        qt.assert_called_once_with(paths, source)

    def test_non_windows_goes_straight_to_qt(self, drag, monkeypatch):
        win32, qt, source = drag
        monkeypatch.setattr(sys, "platform", "linux")
        paths = [Path("/home/dl/a.txt")]

        desktop.startFileDrag(paths, source)

        win32.assert_not_called()
        qt.assert_called_once_with(paths, source)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
