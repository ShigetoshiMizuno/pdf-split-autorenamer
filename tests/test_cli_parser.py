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
