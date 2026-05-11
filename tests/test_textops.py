# -*- coding: utf-8 -*-
"""T-10a: textops モジュールのユニットテスト

対象関数:
- fix_mojibake
- fix_broken_unicode
- extract_dates_all
- extract_kind
- sanitize_filename
"""
from __future__ import annotations

import pytest

from pdf_split_autorenamer.textops import (
    MOJIBAKE_FIX,
    extract_dates_all,
    extract_kind,
    fix_broken_unicode,
    fix_mojibake,
    sanitize_filename,
)


# ---------------------------------------------------------------------------
# fix_mojibake
# ---------------------------------------------------------------------------

class TestFixMojibake:
    def test_mojibake_mapping_朁(self):
        """朁 → 月 に置換される"""
        assert fix_mojibake("朁曜日") == "月曜日"

    def test_mojibake_mapping_拁(self):
        """拁 → 拝 に置換される"""
        assert fix_mojibake("礼拁") == "礼拝"

    def test_mojibake_mapping_紁(self):
        """紁 → 旨 に置換される"""
        assert fix_mojibake("紁意") == "旨意"

    def test_mojibake_mapping_迁(self):
        """迁 → 迎 に置換される"""
        assert fix_mojibake("歓迁") == "歓迎"

    def test_mojibake_mapping_曁(self):
        """曁 → 曜 に置換される"""
        assert fix_mojibake("日曁日") == "日曜日"

    def test_all_mojibake_keys_covered(self):
        """MOJIBAKE_FIX の全キーが正しく置換されること"""
        for k, v in MOJIBAKE_FIX.items():
            result = fix_mojibake(k)
            assert result == v, f"{k!r} → {v!r} の置換が失敗: {result!r}"

    def test_isolated_E_after_kanji_removed(self):
        """漢字直後の孤立 E が除去される"""
        assert fix_mojibake("礼拝E") == "礼拝"

    def test_E_with_following_alpha_not_removed(self):
        """E の後に英字が続く場合は除去されない"""
        result = fix_mojibake("礼拝EX")
        assert "E" in result, f"礼拝EX の E が誤って除去された: {result!r}"

    def test_replacement_character_removed(self):
        """U+FFFD（文字化け文字）が除去される"""
        assert fix_mojibake("テスト�文書") == "テスト文書"

    def test_empty_string(self):
        """空文字列を渡しても動作する"""
        assert fix_mojibake("") == ""

    def test_no_change_for_normal_text(self):
        """変換対象がない通常の文字列は変化しない"""
        s = "主日礼拝メッセージ要旨"
        assert fix_mojibake(s) == s


# ---------------------------------------------------------------------------
# fix_broken_unicode
# ---------------------------------------------------------------------------

class TestFixBrokenUnicode:
    def test_cp1252_mojibake_restored(self):
        """cp1252 化け文字列が正しく復元される: '牧師' の UTF-8 バイトを cp1252 で読んだ化けを復元"""
        # '牧師'.encode('utf-8') = b'\xe7\x89\xa7\xe5\xb8\xab'
        # b'\xe7\x89\xa7\xe5\xb8\xab'.decode('cp1252') = 'ç‰§å¸«'
        mojibake = "牧師".encode("utf-8").decode("cp1252")
        result = fix_broken_unicode(mojibake)
        assert result == "牧師", f"復元失敗: {result!r}"

    def test_normal_string_unchanged(self):
        """日本語を含まない通常の文字列は変化しない"""
        s = "hello world"
        assert fix_broken_unicode(s) == s

    def test_empty_string(self):
        """空文字列は空文字列を返す"""
        assert fix_broken_unicode("") == ""

    def test_pure_japanese_unchanged(self):
        """正常な日本語文字列はそのまま返る（化けていない）"""
        s = "主日礼拝"
        # 正常な日本語は cp1252 でエンコードできないため変換されない
        result = fix_broken_unicode(s)
        assert result == s


# ---------------------------------------------------------------------------
# extract_dates_all
# ---------------------------------------------------------------------------

class TestExtractDatesAll:
    def test_japanese_date_format(self):
        """2026年4月6日 → ['2026-04-06']"""
        assert extract_dates_all("2026年4月6日") == ["2026-04-06"]

    def test_dot_separator(self):
        """2026.04.06 → ['2026-04-06']"""
        assert extract_dates_all("2026.04.06") == ["2026-04-06"]

    def test_slash_separator(self):
        """2026/04/06 → ['2026-04-06']"""
        assert extract_dates_all("2026/04/06") == ["2026-04-06"]

    def test_hyphen_separator(self):
        """2026-04-06 → ['2026-04-06']"""
        assert extract_dates_all("2026-04-06") == ["2026-04-06"]

    def test_fullwidth_digits_japanese_format(self):
        """全角数字の和暦 ２０２６年４月６日 → ['2026-04-06']"""
        assert extract_dates_all("２０２６年４月６日") == ["2026-04-06"]

    def test_year_out_of_range_1999(self):
        """1999年は範囲外（2000年未満）なので除外される"""
        assert extract_dates_all("1999年4月6日") == []

    def test_year_out_of_range_2101(self):
        """2101年は範囲外（2100年超）なので除外される"""
        assert extract_dates_all("2101年4月6日") == []

    def test_month_zero_excluded(self):
        """月が 0 の日付は除外される"""
        assert extract_dates_all("2026年0月6日") == []

    def test_day_zero_excluded(self):
        """日が 0 の日付は除外される"""
        assert extract_dates_all("2026年4月0日") == []

    def test_multiple_dates_returned(self):
        """複数日付が含まれる場合はすべて返す"""
        text = "2026年4月6日と2026年4月13日"
        result = extract_dates_all(text)
        assert "2026-04-06" in result
        assert "2026-04-13" in result
        assert len(result) == 2

    def test_empty_string(self):
        """空文字列は空リストを返す"""
        assert extract_dates_all("") == []

    def test_no_date_in_text(self):
        """日付がない文字列は空リストを返す"""
        assert extract_dates_all("主日礼拝メッセージ") == []


# ---------------------------------------------------------------------------
# extract_kind
# ---------------------------------------------------------------------------

class TestExtractKind:
    def test_body_contains_invoice(self):
        """本文に '請求' が含まれれば '請求書' を返す"""
        text = "この文書は\n請求書\nテキスト"
        assert extract_kind(text) == "請求書"

    def test_head_contains_minutes(self):
        """先頭行に '議事録' が含まれれば '議事録' を返す"""
        text = "議事録\n2026年4月6日"
        assert extract_kind(text) == "議事録"

    def test_no_match_returns_default(self):
        """何もマッチしなければデフォルト '書類' を返す"""
        text = "ランダムなテキストです"
        assert extract_kind(text) == "書類"

    def test_notice_pattern_matched(self):
        """'お知らせ' が含まれれば '通知書' を返す"""
        text = "お知らせ\n詳細内容"
        assert extract_kind(text) == "通知書"

    def test_custom_default_kind(self):
        """デフォルト種別をカスタマイズできる"""
        text = "ランダムなテキスト"
        assert extract_kind(text, default_kind="不明") == "不明"

    def test_estimate_in_head(self):
        """先頭行に '見積書' があれば正しく判定される"""
        text = "見積書\n2026年4月6日"
        assert extract_kind(text) == "見積書"

    def test_empty_string_returns_default(self):
        """空文字列はデフォルト種別を返す"""
        assert extract_kind("") == "書類"


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_windows_forbidden_chars_removed(self):
        """Windows 禁止文字 <>/\\|?*:\" が除去される"""
        result = sanitize_filename('abc<>:"/\\|?*def')
        assert result == "abcdef"

    def test_spaces_converted_to_underscore(self):
        """空白は _ に変換される"""
        assert sanitize_filename("2026 04 06") == "2026_04_06"

    def test_trailing_dots_removed(self):
        """末尾の . が削除される"""
        assert sanitize_filename("ファイル名.") == "ファイル名"

    def test_trailing_spaces_removed(self):
        """末尾の空白が削除される"""
        result = sanitize_filename("ファイル名  ")
        assert not result.endswith(" ")

    def test_max_length_truncation(self):
        """max_length で切り捨てられる"""
        long_name = "あ" * 100
        result = sanitize_filename(long_name, max_length=10)
        assert len(result) <= 10

    def test_empty_string_returns_empty(self):
        """空文字列は空文字列を返す"""
        assert sanitize_filename("") == ""

    def test_normal_filename_unchanged(self):
        """通常のファイル名は変化しない"""
        name = "2026-04-06_主日礼拝メッセージ要旨"
        assert sanitize_filename(name) == name

    def test_default_max_length_80(self):
        """デフォルト max_length は 80"""
        long_name = "a" * 200
        result = sanitize_filename(long_name)
        assert len(result) <= 80

    def test_multiple_spaces_become_single_underscore(self):
        """連続する空白は 1つの _ になる"""
        result = sanitize_filename("a   b")
        assert result == "a_b"


# ---------------------------------------------------------------------------
# load_profile
# ---------------------------------------------------------------------------

class TestLoadProfile:
    def test_load_profile_basic(self, tmp_path):
        """TOML プロファイルを読み込めること"""
        from pdf_split_autorenamer.textops import load_profile
        toml_content = (
            '[[title_patterns]]\npattern = "週報"\nlabel = "週報"\n\n'
            '[[body_patterns]]\npattern = "祈祷会"\nlabel = "祈祷会"\n'
        ).encode("utf-8")
        p = tmp_path / "profile.toml"
        p.write_bytes(toml_content)
        title_pats, body_pats = load_profile(p)
        assert len(title_pats) == 1
        assert len(body_pats) == 1
        assert title_pats[0][1] == "週報"
        assert body_pats[0][1] == "祈祷会"

    def test_load_profile_empty(self, tmp_path):
        """空の TOML でも空リストを返すこと"""
        from pdf_split_autorenamer.textops import load_profile
        p = tmp_path / "empty.toml"
        p.write_bytes(b"")
        title_pats, body_pats = load_profile(p)
        assert title_pats == []
        assert body_pats == []

    def test_load_profile_raises_when_no_tomllib(self, tmp_path):
        """tomllib が None のとき ImportError を送出する（L191）"""
        from unittest.mock import patch
        from pdf_split_autorenamer.textops import load_profile
        p = tmp_path / "profile.toml"
        p.write_bytes(b"")
        with patch("pdf_split_autorenamer.textops.tomllib", None):
            with pytest.raises(ImportError, match="TOML"):
                load_profile(p)


# ---------------------------------------------------------------------------
# load_mojibake_map
# ---------------------------------------------------------------------------

class TestLoadMojibakeMap:
    def test_load_mojibake_map_basic(self, tmp_path):
        """TOML から置換マップを読み込めること"""
        from pdf_split_autorenamer.textops import load_mojibake_map
        toml_content = '[[replacements]]\nwrong = "朁"\ncorrect = "月"\n'.encode("utf-8")
        p = tmp_path / "mojibake.toml"
        p.write_bytes(toml_content)
        result = load_mojibake_map(p)
        assert result == {"朁": "月"}

    def test_load_mojibake_map_empty(self, tmp_path):
        """空の TOML では空 dict を返すこと"""
        from pdf_split_autorenamer.textops import load_mojibake_map
        p = tmp_path / "empty.toml"
        p.write_bytes(b"")
        result = load_mojibake_map(p)
        assert result == {}

    def test_load_mojibake_map_raises_when_no_tomllib(self, tmp_path):
        """tomllib が None のとき ImportError を送出する（L218）"""
        from unittest.mock import patch
        from pdf_split_autorenamer.textops import load_mojibake_map
        p = tmp_path / "mojibake.toml"
        p.write_bytes(b"")
        with patch("pdf_split_autorenamer.textops.tomllib", None):
            with pytest.raises(ImportError, match="TOML"):
                load_mojibake_map(p)
