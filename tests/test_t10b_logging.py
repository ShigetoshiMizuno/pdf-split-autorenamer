# -*- coding: utf-8 -*-
"""T-10b: logging 移行の検証テスト

- --verbose / --quiet オプションが analyze / split / rename サブコマンドに存在するか
- analyze.py / split.py に logging が使われているか
- gui.py に _TextHandler が存在するか
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# --verbose / --quiet オプションが各サブコマンドに存在するか
# ---------------------------------------------------------------------------

class TestVerboseQuietOptions:
    """build_parser() が analyze / split / rename に --verbose/--quiet を持つか"""

    def _get_subparser_actions(self, subcmd: str):
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        # subparsers を走査して subcmd を探す
        for action in parser._subparsers._group_actions:
            choices = action.choices
            if choices and subcmd in choices:
                return choices[subcmd]._actions
        return []

    def test_analyze_has_verbose(self):
        actions = self._get_subparser_actions("analyze")
        opts = [o for a in actions for o in a.option_strings]
        assert "--verbose" in opts, "analyze サブコマンドに --verbose がない"

    def test_analyze_has_quiet(self):
        actions = self._get_subparser_actions("analyze")
        opts = [o for a in actions for o in a.option_strings]
        assert "--quiet" in opts, "analyze サブコマンドに --quiet がない"

    def test_split_has_verbose(self):
        actions = self._get_subparser_actions("split")
        opts = [o for a in actions for o in a.option_strings]
        assert "--verbose" in opts, "split サブコマンドに --verbose がない"

    def test_split_has_quiet(self):
        actions = self._get_subparser_actions("split")
        opts = [o for a in actions for o in a.option_strings]
        assert "--quiet" in opts, "split サブコマンドに --quiet がない"

    def test_rename_has_verbose(self):
        actions = self._get_subparser_actions("rename")
        opts = [o for a in actions for o in a.option_strings]
        assert "--verbose" in opts, "rename サブコマンドに --verbose がない"

    def test_rename_has_quiet(self):
        actions = self._get_subparser_actions("rename")
        opts = [o for a in actions for o in a.option_strings]
        assert "--quiet" in opts, "rename サブコマンドに --quiet がない"


# ---------------------------------------------------------------------------
# _setup_logging が cli.py に存在するか
# ---------------------------------------------------------------------------

class TestSetupLogging:
    def test_setup_logging_exists_in_cli(self):
        from pdf_split_autorenamer import cli
        assert hasattr(cli, "_setup_logging"), \
            "_setup_logging が cli.py に存在しない"

    def test_setup_logging_sets_debug_level_when_verbose(self):
        from pdf_split_autorenamer.cli import _setup_logging
        # verbose=True → ルートロガーが DEBUG レベルになること
        _setup_logging(verbose=True, quiet=False)
        assert logging.getLogger().level == logging.DEBUG, \
            "verbose=True のとき root logger が DEBUG になっていない"

    def test_setup_logging_sets_warning_level_when_quiet(self):
        from pdf_split_autorenamer.cli import _setup_logging
        _setup_logging(verbose=False, quiet=True)
        assert logging.getLogger().level == logging.WARNING, \
            "quiet=True のとき root logger が WARNING になっていない"

    def test_setup_logging_sets_info_level_by_default(self):
        from pdf_split_autorenamer.cli import _setup_logging
        _setup_logging(verbose=False, quiet=False)
        assert logging.getLogger().level == logging.INFO, \
            "デフォルトのとき root logger が INFO になっていない"


# ---------------------------------------------------------------------------
# analyze.py に logging が使われているか
# ---------------------------------------------------------------------------

class TestAnalyzeUsesLogging:
    def test_logging_imported_in_analyze(self):
        """analyze.py に logging がインポートされているか"""
        import pdf_split_autorenamer.analyze as mod
        assert hasattr(mod, "logging") or "logging" in dir(mod), \
            "analyze.py に logging がインポートされていない"

    def test_collect_pages_uses_logging_warning_on_open_failure(self):
        """collect_pages が PDF オープン失敗時に logging.warning を呼ぶか"""
        from unittest.mock import MagicMock, patch
        from pathlib import Path

        fake_path = MagicMock(spec=Path)
        fake_path.name = "broken.pdf"
        fake_path.stem = "broken"
        fake_path.read_bytes.return_value = b"not a pdf"

        with patch("pdf_split_autorenamer.analyze.list_pdfs", return_value=[fake_path]), \
             patch("pdf_split_autorenamer.analyze.fitz") as mock_fitz, \
             patch("pdf_split_autorenamer.analyze.logging") as mock_logging:
            mock_fitz.open.side_effect = Exception("invalid PDF")
            from pathlib import Path as RealPath
            import pdf_split_autorenamer.analyze as analyze
            analyze.collect_pages(RealPath("."), RealPath(".") / "thumbs")

        # logging.warning が呼ばれていること
        assert mock_logging.warning.called, \
            "PDF オープン失敗時に logging.warning が呼ばれていない"


# ---------------------------------------------------------------------------
# split.py に logging が使われているか
# ---------------------------------------------------------------------------

class TestSplitUsesLogging:
    def test_logging_imported_in_split(self):
        """split.py に logging がインポートされているか"""
        import pdf_split_autorenamer.split as mod
        assert hasattr(mod, "logging") or "logging" in dir(mod), \
            "split.py に logging がインポートされていない"

    def test_split_logs_warning_on_missing_pdf(self):
        """run_split が missing な PDF に対して logging.warning を呼ぶか"""
        import json
        from unittest.mock import MagicMock, patch
        from pathlib import Path

        groups = {"nonexistent.pdf": [{"range": [1, 2], "name": "test"}]}

        with patch("pdf_split_autorenamer.split.logging") as mock_logging, \
             patch("builtins.open", side_effect=FileNotFoundError("groups.json")):
            pass  # open パッチはここでは不要 — tmp_path で代替

        # tmp_path を使って実際に groups.json を書いてテスト
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            work = tmp / ".psar"
            work.mkdir()
            (work / "groups.json").write_text(
                json.dumps(groups), encoding="utf-8"
            )
            with patch("pdf_split_autorenamer.split.logger") as mock_logger:
                from pdf_split_autorenamer.split import run_split
                run_split(tmp, work_dir=work)

            assert mock_logger.warning.called, \
                "PDF が存在しないときに logger.warning が呼ばれていない"


# ---------------------------------------------------------------------------
# gui.py に _TextHandler が存在するか
# ---------------------------------------------------------------------------

class TestGuiTextHandler:
    def test_text_handler_class_exists_in_gui(self):
        """gui.py に _TextHandler クラスが存在するか"""
        import pdf_split_autorenamer.gui as gui
        assert hasattr(gui, "_TextHandler"), \
            "gui.py に _TextHandler が存在しない"

    def test_text_handler_is_logging_handler(self):
        """_TextHandler が logging.Handler のサブクラスか"""
        import pdf_split_autorenamer.gui as gui
        assert issubclass(gui._TextHandler, logging.Handler), \
            "_TextHandler が logging.Handler のサブクラスでない"

    def test_text_handler_emit_schedules_append(self):
        """_TextHandler.emit が after(0, ...) をスケジュールするか"""
        import pdf_split_autorenamer.gui as gui
        widget = MagicMock()
        handler = gui._TextHandler(widget)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        record = logging.LogRecord(
            name="test", level=logging.WARNING,
            pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        handler.emit(record)
        widget.after.assert_called_once()
        call_args = widget.after.call_args
        assert call_args.args[0] == 0, "after の第1引数が 0 でない"
