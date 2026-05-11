# -*- coding: utf-8 -*-
"""WeasyPrint 版 generate_demo_pdf.py のテスト

WeasyPrint + GTK Runtime がインストールされていない環境では全テストをスキップ。
"""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

import pytest

# fitz (PyMuPDF) は必須依存
try:
    import fitz  # noqa: F401
except ImportError:
    pytest.skip("PyMuPDF が未インストール", allow_module_level=True)

# Windows では GTK DLL を先にロードしてから WeasyPrint を import
if sys.platform == "win32":
    import os

    gtk_bin = r"C:\Program Files\GTK3-Runtime Win64\bin"
    if not Path(gtk_bin).exists():
        pytest.skip("GTK3 Runtime が見つかりません", allow_module_level=True)
    try:
        os.add_dll_directory(gtk_bin)
    except OSError as exc:
        pytest.skip(f"GTK DLL ロード失敗: {exc}", allow_module_level=True)

# WeasyPrint が使えない環境ではスキップ
weasyprint = pytest.importorskip(
    "weasyprint",
    reason="weasyprint 未インストール。pip install 'pdf-split-autorenamer[demo]' を実行してください。",
)

# スクリプト本体を import
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

try:
    import generate_demo_pdf as gdp
except ImportError as exc:
    pytest.skip(f"generate_demo_pdf のインポートに失敗: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# 各 _doc_xxx 関数のユニットテスト
# ---------------------------------------------------------------------------

class TestDocFunctions:
    """各書類生成関数が適切な dict を返すことを確認"""

    def _check_doc(self, doc: dict, expected_klass: str, *keywords: str) -> None:
        assert isinstance(doc, dict), "dict を返すこと"
        assert "klass" in doc, "klass キーが必要"
        assert "html" in doc, "html キーが必要"
        assert doc["klass"] == expected_klass, f"klass が {expected_klass} であること"
        for kw in keywords:
            assert kw in doc["html"], f"html に '{kw}' が含まれること"

    def test_invoice(self):
        doc = gdp._doc_invoice()
        self._check_doc(doc, "doc--invoice", "請求書", "2026年4月1日", "330,000")

    def test_quotation(self):
        doc = gdp._doc_quotation()
        self._check_doc(doc, "doc--quotation", "見積書", "2026年4月8日", "389,400")

    def test_minutes(self):
        doc = gdp._doc_minutes()
        self._check_doc(doc, "doc--minutes", "議事録", "2026年4月15日")

    def test_proposal(self):
        doc = gdp._doc_proposal()
        self._check_doc(doc, "doc--proposal", "稟議", "2026年4月20日")

    def test_travel_report(self):
        doc = gdp._doc_travel_report()
        self._check_doc(doc, "doc--travel-report", "出張報告書", "2026年4月22日")

    def test_purchase_order(self):
        doc = gdp._doc_purchase_order()
        self._check_doc(doc, "doc--purchase-order", "発注書", "2026年4月25日")

    def test_receipt(self):
        doc = gdp._doc_receipt()
        self._check_doc(doc, "doc--receipt", "領収書", "2026年4月28日")

    def test_contract(self):
        doc = gdp._doc_contract()
        self._check_doc(doc, "doc--contract", "契約書", "2026年5月1日")


# ---------------------------------------------------------------------------
# _render_html のユニットテスト
# ---------------------------------------------------------------------------

class TestRenderHtml:
    def test_returns_html_string(self):
        docs = [gdp._doc_invoice()]
        html = gdp._render_html(docs)
        assert html.startswith("<!doctype html>"), "DOCTYPE から始まること"
        assert '<html lang="ja">' in html, 'lang="ja" が含まれること'
        assert "</html>" in html, "閉じタグで終わること"

    def test_contains_css(self):
        docs = [gdp._doc_invoice()]
        html = gdp._render_html(docs)
        assert "@page" in html, "CSS @page ルールが含まれること"
        assert "font-family" in html, "font-family 指定が含まれること"

    def test_page_break_between_docs(self):
        docs = [gdp._doc_invoice(), gdp._doc_quotation()]
        html = gdp._render_html(docs)
        # 複数書類間に改ページ指定があること
        assert "page-break-after" in html or "break-after" in html, "改ページ指定が含まれること"


# ---------------------------------------------------------------------------
# make_demo_pdf の統合テスト（実際に PDF を生成して検証）
# ---------------------------------------------------------------------------

_EXPECTED_KEYWORDS = [
    ("請求書", "2026年4月1日"),
    ("見積書", "2026年4月8日"),
    ("議事録", "2026年4月15日"),   # p3
    ("議事録", "2026年4月15日"),   # p4 (2/2)
    ("稟議", "2026年4月20日"),     # p5
    ("出張報告書", "2026年4月22日"),  # p6
    ("発注書", "2026年4月25日"),   # p7
    ("領収書", "2026年4月28日"),   # p8
    ("契約書", "2026年5月1日"),    # p9
    ("契約書", "2026年5月1日"),    # p10 (2/2)
]


@pytest.fixture(scope="module")
def generated_pdf(tmp_path_factory):
    """テスト用 PDF を一度だけ生成してキャッシュする"""
    out_dir = tmp_path_factory.mktemp("demo_pdf")
    out_path = out_dir / "test_demo.pdf"
    gdp.make_demo_pdf(out_path)
    return out_path


class TestMakeDemoPdf:
    def test_pdf_exists(self, generated_pdf):
        assert generated_pdf.exists(), "PDF ファイルが生成されること"
        assert generated_pdf.stat().st_size > 1024, "PDF サイズが 1KB 以上であること"

    def test_page_count_is_10(self, generated_pdf):
        import fitz
        doc = fitz.open(str(generated_pdf))
        assert doc.page_count == 10, f"10 ページであること (実際: {doc.page_count})"
        doc.close()

    def test_all_pages_have_text(self, generated_pdf):
        import fitz
        doc = fitz.open(str(generated_pdf))
        for i in range(doc.page_count):
            text = doc[i].get_text()
            assert len(text) > 50, f"p{i+1} のテキストが短すぎる: {repr(text[:100])}"
        doc.close()

    def test_expected_keywords_per_page(self, generated_pdf):
        import fitz
        doc = fitz.open(str(generated_pdf))
        errors = []
        for i, (kw1, kw2) in enumerate(_EXPECTED_KEYWORDS):
            text = doc[i].get_text()
            if kw1 not in text:
                errors.append(f"p{i+1}: '{kw1}' が見つからない")
            if kw2 not in text:
                errors.append(f"p{i+1}: '{kw2}' が見つからない")
        doc.close()
        assert not errors, "\n".join(errors)

    def test_main_function(self, tmp_path):
        """main() が 0 を返して PDF を生成すること"""
        out_path = tmp_path / "main_test.pdf"
        result = gdp.main([str(out_path)])
        assert result == 0, f"main() が 0 を返すこと (実際: {result})"
        assert out_path.exists(), "main() が PDF を生成すること"
