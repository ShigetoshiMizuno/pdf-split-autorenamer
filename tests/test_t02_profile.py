# -*- coding: utf-8 -*-
"""T-02: 外部プロファイル読み込み（TOML）のテスト

テスト対象:
- textops.load_profile() の存在と動作
- 有効な TOML からパターンが正しく読み込まれるか
- title_patterns / body_patterns が re.Pattern のリストとして返るか
- CLI rename サブコマンドに --profile オプションが存在するか
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# load_profile のインポート確認
# ---------------------------------------------------------------------------

class TestLoadProfileExists:
    def test_load_profile_importable(self):
        """textops に load_profile が存在する"""
        from pdf_split_autorenamer import textops
        assert hasattr(textops, "load_profile"), "textops に load_profile が存在しない"

    def test_load_profile_is_callable(self):
        """load_profile が呼び出し可能"""
        from pdf_split_autorenamer.textops import load_profile
        assert callable(load_profile)


# ---------------------------------------------------------------------------
# load_profile の動作テスト
# ---------------------------------------------------------------------------

class TestLoadProfile:
    def test_load_minimal_toml(self, tmp_path: Path):
        """最小限の TOML ファイルを正常に読み込める"""
        toml_content = """\
[[title_patterns]]
pattern = "週報"
label = "週報"

[[body_patterns]]
pattern = "お知らせ"
label = "お知らせ"
"""
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.textops import load_profile
        title_patterns, body_patterns = load_profile(profile_path)

        assert len(title_patterns) == 1
        assert len(body_patterns) == 1

    def test_title_patterns_are_compiled_regex(self, tmp_path: Path):
        """title_patterns の第1要素が re.Pattern である"""
        toml_content = """\
[[title_patterns]]
pattern = "主日礼拝.{0,8}メッセージ要[旨約]"
label = "主日礼拝メッセージ要旨"
"""
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.textops import load_profile
        title_patterns, body_patterns = load_profile(profile_path)

        assert len(title_patterns) == 1
        pat, label = title_patterns[0]
        assert isinstance(pat, re.Pattern), f"re.Pattern を期待したが {type(pat)} だった"
        assert label == "主日礼拝メッセージ要旨"

    def test_body_patterns_are_compiled_regex(self, tmp_path: Path):
        """body_patterns の第1要素が re.Pattern である"""
        toml_content = """\
[[body_patterns]]
pattern = "お知らせ|お和らせ"
label = "お知らせ"
"""
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.textops import load_profile
        title_patterns, body_patterns = load_profile(profile_path)

        assert len(body_patterns) == 1
        pat, label = body_patterns[0]
        assert isinstance(pat, re.Pattern), f"re.Pattern を期待したが {type(pat)} だった"
        assert label == "お知らせ"

    def test_pattern_actually_matches(self, tmp_path: Path):
        """読み込んだパターンで実際にマッチできる"""
        toml_content = """\
[[title_patterns]]
pattern = "週報"
label = "週報"
"""
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.textops import load_profile
        title_patterns, _ = load_profile(profile_path)

        pat, label = title_patterns[0]
        assert pat.search("2026年度週報") is not None
        assert pat.search("月曜日のメモ") is None

    def test_multiple_patterns_loaded_in_order(self, tmp_path: Path):
        """複数パターンが定義順に読み込まれる"""
        toml_content = """\
[[title_patterns]]
pattern = "主日礼拝"
label = "主日礼拝メッセージ要旨"

[[title_patterns]]
pattern = "週報"
label = "週報"

[[title_patterns]]
pattern = "会計報告"
label = "会計報告"
"""
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.textops import load_profile
        title_patterns, _ = load_profile(profile_path)

        assert len(title_patterns) == 3
        labels = [label for _, label in title_patterns]
        assert labels == ["主日礼拝メッセージ要旨", "週報", "会計報告"]

    def test_empty_lists_when_sections_absent(self, tmp_path: Path):
        """title_patterns / body_patterns セクションがない場合は空リストを返す"""
        toml_content = 'name = "test"\n'
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.textops import load_profile
        title_patterns, body_patterns = load_profile(profile_path)

        assert title_patterns == []
        assert body_patterns == []

    def test_returns_tuple_of_two_lists(self, tmp_path: Path):
        """返り値がタプル (list, list) の形式"""
        toml_content = """\
[[title_patterns]]
pattern = "週報"
label = "週報"
"""
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.textops import load_profile
        result = load_profile(profile_path)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)

    def test_name_field_ignored(self, tmp_path: Path):
        """name フィールドが存在しても正常に読み込める"""
        toml_content = """\
name = "church"

[[title_patterns]]
pattern = "週報"
label = "週報"
"""
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.textops import load_profile
        title_patterns, _ = load_profile(profile_path)
        assert len(title_patterns) == 1


# ---------------------------------------------------------------------------
# CLI --profile オプションの存在確認
# ---------------------------------------------------------------------------

class TestCliProfileOption:
    def test_rename_subcommand_has_profile_option(self):
        """rename サブコマンドに --profile オプションが存在する"""
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        # rename サブコマンドを解析して --profile が使えるか確認
        args = parser.parse_args(["rename", "--profile", "church.toml", "."])
        assert hasattr(args, "profile")
        assert args.profile == "church.toml"

    def test_rename_subcommand_profile_default_is_none(self):
        """--profile 未指定のとき args.profile は None"""
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["rename", "."])
        assert hasattr(args, "profile")
        assert args.profile is None


# ---------------------------------------------------------------------------
# run_rename の profile パラメータ確認
# ---------------------------------------------------------------------------

class TestRunRenameProfileParam:
    def test_run_rename_accepts_profile_param(self, tmp_path: Path):
        """run_rename が profile パラメータを受け付ける（空ディレクトリで動作確認）"""
        from pdf_split_autorenamer.rename import run_rename
        import inspect
        sig = inspect.signature(run_rename)
        assert "profile" in sig.parameters, "run_rename に profile パラメータが存在しない"

    def test_run_rename_profile_default_is_none(self):
        """run_rename の profile パラメータのデフォルトが None"""
        from pdf_split_autorenamer.rename import run_rename
        import inspect
        sig = inspect.signature(run_rename)
        assert sig.parameters["profile"].default is None

    def test_run_rename_with_profile_toml(self, tmp_path: Path):
        """profile TOML を指定して run_rename を実行できる（対象なしでも例外なし）"""
        toml_content = """\
[[title_patterns]]
pattern = "週報"
label = "週報"
"""
        profile_path = tmp_path / "test.toml"
        profile_path.write_text(toml_content, encoding="utf-8")

        from pdf_split_autorenamer.rename import run_rename
        result = run_rename(tmp_path, mode="split", apply=False, profile=profile_path)
        assert result["targets"] == 0
