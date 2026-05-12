# -*- coding: utf-8 -*-
"""cli.py の argparse パーサーテスト + コマンド関数の統合テスト"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pdf_split_autorenamer.cli import build_parser, main


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_parser_is_created(self):
        """build_parser() が ArgumentParser を返す"""
        import argparse
        p = build_parser()
        assert isinstance(p, argparse.ArgumentParser)

    def test_version_raises_systemexit(self):
        """--version で SystemExit が発生する"""
        p = build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["--version"])

    def test_no_args_raises_systemexit(self):
        """引数なしで SystemExit が発生する（required subcommand）"""
        p = build_parser()
        with pytest.raises(SystemExit):
            p.parse_args([])


# ---------------------------------------------------------------------------
# analyze サブコマンド
# ---------------------------------------------------------------------------

class TestAnalyzeParser:
    def test_analyze_folder_arg(self):
        """analyze サブコマンドで folder 引数が取得できる"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder"])
        assert args.folder == "./folder"

    def test_analyze_no_ocr_fallback_default_false(self):
        """--no-ocr-fallback のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder"])
        assert args.no_ocr_fallback is False

    def test_analyze_yes_default_false(self):
        """--yes のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder"])
        assert args.yes is False

    def test_analyze_yes_flag(self):
        """--yes を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder", "--yes"])
        assert args.yes is True

    def test_analyze_no_ocr_fallback_flag(self):
        """--no-ocr-fallback を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder", "--no-ocr-fallback"])
        assert args.no_ocr_fallback is True

    def test_analyze_title_default(self):
        """--title のデフォルト値が設定されている"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder"])
        assert args.title == "PDF 分割レビュー"

    def test_analyze_title_custom(self):
        """--title でカスタムタイトルを設定できる"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder", "--title", "カスタムタイトル"])
        assert args.title == "カスタムタイトル"

    def test_analyze_verbose_default_false(self):
        """--verbose のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder"])
        assert args.verbose is False

    def test_analyze_verbose_flag(self):
        """--verbose を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder", "--verbose"])
        assert args.verbose is True

    def test_analyze_quiet_flag(self):
        """--quiet を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder", "--quiet"])
        assert args.quiet is True

    def test_analyze_profile_help_says_glossary(self):
        """issue #50: analyze --profile の help 文言に「用語集」が含まれること"""
        import io
        p = build_parser()
        buf = io.StringIO()
        try:
            p.parse_args(["analyze", "--help"])
        except SystemExit:
            pass
        # argparse の help テキストを formatter から取得
        formatter = p._subparsers._actions[-1].choices["analyze"]._get_formatter()
        formatter.add_arguments(
            p._subparsers._actions[-1].choices["analyze"]._option_string_actions.values()
        )
        help_text = formatter.format_help()
        assert "用語集" in help_text, \
            f"analyze --profile の help に「用語集」がない (issue #50): {help_text}"


# ---------------------------------------------------------------------------
# split サブコマンド
# ---------------------------------------------------------------------------

class TestSplitParser:
    def test_split_folder_arg(self):
        """split サブコマンドで folder 引数が取得できる"""
        p = build_parser()
        args = p.parse_args(["split", "./folder"])
        assert args.folder == "./folder"

    def test_split_dry_run_default_false(self):
        """--dry-run のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["split", "./folder"])
        assert args.dry_run is False

    def test_split_dry_run_flag(self):
        """--dry-run を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["split", "./folder", "--dry-run"])
        assert args.dry_run is True
        assert args.force is False

    def test_split_force_default_false(self):
        """--force のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["split", "./folder"])
        assert args.force is False

    def test_split_force_flag(self):
        """--force を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["split", "./folder", "--force"])
        assert args.force is True

    def test_split_dry_run_and_force(self):
        """--dry-run と --force を同時に指定できる"""
        p = build_parser()
        args = p.parse_args(["split", "./folder", "--dry-run", "--force"])
        assert args.dry_run is True
        assert args.force is True


# ---------------------------------------------------------------------------
# rename サブコマンド
# ---------------------------------------------------------------------------

class TestRenameParser:
    def test_rename_folder_arg(self):
        """rename サブコマンドで folder 引数が取得できる"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder"])
        assert args.folder == "./folder"

    def test_rename_apply_default_false(self):
        """--apply のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder"])
        assert args.apply is False

    def test_rename_apply_flag(self):
        """--apply を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder", "--apply"])
        assert args.apply is True

    def test_rename_retarget_unknown_default_false(self):
        """--retarget-unknown のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder"])
        assert args.retarget_unknown is False

    def test_rename_retarget_unknown_flag(self):
        """--retarget-unknown を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder", "--retarget-unknown"])
        assert args.retarget_unknown is True

    def test_rename_all_default_false(self):
        """--all のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder"])
        assert args.all is False

    def test_rename_all_flag(self):
        """--all を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder", "--all"])
        assert args.all is True

    def test_rename_profile_default_none(self):
        """--profile のデフォルトは None"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder"])
        assert args.profile is None

    def test_rename_profile_flag(self):
        """--profile でプロファイルパスを指定できる"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder", "--profile", "my_profile.toml"])
        assert args.profile == "my_profile.toml"

    def test_rename_no_ocr_fallback_flag(self):
        """--no-ocr-fallback を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder", "--no-ocr-fallback"])
        assert args.no_ocr_fallback is True

    def test_rename_verbose_flag(self):
        """--verbose を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder", "--verbose"])
        assert args.verbose is True

    def test_rename_quiet_flag(self):
        """--quiet を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["rename", "./folder", "--quiet"])
        assert args.quiet is True


# ---------------------------------------------------------------------------
# cmd_analyze / cmd_split / cmd_rename / main — モックを使った統合テスト
# ---------------------------------------------------------------------------

class TestCmdAnalyze:
    def test_cmd_analyze_not_a_directory(self, tmp_path):
        """存在しないディレクトリを指定すると戻り値 2 が返る"""
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path / "nonexistent"),
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            verbose=False,
            quiet=False,
        )
        result = cmd_analyze(args)
        assert result == 2

    def test_cmd_analyze_calls_run_analyze(self, tmp_path):
        """有効なディレクトリを渡すと analyze.run_analyze が呼ばれる"""
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            verbose=False,
            quiet=False,
        )
        mock_result = {"pages": 0, "groups": 0, "report_html": "", "groups_json": ""}
        with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result):
            result = cmd_analyze(args)
        assert result == 0

    def test_cmd_analyze_llm_strategy_with_yes_skips_prompt(self, tmp_path):
        """--ocr-strategy llm + --yes でプライバシー確認をスキップして実行する"""
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            ocr_strategy="llm",
            yes=True,
            verbose=False,
            quiet=False,
        )
        mock_result = {"pages": 0, "groups": 0, "report_html": "", "groups_json": ""}
        with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result) as mock_run:
            result = cmd_analyze(args)
        assert result == 0
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs.get("ocr_strategy") == "llm"

    def test_cmd_analyze_llm_strategy_non_tty_warns_and_continues(self, tmp_path):
        """--ocr-strategy llm で非 TTY の場合、警告ログを出して続行する"""
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            ocr_strategy="llm",
            yes=False,
            verbose=False,
            quiet=False,
        )
        mock_result = {"pages": 0, "groups": 0, "report_html": "", "groups_json": ""}
        with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result), \
             patch("sys.stdin.isatty", return_value=False):
            result = cmd_analyze(args)
        assert result == 0

    def test_cmd_analyze_llm_strategy_tty_user_confirms(self, tmp_path):
        """--ocr-strategy llm で TTY から 'y' を入力したら続行する"""
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            ocr_strategy="llm",
            yes=False,
            verbose=False,
            quiet=False,
        )
        mock_result = {"pages": 0, "groups": 0, "report_html": "", "groups_json": ""}
        with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result), \
             patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", return_value="y"):
            result = cmd_analyze(args)
        assert result == 0

    def test_cmd_analyze_llm_strategy_tty_user_aborts(self, tmp_path):
        """--ocr-strategy llm で TTY から 'n' を入力したら 1 を返す"""
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            ocr_strategy="llm",
            yes=False,
            verbose=False,
            quiet=False,
        )
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", return_value="n"):
            result = cmd_analyze(args)
        assert result == 1

    def test_cmd_analyze_print_uses_user_friendly_terms(self, tmp_path, capsys):
        """issue #50: cmd_analyze の print 出力に「編集画面」「分割設定」が含まれること

        「report.html」「groups.json」といった内部用語を直接表示しないこと。
        """
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            ocr_strategy="balanced",
            yes=False,
            profile=None,
            verbose=False,
            quiet=False,
        )
        mock_result = {
            "pages": 3,
            "groups": 2,
            "report_html": str(tmp_path / "report.html"),
            "groups_json": str(tmp_path / "groups.json"),
        }
        with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result):
            cmd_analyze(args)
        captured = capsys.readouterr()
        # ユーザー向けラベルが使われていること（パス自体は含まれて良い）
        assert "編集画面:" in captured.out, \
            f"issue #50: 「編集画面:」ラベルが CLI 出力にない: {captured.out!r}"
        assert "分割設定:" in captured.out, \
            f"issue #50: 「分割設定:」ラベルが CLI 出力にない: {captured.out!r}"
        # 「レポート:」「groups.json:」という内部用語ラベルが消えていること
        assert "レポート:" not in captured.out, \
            f"issue #50: 内部用語ラベル「レポート:」が CLI 出力に残っている: {captured.out!r}"
        assert "groups.json:" not in captured.out, \
            f"issue #50: 内部用語ラベル「groups.json:」が CLI 出力に残っている: {captured.out!r}"


class TestCmdSplit:
    def test_cmd_split_file_not_found(self, tmp_path):
        """groups.json がない場合 FileNotFoundError をキャッチして 2 を返す"""
        from pdf_split_autorenamer.cli import cmd_split
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            dry_run=False,
            force=False,
            verbose=False,
            quiet=False,
        )
        result = cmd_split(args)
        assert result == 2

    def test_cmd_split_dry_run_success(self, tmp_path):
        """dry_run=True で正常に 0 を返す"""
        from pdf_split_autorenamer.cli import cmd_split
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            dry_run=True,
            force=False,
            verbose=False,
            quiet=False,
        )
        mock_result = {
            "total_input_pages": 2,
            "files_written": 0,
            "total_output_pages": 0,
            "files_skipped": 0,
            "actions": [{"status": "dry-run", "out": "a.pdf", "range": [1, 1]}],
        }
        with patch("pdf_split_autorenamer.split.run_split", return_value=mock_result):
            result = cmd_split(args)
        assert result == 0

    def test_cmd_split_non_dry_run_prints_stats(self, tmp_path, capsys):
        """dry_run=False のとき書き出し/スキップ件数が出力される（lines 62-63, 74）"""
        from pdf_split_autorenamer.cli import cmd_split
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            dry_run=False,
            force=False,
            verbose=False,
            quiet=False,
        )
        mock_result = {
            "total_input_pages": 3,
            "files_written": 1,
            "total_output_pages": 2,
            "files_skipped": 1,
            "actions": [{"status": "ok", "out": "a.pdf", "range": [1, 2]}],
        }
        with patch("pdf_split_autorenamer.split.run_split", return_value=mock_result):
            result = cmd_split(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "書き出し" in captured.out
        assert "スキップ" in captured.out


class TestCmdRename:
    def test_cmd_rename_returns_zero(self, tmp_path):
        """run_rename が正常に返ったとき 0 を返す"""
        from pdf_split_autorenamer.cli import cmd_rename
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            apply=False,
            retarget_unknown=False,
            all=False,
            pdftotext=None,
            no_ocr_fallback=False,
            profile=None,
            verbose=False,
            quiet=False,
        )
        mock_result = {
            "targets": 0,
            "actions": [],
            "applied": 0,
        }
        with patch("pdf_split_autorenamer.rename.run_rename", return_value=mock_result):
            result = cmd_rename(args)
        assert result == 0

    def test_cmd_rename_retarget_unknown_mode(self, tmp_path):
        """--retarget-unknown のとき mode='unknown' で run_rename が呼ばれる"""
        from pdf_split_autorenamer.cli import cmd_rename
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            apply=False,
            retarget_unknown=True,
            all=False,
            pdftotext=None,
            no_ocr_fallback=False,
            profile=None,
            verbose=False,
            quiet=False,
        )
        mock_result = {"targets": 0, "actions": [], "applied": 0}
        with patch("pdf_split_autorenamer.rename.run_rename", return_value=mock_result) as mock_run:
            cmd_rename(args)
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("mode") == "unknown" or call_kwargs.args[1] == "unknown"

    def test_cmd_rename_all_mode(self, tmp_path):
        """--all のとき mode='all' で run_rename が呼ばれる"""
        from pdf_split_autorenamer.cli import cmd_rename
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            apply=False,
            retarget_unknown=False,
            all=True,
            pdftotext=None,
            no_ocr_fallback=False,
            profile=None,
            verbose=False,
            quiet=False,
        )
        mock_result = {"targets": 0, "actions": [], "applied": 0}
        with patch("pdf_split_autorenamer.rename.run_rename", return_value=mock_result) as mock_run:
            cmd_rename(args)
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("mode") == "all" or call_kwargs.args[1] == "all"


class TestMain:
    def test_main_calls_subcommand(self, tmp_path):
        """main() が正しくサブコマンドを呼び出す"""
        mock_result = {"pages": 0, "groups": 0, "report_html": "", "groups_json": ""}
        with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result):
            result = main(["analyze", str(tmp_path)])
        assert result == 0


class TestGetVersion:
    def test_returns_version_string(self):
        """_get_version() が文字列を返す"""
        from pdf_split_autorenamer.cli import _get_version
        result = _get_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_when_importlib_raises(self):
        """importlib.metadata.version が例外を起こしたとき '0.4.0' を返す（lines 133-134）"""
        from pdf_split_autorenamer.cli import _get_version
        with patch("importlib.metadata.version", side_effect=Exception("not found")):
            result = _get_version()
        assert result == "0.4.0"


class TestStdoutReconfigure:
    def test_reconfigure_exception_is_swallowed(self):
        """stdout.reconfigure が例外を出しても握り潰される (cli.py lines 13-14)"""
        import importlib
        import sys
        import pdf_split_autorenamer.cli as cli_mod

        def raise_attr(encoding):
            raise AttributeError("reconfigure not supported in this environment")

        original = sys.stdout.reconfigure
        sys.stdout.reconfigure = raise_attr
        try:
            importlib.reload(cli_mod)
        finally:
            sys.stdout.reconfigure = original


class TestMainModule:
    def test_cli_py_if_main_guard(self, tmp_path):
        """cli.py の if __name__ == '__main__' ガードをカバー (line 200)"""
        import runpy
        mock_result = {"pages": 0, "groups": 0, "report_html": "", "groups_json": ""}
        with patch("sys.argv", ["psar", "analyze", str(tmp_path)]):
            with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result):
                with pytest.raises(SystemExit) as exc_info:
                    runpy.run_module("pdf_split_autorenamer.cli", run_name="__main__")
        assert exc_info.value.code == 0

    def test_package_main_guard(self):
        """__main__.py の if __name__ == '__main__' ガードをカバー (lines 5-6)"""
        import runpy
        with patch("pdf_split_autorenamer.cli.main", return_value=0):
            with pytest.raises(SystemExit) as exc_info:
                runpy.run_module("pdf_split_autorenamer", run_name="__main__")
        assert exc_info.value.code == 0


class TestCmdGui:
    def test_cmd_gui_calls_gui_main(self, tmp_path):
        """cmd_gui は gui.main を呼び出す (lines 125-126)"""
        import argparse
        from pdf_split_autorenamer.cli import cmd_gui
        args = argparse.Namespace(folder=str(tmp_path))
        with patch("pdf_split_autorenamer.gui.main", return_value=0):
            result = cmd_gui(args)
        assert result == 0


# ---------------------------------------------------------------------------
# serve サブコマンド
# ---------------------------------------------------------------------------

class TestServeParser:
    def test_serve_folder_arg(self):
        """serve サブコマンドで folder 引数が取得できる"""
        p = build_parser()
        args = p.parse_args(["serve", "./folder"])
        assert args.folder == "./folder"

    def test_serve_work_dir_default_none(self):
        """--work-dir のデフォルトは None"""
        p = build_parser()
        args = p.parse_args(["serve", "./folder"])
        assert args.work_dir is None

    def test_serve_work_dir_custom(self):
        """--work-dir でカスタム作業ディレクトリを指定できる"""
        p = build_parser()
        args = p.parse_args(["serve", "./folder", "--work-dir", "./custom"])
        assert args.work_dir == "./custom"

    def test_serve_port_default(self):
        """--port のデフォルトは 8765"""
        p = build_parser()
        args = p.parse_args(["serve", "./folder"])
        assert args.port == 8765

    def test_serve_port_custom(self):
        """--port でポート番号を変更できる"""
        p = build_parser()
        args = p.parse_args(["serve", "./folder", "--port", "9000"])
        assert args.port == 9000

    def test_serve_no_open_default_false(self):
        """--no-open のデフォルトは False"""
        p = build_parser()
        args = p.parse_args(["serve", "./folder"])
        assert args.no_open is False

    def test_serve_no_open_flag(self):
        """--no-open を付けると True になる"""
        p = build_parser()
        args = p.parse_args(["serve", "./folder", "--no-open"])
        assert args.no_open is True

    def test_serve_has_func(self):
        """serve サブコマンドに func が設定されている"""
        p = build_parser()
        args = p.parse_args(["serve", "./folder"])
        assert callable(args.func)


class TestCmdServe:
    def test_cmd_serve_file_not_found(self, tmp_path):
        """report.html がない場合 FileNotFoundError をキャッチして 2 を返す"""
        from pdf_split_autorenamer.cli import cmd_serve
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            port=8765,
            no_open=True,
        )
        with patch("pdf_split_autorenamer.server.serve_report",
                   side_effect=FileNotFoundError("report.html が見つかりません")):
            result = cmd_serve(args)
        assert result == 2

    def test_cmd_serve_success(self, tmp_path):
        """serve_report が正常に返ると 0 を返す"""
        from pdf_split_autorenamer.cli import cmd_serve
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            port=8765,
            no_open=True,
        )
        with patch("pdf_split_autorenamer.server.serve_report", return_value=None):
            result = cmd_serve(args)
        assert result == 0

    def test_cmd_serve_passes_port(self, tmp_path):
        """指定したポート番号が serve_report に渡される"""
        from pdf_split_autorenamer.cli import cmd_serve
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            port=9999,
            no_open=True,
        )
        with patch("pdf_split_autorenamer.server.serve_report", return_value=None) as mock_serve:
            cmd_serve(args)
        mock_serve.assert_called_once()
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs.get("port") == 9999

    def test_cmd_serve_no_open_passed(self, tmp_path):
        """--no-open が auto_open=False として serve_report に渡される"""
        from pdf_split_autorenamer.cli import cmd_serve
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            work_dir=None,
            port=8765,
            no_open=True,
        )
        with patch("pdf_split_autorenamer.server.serve_report", return_value=None) as mock_serve:
            cmd_serve(args)
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs.get("auto_open") is False


class TestCmdRenameWithActions:
    def test_cmd_rename_with_non_empty_actions(self, tmp_path, capsys):
        """アクションがある場合でもクラッシュせず 0 を返す（出力ループも実行される）"""
        from pdf_split_autorenamer.cli import cmd_rename
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            apply=False,
            retarget_unknown=False,
            all=False,
            pdftotext=None,
            no_ocr_fallback=False,
            profile=None,
            verbose=False,
            quiet=False,
        )
        mock_result = {
            "targets": 1,
            "actions": [
                {
                    "status": "dry-run",
                    "src": "scan_01.pdf",
                    "src_display": "scan_01.pdf",
                    "dst": "2026-04-06_議事録.pdf",
                    "date": "2026-04-06",
                    "kind": "議事録",
                    "head": "議事録テキスト",
                }
            ],
            "applied": 0,
        }
        with patch("pdf_split_autorenamer.rename.run_rename", return_value=mock_result):
            result = cmd_rename(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out or "dry-run" in captured.out

    def test_cmd_rename_apply_prints_completed(self, tmp_path, capsys):
        """apply=True のとき '完了: N 件' が出力される"""
        from pdf_split_autorenamer.cli import cmd_rename
        import argparse
        args = argparse.Namespace(
            folder=str(tmp_path),
            apply=True,
            retarget_unknown=False,
            all=False,
            pdftotext=None,
            no_ocr_fallback=False,
            profile=None,
            verbose=False,
            quiet=False,
        )
        mock_result = {
            "targets": 1,
            "actions": [
                {
                    "status": "ok",
                    "src": "scan_01.pdf",
                    "src_display": "scan_01.pdf",
                    "dst": "2026-04-06_議事録.pdf",
                    "date": "2026-04-06",
                    "kind": "議事録",
                    "head": "",
                }
            ],
            "applied": 1,
        }
        with patch("pdf_split_autorenamer.rename.run_rename", return_value=mock_result):
            result = cmd_rename(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "完了" in captured.out
        assert "1" in captured.out


# ---------------------------------------------------------------------------
# issue #50: サブコマンド help に内部用語が含まれないこと
# ---------------------------------------------------------------------------

def _subcommand_help(cmd: str) -> str:
    """指定サブコマンドの help 文字列を取得する"""
    p = build_parser()
    sub = p._subparsers._actions[-1].choices[cmd]
    formatter = sub._get_formatter()
    formatter.add_usage(sub.usage, sub._actions, sub._mutually_exclusive_groups)
    formatter.add_text(sub.description)
    for ag in sub._action_groups:
        formatter.start_section(ag.title)
        formatter.add_arguments(ag._group_actions)
        formatter.end_section()
    return formatter.format_help()


def _top_help() -> str:
    """psar --help のトップレベル help 文字列を取得する"""
    p = build_parser()
    formatter = p._get_formatter()
    formatter.add_usage(p.usage, p._actions, p._mutually_exclusive_groups)
    formatter.add_text(p.description)
    for ag in p._action_groups:
        formatter.start_section(ag.title)
        formatter.add_arguments(ag._group_actions)
        formatter.end_section()
    return formatter.format_help()


class TestSubcommandHelpNoInternalTerms:
    """issue #50: ユーザーが見る help 文字列に内部用語が露出しないこと"""

    def test_split_help_no_groups_json(self):
        """split サブコマンド help に 'groups.json' が含まれないこと"""
        help_text = _subcommand_help("split")
        assert "groups.json" not in help_text, \
            f"issue #50: split help に 'groups.json' が露出している: {help_text!r}"

    def test_serve_help_no_report_html(self):
        """serve サブコマンド help に 'report.html' が含まれないこと"""
        help_text = _subcommand_help("serve")
        assert "report.html" not in help_text, \
            f"issue #50: serve help に 'report.html' が露出している: {help_text!r}"

    def test_serve_help_no_groups_json(self):
        """serve サブコマンド help に 'groups.json' が含まれないこと"""
        help_text = _subcommand_help("serve")
        assert "groups.json" not in help_text, \
            f"issue #50: serve help に 'groups.json' が露出している: {help_text!r}"

    def test_rename_profile_help_says_glossary(self):
        """issue #50: rename --profile の help に「用語集」が含まれること（analyze と表記を揃える）"""
        help_text = _subcommand_help("rename")
        assert "用語集" in help_text, \
            f"issue #50: rename --profile の help に「用語集」がない: {help_text!r}"

    def test_top_level_split_description_no_groups_json(self):
        """psar --help のサブコマンド一覧に 'groups.json' が含まれないこと"""
        help_text = _top_help()
        assert "groups.json" not in help_text, \
            f"issue #50: トップ help に 'groups.json' が露出している: {help_text!r}"

    def test_top_level_serve_description_no_report_html(self):
        """psar --help のサブコマンド一覧に 'report.html' が含まれないこと"""
        help_text = _top_help()
        assert "report.html" not in help_text, \
            f"issue #50: トップ help に 'report.html' が露出している: {help_text!r}"


# ---------------------------------------------------------------------------
# issue #48: analyze / split が複数ファイル引数をサポートすること (nargs="+")
# ---------------------------------------------------------------------------

class TestAnalyzeMultipleFilesParser:
    def test_analyze_accepts_multiple_files(self):
        """issue #48: analyze に複数のファイルパスを渡せること (nargs="+")"""
        p = build_parser()
        args = p.parse_args(["analyze", "a.pdf", "b.pdf", "c.pdf"])
        assert args.inputs == ["a.pdf", "b.pdf", "c.pdf"]

    def test_analyze_single_file_as_list(self):
        """issue #48: analyze に単一ファイルを渡すと list[str] になること"""
        p = build_parser()
        args = p.parse_args(["analyze", "a.pdf"])
        assert args.inputs == ["a.pdf"]

    def test_analyze_single_folder_as_list(self):
        """issue #48: analyze にフォルダを渡すと list[str] になること"""
        p = build_parser()
        args = p.parse_args(["analyze", "./folder"])
        assert args.inputs == ["./folder"]


class TestSplitMultipleFilesParser:
    def test_split_accepts_multiple_files(self):
        """issue #48: split に複数のファイルパスを渡せること (nargs="+")"""
        p = build_parser()
        args = p.parse_args(["split", "a.pdf", "b.pdf"])
        assert args.inputs == ["a.pdf", "b.pdf"]

    def test_split_single_folder_as_list(self):
        """issue #48: split にフォルダを渡すと list[str] になること"""
        p = build_parser()
        args = p.parse_args(["split", "./folder"])
        assert args.inputs == ["./folder"]


class TestCmdAnalyzeMultipleFiles:
    def test_cmd_analyze_multiple_pdfs(self, tmp_path):
        """issue #48: cmd_analyze に複数 PDF を渡すと run_analyze が list[Path] で呼ばれる"""
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        pdf1 = tmp_path / "a.pdf"
        pdf2 = tmp_path / "b.pdf"
        pdf1.write_bytes(b"%PDF-1.4\n%%EOF\n")
        pdf2.write_bytes(b"%PDF-1.4\n%%EOF\n")
        args = argparse.Namespace(
            inputs=[str(pdf1), str(pdf2)],
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            ocr_strategy="balanced",
            yes=False,
            profile=None,
            verbose=False,
            quiet=False,
        )
        mock_result = {"pages": 0, "groups": 0, "report_html": "", "groups_json": ""}
        with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result) as mock_run:
            result = cmd_analyze(args)
        assert result == 0
        # list[Path] として呼ばれていること
        called_inputs = mock_run.call_args[0][0]
        assert isinstance(called_inputs, list)
        assert all(isinstance(p, Path) for p in called_inputs)

    def test_cmd_analyze_single_folder_still_works(self, tmp_path):
        """issue #48: cmd_analyze に単一フォルダを渡しても動作する（後方互換）"""
        from pdf_split_autorenamer.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(
            inputs=[str(tmp_path)],
            work_dir=None,
            pdftotext=None,
            title="Test",
            no_ocr_fallback=False,
            ocr_strategy="balanced",
            yes=False,
            profile=None,
            verbose=False,
            quiet=False,
        )
        mock_result = {"pages": 0, "groups": 0, "report_html": "", "groups_json": ""}
        with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result):
            result = cmd_analyze(args)
        assert result == 0
