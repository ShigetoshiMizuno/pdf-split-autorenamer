# -*- coding: utf-8 -*-
"""v0.2 quick-wins の変更検証テスト

T-07b: avg_phash / hamming 削除
T-04b: _KEEP_CHARS 削除
T-00:  fitz.open() をバイトストリーム経由に変更
FR-1-2: collect_pages が extract_text 経由で動くこと
"""
from __future__ import annotations

import io
import struct
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# T-07b: avg_phash / hamming がエクスポートされていないこと
# ---------------------------------------------------------------------------

class TestT07b_PhashRemoved:
    def test_avg_phash_not_in_pdfio(self):
        """avg_phash は pdfio から削除されている"""
        from pdf_split_autorenamer import pdfio
        assert not hasattr(pdfio, "avg_phash"), \
            "avg_phash が pdfio に残っている（削除されていない）"

    def test_hamming_not_in_pdfio(self):
        """hamming は pdfio から削除されている"""
        from pdf_split_autorenamer import pdfio
        assert not hasattr(pdfio, "hamming"), \
            "hamming が pdfio に残っている（削除されていない）"

    def test_avg_phash_not_imported_in_analyze(self):
        """avg_phash は analyze モジュールにインポートされていない"""
        from pdf_split_autorenamer import analyze
        assert not hasattr(analyze, "avg_phash"), \
            "avg_phash が analyze に残っている"

    def test_hamming_not_imported_in_analyze(self):
        """hamming は analyze モジュールにインポートされていない"""
        from pdf_split_autorenamer import analyze
        assert not hasattr(analyze, "hamming"), \
            "hamming が analyze に残っている"


# ---------------------------------------------------------------------------
# T-04b: _KEEP_CHARS が textops に存在しないこと
# ---------------------------------------------------------------------------

class TestT04b_KeepCharsRemoved:
    def test_keep_chars_not_in_textops(self):
        """_KEEP_CHARS は textops から削除されている"""
        from pdf_split_autorenamer import textops
        assert not hasattr(textops, "_KEEP_CHARS"), \
            "_KEEP_CHARS が textops に残っている（削除されていない）"

    def test_sanitize_filename_still_works(self):
        """_KEEP_CHARS 削除後も sanitize_filename は正常に動作する"""
        from pdf_split_autorenamer.textops import sanitize_filename
        assert sanitize_filename("2026-04-06 主日礼拝") == "2026-04-06_主日礼拝"
        assert sanitize_filename('abc<>:"/\\|?*def') == "abcdef"
        assert sanitize_filename("") == ""


# ---------------------------------------------------------------------------
# T-00: fitz.open() がバイトストリーム経由で呼ばれること
# ---------------------------------------------------------------------------

class TestT00_FitzOpenStream:
    """extract_text_pymupdf と save_pdf_pages が stream= で fitz.open を呼ぶか検証"""

    def _make_fake_path(self, content: bytes = b"%PDF-1.4 fake") -> MagicMock:
        p = MagicMock(spec=Path)
        p.read_bytes.return_value = content
        return p

    def test_extract_text_pymupdf_uses_stream(self):
        """extract_text_pymupdf は fitz.open(stream=...) を使う"""
        from pdf_split_autorenamer import pdfio

        fake_path = self._make_fake_path()
        fake_doc = MagicMock()
        fake_doc.__enter__ = lambda s: s
        fake_doc.__exit__ = MagicMock(return_value=False)
        fake_doc.page_count = 0

        with patch("pdf_split_autorenamer.pdfio.fitz") as mock_fitz:
            mock_fitz.open.return_value = fake_doc
            pdfio.extract_text_pymupdf(fake_path)

        call_kwargs = mock_fitz.open.call_args
        assert "stream" in call_kwargs.kwargs, \
            "fitz.open が stream= キーワードで呼ばれていない"
        assert call_kwargs.kwargs.get("filetype") == "pdf", \
            "fitz.open に filetype='pdf' が渡されていない"
        # 旧来の位置引数でパスを渡していないこと
        assert len(call_kwargs.args) == 0, \
            "fitz.open に位置引数（パス）が渡されている（ストリーム経由になっていない）"

    def test_save_pdf_pages_uses_stream(self):
        """save_pdf_pages は fitz.open(stream=...) を使う"""
        from pdf_split_autorenamer import pdfio

        src = self._make_fake_path()
        out = MagicMock(spec=Path)
        out.write_bytes = MagicMock()

        fake_src_doc = MagicMock()
        fake_src_doc.__enter__ = lambda s: s
        fake_src_doc.__exit__ = MagicMock(return_value=False)
        fake_src_doc.page_count = 3

        fake_new_doc = MagicMock()
        fake_new_doc.insert_pdf = MagicMock()
        fake_new_doc.write = MagicMock(return_value=b"pdfdata")
        fake_new_doc.close = MagicMock()

        with patch("pdf_split_autorenamer.pdfio.fitz") as mock_fitz:
            mock_fitz.open.side_effect = [fake_src_doc, fake_new_doc]
            pdfio.save_pdf_pages(src, 1, 1, out)

        first_call = mock_fitz.open.call_args_list[0]
        assert "stream" in first_call.kwargs, \
            "save_pdf_pages の fitz.open が stream= で呼ばれていない"
        assert first_call.kwargs.get("filetype") == "pdf"


# ---------------------------------------------------------------------------
# FR-1-2: collect_pages が extract_text 経由で動くこと
# ---------------------------------------------------------------------------

class TestFR12_CollectPagesUsesExtractText:
    """collect_pages が pdfio.extract_text を呼び、phash フィールドを含まないこと"""

    def _make_fake_pdf_path(self, name: str = "test.pdf") -> MagicMock:
        p = MagicMock(spec=Path)
        p.name = name
        p.stem = name.replace(".pdf", "")
        p.read_bytes.return_value = b"%PDF fake"
        return p

    def test_collect_pages_calls_extract_text(self, tmp_path):
        """collect_pages が _pdfio.extract_text を経由してテキストを抽出する"""
        from pdf_split_autorenamer import analyze

        fake_pdf = self._make_fake_pdf_path("sample.pdf")

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
             patch("pdf_split_autorenamer.analyze.extract_text",
                   return_value="テストテキスト") as mock_et, \
             patch("pdf_split_autorenamer.analyze.render_thumb"):
            mock_fitz.open.return_value = fake_doc
            thumb_dir = tmp_path / "thumbs"
            pages = analyze.collect_pages(tmp_path, thumb_dir)

        mock_et.assert_called_once()
        assert len(pages) == 1
        assert "phash" not in pages[0], \
            "phash フィールドが pages に残っている（T-07b と矛盾）"

    def test_score_boundary_no_phash_reference(self):
        """score_boundary が phash フィールドを参照しないこと"""
        from pdf_split_autorenamer.analyze import score_boundary

        # phash なし dict でも例外が起きないこと
        prev = {
            "pdf": "a.pdf", "orient": "P",
            "width": 595.0, "height": 842.0,
            "bigram": {"ab", "bc"},
            "title_markers": [],
        }
        cur = {
            "pdf": "a.pdf", "orient": "P",
            "width": 595.0, "height": 842.0,
            "bigram": {"ab", "bc"},
            "title_markers": [],
        }
        score, reasons = score_boundary(prev, cur)
        assert isinstance(score, float)
        assert isinstance(reasons, list)
        # "ph=" が reason に入っていないこと
        for r in reasons:
            assert "ph=" not in r, f"phash 参照が reason に残っている: {r}"
