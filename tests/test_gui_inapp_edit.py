# -*- coding: utf-8 -*-
"""_on_inapp_edit (gui.py:299-349) のカバレッジテスト

3ケース:
  1. is_available()=False  → showwarning を出して subprocess を呼ばない
  2. 正常終了 (returncode=0) → "閉じました" がログに出る
  3. 異常終了 (returncode!=0) → "異常終了" がログに出る
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

class _StringVar:
    def __init__(self, value: str = ""):
        self._v = value
    def get(self) -> str:
        return self._v
    def set(self, v: str) -> None:
        self._v = v


class _BooleanVar:
    def __init__(self, value: bool = False):
        self._v = value
    def get(self) -> bool:
        return self._v
    def set(self, v: bool) -> None:
        self._v = v


def _make_app(folder: str = "") -> object:
    from pdf_split_autorenamer import gui as gui_module
    with patch.object(gui_module.App, "__init__", return_value=None):
        app = gui_module.App()
    app.__dict__.update({
        "folder_var": _StringVar(folder),
        "rename_mode_var": _StringVar("split"),
        "force_var": _BooleanVar(False),
        "profile_var": _StringVar(""),
        "status_var": _StringVar("待機中"),
        "log": MagicMock(),
    })
    return app


# ---------------------------------------------------------------------------
# [A-1] is_available()=False → showwarning を出して subprocess を呼ばない
# ---------------------------------------------------------------------------

class TestOnInappEditUnavailable:
    def test_showwarning_when_pywebview_missing(self, tmp_path):
        """pywebview 未導入時は警告ダイアログを出して return する"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        with patch.object(gui_module._inapp, "is_available", return_value=False), \
             patch.object(gui_module.messagebox, "showwarning") as mw, \
             patch("subprocess.Popen") as mpopen:
            app._on_inapp_edit()
        mw.assert_called_once()
        mpopen.assert_not_called()


# ---------------------------------------------------------------------------
# [A-2] 正常終了 (returncode=0)
# ---------------------------------------------------------------------------

class TestOnInappEditSuccess:
    def test_log_close_message_on_success(self, tmp_path):
        """returncode=0 のとき '閉じました' がログに出る"""
        from pdf_split_autorenamer import gui as gui_module

        psar = tmp_path / ".psar"
        psar.mkdir()
        (psar / "report.html").write_text("<html/>", encoding="utf-8")
        app = _make_app(str(tmp_path))
        logged = []

        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0

        with patch.object(gui_module._inapp, "is_available", return_value=True), \
             patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(app, "_log", side_effect=logged.append), \
             patch.object(app, "_set_status"), \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_inapp_edit()

        assert any("閉じました" in m for m in logged)


# ---------------------------------------------------------------------------
# [A-3] 異常終了 (returncode!=0)
# ---------------------------------------------------------------------------

class TestOnInappEditFailure:
    def test_log_error_message_on_nonzero_returncode(self, tmp_path):
        """returncode!=0 のとき '異常終了' がログに出る"""
        from pdf_split_autorenamer import gui as gui_module

        psar = tmp_path / ".psar"
        psar.mkdir()
        (psar / "report.html").write_text("<html/>", encoding="utf-8")
        app = _make_app(str(tmp_path))
        logged = []

        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 1

        with patch.object(gui_module._inapp, "is_available", return_value=True), \
             patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(app, "_log", side_effect=logged.append), \
             patch.object(app, "_set_status"), \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_inapp_edit()

        assert any("異常終了" in m for m in logged)
