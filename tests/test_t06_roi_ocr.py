# -*- coding: utf-8 -*-
"""T-06: Stage 2 ROI 限定 OCR の検証テスト

- pdfio.crop_page_pixmap: ページ上部クロップ
- pdfio.calc_japanese_ratio: 日本語文字比率算出
- OCR キャッシュの読み書き
- collect_pages の ocr_strategy パラメータ
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# crop_page_pixmap
# ---------------------------------------------------------------------------

class TestCropPagePixmap:
    def test_returns_bytes(self):
        """crop_page_pixmap が bytes を返す"""
        from pdf_split_autorenamer.pdfio import crop_page_pixmap
        import fitz
        pdf_bytes = fitz.open()
        page = pdf_bytes.new_page(width=595, height=842)
        pixmap_bytes = crop_page_pixmap(page, ratio=0.3)
        assert isinstance(pixmap_bytes, bytes)
        assert len(pixmap_bytes) > 0

    def test_cropped_height_smaller(self):
        """クロップ後の画像は元より小さい"""
        from pdf_split_autorenamer.pdfio import crop_page_pixmap
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        full = crop_page_pixmap(page, ratio=1.0)
        cropped = crop_page_pixmap(page, ratio=0.3)
        # PNG ヘッダを比較するのではなく、サイズの差で判断
        assert len(cropped) < len(full)

    def test_invalid_ratio_clamps(self):
        """ratio が 0〜1 の範囲外でもエラーにならない"""
        from pdf_split_autorenamer.pdfio import crop_page_pixmap
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        result = crop_page_pixmap(page, ratio=0.0)
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# calc_japanese_ratio
# ---------------------------------------------------------------------------

class TestCalcJapaneseRatio:
    def test_pure_japanese(self):
        """純日本語テキストは比率が高い"""
        from pdf_split_autorenamer.pdfio import calc_japanese_ratio
        ratio = calc_japanese_ratio("主日礼拝メッセージ要旨")
        assert ratio > 0.8

    def test_pure_ascii(self):
        """ASCII テキストは比率が 0"""
        from pdf_split_autorenamer.pdfio import calc_japanese_ratio
        ratio = calc_japanese_ratio("Hello World")
        assert ratio == 0.0

    def test_empty_string(self):
        """空文字列は 0.0"""
        from pdf_split_autorenamer.pdfio import calc_japanese_ratio
        ratio = calc_japanese_ratio("")
        assert ratio == 0.0

    def test_mixed_text(self):
        """日英混在は 0 < ratio < 1"""
        from pdf_split_autorenamer.pdfio import calc_japanese_ratio
        ratio = calc_japanese_ratio("Hello 礼拝 World")
        assert 0.0 < ratio < 1.0


# ---------------------------------------------------------------------------
# OCR キャッシュ
# ---------------------------------------------------------------------------

class TestOcrCache:
    def test_cache_read_write(self, tmp_path):
        """キャッシュに書いて読める"""
        from pdf_split_autorenamer.pdfio import get_ocr_cache_path, write_ocr_cache, read_ocr_cache
        image_bytes = b"fake_image"
        work_dir = tmp_path / ".psar"
        path = get_ocr_cache_path(work_dir, image_bytes)
        assert path is not None
        write_ocr_cache(path, "テストテキスト")
        result = read_ocr_cache(path)
        assert result == "テストテキスト"

    def test_cache_miss_returns_none(self, tmp_path):
        """キャッシュなしは None"""
        from pdf_split_autorenamer.pdfio import read_ocr_cache
        assert read_ocr_cache(tmp_path / "nonexistent.txt") is None

    def test_cache_dir_created_automatically(self, tmp_path):
        """ocr_cache ディレクトリが自動作成される"""
        from pdf_split_autorenamer.pdfio import get_ocr_cache_path
        work_dir = tmp_path / ".psar"
        path = get_ocr_cache_path(work_dir, b"data")
        assert path.parent.name == "ocr_cache"


# ---------------------------------------------------------------------------
# collect_pages の ocr_strategy パラメータ
# ---------------------------------------------------------------------------

class TestCollectPagesOcrStrategy:
    def _make_fake_pdf(self, name: str = "test.pdf") -> MagicMock:
        p = MagicMock(spec=Path)
        p.name = name
        p.stem = name.replace(".pdf", "")
        p.read_bytes.return_value = b"%PDF fake"
        return p

    def test_collect_pages_accepts_ocr_strategy(self, tmp_path):
        """collect_pages が ocr_strategy キーワード引数を受け付ける"""
        from pdf_split_autorenamer import analyze

        fake_pdf = self._make_fake_pdf()
        fake_page = MagicMock()
        fake_page.rect = MagicMock()
        fake_page.rect.width = 595.0
        fake_page.rect.height = 842.0

        fake_doc = MagicMock()
        fake_doc.page_count = 1
        fake_doc.__getitem__ = MagicMock(return_value=fake_page)
        fake_doc.close = MagicMock()

        with patch("pdf_split_autorenamer.analyze.list_pdfs", return_value=[fake_pdf]), \
             patch("pdf_split_autorenamer.analyze.fitz") as mock_fitz, \
             patch("pdf_split_autorenamer.analyze.extract_text", return_value="テスト"), \
             patch("pdf_split_autorenamer.analyze.render_thumb"):
            mock_fitz.open.return_value = fake_doc
            # ocr_strategy="fast" を渡してもエラーにならない
            pages = analyze.collect_pages(tmp_path, tmp_path / "thumbs", ocr_strategy="fast")
        assert isinstance(pages, list)

    def test_ocr_strategy_roi_triggers_crop(self, tmp_path):
        """ocr_strategy='roi' で日本語比率低い場合に crop_page_pixmap が呼ばれる"""
        from pdf_split_autorenamer import analyze

        fake_pdf = self._make_fake_pdf()
        fake_page = MagicMock()
        fake_page.rect = MagicMock()
        fake_page.rect.width = 595.0
        fake_page.rect.height = 842.0

        fake_doc = MagicMock()
        fake_doc.page_count = 1
        fake_doc.__getitem__ = MagicMock(return_value=fake_page)
        fake_doc.close = MagicMock()

        with patch("pdf_split_autorenamer.analyze.list_pdfs", return_value=[fake_pdf]), \
             patch("pdf_split_autorenamer.analyze.fitz") as mock_fitz, \
             patch("pdf_split_autorenamer.analyze.extract_text", return_value=""), \
             patch("pdf_split_autorenamer.analyze.crop_page_pixmap", return_value=b"png") as mock_crop, \
             patch("pdf_split_autorenamer.analyze.render_thumb"):
            mock_fitz.open.return_value = fake_doc
            analyze.collect_pages(tmp_path, tmp_path / "thumbs", ocr_strategy="roi")

        mock_crop.assert_called()

    def test_roi_cache_hit_uses_cached_text(self, tmp_path):
        """ROI OCR でキャッシュヒットした場合はキャッシュのテキストを使う（analyze.py L91）"""
        from pdf_split_autorenamer import analyze

        fake_pdf = self._make_fake_pdf()
        fake_page = MagicMock()
        fake_page.rect = MagicMock()
        fake_page.rect.width = 595.0
        fake_page.rect.height = 842.0
        fake_doc = MagicMock()
        fake_doc.page_count = 1
        fake_doc.__getitem__ = MagicMock(return_value=fake_page)

        with patch("pdf_split_autorenamer.analyze.list_pdfs", return_value=[fake_pdf]), \
             patch("pdf_split_autorenamer.analyze.fitz") as mock_fitz, \
             patch("pdf_split_autorenamer.analyze.extract_text", return_value=""), \
             patch("pdf_split_autorenamer.analyze.crop_page_pixmap", return_value=b"png"), \
             patch("pdf_split_autorenamer.analyze.get_ocr_cache_path", return_value=tmp_path / "cache.txt"), \
             patch("pdf_split_autorenamer.analyze.read_ocr_cache", return_value="キャッシュテキスト"), \
             patch("pdf_split_autorenamer.analyze.render_thumb"):
            mock_fitz.open.return_value = fake_doc
            pages = analyze.collect_pages(tmp_path, tmp_path / "thumbs", ocr_strategy="roi")

        assert any("キャッシュテキスト" in p.get("text", "") for p in pages)

    def test_roi_ocr_success_uses_roi_text(self, tmp_path):
        """ROI OCR が成功した場合は roi_text でテキストを上書きする（analyze.py L95）"""
        from pdf_split_autorenamer import analyze

        fake_pdf = self._make_fake_pdf()
        fake_page = MagicMock()
        fake_page.rect = MagicMock()
        fake_page.rect.width = 595.0
        fake_page.rect.height = 842.0
        fake_doc = MagicMock()
        fake_doc.page_count = 1
        fake_doc.__getitem__ = MagicMock(return_value=fake_page)

        with patch("pdf_split_autorenamer.analyze.list_pdfs", return_value=[fake_pdf]), \
             patch("pdf_split_autorenamer.analyze.fitz") as mock_fitz, \
             patch("pdf_split_autorenamer.analyze.extract_text", return_value=""), \
             patch("pdf_split_autorenamer.analyze.crop_page_pixmap", return_value=b"png"), \
             patch("pdf_split_autorenamer.analyze.get_ocr_cache_path", return_value=tmp_path / "cache.txt"), \
             patch("pdf_split_autorenamer.analyze.read_ocr_cache", return_value=None), \
             patch("pdf_split_autorenamer.analyze.extract_text_tesseract", return_value="ROI抽出テキスト"), \
             patch("pdf_split_autorenamer.analyze.write_ocr_cache"), \
             patch("pdf_split_autorenamer.analyze.render_thumb"):
            mock_fitz.open.return_value = fake_doc
            pages = analyze.collect_pages(tmp_path, tmp_path / "thumbs", ocr_strategy="roi")

        assert any("ROI抽出テキスト" in p.get("text", "") for p in pages)


# ---------------------------------------------------------------------------
# ocr_strategy="llm" パス
# ---------------------------------------------------------------------------

class TestCollectPagesLlmStrategy:
    def _make_fake_pdf(self, name: str = "test.pdf") -> MagicMock:
        p = MagicMock(spec=Path)
        p.name = name
        p.stem = name.replace(".pdf", "")
        p.read_bytes.return_value = b"%PDF fake"
        return p

    def _make_fake_doc(self):
        fake_page = MagicMock()
        fake_page.rect = MagicMock()
        fake_page.rect.width = 595.0
        fake_page.rect.height = 842.0
        fake_doc = MagicMock()
        fake_doc.page_count = 1
        fake_doc.__getitem__ = MagicMock(return_value=fake_page)
        fake_doc.close = MagicMock()
        return fake_doc, fake_page

    def test_llm_strategy_success_uses_llm_text(self, tmp_path):
        """llm strategy で LLM Vision が成功した場合、日付+タイトルを text に格納する"""
        from pdf_split_autorenamer import analyze
        fake_pdf = self._make_fake_pdf()
        fake_doc, _ = self._make_fake_doc()

        with patch("pdf_split_autorenamer.analyze.list_pdfs", return_value=[fake_pdf]), \
             patch("pdf_split_autorenamer.analyze.fitz") as mock_fitz, \
             patch("pdf_split_autorenamer.analyze.extract_text", return_value=""), \
             patch("pdf_split_autorenamer.analyze.crop_page_pixmap", return_value=b"png"), \
             patch("pdf_split_autorenamer.analyze.get_ocr_cache_path", return_value=tmp_path / "cache.txt"), \
             patch("pdf_split_autorenamer.analyze.read_ocr_cache", return_value=None), \
             patch("pdf_split_autorenamer.analyze._try_llm_vision", return_value="2026-04-06\n主日礼拝メッセージ要旨") as mock_llm, \
             patch("pdf_split_autorenamer.analyze.write_ocr_cache"), \
             patch("pdf_split_autorenamer.analyze.render_thumb"):
            mock_fitz.open.return_value = fake_doc
            pages = analyze.collect_pages(tmp_path, tmp_path / "thumbs", ocr_strategy="llm")

        mock_llm.assert_called_once()
        assert any("2026-04-06" in p.get("text", "") for p in pages)

    def test_llm_strategy_not_available_falls_back_to_tesseract(self, tmp_path):
        """llm strategy で LLM が利用不可（空文字列）の場合、Tesseract にフォールバック"""
        from pdf_split_autorenamer import analyze
        fake_pdf = self._make_fake_pdf()
        fake_doc, _ = self._make_fake_doc()

        with patch("pdf_split_autorenamer.analyze.list_pdfs", return_value=[fake_pdf]), \
             patch("pdf_split_autorenamer.analyze.fitz") as mock_fitz, \
             patch("pdf_split_autorenamer.analyze.extract_text", return_value=""), \
             patch("pdf_split_autorenamer.analyze.crop_page_pixmap", return_value=b"png"), \
             patch("pdf_split_autorenamer.analyze.get_ocr_cache_path", return_value=tmp_path / "cache.txt"), \
             patch("pdf_split_autorenamer.analyze.read_ocr_cache", return_value=None), \
             patch("pdf_split_autorenamer.analyze._try_llm_vision", return_value=""), \
             patch("pdf_split_autorenamer.analyze.extract_text_tesseract", return_value="Tesseractテキスト") as mock_tess, \
             patch("pdf_split_autorenamer.analyze.write_ocr_cache"), \
             patch("pdf_split_autorenamer.analyze.render_thumb"):
            mock_fitz.open.return_value = fake_doc
            pages = analyze.collect_pages(tmp_path, tmp_path / "thumbs", ocr_strategy="llm")

        mock_tess.assert_called_once()
        assert any("Tesseractテキスト" in p.get("text", "") for p in pages)

    def test_llm_strategy_cache_hit_skips_llm(self, tmp_path):
        """llm strategy でキャッシュヒットの場合は LLM を呼ばない"""
        from pdf_split_autorenamer import analyze
        fake_pdf = self._make_fake_pdf()
        fake_doc, _ = self._make_fake_doc()

        with patch("pdf_split_autorenamer.analyze.list_pdfs", return_value=[fake_pdf]), \
             patch("pdf_split_autorenamer.analyze.fitz") as mock_fitz, \
             patch("pdf_split_autorenamer.analyze.extract_text", return_value=""), \
             patch("pdf_split_autorenamer.analyze.crop_page_pixmap", return_value=b"png"), \
             patch("pdf_split_autorenamer.analyze.get_ocr_cache_path", return_value=tmp_path / "cache.txt"), \
             patch("pdf_split_autorenamer.analyze.read_ocr_cache", return_value="キャッシュ済みテキスト"), \
             patch("pdf_split_autorenamer.analyze._try_llm_vision") as mock_llm, \
             patch("pdf_split_autorenamer.analyze.render_thumb"):
            mock_fitz.open.return_value = fake_doc
            pages = analyze.collect_pages(tmp_path, tmp_path / "thumbs", ocr_strategy="llm")

        mock_llm.assert_not_called()
        assert any("キャッシュ済みテキスト" in p.get("text", "") for p in pages)


# ---------------------------------------------------------------------------
# _try_llm_vision ヘルパー
# ---------------------------------------------------------------------------

class TestTryLlmVision:
    def test_returns_date_and_title_when_available(self):
        """ClaudeVisionBackend が利用可能なら date + title を返す"""
        from pdf_split_autorenamer.analyze import _try_llm_vision
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True
        mock_backend.extract_structured.return_value = {"date": "2026-04-06", "title": "週報"}
        with patch("pdf_split_autorenamer.analyze.ClaudeVisionBackend", return_value=mock_backend):
            result = _try_llm_vision(b"fake_image")
        assert "2026-04-06" in result
        assert "週報" in result

    def test_returns_empty_when_not_available(self):
        """ClaudeVisionBackend が利用不可なら空文字列を返す"""
        from pdf_split_autorenamer.analyze import _try_llm_vision
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = False
        with patch("pdf_split_autorenamer.analyze.ClaudeVisionBackend", return_value=mock_backend):
            result = _try_llm_vision(b"fake_image")
        assert result == ""

    def test_returns_empty_on_exception(self):
        """例外が発生した場合は空文字列を返す"""
        from pdf_split_autorenamer.analyze import _try_llm_vision
        with patch("pdf_split_autorenamer.analyze.ClaudeVisionBackend", side_effect=RuntimeError("API error")):
            result = _try_llm_vision(b"fake_image")
        assert result == ""
