# -*- coding: utf-8 -*-
"""gui.py プロファイル TOML 選択機能のテスト

TDD: RED フェーズ — これらのテストは実装前に書かれている。

Tkinter は headless / Tcl インタープリタなしでは動かないため、
App.__init__ 全体をモックし、属性だけを手動で初期化する軽量インスタンスを使う。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 軽量 StringVar / BooleanVar スタブ
# ---------------------------------------------------------------------------

class _StringVar:
    """tk.StringVar の最小スタブ（Tcl 不要）"""
    def __init__(self, value: str = ""):
        self._v = value

    def get(self) -> str:
        return self._v

    def set(self, v: str) -> None:
        self._v = v


class _BooleanVar:
    """tk.BooleanVar の最小スタブ（Tcl 不要）"""
    def __init__(self, value: bool = False):
        self._v = value

    def get(self) -> bool:
        return self._v

    def set(self, v: bool) -> None:
        self._v = v


# ---------------------------------------------------------------------------
# App インスタンスを「Tkinter なし」で構築するファクトリ
# ---------------------------------------------------------------------------

def _make_app(initial_folder: str = "") -> object:
    """App.__init__ を丸ごとモックし、テスト用属性だけをセットしたインスタンスを返す。

    Tcl / Tkinter ウィジェットを一切起動しないため headless 環境でも動く。
    """
    from pdf_split_autorenamer import gui as gui_module

    # App.__init__ を無効化してインスタンスを生成
    with patch.object(gui_module.App, "__init__", return_value=None):
        app = gui_module.App()

    # App.__init__ が本来セットするはずの属性をスタブで手動注入
    app.__dict__["folder_var"] = _StringVar(initial_folder)
    app.__dict__["rename_mode_var"] = _StringVar("split")
    app.__dict__["force_var"] = _BooleanVar(False)
    # profile_var は実装前は存在しないはずなので注入しない
    # （TestProfileVarExists で存在チェックするため）

    # _build_ui が設定するウィジェット類もスタブで注入
    app.__dict__["status_var"] = _StringVar("待機中")
    app.__dict__["log"] = MagicMock()

    return app


# ---------------------------------------------------------------------------
# テスト: profile_var の存在
# ---------------------------------------------------------------------------

class TestProfileVarExists:
    """App.__init__ で profile_var が生成されること"""

    def test_profile_var_is_created(self):
        """実際の App.__init__ を走らせたとき profile_var 属性が作られる"""
        from pdf_split_autorenamer import gui as gui_module

        # __init__ の StringVar / BooleanVar をスタブに差し替えて実行
        with (
            patch.object(gui_module.tk.Tk, "__init__", return_value=None),
            patch("tkinter.Tk.title"),
            patch("tkinter.Tk.geometry"),
            patch("tkinter.Tk.minsize"),
            patch.object(gui_module.tk, "StringVar", side_effect=lambda value="": _StringVar(value)),
            patch.object(gui_module.tk, "BooleanVar", side_effect=lambda value=False: _BooleanVar(value)),
            patch.object(gui_module.App, "_build_ui", return_value=None),
        ):
            with patch.object(gui_module.App, "__init__",
                               wraps=gui_module.App.__init__) as wrapped_init:
                app = object.__new__(gui_module.App)
                # title/geometry/minsize を後付けでモック（インスタンスメソッド）
                app.__dict__["title"] = MagicMock()
                app.__dict__["geometry"] = MagicMock()
                app.__dict__["minsize"] = MagicMock()
                gui_module.App.__init__(app)

        assert "profile_var" in app.__dict__, (
            f"App に profile_var 属性がない。現在の属性: {list(app.__dict__.keys())}"
        )

    def test_profile_var_default_is_empty(self):
        """profile_var のデフォルト値は空文字列（_make_app 経由で確認）

        実装後は _make_app が profile_var を生成するようになるので
        その値が空であることを確認する。
        """
        from pdf_split_autorenamer import gui as gui_module

        with (
            patch.object(gui_module.tk.Tk, "__init__", return_value=None),
            patch.object(gui_module.tk, "StringVar", side_effect=lambda value="": _StringVar(value)),
            patch.object(gui_module.tk, "BooleanVar", side_effect=lambda value=False: _BooleanVar(value)),
            patch.object(gui_module.App, "_build_ui", return_value=None),
        ):
            app = object.__new__(gui_module.App)
            app.__dict__["title"] = MagicMock()
            app.__dict__["geometry"] = MagicMock()
            app.__dict__["minsize"] = MagicMock()
            gui_module.App.__init__(app)

        # profile_var が存在する前提で値を確認
        if "profile_var" not in app.__dict__:
            # RED フェーズ: まだ実装がないので profile_var がない → テスト失敗
            assert False, "profile_var が存在しない"
        assert app.__dict__["profile_var"].get() == ""


# ---------------------------------------------------------------------------
# テスト: _on_browse_profile メソッド
# ---------------------------------------------------------------------------

class TestOnBrowseProfileMethod:
    """_on_browse_profile メソッドが存在し、filedialog を呼ぶこと"""

    def test_method_exists(self):
        """App クラスに _on_browse_profile メソッドがある"""
        from pdf_split_autorenamer.gui import App
        assert callable(getattr(App, "_on_browse_profile", None)), (
            "App に _on_browse_profile メソッドがない"
        )

    def test_browse_sets_profile_var(self):
        """filedialog でファイルを選択すると profile_var に設定される"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        stub = _StringVar()
        app.__dict__["profile_var"] = stub

        with patch.object(gui_module.filedialog, "askopenfilename",
                          return_value="/path/to/profile.toml"):
            app._on_browse_profile()

        assert stub.get() == "/path/to/profile.toml"

    def test_browse_cancel_empty_keeps_existing(self):
        """キャンセル（空文字返却）のとき profile_var は変更されない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        stub = _StringVar("/existing/profile.toml")
        app.__dict__["profile_var"] = stub

        with patch.object(gui_module.filedialog, "askopenfilename", return_value=""):
            app._on_browse_profile()

        assert stub.get() == "/existing/profile.toml"

    def test_browse_cancel_none_keeps_existing(self):
        """キャンセルで None が返ったとき profile_var は変更されない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        stub = _StringVar("/existing/profile.toml")
        app.__dict__["profile_var"] = stub

        with patch.object(gui_module.filedialog, "askopenfilename", return_value=None):
            app._on_browse_profile()

        assert stub.get() == "/existing/profile.toml"


# ---------------------------------------------------------------------------
# テスト: _on_rename が profile= を run_rename に渡すこと
# ---------------------------------------------------------------------------

class TestOnRenamePassesProfile:
    """_on_rename が profile_var の値を run_rename の profile= 引数に渡すこと"""

    def _call_dry(self, profile_path: str) -> "Path | None":
        """dry-run (_on_rename(apply_=False)) を呼び、run_rename に渡された profile を返す"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("/tmp/folder")

        # スタブで属性を上書き
        app.__dict__["folder_var"] = _StringVar("/tmp/folder")
        app.__dict__["rename_mode_var"] = _StringVar("split")
        app.__dict__["profile_var"] = _StringVar(profile_path)

        captured: dict = {}

        def fake_run_rename(folder, mode="split", apply=False, profile=None, **kw):
            captured["profile"] = profile
            return {"targets": 0, "actions": [], "applied": 0}

        with (
            patch.object(gui_module._rename, "run_rename", side_effect=fake_run_rename),
            patch.object(app, "_get_folder", return_value=Path("/tmp/folder")),
            patch.object(app, "_log"),
            patch.object(app, "_set_status"),
            patch.object(app, "_run_async",
                         side_effect=lambda fn, cb=None: (cb(fn()) if cb else fn())),
        ):
            app._on_rename(apply_=False)

        return captured.get("profile")

    def test_dry_run_no_profile(self):
        """profile_var が空のとき profile=None が渡される"""
        assert self._call_dry("") is None

    def test_dry_run_with_profile(self):
        """profile_var にパスがあるとき profile=Path(...) が渡される"""
        assert self._call_dry("/path/to/profile.toml") == Path("/path/to/profile.toml")

    def _call_apply_preview(self, profile_path: str) -> "Path | None":
        """apply=True の確認ダイアログ前の dry-run プレビューで渡された profile を返す"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("/tmp/folder")

        app.__dict__["folder_var"] = _StringVar("/tmp/folder")
        app.__dict__["rename_mode_var"] = _StringVar("split")
        app.__dict__["profile_var"] = _StringVar(profile_path)

        captured: dict = {}

        def fake_run_rename(folder, mode="split", apply=False, profile=None, **kw):
            captured["profile"] = profile
            return {"targets": 0, "actions": [], "applied": 0}

        with (
            patch.object(gui_module._rename, "run_rename", side_effect=fake_run_rename),
            patch.object(app, "_get_folder", return_value=Path("/tmp/folder")),
            patch.object(app, "_log"),
            patch.object(app, "_set_status"),
            patch.object(gui_module.messagebox, "askyesno", return_value=False),
            patch.object(app, "_run_async",
                         side_effect=lambda fn, cb=None: (cb(fn()) if cb else fn())),
        ):
            app._on_rename(apply_=True)

        return captured.get("profile")

    def test_apply_preview_with_profile(self):
        """apply=True のプレビュー dry-run でも profile が渡される"""
        assert self._call_apply_preview("/path/to/profile.toml") == Path("/path/to/profile.toml")

    def test_apply_preview_no_profile(self):
        """apply=True かつ profile 未選択のとき profile=None"""
        assert self._call_apply_preview("") is None
