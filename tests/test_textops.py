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
from pathlib import Path
from unittest.mock import patch

import pytest

from pdf_split_autorenamer.textops import (
    MOJIBAKE_FIX,
    extract_dates_all,
    extract_kind,
    fix_broken_unicode,
    fix_mojibake,
    load_mojibake_map,
    load_profile,
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

    def test_duplicate_pattern_deduplicates_same_position(self):
        """同一位置に複数パターンが一致する場合、seen_positions により1件のみ返る (line 94)"""
        import re
        import pdf_split_autorenamer.textops as textops_module
        dup_patterns = [
            re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
            re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
        ]
        with patch.object(textops_module, "_DATE_PATTERNS", dup_patterns):
            result = extract_dates_all("2026-04-06")
        assert result == ["2026-04-06"]


# ---------------------------------------------------------------------------
# extract_kind
# ---------------------------------------------------------------------------

class TestExtractKind:
    def test_body_contains_sunday_message(self):
        """本文に '主日礼拝メッセージ要旨' が含まれれば 'ub0bb日礼拝メッセージ要旨' を返す"""
        text = "この文書は\n主日礼拝メッセージ要旨\nテキスト"
        assert extract_kind(text) == "主日礼拝メッセージ要旨"

    def test_head_contains_weekly_bulletin(self):
        """先頭行に '週報' が含まれれば '週報' を返す"""
        text = "週報\n2026年4月6日"
        assert extract_kind(text) == "週報"

    def test_no_match_returns_default(self):
        """何もマッチしなければデフォルト '書類' を返す"""
        text = "ランダムなテキストです"
        assert extract_kind(text) == "書類"

    def test_ocr_kankei_judged_as_weekly(self):
        """OCR化け '歓迁' → 歓迎パターンが '週報' に判定される"""
        # 歓迁 は MOJIBAKE_FIX で歓迎になり、週報パターンにマッチする
        text = "歓迁礼拝\nお知らせ"
        assert extract_kind(text) == "週報"

    def test_custom_default_kind(self):
        """デフォルト種別をカスタマイズできる"""
        text = "ランダムなテキスト"
        assert extract_kind(text, default_kind="不明") == "不明"

    def test_sunday_message_in_head(self):
        """先頭行に '主日礼拝メッセージ要旨' があれば正しく判定される"""
        text = "主日礼拝メッセージ要旨\n2026年4月6日"
        assert extract_kind(text) == "主日礼拝メッセージ要旨"

    def test_empty_string_returns_default(self):
        """空文字列はデフォルト種別を返す"""
        assert extract_kind("") == "書類"

    def test_body_only_match_returns_correct_kind(self):
        """タイトル領域（先頭6行）にはマッチしないが本文にはマッチする場合、body_patterns で判定される"""
        # 先頭6行にはマッチしないよう無関係なテキストを7行並べ、本文に '主日礼拝メッセージ要旨' を入れる
        padding = "\n".join([f"行{i}：無関係なテキスト" for i in range(1, 8)])
        text = padding + "\n主日礼拝メッセージ要旨\n説教原稿"
        assert extract_kind(text) == "主日礼拝メッセージ要旨"

    def test_fix_broken_unicode_no_recovery_returns_original(self):
        """fix_broken_unicode: 典型化け文字を含むが復元できない場合は元の文字列を返す"""
        from pdf_split_autorenamer.textops import fix_broken_unicode
        # 'ç' はフィルタを通過するが、cp1252→UTF-8 デコードで日本語を生成しない
        result = fix_broken_unicode("ç")
        assert result == "ç"

    def test_fix_broken_unicode_encode_error_skipped(self):
        """fix_broken_unicode: cp1252 でエンコードできない文字を含む場合もクラッシュしない"""
        from pdf_split_autorenamer.textops import fix_broken_unicode
        # 'ç' + 日本語: cp1252 エンコード失敗 → UnicodeEncodeError ハンドラを通過して元文字列を返す
        result = fix_broken_unicode("ç日本語")
        assert isinstance(result, str)


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
# load_profile / load_mojibake_map — tomllib=None の ImportError
# ---------------------------------------------------------------------------

class TestLoadProfileTomllibNone:
    def test_raises_import_error_when_tomllib_none(self, tmp_path):
        """tomllib が None のとき ImportError を送出する（line 191）"""
        dummy = tmp_path / "dummy.toml"
        dummy.write_text("", encoding="utf-8")
        with patch("pdf_split_autorenamer.textops.tomllib", None):
            with pytest.raises(ImportError, match="TOML"):
                load_profile(dummy)


class TestLoadMojibakeMapTomllibNone:
    def test_raises_import_error_when_tomllib_none(self, tmp_path):
        """tomllib が None のとき ImportError を送出する（line 218）"""
        dummy = tmp_path / "dummy.toml"
        dummy.write_text("", encoding="utf-8")
        with patch("pdf_split_autorenamer.textops.tomllib", None):
            with pytest.raises(ImportError, match="TOML"):
                load_mojibake_map(dummy)


# ---------------------------------------------------------------------------
# load_profile / load_mojibake_map — 実 TOML ファイルを使った統合テスト
# ---------------------------------------------------------------------------

class TestLoadProfileIntegration:
    def test_load_church_toml(self):
        """church.toml を読み込んで title_patterns / body_patterns を返す"""
        profiles_dir = Path(__file__).parent.parent / "profiles"
        church_toml = profiles_dir / "church.toml"
        if not church_toml.exists():
            pytest.skip("church.toml が見つかりません")
        title_patterns, body_patterns = load_profile(church_toml)
        assert len(title_patterns) > 0
        assert len(body_patterns) > 0

    def test_load_profile_patterns_work_with_extract_kind(self):
        """load_profile で取得したパターンが extract_kind で正しく機能する"""
        profiles_dir = Path(__file__).parent.parent / "profiles"
        church_toml = profiles_dir / "church.toml"
        if not church_toml.exists():
            pytest.skip("church.toml が見つかりません")
        title_patterns, body_patterns = load_profile(church_toml)
        result = extract_kind("週報\n2026年4月6日", title_patterns=title_patterns,
                              body_patterns=body_patterns)
        assert result == "週報"

    def test_load_profile_from_toml_content(self, tmp_path):
        """TOML コンテンツを直接書いてプロファイルを読み込む"""
        toml_content = (
            '[[title_patterns]]\n'
            'pattern = "test-doc"\n'
            'label = "TestDoc"\n'
            '\n'
            '[[body_patterns]]\n'
            'pattern = "body-test"\n'
            'label = "BodyKind"\n'
        )
        toml_path = tmp_path / "test.toml"
        toml_path.write_text(toml_content, encoding="utf-8")
        title_patterns, body_patterns = load_profile(toml_path)
        assert len(title_patterns) == 1
        assert len(body_patterns) == 1
        assert title_patterns[0][1] == "TestDoc"
        assert body_patterns[0][1] == "BodyKind"


class TestTomllibImportChain:
    def test_tomllib_fallback_chain_when_builtin_missing(self):
        """tomllib も tomli も利用不可な環境では textops.tomllib が None になる (lines 10-14)"""
        import importlib
        import sys
        import pdf_split_autorenamer.textops as textops_mod

        with patch.dict(sys.modules, {"tomllib": None, "tomli": None}):
            importlib.reload(textops_mod)
            assert textops_mod.tomllib is None

        # テスト後に正常状態へ戻す
        importlib.reload(textops_mod)


class TestLoadMojibakeMapIntegration:
    def test_load_scansnap_s500_toml(self):
        """scansnap-s500.toml を読み込んで置換マップを返す"""
        profiles_dir = Path(__file__).parent.parent / "profiles"
        scansnap_toml = profiles_dir / "scansnap-s500.toml"
        if not scansnap_toml.exists():
            pytest.skip("scansnap-s500.toml が見つかりません")
        result = load_mojibake_map(scansnap_toml)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_load_mojibake_map_from_toml_content(self, tmp_path):
        """TOML コンテンツを直接書いてマップを読み込む"""
        toml_content = (
            '[[replacements]]\n'
            'wrong = "X"\n'
            'correct = "Y"\n'
            '\n'
            '[[replacements]]\n'
            'wrong = "A"\n'
            'correct = "B"\n'
        )
        toml_path = tmp_path / "test.toml"
        toml_path.write_text(toml_content, encoding="utf-8")
        result = load_mojibake_map(toml_path)
        assert result == {"X": "Y", "A": "B"}
