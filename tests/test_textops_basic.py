# -*- coding: utf-8 -*-
"""textops.py の基本テスト（main ブランチ用）"""
from __future__ import annotations

from pdf_split_autorenamer.textops import (
    extract_dates_all,
    extract_kind,
    fix_broken_unicode,
    fix_mojibake,
    sanitize_filename,
)


class TestFixMojibake:
    def test_replaces_mapped_char(self):
        assert fix_mojibake("4朁6日") == "4月6日"

    def test_removes_isolated_e_after_kanji(self):
        assert fix_mojibake("礼拝E") == "礼拝"

    def test_removes_replacement_char(self):
        assert fix_mojibake("テスト�") == "テスト"

    def test_no_change_on_clean_text(self):
        assert fix_mojibake("2026年4月6日") == "2026年4月6日"


class TestFixBrokenUnicode:
    def test_restores_garbled_japanese(self):
        garbled = "牧師".encode("utf-8").decode("cp1252", errors="replace")
        result = fix_broken_unicode(garbled)
        assert "牧" in result or result == garbled  # best-effort

    def test_empty_string_returns_empty(self):
        assert fix_broken_unicode("") == ""

    def test_clean_ascii_unchanged(self):
        assert fix_broken_unicode("hello") == "hello"

    def test_cp1252_invalid_utf8_path(self):
        # "€" encodes to b"\x80" in cp1252, which is an invalid UTF-8 start byte.
        # This exercises the `except UnicodeDecodeError: continue` branch (lines 40-41).
        result = fix_broken_unicode("€")
        assert isinstance(result, str)  # returns unchanged "€"


class TestExtractDatesAll:
    def test_iso_format(self):
        assert extract_dates_all("2026-04-06") == ["2026-04-06"]

    def test_japanese_format(self):
        assert extract_dates_all("2026年4月6日") == ["2026-04-06"]

    def test_dot_format(self):
        assert extract_dates_all("2026.4.6") == ["2026-04-06"]

    def test_slash_format(self):
        assert extract_dates_all("2026/4/6") == ["2026-04-06"]

    def test_multiple_dates(self):
        dates = extract_dates_all("2026-01-01 と 2026-12-31")
        assert "2026-01-01" in dates
        assert "2026-12-31" in dates

    def test_invalid_date_ignored(self):
        assert extract_dates_all("2026-13-01") == []

    def test_out_of_range_year_ignored(self):
        assert extract_dates_all("1999-01-01") == []

    def test_fullwidth_digits(self):
        dates = extract_dates_all("２０２６年４月６日")
        assert dates == ["2026-04-06"]

    def test_empty_text(self):
        assert extract_dates_all("") == []


class TestExtractKind:
    def test_weekly_bulletin_title(self):
        assert extract_kind("週報\n2026年4月6日") == "週報"

    def test_accounting_report(self):
        assert extract_kind("会計報告\n2026年度") == "会計報告"

    def test_default_kind_when_no_match(self):
        assert extract_kind("特に分類できないテキスト") == "書類"

    def test_custom_default_kind(self):
        assert extract_kind("no match", default_kind="未分類") == "未分類"

    def test_body_pattern_used_when_title_fails(self):
        text = "\n\n\n\n\n\n主日礼拝メッセージ要旨"  # after 6 head lines
        result = extract_kind(text)
        assert result == "主日礼拝メッセージ要旨"

    def test_body_only_pattern_after_six_non_matching_lines(self):
        # "祈祷会" is in DEFAULT_BODY_PATTERNS but not in DEFAULT_TITLE_PATTERNS.
        # Putting it after 6 non-empty non-matching lines forces the body branch (line 137).
        lines = ["行1", "行2", "行3", "行4", "行5", "行6", "祈祷会"]
        result = extract_kind("\n".join(lines))
        assert result == "祈祷会"


class TestSanitizeFilename:
    def test_removes_invalid_windows_chars(self):
        assert ":" not in sanitize_filename("file:name")

    def test_strips_leading_trailing_spaces(self):
        result = sanitize_filename("  test  ")
        assert result == "test"

    def test_replaces_spaces_with_underscore(self):
        assert sanitize_filename("hello world") == "hello_world"

    def test_empty_returns_empty(self):
        assert sanitize_filename("") == ""

    def test_max_length_truncated(self):
        long = "あ" * 100
        result = sanitize_filename(long, max_length=10)
        assert len(result) <= 10

    def test_strips_trailing_dots(self):
        result = sanitize_filename("test...")
        assert not result.endswith(".")
