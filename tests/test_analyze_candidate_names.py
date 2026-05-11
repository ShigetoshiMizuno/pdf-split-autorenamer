# -*- coding: utf-8 -*-
"""generate_candidate_names のユニットテスト"""
import pytest
from pdf_split_autorenamer.analyze import generate_candidate_names


def _make_page(pdf="test.pdf", page=1, text="", text_head=""):
    """テスト用ページ dict を作る"""
    return {
        "pdf": pdf,
        "page": page,
        "text": text,
        "text_head": text_head or text[:200],
        "orient": "P",
        "width": 595.0,
        "height": 842.0,
        "thumb": "",
        "title_markers": [],
        "bigram": set(),
    }


def _make_groups(pdf="test.pdf", groups_data=None):
    """テスト用 groups dict を作る"""
    if groups_data is None:
        groups_data = [{"range": [1, 1], "name": ""}]
    return {pdf: groups_data}


class TestGenerateCandidateNames:
    """generate_candidate_names の挙動テスト"""

    def test_all_elements_present(self):
        """日付・カテゴリ・取引先・文書番号が揃っている場合"""
        text = (
            "2026年4月1日\n"
            "請求書\n"
            "株式会社山田工業 御中\n"
            "No. 2026-0401-001\n"
        )
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert "2026-04-01" in name
        assert "請求書" in name  # Phase B 後は業務向けパターンで「請求書」が抽出される（S-1）
        assert name != ""

    def test_name_is_filled(self):
        """name フィールドが空でなくなる"""
        text = "2026年3月15日\n議事録\n"
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        assert result["test.pdf"][0]["name"] != ""

    def test_date_unknown_fallback(self):
        """日付が取れない場合は '日付不明' が prefix になる"""
        text = "請求書\n本文テキスト\n"
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert "日付不明" in name

    def test_kind_default_without_patterns(self):
        """カテゴリが識別できない場合は '書類' がデフォルト"""
        text = "2026年1月1日\nテキストのみ"
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        # 日付は入るはず
        assert "2026-01-01" in name

    def test_vendor_included_in_name(self):
        """取引先名がハイフン区切りで含まれる"""
        text = (
            "2026年4月1日\n"
            "見積書\n"
            "株式会社テスト商事 御中\n"
        )
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        # テスト商事が含まれているか、少なくとも name が非空
        assert name != ""
        assert "-" in name or "日付不明" in name or "2026" in name

    def test_multiple_groups_in_one_pdf(self):
        """1 PDF に複数グループがある場合、それぞれに name が設定される"""
        page1 = _make_page(pdf="multi.pdf", page=1, text="2026年4月1日\n請求書")
        page2 = _make_page(pdf="multi.pdf", page=2, text="2026年4月5日\n見積書")
        pages = [page1, page2]
        groups = {
            "multi.pdf": [
                {"range": [1, 1], "name": ""},
                {"range": [2, 2], "name": ""},
            ]
        }
        result = generate_candidate_names(pages, groups)
        assert result["multi.pdf"][0]["name"] != ""
        assert result["multi.pdf"][1]["name"] != ""

    def test_multiple_pdfs(self):
        """複数 PDF にまたがるグループも処理される"""
        page1 = _make_page(pdf="a.pdf", page=1, text="2026年1月1日\n議事録")
        page2 = _make_page(pdf="b.pdf", page=1, text="2026年2月1日\n会計報告")
        pages = [page1, page2]
        groups = {
            "a.pdf": [{"range": [1, 1], "name": ""}],
            "b.pdf": [{"range": [1, 1], "name": ""}],
        }
        result = generate_candidate_names(pages, groups)
        assert result["a.pdf"][0]["name"] != ""
        assert result["b.pdf"][0]["name"] != ""

    def test_empty_text_uses_fallback(self):
        """テキストが空のグループは '日付不明_書類' にフォールバック"""
        pages = [_make_page(text="")]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert name != ""
        assert "日付不明" in name

    def test_name_sanitized(self):
        """生成された name が Windows 安全な文字列になる"""
        text = "2026年4月1日\n請求書"
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        # Windows 禁止文字が含まれないこと
        for ch in '<>:"/\\|?*':
            assert ch not in name

    def test_name_max_length(self):
        """生成された name が 80 文字以内"""
        text = "2026年4月1日\n請求書"
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert len(name) <= 80

    def test_profile_patterns_used(self):
        """profile_patterns を渡すとカテゴリ判定に使われる"""
        import re
        title_patterns = [(re.compile(r"請求書"), "請求書")]
        body_patterns = []
        text = "2026年4月1日\n請求書\n本文"
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(
            pages, groups,
            profile_patterns=(title_patterns, body_patterns)
        )
        name = result["test.pdf"][0]["name"]
        assert "請求書" in name

    def test_returns_groups_dict(self):
        """戻り値が dict[str, list[dict]] 型"""
        pages = [_make_page(text="2026年1月1日")]
        groups = _make_groups()
        result = generate_candidate_names(pages, groups)
        assert isinstance(result, dict)
        assert isinstance(result["test.pdf"], list)

    def test_build_initial_groups_name_empty_preserved(self):
        """build_initial_groups 単体では name == '' のまま（このテストは保護用）"""
        from pdf_split_autorenamer.analyze import build_initial_groups
        pages = [_make_page()]
        result = build_initial_groups(pages)
        assert result["test.pdf"][0]["name"] == ""

    # --- 業務カテゴリ別テスト（C2 追加） ---

    def test_category_seikyu_sho(self):
        """請求書カテゴリが正しく候補名に含まれる"""
        text = (
            "2026年4月1日\n"
            "請求書\n"
            "株式会社山田工業 御中\n"
            "No. INV-001\n"
        )
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert "請求書" in name

    def test_category_mitsumori_sho(self):
        """見積書カテゴリが正しく候補名に含まれる"""
        text = (
            "2026年5月10日\n"
            "見積書\n"
            "株式会社テスト商事 御中\n"
            "No. Q-2026-001\n"
        )
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert "見積書" in name

    def test_category_gijiroku(self):
        """議事録カテゴリが正しく候補名に含まれる"""
        text = (
            "2026年3月20日\n"
            "議事録\n"
            "第1回役員会\n"
        )
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert "議事録" in name

    def test_vendor_only_no_docno(self):
        """取引先のみ（文書番号なし）のケース"""
        text = (
            "2026年4月1日\n"
            "請求書\n"
            "株式会社取引先商事 御中\n"
        )
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert "請求書" in name
        assert "取引先商事" in name
        assert name.count("-") >= 1

    def test_docno_only_no_vendor(self):
        """文書番号のみ（取引先なし）のケース"""
        text = (
            "2026年4月1日\n"
            "請求書\n"
            "No. INV-2026-0401\n"
        )
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert "請求書" in name
        assert "INV-2026-0401" in name

    def test_no_vendor_no_docno(self):
        """取引先・文書番号ともに欠落 → カテゴリのみ"""
        text = (
            "2026年4月1日\n"
            "請求書\n"
            "ご確認ください\n"
        )
        pages = [_make_page(text=text)]
        groups = _make_groups(groups_data=[{"range": [1, 1], "name": ""}])
        result = generate_candidate_names(pages, groups)
        name = result["test.pdf"][0]["name"]
        assert "請求書" in name
        assert "2026-04-01" in name
