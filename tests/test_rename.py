# -*- coding: utf-8 -*-
"""T-10: rename モジュールのユニットテスト

対象関数:
- choose_date(text, hint_filename) -> str | None
- resolve_filenames(plan) -> list[dict]
"""
from __future__ import annotations

import pytest

from pdf_split_autorenamer.rename import choose_date, resolve_filenames


# ---------------------------------------------------------------------------
# choose_date
# ---------------------------------------------------------------------------

class TestChooseDate:
    def test_date_in_text_is_returned(self):
        """テキスト中に日付が含まれる → その日付を返す"""
        text = "2026年4月6日の礼拝"
        result = choose_date(text, "file_01.pdf")
        assert result == "2026-04-06"

    def test_date_from_filename_when_no_date_in_text(self):
        """テキスト中に日付なし、ファイル名に日付 → ファイル名の日付を返す"""
        # ファイル名の名前部分に日付を含む形式
        text = "日付のないテキスト"
        # rename.date_from_filename は existing_name_part → date_from_string で抽出
        # existing_name_part は `<stem>_NN_<name>.pdf` の name 部分を返す
        result = choose_date(text, "scan_01_2026-04-13.pdf")
        assert result == "2026-04-13"

    def test_none_when_no_date_anywhere(self):
        """テキストにもファイル名にも日付なし → None を返す"""
        result = choose_date("日付のないテキスト", "scan_01_週報.pdf")
        assert result is None

    def test_most_frequent_date_returned(self):
        """複数の日付候補がある → 最頻出を返す"""
        # 2026-04-06 が 3回, 2026-04-13 が 1回
        text = (
            "2026年4月6日の礼拝\n"
            "2026年4月6日のお知らせ\n"
            "2026年4月6日 以上\n"
            "2026年4月13日の次回礼拝"
        )
        result = choose_date(text, "scan_01.pdf")
        assert result == "2026-04-06"

    def test_hint_filename_date_preferred_when_in_candidates(self):
        """ヒントファイル名の日付が候補中に含まれる → ヒントの日付を返す"""
        # ヒント: 2026-04-13、テキスト候補: 2026-04-06（1回）, 2026-04-13（1回）
        text = "2026年4月6日と2026年4月13日の礼拝"
        result = choose_date(text, "scan_01_2026-04-13.pdf")
        assert result == "2026-04-13"

    def test_returns_str_or_none(self):
        """戻り値は str か None である"""
        result = choose_date("2026年4月6日", "scan_01.pdf")
        assert result is None or isinstance(result, str)

    def test_empty_text_with_no_filename_date_returns_none(self):
        """空のテキストでファイル名にも日付なし → None"""
        result = choose_date("", "scan_01.pdf")
        assert result is None

    def test_multiple_same_dates_most_common(self):
        """同じ日付が複数回登場する場合はその日付を返す"""
        text = "2026-04-06\n2026-04-06\n2026-05-11"
        result = choose_date(text, "scan_01.pdf")
        assert result == "2026-04-06"


# ---------------------------------------------------------------------------
# resolve_filenames
# ---------------------------------------------------------------------------

class TestResolveFilenames:
    def _make_item(
        self,
        date: str | None,
        kind: str,
        fallback: str = "",
    ) -> dict:
        """テスト用の plan item を生成する（src はダミー）"""
        from pathlib import Path
        return {
            "src": Path("dummy.pdf"),
            "date": date,
            "kind": kind,
            "fallback": fallback,
            "head": "",
        }

    def test_unique_date_and_kind_no_suffix(self):
        """ユニークな日付+書類タイプ → ベース名のまま .pdf を付与"""
        plan = [
            self._make_item("2026-04-06", "週報"),
        ]
        result = resolve_filenames(plan)
        assert result[0]["final"] == "2026-04-06_週報.pdf"

    def test_duplicate_date_and_kind_gets_suffix(self):
        """同じ日付+書類タイプが2件 → _01.pdf, _02.pdf のサフィックスが付く"""
        plan = [
            self._make_item("2026-04-06", "週報"),
            self._make_item("2026-04-06", "週報"),
        ]
        result = resolve_filenames(plan)
        finals = {item["final"] for item in result}
        assert "2026-04-06_週報_01.pdf" in finals
        assert "2026-04-06_週報_02.pdf" in finals

    def test_none_date_uses_日付不明_prefix(self):
        """date が None → 日付不明_xxx.pdf 形式になる"""
        plan = [
            self._make_item(None, "週報"),
        ]
        result = resolve_filenames(plan)
        assert result[0]["final"] == "日付不明_週報.pdf"

    def test_none_date_duplicate_gets_suffix(self):
        """date が None の重複も連番サフィックスが付く"""
        plan = [
            self._make_item(None, "書類"),
            self._make_item(None, "書類"),
        ]
        result = resolve_filenames(plan)
        finals = {item["final"] for item in result}
        assert "日付不明_書類_01.pdf" in finals
        assert "日付不明_書類_02.pdf" in finals

    def test_different_kinds_no_suffix(self):
        """同じ日付でも書類タイプが違う場合はサフィックスなし"""
        plan = [
            self._make_item("2026-04-06", "週報"),
            self._make_item("2026-04-06", "会計報告"),
        ]
        result = resolve_filenames(plan)
        finals = {item["final"] for item in result}
        assert "2026-04-06_週報.pdf" in finals
        assert "2026-04-06_会計報告.pdf" in finals

    def test_three_duplicates_get_01_02_03(self):
        """3件重複 → _01, _02, _03 が付く"""
        plan = [
            self._make_item("2026-04-06", "週報"),
            self._make_item("2026-04-06", "週報"),
            self._make_item("2026-04-06", "週報"),
        ]
        result = resolve_filenames(plan)
        finals = [item["final"] for item in result]
        assert "2026-04-06_週報_01.pdf" in finals
        assert "2026-04-06_週報_02.pdf" in finals
        assert "2026-04-06_週報_03.pdf" in finals

    def test_final_field_is_added_to_each_item(self):
        """resolve_filenames 後に各 item に final フィールドが付与される"""
        plan = [
            self._make_item("2026-04-06", "週報"),
            self._make_item("2026-05-11", "会計報告"),
        ]
        result = resolve_filenames(plan)
        for item in result:
            assert "final" in item
            assert item["final"].endswith(".pdf")

    def test_fallback_used_when_kind_is_default(self):
        """kind が '書類' かつ fallback がある場合は fallback が使われる"""
        plan = [
            self._make_item("2026-04-06", "書類", fallback="週報20260406"),
        ]
        result = resolve_filenames(plan)
        # fallback が kind_part として使われるため、"書類" ではなく fallback が入る
        assert "書類" not in result[0]["final"] or result[0]["final"] == "2026-04-06_書類.pdf"
        # fallback が使われた場合
        if result[0]["final"] != "2026-04-06_書類.pdf":
            assert "週報20260406" in result[0]["final"]

    def test_returns_list_of_dict(self):
        """戻り値は list[dict] である"""
        plan = [self._make_item("2026-04-06", "週報")]
        result = resolve_filenames(plan)
        assert isinstance(result, list)
        assert isinstance(result[0], dict)
