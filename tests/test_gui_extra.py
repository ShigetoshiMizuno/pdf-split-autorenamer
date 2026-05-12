# -*- coding: utf-8 -*-
"""gui.py の追加カバレッジテスト（Tkinter を最大限モック）

対象:
- _TextHandler._append
- App._build_ui
- App._on_browse / _get_folder
- App._log / _set_status / _run_async
- App._build_split_summary (static)
- App._on_analyze early return
- App._on_open_report
- App._on_split early return
- main / __main__ guard

issue #40: Step 3 「自動リネーム」を Step 2 分割に統合したため、
_on_rename / _build_rename_summary / _on_browse_profile / profile_var /
rename_mode_var 関連のテストは削除。
"""
from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# スタブ (test_gui_profile.py と共通)
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
        "profile_var": _StringVar(""),
        "force_var": _BooleanVar(False),
        "status_var": _StringVar("待機中"),
        "log": MagicMock(),
    })
    return app


# ---------------------------------------------------------------------------
# _TextHandler._append  (lines 37-38)
# ---------------------------------------------------------------------------

class TestTextHandlerAppend:
    def test_append_inserts_and_scrolls(self):
        """_append が insert → see を呼ぶこと"""
        from pdf_split_autorenamer.gui import _TextHandler
        mock_widget = MagicMock()
        handler = _TextHandler(mock_widget)
        handler._append("hello world")
        mock_widget.insert.assert_called_once_with("end", "hello world\n")
        mock_widget.see.assert_called_once_with("end")


# ---------------------------------------------------------------------------
# _build_ui  (lines 56-128)
# ---------------------------------------------------------------------------

class TestBuildUi:
    def test_build_ui_runs_without_error(self):
        """ttk / tk をモックして _build_ui がクラッシュしないこと (lines 56-128)"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        with patch.object(gui_module, "ttk", MagicMock()), \
             patch.object(gui_module, "tk", MagicMock()), \
             patch("logging.getLogger", return_value=MagicMock()):
            app._build_ui()


# ---------------------------------------------------------------------------
# App.__init__  (Tk 実体生成までモックして、属性初期化と _build_ui 呼び出しをカバー)
# ---------------------------------------------------------------------------

class TestAppInit:
    def test_init_creates_state_vars(self):
        """App.__init__ が title/geometry/minsize/folder_var/force_var を初期化し _build_ui を呼ぶ"""
        from pdf_split_autorenamer import gui as gui_module
        with patch.object(gui_module.tk.Tk, "__init__", return_value=None), \
             patch.object(gui_module.App, "title"), \
             patch.object(gui_module.App, "geometry"), \
             patch.object(gui_module.App, "minsize"), \
             patch.object(gui_module.App, "_build_ui") as mb_ui, \
             patch.object(gui_module, "tk", MagicMock(StringVar=MagicMock, BooleanVar=MagicMock)):
            app = gui_module.App(initial_folder="/tmp")
        mb_ui.assert_called_once()
        # folder_var / force_var が設定されている
        assert hasattr(app, "folder_var")
        assert hasattr(app, "force_var")


# ---------------------------------------------------------------------------
# _on_browse  (lines 133-136)
# ---------------------------------------------------------------------------

class TestOnBrowse:
    def test_browse_sets_folder_var(self):
        """フォルダを選択すると folder_var に設定される"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        with patch.object(gui_module.filedialog, "askdirectory", return_value="/some/folder"):
            app._on_browse()
        assert app.folder_var.get() == "/some/folder"

    def test_browse_cancel_keeps_existing(self):
        """キャンセル（空文字）のとき folder_var は変更されない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("/original")
        with patch.object(gui_module.filedialog, "askdirectory", return_value=""):
            app._on_browse()
        assert app.folder_var.get() == "/original"


# ---------------------------------------------------------------------------
# _get_folder  (lines 147-155)
# ---------------------------------------------------------------------------

class TestGetFolder:
    def test_empty_folder_shows_warning_returns_none(self):
        """folder_var が空なら警告ダイアログを出して None を返す"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("")
        with patch.object(gui_module.messagebox, "showwarning") as mw:
            result = app._get_folder()
        assert result is None
        mw.assert_called_once()

    def test_nonexistent_folder_shows_error_returns_none(self):
        """存在しないパスならエラーダイアログを出して None を返す"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("/nonexistent/xyz/abc")
        with patch.object(gui_module.messagebox, "showerror") as me:
            result = app._get_folder()
        assert result is None
        me.assert_called_once()

    def test_valid_folder_returns_path(self, tmp_path):
        """存在するフォルダなら Path を返す"""
        from pdf_split_autorenamer.gui import App
        app = _make_app(str(tmp_path))
        result = app._get_folder()
        assert result == tmp_path

    def test_valid_pdf_file_returns_path(self, tmp_path):
        """issue #35: 単一 PDF ファイルパスでも受理する"""
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
        app = _make_app(str(pdf))
        result = app._get_folder()
        assert result == pdf


class TestOnBrowseFile:
    def test_browse_file_sets_path(self, tmp_path):
        """issue #35: ファイル選択で folder_var に PDF パスがセットされる"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        with patch.object(gui_module.filedialog, "askopenfilename",
                          return_value="/tmp/a.pdf"):
            app._on_browse_file()
        assert app.folder_var.get() == "/tmp/a.pdf"

    def test_browse_file_cancel_keeps_existing(self):
        """ファイル選択キャンセルなら folder_var は変更されない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("/orig")
        with patch.object(gui_module.filedialog, "askopenfilename", return_value=""):
            app._on_browse_file()
        assert app.folder_var.get() == "/orig"

    def test_browse_file_initial_from_file(self, tmp_path):
        """既に PDF ファイルが入っているとき、initialdir はその親フォルダ"""
        from pdf_split_autorenamer import gui as gui_module
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
        app = _make_app(str(pdf))
        captured = {}

        def fake_open(**kwargs):
            captured.update(kwargs)
            return ""

        with patch.object(gui_module.filedialog, "askopenfilename", side_effect=fake_open):
            app._on_browse_file()
        assert captured.get("initialdir") == str(tmp_path)


# ---------------------------------------------------------------------------
# _log / _set_status  (lines 158-164)
# ---------------------------------------------------------------------------

class TestLogAndStatus:
    def test_log_inserts_text(self):
        """_log が insert / see を呼ぶこと"""
        app = _make_app()
        with patch.object(app, "update_idletasks"):
            app._log("テストメッセージ")
        app.log.insert.assert_called_once_with("end", "テストメッセージ\n")
        app.log.see.assert_called_once_with("end")

    def test_set_status_updates_var(self):
        """_set_status が status_var を更新すること"""
        app = _make_app()
        with patch.object(app, "update_idletasks"):
            app._set_status("処理中")
        assert app.status_var.get() == "処理中"


# ---------------------------------------------------------------------------
# _run_async  (lines 167-176)
# ---------------------------------------------------------------------------

class TestRunAsync:
    def test_run_async_calls_on_done_with_result(self):
        """ワーカースレッドが完了すると on_done がコールバックされる"""
        app = _make_app()
        done_values = []
        event = threading.Event()

        def on_done(r):
            done_values.append(r)
            event.set()

        with patch.object(app, "after", side_effect=lambda delay, fn, *a: fn(*a)):
            app._run_async(lambda: 42, on_done)

        event.wait(timeout=3)
        assert done_values == [42]

    def test_run_async_exception_logs_error(self):
        """ワーカーが例外を出すと _log("ERROR: ...") が呼ばれる"""
        app = _make_app()
        logged = []
        event = threading.Event()

        def after_impl(delay, fn, *args):
            result = fn(*args)
            event.set()
            return result

        with patch.object(app, "after", side_effect=after_impl), \
             patch.object(app, "_log", side_effect=logged.append), \
             patch.object(app, "_set_status"):
            app._run_async(lambda: (_ for _ in ()).throw(ValueError("boom")))

        event.wait(timeout=3)
        assert any("ERROR" in m for m in logged)

    def test_run_async_no_callback_runs_target(self):
        """on_done が None でもターゲットは実行される"""
        app = _make_app()
        called = threading.Event()
        with patch.object(app, "after"):
            app._run_async(lambda: called.set())
        called.wait(timeout=3)
        assert called.is_set()


# ---------------------------------------------------------------------------
# Static summaries  (lines 181-214)
# ---------------------------------------------------------------------------

class TestBuildSplitSummary:
    def test_basic_output(self):
        from pdf_split_autorenamer.gui import App
        res = {"actions": [{"status": "ok", "out": "file.pdf", "range": "1-3"}],
               "files_written": 1, "total_output_pages": 3}
        s = App._build_split_summary(res)
        assert "1 ファイル" in s
        assert "3 ページ" in s
        assert "file.pdf" in s

    def test_long_list_truncated(self):
        from pdf_split_autorenamer.gui import App
        actions = [{"status": "ok", "out": f"f{i}.pdf", "range": f"{i}"} for i in range(15)]
        res = {"actions": actions, "files_written": 15, "total_output_pages": 15}
        s = App._build_split_summary(res)
        assert "他 5 件" in s

    def test_empty_actions(self):
        from pdf_split_autorenamer.gui import App
        res = {"actions": [], "files_written": 0, "total_output_pages": 0}
        s = App._build_split_summary(res)
        assert "実行してよろしいですか" in s


# issue #40: TestBuildRenameSummary は Step 3 自動リネーム削除に伴い廃止。
# rename ロジック自体は CLI 用に残存し、tests/test_rename.py でカバーされる。


# ---------------------------------------------------------------------------
# _on_analyze early return
# ---------------------------------------------------------------------------

class TestOnAnalyze:
    def test_early_return_when_no_folder(self):
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("")
        with patch.object(app, "_get_folder", return_value=None), \
             patch.object(app, "_run_async") as mra:
            app._on_analyze()
        mra.assert_not_called()

    def test_calls_run_analyze(self, tmp_path):
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        mock_result = {"pages": 2, "groups": 1, "report_html": None, "groups_json": ""}
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status"), \
             patch.object(gui_module._analyze, "run_analyze", return_value=mock_result), \
             patch.object(gui_module.messagebox, "showwarning"), \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_analyze()

    def test_analyze_done_opens_browser_when_pywebview_unavailable(self, tmp_path):
        """pywebview 未導入時: 正常解析でダイアログなしに webbrowser.open が呼ばれる (#37 + #30)"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        fake_html = str(tmp_path / "report.html")
        mock_result = {"pages": 3, "groups": 2, "report_html": fake_html, "groups_json": ""}
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status"), \
             patch.object(gui_module._analyze, "run_analyze", return_value=mock_result), \
             patch.object(gui_module._inapp, "is_available", return_value=False), \
             patch.object(gui_module.messagebox, "askyesno") as masky, \
             patch.object(gui_module.messagebox, "showwarning") as msw, \
             patch.object(gui_module, "webbrowser") as mwb, \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_analyze()
        masky.assert_not_called()
        msw.assert_not_called()
        mwb.open.assert_called_once()

    def test_analyze_done_invokes_inapp_edit_when_pywebview_available(self, tmp_path):
        """pywebview 導入時: 正常解析でダイアログなしに _on_inapp_edit が呼ばれる (#37 + #30)"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        fake_html = str(tmp_path / "report.html")
        mock_result = {"pages": 3, "groups": 2, "report_html": fake_html, "groups_json": ""}
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status"), \
             patch.object(gui_module._analyze, "run_analyze", return_value=mock_result), \
             patch.object(gui_module._inapp, "is_available", return_value=True), \
             patch.object(gui_module.messagebox, "askyesno") as masky, \
             patch.object(app, "_on_inapp_edit") as m_edit, \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_analyze()
        masky.assert_not_called()
        m_edit.assert_called_once()

    def test_analyze_done_pages_zero_shows_warning(self, tmp_path):
        """issue #37: pages == 0 → 警告ダイアログ、ブラウザも編集も開かない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        fake_html = str(tmp_path / "report.html")
        mock_result = {"pages": 0, "groups": 0, "report_html": fake_html, "groups_json": ""}
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status"), \
             patch.object(gui_module._analyze, "run_analyze", return_value=mock_result), \
             patch.object(gui_module.messagebox, "showwarning") as msw, \
             patch.object(gui_module, "webbrowser") as mwb, \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_analyze()
        msw.assert_called_once()
        mwb.open.assert_not_called()

    def test_analyze_done_groups_zero_shows_warning(self, tmp_path):
        """issue #37: groups == 0 (pages > 0) → 警告ダイアログ、ブラウザは開かない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        fake_html = str(tmp_path / "report.html")
        mock_result = {"pages": 5, "groups": 0, "report_html": fake_html, "groups_json": ""}
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status"), \
             patch.object(gui_module._analyze, "run_analyze", return_value=mock_result), \
             patch.object(gui_module.messagebox, "showwarning") as msw, \
             patch.object(gui_module, "webbrowser") as mwb, \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_analyze()
        msw.assert_called_once()
        mwb.open.assert_not_called()

    def test_analyze_done_html_missing_shows_warning(self, tmp_path):
        """issue #37: report_html が None → 警告ダイアログ、ブラウザは開かない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        mock_result = {"pages": 3, "groups": 2, "report_html": None, "groups_json": ""}
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status"), \
             patch.object(gui_module._analyze, "run_analyze", return_value=mock_result), \
             patch.object(gui_module.messagebox, "showwarning") as msw, \
             patch.object(gui_module, "webbrowser") as mwb, \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_analyze()
        msw.assert_called_once()
        mwb.open.assert_not_called()


# ---------------------------------------------------------------------------
# _on_open_report  (lines 245-252)
# ---------------------------------------------------------------------------

class TestOnOpenReport:
    def test_early_return_when_no_folder(self):
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        with patch.object(app, "_get_folder", return_value=None), \
             patch.object(gui_module, "webbrowser") as mwb:
            app._on_open_report()
        mwb.open.assert_not_called()

    def test_warning_when_report_missing(self, tmp_path):
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(gui_module.messagebox, "showwarning") as mw:
            app._on_open_report()
        mw.assert_called_once()

    def test_opens_browser_when_report_exists(self, tmp_path):
        from pdf_split_autorenamer import gui as gui_module
        psar = tmp_path / ".psar"
        psar.mkdir()
        (psar / "report.html").write_text("<html/>", encoding="utf-8")
        app = _make_app(str(tmp_path))
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(gui_module, "webbrowser") as mwb:
            app._on_open_report()
        mwb.open.assert_called_once()


# ---------------------------------------------------------------------------
# _on_split early return  (lines 255-257)
# ---------------------------------------------------------------------------

class TestOnSplit:
    def test_early_return_when_no_folder(self):
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        with patch.object(app, "_get_folder", return_value=None), \
             patch.object(app, "_run_async") as mra:
            app._on_split(False)
        mra.assert_not_called()

    def test_dry_run_logs_actions(self, tmp_path):
        """_on_split(False): done_dry コールバックがアクションをログに出力 (lines 258-275)"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        logged = []
        mock_result = {
            "actions": [{"status": "ok", "out": "out.pdf", "src": "src.pdf", "range": "1-3"}],
            "total_input_pages": 5,
            "files_written": 1,
            "total_output_pages": 3,
            "files_skipped": 0,
        }
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(gui_module._split, "run_split", return_value=mock_result), \
             patch.object(app, "_log", side_effect=logged.append), \
             patch.object(app, "_set_status"), \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_split(apply_=False)
        assert any("out.pdf" in m for m in logged)

    def test_apply_with_confirm_logs_results(self, tmp_path):
        """_on_split(True): done_preview → messagebox.askyesno=True → done_apply (lines 278-308)"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        logged = []
        mock_result = {
            "actions": [{"status": "ok", "out": "out.pdf", "src": "src.pdf", "range": "1-3"}],
            "total_input_pages": 5,
            "files_written": 1,
            "total_output_pages": 3,
            "files_skipped": 0,
        }
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(gui_module._split, "run_split", return_value=mock_result), \
             patch.object(gui_module.messagebox, "askyesno", return_value=True), \
             patch.object(app, "_log", side_effect=logged.append), \
             patch.object(app, "_set_status"), \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_split(apply_=True)
        assert any("分割完了" in m or "out.pdf" in m for m in logged)

    def test_apply_cancel_sets_cancel_status(self, tmp_path):
        """_on_split(True): messagebox.askyesno=False → キャンセル (line 288-289)"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        statuses = []
        mock_result = {
            "actions": [],
            "total_input_pages": 0,
            "files_written": 0,
            "total_output_pages": 0,
            "files_skipped": 0,
        }
        with patch.object(app, "_get_folder", return_value=tmp_path), \
             patch.object(gui_module._split, "run_split", return_value=mock_result), \
             patch.object(gui_module.messagebox, "askyesno", return_value=False), \
             patch.object(app, "_log"), \
             patch.object(app, "_set_status", side_effect=statuses.append), \
             patch.object(app, "_run_async",
                          side_effect=lambda fn, cb=None: cb(fn()) if cb else fn()):
            app._on_split(apply_=True)
        assert "キャンセル" in statuses


# issue #40: _on_rename テスト群は廃止。GUI 自動リネームは Step 2 分割に統合された。
# rename ロジック自体は CLI 用に残存し、tests/test_rename.py でカバーされる。


# ---------------------------------------------------------------------------
# _toggle_split_advanced  (Step 2 詳細オプション折りたたみ)
# ---------------------------------------------------------------------------

class TestToggleAdvanced:
    def _make_app_with_advanced(self, split_checked: bool) -> object:
        app = _make_app()
        app.__dict__["_split_advanced_var"] = _BooleanVar(split_checked)
        split_frame = MagicMock()
        split_frame.master.winfo_children.return_value = [MagicMock(), MagicMock()]
        app.__dict__["_split_advanced_frame"] = split_frame
        return app

    def test_toggle_split_advanced_pack_when_checked(self):
        """split_advanced_var=True → pack が呼ばれる"""
        app = self._make_app_with_advanced(split_checked=True)
        app._toggle_split_advanced()
        app._split_advanced_frame.pack.assert_called_once()
        app._split_advanced_frame.pack_forget.assert_not_called()

    def test_toggle_split_advanced_pack_forget_when_unchecked(self):
        """split_advanced_var=False → pack_forget が呼ばれる"""
        app = self._make_app_with_advanced(split_checked=False)
        app._toggle_split_advanced()
        app._split_advanced_frame.pack_forget.assert_called_once()
        app._split_advanced_frame.pack.assert_not_called()


# ---------------------------------------------------------------------------
# main + __main__ guard
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# issue #48: Menubutton 統合入力ボタンのテスト
# ---------------------------------------------------------------------------

class TestMenubuttonInput:
    def test_input_button_is_menubutton(self):
        """issue #48: 入力選択ボタンが Menubutton であること"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        with patch.object(gui_module, "ttk", MagicMock()) as mock_ttk, \
             patch.object(gui_module, "tk", MagicMock()), \
             patch("logging.getLogger", return_value=MagicMock()):
            app._build_ui()
        # Menubutton が呼ばれていること
        mock_ttk.Menubutton.assert_called()

    def test_input_paths_attribute_exists(self):
        """issue #48: App に _input_paths 属性が存在すること"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        app._input_paths = []  # _make_app は __init__ をスキップするので明示設定
        assert hasattr(app, "_input_paths")
        assert isinstance(app._input_paths, list)

    def test_on_browse_sets_input_paths_single_folder(self, tmp_path):
        """issue #48: フォルダ選択で _input_paths が [Path(folder)] になる"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app()
        app._input_paths = []
        with patch.object(gui_module.filedialog, "askdirectory",
                          return_value=str(tmp_path)):
            app._on_browse()
        assert app._input_paths == [tmp_path]

    def test_on_browse_files_sets_multiple_input_paths(self, tmp_path):
        """issue #48: 複数 PDF 選択で _input_paths に複数 Path が入る"""
        from pdf_split_autorenamer import gui as gui_module
        pdf1 = tmp_path / "a.pdf"
        pdf2 = tmp_path / "b.pdf"
        pdf1.write_bytes(b"%PDF-1.4\n%%EOF\n")
        pdf2.write_bytes(b"%PDF-1.4\n%%EOF\n")
        app = _make_app()
        app._input_paths = []
        with patch.object(gui_module.filedialog, "askopenfilenames",
                          return_value=(str(pdf1), str(pdf2))):
            app._on_browse_files()
        assert set(app._input_paths) == {pdf1, pdf2}

    def test_on_browse_files_single_pdf_updates_folder_var(self, tmp_path):
        """issue #48: 単一 PDF 選択で folder_var がそのパスになる"""
        from pdf_split_autorenamer import gui as gui_module
        pdf1 = tmp_path / "a.pdf"
        pdf1.write_bytes(b"%PDF-1.4\n%%EOF\n")
        app = _make_app()
        app._input_paths = []
        with patch.object(gui_module.filedialog, "askopenfilenames",
                          return_value=(str(pdf1),)):
            app._on_browse_files()
        assert app.folder_var.get() == str(pdf1)

    def test_on_browse_files_multiple_pdfs_shows_summary_in_folder_var(self, tmp_path):
        """issue #48: 複数 PDF 選択で folder_var がサマリー文字列になる"""
        from pdf_split_autorenamer import gui as gui_module
        pdf1 = tmp_path / "a.pdf"
        pdf2 = tmp_path / "b.pdf"
        pdf3 = tmp_path / "c.pdf"
        for p in [pdf1, pdf2, pdf3]:
            p.write_bytes(b"%PDF-1.4\n%%EOF\n")
        app = _make_app()
        app._input_paths = []
        with patch.object(gui_module.filedialog, "askopenfilenames",
                          return_value=(str(pdf1), str(pdf2), str(pdf3))):
            app._on_browse_files()
        summary = app.folder_var.get()
        # 件数が含まれること
        assert "3" in summary

    def test_on_browse_files_cancel_keeps_existing(self):
        """issue #48: ファイル選択キャンセル時は _input_paths と folder_var を変更しない"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("/original")
        app._input_paths = []
        with patch.object(gui_module.filedialog, "askopenfilenames",
                          return_value=()):
            app._on_browse_files()
        assert app.folder_var.get() == "/original"
        assert app._input_paths == []

    def test_get_inputs_returns_folder_path(self, tmp_path):
        """issue #48: フォルダが設定されているとき _get_inputs が Path を返す"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app(str(tmp_path))
        app._input_paths = [tmp_path]
        result = app._get_inputs()
        assert result == tmp_path

    def test_get_inputs_returns_list_for_multiple_pdfs(self, tmp_path):
        """issue #48: 複数 PDF が設定されているとき _get_inputs が list[Path] を返す"""
        from pdf_split_autorenamer import gui as gui_module
        pdf1 = tmp_path / "a.pdf"
        pdf2 = tmp_path / "b.pdf"
        for p in [pdf1, pdf2]:
            p.write_bytes(b"%PDF-1.4\n%%EOF\n")
        app = _make_app()
        app._input_paths = [pdf1, pdf2]
        result = app._get_inputs()
        assert isinstance(result, list)
        assert set(result) == {pdf1, pdf2}

    def test_get_inputs_empty_shows_warning(self):
        """issue #48: _input_paths が空かつ folder_var も空なら警告を出して None を返す"""
        from pdf_split_autorenamer import gui as gui_module
        app = _make_app("")
        app._input_paths = []
        # messagebox.showwarning は Tk インスタンスを必要とするためモック
        with patch.object(gui_module.messagebox, "showwarning") as mw, \
             patch.object(app, "update_idletasks", return_value=None):
            result = app._get_inputs()
        assert result is None
        mw.assert_called_once()


class TestMain:
    def test_main_creates_app_and_mainloops(self):
        """main() が App を生成して mainloop() を呼ぶこと"""
        from pdf_split_autorenamer import gui as gui_module
        mock_app = MagicMock()
        with patch.object(gui_module, "App", return_value=mock_app) as mock_cls:
            result = gui_module.main(initial_folder="/tmp")
        mock_cls.assert_called_once_with(initial_folder="/tmp")
        mock_app.mainloop.assert_called_once()
        assert result == 0

    def test_gui_if_main_guard(self):
        """gui.py の if __name__ == '__main__' をカバー (line 375)

        runpy は fresh namespace を使うため tkinter.Tk を直接パッチする。
        """
        import runpy
        import sys as _sys
        import tkinter
        import tkinter.ttk as _ttk

        mock_tk = MagicMock()
        with patch.object(tkinter, "Tk", return_value=mock_tk), \
             patch.object(_ttk, "Frame", return_value=MagicMock()), \
             patch.object(_ttk, "Label", return_value=MagicMock()), \
             patch.object(_ttk, "Button", return_value=MagicMock()), \
             patch.object(_ttk, "Entry", return_value=MagicMock()), \
             patch.object(_ttk, "Scrollbar", return_value=MagicMock()), \
             patch.object(_ttk, "LabelFrame", return_value=MagicMock()), \
             patch.object(_ttk, "Radiobutton", return_value=MagicMock()), \
             patch.object(_ttk, "Checkbutton", return_value=MagicMock()), \
             patch.object(tkinter, "Text", return_value=MagicMock()), \
             patch.object(tkinter, "StringVar", return_value=MagicMock()), \
             patch.object(tkinter, "BooleanVar", return_value=MagicMock()):
            mock_tk.mainloop.return_value = None
            with patch.object(_sys, "exit", side_effect=SystemExit(0)):
                with pytest.raises(SystemExit):
                    runpy.run_module("pdf_split_autorenamer.gui", run_name="__main__")
