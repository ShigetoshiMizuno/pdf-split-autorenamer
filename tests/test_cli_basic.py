# -*- coding: utf-8 -*-
"""cli.py の基本テスト（main ブランチ用）"""
from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from pdf_split_autorenamer.cli import build_parser, cmd_rename, cmd_split, main


def _make_pdf(path: Path, pages: int = 2) -> Path:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


class TestBuildParser:
    def test_returns_parser(self):
        import argparse
        parser = build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_rename_subcommand_exists(self):
        parser = build_parser()
        args = parser.parse_args(["rename", "/tmp"])
        assert args.cmd == "rename"

    def test_split_subcommand_exists(self):
        parser = build_parser()
        args = parser.parse_args(["split", "/tmp"])
        assert args.cmd == "split"

    def test_analyze_subcommand_exists(self):
        parser = build_parser()
        args = parser.parse_args(["analyze", "/tmp"])
        assert args.cmd == "analyze"

    def test_rename_apply_flag(self):
        parser = build_parser()
        args = parser.parse_args(["rename", "/tmp", "--apply"])
        assert args.apply is True

    def test_rename_retarget_unknown_flag(self):
        parser = build_parser()
        args = parser.parse_args(["rename", "/tmp", "--retarget-unknown"])
        assert args.retarget_unknown is True

    def test_rename_all_flag(self):
        parser = build_parser()
        args = parser.parse_args(["rename", "/tmp", "--all"])
        assert args.all is True

    def test_split_dry_run_flag(self):
        parser = build_parser()
        args = parser.parse_args(["split", "/tmp", "--dry-run"])
        assert args.dry_run is True


class TestCmdAnalyze:
    def test_nonexistent_folder_returns_2(self, tmp_path):
        result = main(["analyze", str(tmp_path / "nonexistent")])
        assert result == 2

    def test_empty_folder_returns_0(self, tmp_path):
        result = main(["analyze", str(tmp_path)])
        assert result == 0

    def test_with_pdf_returns_0(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=2)
        result = main(["analyze", str(tmp_path)])
        assert result == 0


class TestCmdSplit:
    def test_missing_groups_json_returns_2(self, tmp_path):
        result = main(["split", str(tmp_path)])
        assert result == 2

    def test_dry_run_no_groups_json_returns_2(self, tmp_path):
        result = main(["split", str(tmp_path), "--dry-run"])
        assert result == 2

    def test_dry_run_with_groups_json_returns_0(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        result = main(["split", str(tmp_path), "--dry-run"])
        assert result == 0

    def test_actual_split_returns_0(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        result = main(["split", str(tmp_path)])
        assert result == 0
        assert (tmp_path / "scan_01.pdf").exists()


class TestCmdRename:
    def test_no_targets_returns_0(self, tmp_path):
        result = main(["rename", str(tmp_path)])
        assert result == 0

    def test_retarget_unknown_mode(self, tmp_path):
        result = main(["rename", str(tmp_path), "--retarget-unknown"])
        assert result == 0

    def test_all_mode(self, tmp_path):
        result = main(["rename", str(tmp_path), "--all"])
        assert result == 0

    def test_apply_flag_with_target(self, tmp_path):
        src = tmp_path / "scan_01.pdf"
        _make_pdf(src)
        result = main(["rename", str(tmp_path), "--apply"])
        assert result == 0

    def test_dry_run_shows_instructions(self, tmp_path):
        (tmp_path / "scan_01.pdf").write_bytes(b"%PDF-1.4")
        result = main(["rename", str(tmp_path)])
        assert result == 0


class TestSplitUserFriendlyError:
    def test_missing_split_config_error_uses_user_friendly_term(self, tmp_path):
        """issue #50: 分割設定が見つからない場合のエラーメッセージが「分割設定」を使うこと

        内部ファイル名「groups.json」をユーザーに見せず「分割設定」と案内する。
        """
        from pdf_split_autorenamer.split import run_split
        import pytest
        with pytest.raises(FileNotFoundError) as exc_info:
            run_split(tmp_path)
        error_msg = str(exc_info.value)
        assert "分割設定" in error_msg, \
            f"issue #50: FileNotFoundError のメッセージに「分割設定」がない: {error_msg!r}"
