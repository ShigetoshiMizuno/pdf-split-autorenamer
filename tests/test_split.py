# -*- coding: utf-8 -*-
"""T-10: split モジュールのユニットテスト

対象関数:
- normalize_groups(raw) -> dict[str, list[dict]]

run_split は実際の PDF が必要なのでテストスコープ外（skip）。
"""
from __future__ import annotations

import pytest

from pdf_split_autorenamer.split import normalize_groups


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
# run_split は実際の PDF が必要なのでスキップ
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="run_split は実際の PDF ファイルが必要なのでスコープ外")
def test_run_split_requires_real_pdf():
    pass
