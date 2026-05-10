# -*- coding: utf-8 -*-
"""T-01: Tesseract フォールバック実装の検証テスト (Issue #3 / SPEC FR-1-2 拡張)

RED フェーズ: 全テストが FAIL することを確認する。
"""
from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 関数存在確認
# ---------------------------------------------------------------------------

class TestFunctionExists:
    def test_find_tesseract_exists(self):
        """find_tesseract が pdfio に存在する"""
        from pdf_split_autorenamer import pdfio
        assert hasattr(pdfio, "find_tesseract"), \
            "find_tesseract が pdfio に存在しない"

    def test_has_text_layer_exists(self):
        """has_text_layer が pdfio に存在する"""
        from pdf_split_autorenamer import pdfio
        assert hasattr(pdfio, "has_text_layer"), \
            "has_text_layer が pdfio に存在しない"

    def test_extract_text_tesseract_exists(self):
        """extract_text_tesseract が pdfio に存在する"""
        from pdf_split_autorenamer import pdfio
        assert hasattr(pdfio, "extract_text_tesseract"), \
            "extract_text_tesseract が pdfio に存在しない"


# ---------------------------------------------------------------------------
# シグネチャ確認
# ---------------------------------------------------------------------------

class TestSignatures:
    def test_extract_text_has_ocr_fallback_param(self):
        """extract_text が ocr_fallback パラメータを受け付ける"""
        from pdf_split_autorenamer.pdfio import extract_text
        sig = inspect.signature(extract_text)
        assert "ocr_fallback" in sig.parameters, \
            "extract_text に ocr_fallback パラメータがない"

    def test_extract_text_ocr_fallback_default_true(self):
        """extract_text の ocr_fallback デフォルトは True"""
        from pdf_split_autorenamer.pdfio import extract_text
        sig = inspect.signature(extract_text)
        param = sig.parameters["ocr_fallback"]
        assert param.default is True, \
            f"ocr_fallback のデフォルトが True でない: {param.default}"

    def test_collect_pages_has_ocr_fallback_param(self):
        """collect_pages が ocr_fallback パラメータを受け付ける"""
        from pdf_split_autorenamer.analyze import collect_pages
        sig = inspect.signature(collect_pages)
        assert "ocr_fallback" in sig.parameters, \
            "collect_pages に ocr_fallback パラメータがない"

    def test_run_analyze_has_ocr_fallback_param(self):
        """run_analyze が ocr_fallback パラメータを受け付ける"""
        from pdf_split_autorenamer.analyze import run_analyze
        sig = inspect.signature(run_analyze)
        assert "ocr_fallback" in sig.parameters, \
            "run_analyze に ocr_fallback パラメータがない"

    def test_run_rename_has_ocr_fallback_param(self):
        """run_rename が ocr_fallback パラメータを受け付ける"""
        from pdf_split_autorenamer.rename import run_rename
        sig = inspect.signature(run_rename)
        assert "ocr_fallback" in sig.parameters, \
            "run_rename に ocr_fallback パラメータがない"


# ---------------------------------------------------------------------------
# CLI オプション確認
# ---------------------------------------------------------------------------

class TestCliOptions:
    def test_analyze_has_no_ocr_fallback_option(self):
        """analyze サブコマンドに --no-ocr-fallback オプションが存在する"""
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        # analyze サブコマンドのパーサーを取得して引数を確認
        args = parser.parse_args(["analyze", ".", "--no-ocr-fallback"])
        assert hasattr(args, "no_ocr_fallback"), \
            "analyze に --no-ocr-fallback オプションがない"
        assert args.no_ocr_fallback is True

    def test_rename_has_no_ocr_fallback_option(self):
        """rename サブコマンドに --no-ocr-fallback オプションが存在する"""
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["rename", ".", "--no-ocr-fallback"])
        assert hasattr(args, "no_ocr_fallback"), \
            "rename に --no-ocr-fallback オプションがない"
        assert args.no_ocr_fallback is True

    def test_analyze_no_ocr_fallback_default_false(self):
        """analyze で --no-ocr-fallback を指定しない場合はデフォルト False"""
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["analyze", "."])
        assert args.no_ocr_fallback is False

    def test_rename_no_ocr_fallback_default_false(self):
        """rename で --no-ocr-fallback を指定しない場合はデフォルト False"""
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["rename", "."])
        assert args.no_ocr_fallback is False


# ---------------------------------------------------------------------------
# has_text_layer のロジック確認（fitz モック）
# ---------------------------------------------------------------------------

class TestHasTextLayer:
    def _make_fake_path(self, content: bytes = b"%PDF fake") -> MagicMock:
        p = MagicMock(spec=Path)
        p.read_bytes.return_value = content
        return p

    def _make_page_with_text(self, text: str) -> MagicMock:
        page = MagicMock()
        page.get_text.return_value = text
        return page

    def test_has_text_layer_returns_true_when_text_exists(self):
        """テキストがあるページが1つでもあれば True を返す"""
        from pdf_split_autorenamer import pdfio
        fake_path = self._make_fake_path()

        fake_page = self._make_page_with_text("こんにちは")
        fake_doc = MagicMock()
        fake_doc.__enter__ = lambda s: s
        fake_doc.__exit__ = MagicMock(return_value=False)
        fake_doc.page_count = 1
        fake_doc.__iter__ = MagicMock(return_value=iter([fake_page]))

        with patch("pdf_split_autorenamer.pdfio.fitz") as mock_fitz:
            mock_fitz.open.return_value = fake_doc
            result = pdfio.has_text_layer(fake_path)

        assert result is True

    def test_has_text_layer_returns_false_when_no_text(self):
        """全ページがテキスト空なら False を返す"""
        from pdf_split_autorenamer import pdfio
        fake_path = self._make_fake_path()

        fake_page = self._make_page_with_text("   \n  ")
        fake_doc = MagicMock()
        fake_doc.__enter__ = lambda s: s
        fake_doc.__exit__ = MagicMock(return_value=False)
        fake_doc.page_count = 1
        fake_doc.__iter__ = MagicMock(return_value=iter([fake_page]))

        with patch("pdf_split_autorenamer.pdfio.fitz") as mock_fitz:
            mock_fitz.open.return_value = fake_doc
            result = pdfio.has_text_layer(fake_path)

        assert result is False


# ---------------------------------------------------------------------------
# extract_text_tesseract のロジック確認（find_tesseract モック）
# ---------------------------------------------------------------------------

class TestExtractTextTesseract:
    def test_returns_empty_when_tesseract_not_found(self):
        """find_tesseract が None を返す場合は空文字列を返す"""
        from pdf_split_autorenamer import pdfio
        with patch("pdf_split_autorenamer.pdfio.find_tesseract", return_value=None):
            result = pdfio.extract_text_tesseract(b"fake image bytes")
        assert result == "", \
            f"find_tesseract=None の場合に空文字列が返らない: {result!r}"

    def test_returns_empty_and_warns_when_traineddata_missing(self):
        """jpn traineddata が存在しない場合は空文字列を返し warning を出す"""
        from pdf_split_autorenamer import pdfio
        import subprocess

        fake_proc = MagicMock()
        fake_proc.stdout = b""
        fake_proc.stderr = b"Error, could not initialize tesseract tessdata/jpn.traineddata"
        fake_proc.returncode = 1

        with patch("pdf_split_autorenamer.pdfio.find_tesseract", return_value="/usr/bin/tesseract"), \
             patch("pdf_split_autorenamer.pdfio.subprocess.run", return_value=fake_proc), \
             patch("pdf_split_autorenamer.pdfio.logging.warning") as mock_warn:
            result = pdfio.extract_text_tesseract(b"fake image bytes")

        assert result == ""
        # warning が呼ばれたこと
        assert mock_warn.called, "traineddata 不在時に warning が呼ばれていない"
