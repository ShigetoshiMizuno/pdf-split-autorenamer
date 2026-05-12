# -*- coding: utf-8 -*-
"""T-04: MOJIBAKE_FIX 外部化の検証テスト

- load_mojibake_map() の動作
- fix_mojibake() の extra_map 対応
- DEFAULT_TITLE_PATTERNS の簡素化（歓迎 のみ）
- extract_kind の OCR 化け → 正字マッチ
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# load_mojibake_map
# ---------------------------------------------------------------------------

class TestLoadMojibakeMap:
    def test_load_from_toml(self, tmp_path):
        """TOML ファイルから mojibake マップを読み込む"""
        toml = tmp_path / "test.toml"
        toml.write_text(
            '[meta]\nname = "test"\n\n'
            '[[replacements]]\nwrong = "朁"\ncorrect = "月"\n\n'
            '[[replacements]]\nwrong = "迁"\ncorrect = "迎"\n',
            encoding="utf-8",
        )
        from pdf_split_autorenamer.textops import load_mojibake_map
        m = load_mojibake_map(toml)
        assert m == {"朁": "月", "迁": "迎"}

    def test_empty_replacements(self, tmp_path):
        """replacements が空でも空 dict を返す"""
        toml = tmp_path / "empty.toml"
        toml.write_text('[meta]\nname = "empty"\n', encoding="utf-8")
        from pdf_split_autorenamer.textops import load_mojibake_map
        assert load_mojibake_map(toml) == {}

    def test_missing_file_raises(self, tmp_path):
        """存在しないファイルは FileNotFoundError"""
        from pdf_split_autorenamer.textops import load_mojibake_map
        with pytest.raises(FileNotFoundError):
            load_mojibake_map(tmp_path / "no_such.toml")

    def test_missing_correct_key_raises(self, tmp_path):
        """correct キーが欠けていると ValueError"""
        toml = tmp_path / "bad.toml"
        toml.write_text(
            '[[replacements]]\nwrong = "X"\n',
            encoding="utf-8",
        )
        from pdf_split_autorenamer.textops import load_mojibake_map
        with pytest.raises((KeyError, ValueError)):
            load_mojibake_map(toml)

    def test_scansnap_profile_parseable(self):
        """同梱の scansnap-s500.toml が読み込めること"""
        profiles_dir = Path(__file__).parent.parent / "profiles"
        scansnap = profiles_dir / "scansnap-s500.toml"
        if not scansnap.exists():
            pytest.skip("scansnap-s500.toml not yet created")
        from pdf_split_autorenamer.textops import load_mojibake_map
        m = load_mojibake_map(scansnap)
        assert isinstance(m, dict)
        assert len(m) >= 5
        assert "迁" in m and m["迁"] == "迎"


# ---------------------------------------------------------------------------
# fix_mojibake extra_map
# ---------------------------------------------------------------------------

class TestFixMojibakeExtraMap:
    def test_extra_map_applied(self):
        """extra_map の置換が適用される"""
        from pdf_split_autorenamer.textops import fix_mojibake
        result = fix_mojibake("歎迎", extra_map={"歎": "歓"})
        assert result == "歓迎"

    def test_extra_map_none_behaves_as_before(self):
        """extra_map=None は従来と同じ動作"""
        from pdf_split_autorenamer.textops import fix_mojibake
        assert fix_mojibake("朁") == "月"
        assert fix_mojibake("迁") == "迎"

    def test_extra_map_plus_builtin(self):
        """extra_map と組み込みの両方が適用される"""
        from pdf_split_autorenamer.textops import fix_mojibake
        result = fix_mojibake("歎迁", extra_map={"歎": "歓"})
        assert result == "歓迎"


# ---------------------------------------------------------------------------
# MOJIBAKE_FIX デフォルトで 歓 バリアントをカバー
# ---------------------------------------------------------------------------

class TestDefaultMojibakeCoversKanVariants:
    """MOJIBAKE_FIX に 歎→歓 / 藪→歓 / 裁→歓 / 鐵→歓 / 欽→歓 が含まれること"""

    @pytest.mark.parametrize("wrong_char", ["歎", "藪", "裁", "鐵", "欽"])
    def test_variant_converted_to_kan(self, wrong_char):
        """歓の OCR バリアントが歓に変換される"""
        from pdf_split_autorenamer.textops import fix_mojibake
        result = fix_mojibake(wrong_char + "迎")
        assert result == "歓迎", f"{wrong_char}迎 → 歓迎 に変換されなかった (got: {result!r})"


# ---------------------------------------------------------------------------
# DEFAULT_TITLE_PATTERNS の簡素化
# ---------------------------------------------------------------------------

class TestDefaultTitlePatternSimplified:
    def test_invoice_pattern_matches_invoice(self):
        """DEFAULT_TITLE_PATTERNS の請求書パターンが 請求書 にマッチする"""
        from pdf_split_autorenamer.textops import DEFAULT_TITLE_PATTERNS
        invoice_patterns = [
            pat for pat, label in DEFAULT_TITLE_PATTERNS
            if label == "請求書" and pat.search("請求書")
        ]
        assert len(invoice_patterns) >= 1, "請求書にマッチするパターンが DEFAULT_TITLE_PATTERNS にない"

    def test_no_ocr_variant_in_patterns(self):
        """DEFAULT_TITLE_PATTERNS に OCR 化け変体が直接含まれないこと"""
        from pdf_split_autorenamer.textops import DEFAULT_TITLE_PATTERNS
        ocr_variants = ["歎", "藪", "裁", "鐵", "欽", "迁"]
        for pat, _label in DEFAULT_TITLE_PATTERNS:
            for v in ocr_variants:
                assert v not in pat.pattern, (
                    f"OCR 変体 {v!r} が DEFAULT_TITLE_PATTERNS のパターン {pat.pattern!r} に残っている"
                )


# ---------------------------------------------------------------------------
# extract_kind の統合テスト
# ---------------------------------------------------------------------------

class TestExtractKindAfterMojibake:
    @pytest.mark.parametrize("text,expected", [
        ("請求書", "請求書"),
        ("御請求書", "請求書"),
        ("見積書", "見積書"),
        ("議事録", "議事録"),
        ("稟議書", "稟議書"),
        ("領収書", "領収書"),
        ("納品書", "納品書"),
        ("通知書", "通知書"),
    ])
    def test_business_documents_classified(self, text, expected):
        """業務書類の代表的なキーワードが正しく分類される"""
        from pdf_split_autorenamer.textops import extract_kind
        result = extract_kind(text)
        assert result == expected, f"'{text}' → {expected!r} ではなく {result!r} になった"
