# -*- coding: utf-8 -*-
"""gui.py の D&D（ドラッグ＆ドロップ）機能テスト

issue #47: テキストボックスへの D&D 入力対応

対象:
- App._register_dnd
- App._on_drop
- _DND_AVAILABLE フラグによる継承切替ロジック
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# ローカルスタブ（テストファイル独立性を保つため）
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
    """モック済みの App インスタンスを返す。"""
    from pdf_split_autorenamer import gui as gui_module

    with patch.object(gui_module.App, "__init__", return_value=None):
        app = gui_module.App()

    # tk.splitlist のスタブ（tkinterdnd2 の event.data パース用）
    mock_tk = MagicMock()
    mock_tk.splitlist = lambda s: _splitlist_simple(s)

    app.__dict__.update({
        "folder_var": _StringVar(folder),
        "profile_var": _StringVar(""),
        "force_var": _BooleanVar(False),
        "status_var": _StringVar("待機中"),
        "log": MagicMock(),
        "_input_paths": [],
        "tk": mock_tk,
    })
    return app


def _splitlist_simple(s: str) -> list[str]:
    """tk.splitlist の簡易スタブ。
    - `{path1} {path2}` 形式を解析して中括弧を除いたリストを返す
    - 中括弧がなければスペース区切りで分割
    """
    s = s.strip()
    if "{" in s:
        # {path1} {path2} 形式
        import re
        items = re.findall(r"\{([^}]+)\}", s)
        if items:
            return items
    # 通常のスペース区切り（単一パスも含む）
    return s.split() if s else []


def _make_drop_event(data: str) -> MagicMock:
    """event.data を持つ簡易ドロップイベントを返す。"""
    event = MagicMock()
    event.data = data
    return event


# ---------------------------------------------------------------------------
# テスト本体
# ---------------------------------------------------------------------------

class TestOnDropSinglePdf:
    def test_dnd_single_pdf_sets_folder_var(self, tmp_path):
        """単一 PDF パスのドロップで folder_var と _input_paths が正しくセットされること"""
        from pdf_split_autorenamer import gui as gui_module

        pdf = tmp_path / "sample.pdf"
        pdf.touch()

        app = _make_app()
        event = _make_drop_event(str(pdf))

        with patch.object(gui_module, "_DND_AVAILABLE", True):
            app._on_drop(event)

        assert app.folder_var.get() == str(pdf)
        assert app._input_paths == [Path(pdf)]


class TestOnDropSingleFolder:
    def test_dnd_single_folder_sets_folder_var(self, tmp_path):
        """単一フォルダのドロップで folder_var と _input_paths が正しくセットされること"""
        from pdf_split_autorenamer import gui as gui_module

        app = _make_app()
        event = _make_drop_event(str(tmp_path))

        with patch.object(gui_module, "_DND_AVAILABLE", True):
            app._on_drop(event)

        assert app.folder_var.get() == str(tmp_path)
        assert app._input_paths == [Path(tmp_path)]


class TestOnDropMultiplePdfs:
    def test_dnd_multiple_pdfs_sets_display_string(self, tmp_path):
        """複数 PDF で '(N ファイル) first 他 N-1 件' 表示になること"""
        from pdf_split_autorenamer import gui as gui_module

        pdf1 = tmp_path / "a.pdf"
        pdf2 = tmp_path / "b.pdf"
        pdf3 = tmp_path / "c.pdf"
        pdf1.touch()
        pdf2.touch()
        pdf3.touch()

        app = _make_app()
        # tk.splitlist スタブが複数パスを正しく処理できるよう event.data を設定
        app.tk.splitlist = lambda s: [str(pdf1), str(pdf2), str(pdf3)]
        event = _make_drop_event(f"{pdf1} {pdf2} {pdf3}")

        with patch.object(gui_module, "_DND_AVAILABLE", True):
            app._on_drop(event)

        folder_val = app.folder_var.get()
        assert "(3 ファイル)" in folder_val
        assert "a.pdf" in folder_val
        assert "他 2 件" in folder_val
        assert len(app._input_paths) == 3


class TestOnDropMixed:
    def test_dnd_mixed_pdfs_and_dir_stores_all_paths(self, tmp_path):
        """PDF + フォルダ混在時に全パスが _input_paths に積まれること"""
        from pdf_split_autorenamer import gui as gui_module

        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        app = _make_app()
        app.tk.splitlist = lambda s: [str(pdf), str(subdir)]
        event = _make_drop_event(f"{pdf} {subdir}")

        with patch.object(gui_module, "_DND_AVAILABLE", True):
            app._on_drop(event)

        assert Path(pdf) in app._input_paths
        assert Path(subdir) in app._input_paths
        assert len(app._input_paths) == 2


class TestOnDropNonPdf:
    def test_dnd_non_pdf_shows_error(self, tmp_path):
        """PDF 以外の単一ファイルで messagebox.showerror が呼ばれ、状態変更なしであること"""
        from pdf_split_autorenamer import gui as gui_module

        txt = tmp_path / "readme.txt"
        txt.touch()

        app = _make_app()
        event = _make_drop_event(str(txt))
        original_paths = list(app._input_paths)
        original_folder = app.folder_var.get()

        with patch.object(gui_module, "_DND_AVAILABLE", True), \
             patch.object(gui_module.messagebox, "showerror") as mock_err:
            app._on_drop(event)

        mock_err.assert_called_once_with(
            "エラー",
            "PDF ファイルまたはフォルダをドロップしてください: readme.txt",
        )
        assert app._input_paths == original_paths
        assert app.folder_var.get() == original_folder


class TestRegisterDndUnavailable:
    def test_dnd_unavailable_no_crash(self):
        """_DND_AVAILABLE=False で _register_dnd を呼んでも例外なしであること"""
        from pdf_split_autorenamer import gui as gui_module

        app = _make_app()
        mock_widget = MagicMock()

        with patch.object(gui_module, "_DND_AVAILABLE", False):
            # 例外が出なければ OK
            app._register_dnd(mock_widget)

        # _DND_AVAILABLE=False ならウィジェット操作は呼ばれないこと
        mock_widget.drop_target_register.assert_not_called()
        mock_widget.dnd_bind.assert_not_called()


class TestRegisterDndAvailable:
    def test_register_dnd_calls_drop_target_register_when_available(self):
        """_DND_AVAILABLE=True モンキーパッチで drop_target_register が呼ばれること"""
        from pdf_split_autorenamer import gui as gui_module

        app = _make_app()
        mock_widget = MagicMock()

        with patch.object(gui_module, "_DND_AVAILABLE", True):
            app._register_dnd(mock_widget)

        mock_widget.drop_target_register.assert_called_once_with("DND_Files")
        mock_widget.dnd_bind.assert_called_once_with("<<Drop>>", app._on_drop)


class TestOnDropEventDataParsing:
    def test_on_drop_event_data_parsing_with_spaces(self, tmp_path):
        """スペースを含むパス '{C:/path with space.pdf}' が正しくパースされること"""
        from pdf_split_autorenamer import gui as gui_module

        # スペースを含むファイルパスを作成
        spaced_dir = tmp_path / "path with space"
        spaced_dir.mkdir()
        pdf = spaced_dir / "document.pdf"
        pdf.touch()

        app = _make_app()
        # tkinterdnd2 の {path} 形式でイベントデータを設定
        event = _make_drop_event(f"{{{pdf}}}")

        with patch.object(gui_module, "_DND_AVAILABLE", True):
            app._on_drop(event)

        assert app.folder_var.get() == str(pdf)
        assert app._input_paths == [Path(pdf)]
