# -*- coding: utf-8 -*-
"""extract_vendor / extract_doc_number のユニットテスト"""
import pytest
from pdf_split_autorenamer.textops import extract_vendor, extract_doc_number


class TestExtractVendor:
    """取引先抽出: extract_vendor"""

    # --- 正例 ---

    def test_kabushiki_mae_gochu(self):
        """株式会社○○ 御中 パターン（前置）"""
        text = "株式会社山田工業 御中\n本文テキスト"
        result = extract_vendor(text)
        assert result == "山田工業"

    def test_kabushiki_ato_sama(self):
        """○○株式会社 様 パターン（後置）"""
        text = "山田商事株式会社 様\nご請求申し上げます"
        result = extract_vendor(text)
        assert result == "山田商事"

    def test_yuugen_kaisha(self):
        """有限会社パターン"""
        text = "有限会社田中商店 御中\n"
        result = extract_vendor(text)
        assert result == "田中商店"

    def test_godo_kaisha(self):
        """合同会社パターン"""
        text = "合同会社テスト事務所 様\n"
        result = extract_vendor(text)
        assert result == "テスト事務所"

    def test_paren_kabu_prefix(self):
        """(株)○○ パターン"""
        text = "(株)サンプル産業 御中\n"
        result = extract_vendor(text)
        assert result is not None
        assert "サンプル産業" in result

    def test_paren_kabu_suffix(self):
        """○○(株) パターン（後置なし敬称なし）"""
        text = "テスト物産(株)\n本文"
        result = extract_vendor(text)
        assert result is not None

    def test_inc_pattern(self):
        """英語社名 Inc. パターン"""
        text = "Acme Corp Inc.\n本文"
        result = extract_vendor(text)
        assert result is not None
        assert "Acme Corp" in result or result is not None

    def test_co_ltd_pattern(self):
        """Co., Ltd. パターン"""
        text = "Global Trade Co., Ltd.\nご担当者様"
        result = extract_vendor(text)
        assert result is not None

    def test_space_removal(self):
        """半角空白が除去される（山田 工業 → 山田工業）"""
        text = "株式会社山田 工業 御中\n本文"
        result = extract_vendor(text)
        assert result is not None
        assert " " not in result

    def test_max_len_trim(self):
        """max_len でトリムされる"""
        # パターンの `.{1,20}?` 制限内に収まる社名（10文字）を使い、max_len=5 でトリムを確認
        name = "あいうえおかきくけこ"  # 10文字
        text = f"株式会社{name} 御中\n本文"
        result = extract_vendor(text, max_len=5)
        assert result is not None
        assert len(result) <= 5

    def test_first_line_priority(self):
        """先頭 10 行内のマッチを優先し、先頭の社名が返ること（S-2）"""
        lines = ["株式会社最初商事 御中"] + ["本文行"] * 5 + ["株式会社後半商事 様"]
        text = "\n".join(lines)
        result = extract_vendor(text)
        assert result is not None
        assert "最初商事" in result

    # --- 前置×殿 / 後置×御中・様・殿 / (株)前置×様・殿（S-3 追加） ---

    def test_kabushiki_mae_dono(self):
        """株式会社○○ 殿 パターン（前置×殿）"""
        text = "株式会社前置物産 殿\n本文"
        result = extract_vendor(text)
        assert result is not None
        assert "前置物産" in result

    def test_kabushiki_ato_gochu(self):
        """○○株式会社 御中 パターン（後置×御中）"""
        text = "後置商事株式会社 御中\n本文"
        result = extract_vendor(text)
        assert result is not None
        assert "後置商事" in result

    def test_kabushiki_ato_dono(self):
        """○○株式会社 殿 パターン（後置×殿）"""
        text = "後置産業株式会社 殿\n本文"
        result = extract_vendor(text)
        assert result is not None
        assert "後置産業" in result

    def test_paren_kabu_prefix_sama(self):
        """(株)○○ 様 パターン（括弧前置×様）"""
        text = "(株)括弧商事 様\n本文"
        result = extract_vendor(text)
        assert result is not None
        assert "括弧商事" in result

    def test_paren_kabu_prefix_dono(self):
        """(株)○○ 殿 パターン（括弧前置×殿）"""
        text = "(株)括弧物産 殿\n本文"
        result = extract_vendor(text)
        assert result is not None
        assert "括弧物産" in result

    # --- 負例 ---

    def test_no_company_returns_none(self):
        """会社名なしのテキストは None"""
        text = "ご請求金額: 100,000 円\n振込先: 〇〇銀行"
        result = extract_vendor(text)
        assert result is None

    def test_empty_string_returns_none(self):
        """空文字は None"""
        assert extract_vendor("") is None

    def test_newlines_only_returns_none(self):
        """改行のみは None（S-3 異常系）"""
        assert extract_vendor("\n\n\n") is None

    def test_spaces_only_returns_none(self):
        """空白のみは None（S-3 異常系）"""
        assert extract_vendor("   ") is None

    def test_plain_japanese_no_match(self):
        """会社名パターンに合わない日本語は None"""
        text = "2026年4月1日\n請求書\nご確認ください"
        result = extract_vendor(text)
        assert result is None


class TestExtractDocNumber:
    """文書番号抽出: extract_doc_number"""

    # --- 正例 ---

    def test_no_pattern(self):
        """No. XXX パターン"""
        text = "No. 2026-0401-001\n発行日: 2026-04-01"
        result = extract_doc_number(text)
        assert result == "2026-0401-001"

    def test_no_without_dot(self):
        """No XXX パターン（ドットなし）"""
        text = "No 2026-0401-002\n本文"
        result = extract_doc_number(text)
        assert result == "2026-0401-002"

    def test_po_pattern(self):
        """PO-XXX パターン"""
        text = "発注番号: PO-2026-001\n本文"
        result = extract_doc_number(text)
        assert result is not None

    def test_q_pattern(self):
        """Q-XXX パターン（見積番号）"""
        text = "見積番号: Q-2026-042\n本文"
        result = extract_doc_number(text)
        assert result is not None

    def test_r_pattern(self):
        """R-XXX パターン"""
        text = "管理番号 R-001-2026\n本文"
        result = extract_doc_number(text)
        assert result is not None

    def test_seikyu_bango(self):
        """請求番号: XXX パターン"""
        text = "請求番号: INV-2026-0401\n本文"
        result = extract_doc_number(text)
        assert result == "INV-2026-0401"

    def test_hatchu_bango(self):
        """発注番号: XXX パターン"""
        text = "発注番号: ORD2026001\n本文"
        result = extract_doc_number(text)
        assert result == "ORD2026001"

    def test_uppercase_no(self):
        """NO. パターン（大文字）"""
        text = "NO. INV-2026-001\n本文"
        result = extract_doc_number(text)
        assert result is not None

    def test_max_len_trim(self):
        """max_len でトリムされる"""
        text = "No. " + "A" * 40
        result = extract_doc_number(text, max_len=30)
        assert result is not None
        assert len(result) <= 30

    def test_fullwidth_no_dot(self):
        """全角 Ｎｏ. パターン（S-3）"""
        text = "Ｎｏ. 2026-0401-001\n本文"
        result = extract_doc_number(text)
        assert result is not None
        assert "2026-0401-001" in result

    def test_fullwidth_no_fullwidth_period(self):
        """全角 Ｎｏ．（全角ピリオド）パターン（S-3）"""
        text = "Ｎｏ．2026-0401-002\n本文"
        result = extract_doc_number(text)
        assert result is not None
        assert "2026-0401-002" in result

    def test_fullwidth_colon_seikyu(self):
        """請求番号：（全角コロン）パターン（S-3）"""
        text = "請求番号：INV-2026-0401\n本文"
        result = extract_doc_number(text)
        assert result is not None
        assert "INV-2026-0401" in result

    # --- 負例 ---

    def test_no_number_returns_none(self):
        """文書番号なしのテキストは None"""
        text = "株式会社山田工業 御中\n本文"
        result = extract_doc_number(text)
        assert result is None

    def test_empty_string_returns_none(self):
        """空文字は None"""
        assert extract_doc_number("") is None

    def test_newlines_only_returns_none(self):
        """改行のみは None（S-3 異常系）"""
        assert extract_doc_number("\n\n\n") is None

    def test_spaces_only_returns_none(self):
        """空白のみは None（S-3 異常系）"""
        assert extract_doc_number("   ") is None


class TestExtractVendorBugFixes:
    """W-1/W-2 バグ修正テスト（QA Round 2）"""

    def test_no_date_in_vendor_result(self):
        """W-1: 後置会社形態パターンが改行をまたいで日付を社名と誤認しないこと。
        "2026年5月1日\\n株式会社デジタルパートナーズ" のとき、
        戻り値に日付文字列が含まれないこと（理想: "デジタルパートナーズ" のみ）"""
        text = "2026年5月1日\n株式会社デジタルパートナーズ\n代表取締役 高橋 花子"
        result = extract_vendor(text)
        # 日付由来の文字列が混入しないこと
        assert result is not None
        assert "2026" not in result
        assert "年" not in result
        assert "月" not in result
        assert "日" not in result
        assert "デジタルパートナーズ" in result

    def test_no_department_role_in_vendor_result(self):
        """W-2: 前置会社形態パターンが部署/役職/担当者名まで含めないこと。
        "株式会社 関西商会　購買部 部長 山本様" のとき、
        戻り値が "関西商会" のみで部署・役職・個人名を含まないこと"""
        text = "株式会社 関西商会　購買部 部長 山本様"
        result = extract_vendor(text)
        assert result is not None
        assert result == "関西商会"
        # 部署・役職・個人名が含まれないこと
        assert "購買部" not in result
        assert "部長" not in result
        assert "山本" not in result

    def test_vendor_with_full_width_space_between_dept(self):
        """W-2 全角空白対応: 全角空白で区切られた部署/役職が混入しないこと。
        "合同会社テック商会　営業部 担当 鈴木様" のとき戻り値が "テック商会" のみ"""
        text = "合同会社テック商会　営業部 担当 鈴木様"
        result = extract_vendor(text)
        assert result is not None
        assert result == "テック商会"
        assert "営業部" not in result
        assert "担当" not in result
        assert "鈴木" not in result

    def test_date_filter_returns_none_when_only_date(self):
        """W-1 追加防衛: 抽出結果が日付パターンのみになる場合は None を返すこと"""
        # 日付だけが残ってしまうようなテキスト
        text = "2026年5月1日\n合同会社\n詳細本文"
        result = extract_vendor(text)
        # 戻り値が None か、日付パターンを含まないこと
        if result is not None:
            assert "2026" not in result
            import re
            assert not re.search(r"\d{4}[年/\-]\d{1,2}", result)

    def test_dept_name_as_part_of_company_name(self):
        """W-A: 部署名を社名本体に含む法人名は切り詰めない"""
        assert extract_vendor("ABC開発部株式会社 御中") == "ABC開発部"
        assert extract_vendor("東京技術部株式会社 様") == "東京技術部"
        assert extract_vendor("関西営業部株式会社 御中") == "関西営業部"

    def test_dept_with_space_is_trimmed(self):
        """W-A 既存挙動維持: 空白を伴う部署名は社名外として切り詰める"""
        # 後置会社形態あり・末尾が空白付き部署名 → 空白の前で切り詰める
        assert extract_vendor("関西商会株式会社 購買部 様") == "関西商会"
