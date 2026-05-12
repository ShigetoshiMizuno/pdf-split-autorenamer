# -*- coding: utf-8 -*-
"""issue #50: GUI に「用語集」入力欄が存在することをテスト（RED フェーズ）

- App に profile_var 属性が存在すること
- _build_ui で「用語集」ラベル・Entry・「参照…」ボタンが作られること
- _on_browse_profile が profile_var をセットすること
- _on_analyze が profile_var の値を run_analyze の profile 引数に渡すこと
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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
        "profile_var": _StringVar(""),
        "force_var": _BooleanVar(False),
        "status_var": _StringVar("待機中"),
        "log": MagicMock(),
        "_input_paths": [],  # issue #48: 複数入力パスリスト
    })
    return app


# ---------------------------------------------------------------------------
# App に profile_var 属性が存在すること
# ---------------------------------------------------------------------------

class TestAppHasProfileVar:
    def test_app_init_creates_profile_var(self):
        """App.__init__ が profile_var を初期化すること（issue #50）"""
        from pdf_split_autorenamer import gui as gui_module
        with patch.object(gui_module.tk.Tk, "__init__", return_value=None), \
             patch.object(gui_module.App, "title"), \
             patch.object(gui_module.App, "geometry"), \
             patch.object(gui_module.App, "minsize"), \
             patch.object(gui_module.App, "_build_ui"), \
             patch.object(gui_module, "tk", MagicMock(
                 StringVar=MagicMock(return_value=_StringVar()),
                 BooleanVar=MagicMock(return_value=_BooleanVar()),
             )):
            app = gui_module.App()
        assert hasattr(app, "profile_var"), "App に profile_var がない (issue #50)"


# ---------------------------------------------------------------------------
# _build_ui に「用語集」ラベルが含まれること
# ---------------------------------------------------------------------------

class TestBuildUiProfileWidget:
    def test_build_ui_has_profile_label(self):
        """_build_ui が「用語集」というラベルを作ること（issue #50）"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()

        label_texts: list[str] = []

        mock_ttk = MagicMock()

        def capture_label(*args, **kwargs):
            text = kwargs.get("text", "")
            label_texts.append(text)
            return MagicMock()

        mock_ttk.Label.side_effect = capture_label
        mock_ttk.LabelFrame.return_value = MagicMock()
        mock_ttk.Frame.return_value = MagicMock()
        mock_ttk.Button.return_value = MagicMock()
        mock_ttk.Entry.return_value = MagicMock()
        mock_ttk.Scrollbar.return_value = MagicMock()
        mock_ttk.Checkbutton.return_value = MagicMock()

        with patch.object(gui_module, "ttk", mock_ttk), \
             patch.object(gui_module, "tk", MagicMock(
                 StringVar=MagicMock(return_value=_StringVar()),
                 BooleanVar=MagicMock(return_value=_BooleanVar()),
                 Text=MagicMock(),
             )), \
             patch("logging.getLogger", return_value=MagicMock()):
            app.profile_var = _StringVar()
            app._split_advanced_var = _BooleanVar()
            app._build_ui()

        assert any("用語集" in t for t in label_texts), \
            f"「用語集」ラベルが _build_ui に存在しない (issue #50). ラベル一覧: {label_texts}"


# ---------------------------------------------------------------------------
# _on_browse_profile: profile_var をセットすること
# ---------------------------------------------------------------------------

class TestOnBrowseProfile:
    def test_browse_profile_sets_profile_var(self):
        """「用語集 参照…」ボタンで TOML を選択すると profile_var がセットされる"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        with patch.object(gui_module.filedialog, "askopenfilename",
                          return_value="/path/to/my_profile.toml"):
            app._on_browse_profile()
        assert app.profile_var.get() == "/path/to/my_profile.toml"

    def test_browse_profile_cancel_keeps_existing(self):
        """「用語集 参照…」キャンセルなら profile_var は変更されない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        app.profile_var.set("/existing.toml")
        with patch.object(gui_module.filedialog, "askopenfilename", return_value=""):
            app._on_browse_profile()
        assert app.profile_var.get() == "/existing.toml"


# ---------------------------------------------------------------------------
# _on_analyze が profile を run_analyze に渡すこと
# ---------------------------------------------------------------------------

class TestOnAnalyzePassesProfile:
    def test_analyze_passes_profile_when_set(self, tmp_path):
        """profile_var に TOML パスが入っていると run_analyze の profile 引数に渡される"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        toml_path = tmp_path / "my.toml"
        toml_path.write_text("[patterns]\n", encoding="utf-8")
        app.profile_var.set(str(toml_path))

        mock_result = {"pages": 0, "groups": 0, "report_html": None, "groups_json": ""}
        captured_kwargs: dict = {}

        def fake_run_analyze(folder, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_result

        with patch.object(app, "_get_inputs", return_value=tmp_path), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status"), \
             patch.object(gui_module._analyze, "run_analyze", side_effect=fake_run_analyze), \
             patch.object(gui_module.messagebox, "showwarning"), \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_analyze()

        assert "profile" in captured_kwargs, \
            "_on_analyze が run_analyze に profile を渡していない (issue #50)"
        assert captured_kwargs["profile"] == toml_path, \
            f"profile の値が一致しない: {captured_kwargs.get('profile')} != {toml_path}"

    def test_analyze_passes_none_profile_when_empty(self, tmp_path):
        """profile_var が空なら run_analyze に profile=None が渡される"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        app.profile_var.set("")

        mock_result = {"pages": 0, "groups": 0, "report_html": None, "groups_json": ""}
        captured_kwargs: dict = {}

        def fake_run_analyze(folder, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_result

        with patch.object(app, "_get_inputs", return_value=tmp_path), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status"), \
             patch.object(gui_module._analyze, "run_analyze", side_effect=fake_run_analyze), \
             patch.object(gui_module.messagebox, "showwarning"), \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_analyze()

        assert captured_kwargs.get("profile") is None, \
            f"profile_var が空のとき profile=None を期待したが: {captured_kwargs.get('profile')}"
