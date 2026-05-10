# -*- coding: utf-8 -*-
"""T-10: split モジュールのユニットテスト

対象関数:
- normalize_groups(raw) -> dict[str, list[dict]]
- run_split（groups.json + 実際の PDF を使った統合テスト）

run_split の純 Python ロジック（missing PDF, out-of-range, dry-run, skip-exists）は
PDF を生成して確認する。
"""
from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from pdf_split_autorenamer.split import normalize_groups, run_split
from pdf_split_autorenamer.textops import sanitize_filename


# ---------------------------------------------------------------------------
# normalize_groups
# ---------------------------------------------------------------------------

class TestNormalizeGroups:
    def test_old_schema_list_pair_is_normalized(self):
        """旧スキーマ（list of [from, to] ペア）が正規化される"""
        raw = {
            "file.pdf": [
                [1, 3],
                [4, 6],
            ]
        }
        result = normalize_groups(raw)
        assert "file.pdf" in result
        assert result["file.pdf"] == [
            {"range": [1, 3], "name": ""},
            {"range": [4, 6], "name": ""},
        ]

    def test_new_schema_dict_is_preserved(self):
        """新スキーマ（list of {range: [from, to], name: str}）がそのまま維持される"""
        raw = {
            "file.pdf": [
                {"range": [1, 3], "name": "週報"},
                {"range": [4, 6], "name": "会計報告"},
            ]
        }
        result = normalize_groups(raw)
        assert result["file.pdf"] == [
            {"range": [1, 3], "name": "週報"},
            {"range": [4, 6], "name": "会計報告"},
        ]

    def test_invalid_entries_are_skipped(self):
        """不正な形式のエントリがスキップされる"""
        raw = {
            "file.pdf": [
                [1, 3],           # 正常な旧スキーマ
                "invalid_string", # 不正（文字列）
                {"range": [4, 6], "name": ""},  # 正常な新スキーマ
                {"no_range": True},              # 不正（range なし）
                [1],              # 不正（要素が 1 つしかない）
            ]
        }
        result = normalize_groups(raw)
        assert "file.pdf" in result
        assert len(result["file.pdf"]) == 2
        assert result["file.pdf"][0]["range"] == [1, 3]
        assert result["file.pdf"][1]["range"] == [4, 6]

    def test_empty_name_is_ok(self):
        """name が空文字列でも OK"""
        raw = {
            "file.pdf": [
                {"range": [1, 5], "name": ""},
            ]
        }
        result = normalize_groups(raw)
        assert result["file.pdf"][0]["name"] == ""

    def test_multiple_pdfs_normalized(self):
        """複数の PDF キーを持つ dict が正規化される"""
        raw = {
            "a.pdf": [[1, 2]],
            "b.pdf": [{"range": [1, 3], "name": "週報"}],
        }
        result = normalize_groups(raw)
        assert "a.pdf" in result
        assert "b.pdf" in result
        assert result["a.pdf"][0]["range"] == [1, 2]
        assert result["b.pdf"][0]["name"] == "週報"

    def test_empty_dict_returns_empty_dict(self):
        """空の dict を渡すと空の dict を返す"""
        result = normalize_groups({})
        assert result == {}

    def test_empty_items_list_returns_empty_list(self):
        """items リストが空の場合は空リストを返す"""
        raw = {"file.pdf": []}
        result = normalize_groups(raw)
        assert result["file.pdf"] == []

    def test_range_values_are_converted_to_int(self):
        """range の値が int に変換される"""
        raw = {
            "file.pdf": [
                {"range": ["1", "5"], "name": ""},
            ]
        }
        result = normalize_groups(raw)
        r = result["file.pdf"][0]["range"]
        assert isinstance(r[0], int)
        assert isinstance(r[1], int)
        assert r == [1, 5]

    def test_old_schema_tuple_is_accepted(self):
        """旧スキーマとして tuple も受け付ける"""
        raw = {
            "file.pdf": [
                (1, 3),
            ]
        }
        result = normalize_groups(raw)
        assert result["file.pdf"][0]["range"] == [1, 3]


# ---------------------------------------------------------------------------
# sanitize_filename（textops.sanitize_filename を split から利用）
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_removes_forbidden_chars(self):
        """Windows 禁止文字 (<>:"/\\|?*) を除去する"""
        result = sanitize_filename('file<>:"/\\|?*.pdf')
        for ch in '<>:"/\\|?*':
            assert ch not in result

    def test_replaces_whitespace_with_underscore(self):
        """空白をアンダースコアに変換する"""
        result = sanitize_filename("hello world")
        assert " " not in result
        assert "_" in result

    def test_empty_string_returns_empty(self):
        """空文字列は空文字列を返す"""
        assert sanitize_filename("") == ""

    def test_normal_japanese_name_unchanged(self):
        """禁止文字がない日本語ファイル名はそのまま返る"""
        result = sanitize_filename("週報2026年4月")
        assert result == "週報2026年4月"

    def test_max_length_80(self):
        """デフォルト max_length=80 で切り詰められる"""
        result = sanitize_filename("a" * 100)
        assert len(result) <= 80

    def test_custom_max_length(self):
        """max_length を指定するとその長さに切り詰められる"""
        result = sanitize_filename("a" * 50, max_length=10)
        assert len(result) <= 10

    def test_trailing_dots_and_spaces_removed(self):
        """末尾のピリオドと空白が除去される"""
        result = sanitize_filename("filename. ")
        assert not result.endswith(".")
        assert not result.endswith(" ")


# ---------------------------------------------------------------------------
# run_split — groups.json + PDF を使った統合テスト
# ---------------------------------------------------------------------------

def _make_multipage_pdf(pages: list[str]) -> bytes:
    """複数ページの PDF を bytes で返す"""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    data = doc.write()
    doc.close()
    return data


def _write_groups_json(work_dir: Path, content: dict) -> Path:
    """work_dir に groups.json を書き込んで Path を返す"""
    work_dir.mkdir(parents=True, exist_ok=True)
    p = work_dir / "groups.json"
    p.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return p


class TestRunSplit:
    def test_raises_if_no_groups_json(self, tmp_path):
        """groups.json が存在しない場合 FileNotFoundError が発生する"""
        with pytest.raises(FileNotFoundError):
            run_split(tmp_path)

    def test_missing_pdf_logged_as_missing(self, tmp_path):
        """PDF が存在しない場合、actions に status='missing' が入る"""
        _write_groups_json(
            tmp_path / ".psar",
            {"nonexistent.pdf": [{"range": [1, 1], "name": ""}]},
        )
        result = run_split(tmp_path)
        statuses = [a["status"] for a in result["actions"]]
        assert "missing" in statuses

    def test_dry_run_does_not_write_files(self, tmp_path):
        """dry_run=True では PDF ファイルが書き出されない"""
        src = tmp_path / "source.pdf"
        src.write_bytes(_make_multipage_pdf(["Page1", "Page2"]))
        _write_groups_json(
            tmp_path / ".psar",
            {"source.pdf": [{"range": [1, 1], "name": ""}]},
        )
        result = run_split(tmp_path, dry_run=True)
        # 書き出しなし
        assert result["files_written"] == 0
        statuses = [a["status"] for a in result["actions"]]
        assert "dry-run" in statuses

    def test_out_of_range_group_skipped(self, tmp_path):
        """範囲外ページを指定したグループはスキップされる"""
        src = tmp_path / "source.pdf"
        src.write_bytes(_make_multipage_pdf(["Page1"]))
        _write_groups_json(
            tmp_path / ".psar",
            {"source.pdf": [{"range": [1, 99], "name": ""}]},
        )
        result = run_split(tmp_path)
        statuses = [a["status"] for a in result["actions"]]
        assert "out-of-range" in statuses

    def test_split_writes_file(self, tmp_path):
        """正常なグループ指定で PDF が書き出される"""
        src = tmp_path / "source.pdf"
        src.write_bytes(_make_multipage_pdf(["Page1", "Page2"]))
        _write_groups_json(
            tmp_path / ".psar",
            {"source.pdf": [{"range": [1, 1], "name": "週報"}]},
        )
        result = run_split(tmp_path)
        assert result["files_written"] == 1
        assert (tmp_path / "source_01_週報.pdf").exists()

    def test_skip_existing_without_force(self, tmp_path):
        """既存ファイルがある場合 force=False でスキップされる"""
        src = tmp_path / "source.pdf"
        src.write_bytes(_make_multipage_pdf(["Page1", "Page2"]))
        # 出力先ファイルを事前に作成
        (tmp_path / "source_01.pdf").write_bytes(b"dummy")
        _write_groups_json(
            tmp_path / ".psar",
            {"source.pdf": [{"range": [1, 1], "name": ""}]},
        )
        result = run_split(tmp_path, force=False)
        statuses = [a["status"] for a in result["actions"]]
        assert "skip-exists" in statuses
        assert result["files_skipped"] == 1
