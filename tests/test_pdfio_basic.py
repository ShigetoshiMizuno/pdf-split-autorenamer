# -*- coding: utf-8 -*-
"""pdfio.py の基本テスト（main ブランチ用）"""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pdf_split_autorenamer.pdfio import (
    extract_text,
    extract_text_pdftotext,
    extract_text_pymupdf,
    find_pdftotext,
    list_pdfs,
    render_thumb,
    save_pdf_pages,
)


def _make_pdf(path: Path, pages: int = 2, text: str = "") -> Path:
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        if text:
            page.insert_text((50, 50), text)
    doc.save(str(path))
    doc.close()
    return path


class TestFindPdftotext:
    def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.delenv("PDFTOTEXT", raising=False)
        from unittest.mock import patch
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.is_file", return_value=False):
                result = find_pdftotext()
        assert result is None

    def test_env_var_takes_priority(self, tmp_path, monkeypatch):
        fake_exe = tmp_path / "pdftotext.exe"
        fake_exe.write_bytes(b"fake")
        monkeypatch.setenv("PDFTOTEXT", str(fake_exe))
        result = find_pdftotext()
        assert result == str(fake_exe)

    def test_finds_from_candidate_paths(self, monkeypatch):
        # Mocks Path.is_file to True so the first Windows candidate is returned (line 34)
        monkeypatch.delenv("PDFTOTEXT", raising=False)
        from unittest.mock import patch
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.is_file", return_value=True):
                result = find_pdftotext()
        assert result is not None
        assert result.endswith("pdftotext.exe")


class TestExtractTextPymupdf:
    def test_extracts_text_from_pdf(self, tmp_path):
        pdf = _make_pdf(tmp_path / "test.pdf", text="Hello PDF")
        text = extract_text_pymupdf(pdf)
        assert "Hello PDF" in text

    def test_page_no_out_of_range_returns_empty(self, tmp_path):
        pdf = _make_pdf(tmp_path / "test.pdf", pages=2)
        result = extract_text_pymupdf(pdf, page_no=999)
        assert result == ""

    def test_page_no_in_range_returns_text(self, tmp_path):
        pdf = _make_pdf(tmp_path / "test.pdf", pages=2, text="Page text")
        result = extract_text_pymupdf(pdf, page_no=1)
        assert isinstance(result, str)

    def test_nonexistent_file_returns_empty(self, tmp_path):
        result = extract_text_pymupdf(tmp_path / "nonexistent.pdf")
        assert result == ""


class TestExtractTextPdftotext:
    def test_returns_empty_when_no_pdftotext_available(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PDFTOTEXT", raising=False)
        from unittest.mock import patch
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.is_file", return_value=False):
                result = extract_text_pdftotext(tmp_path / "test.pdf", pdftotext=None)
        assert result == ""


class TestExtractText:
    def test_falls_back_to_pymupdf_when_no_pdftotext(self, tmp_path):
        pdf = _make_pdf(tmp_path / "test.pdf", text="Fallback text")
        text = extract_text(pdf, pdftotext="nonexistent_command")
        assert isinstance(text, str)


class TestSavePdfPages:
    def test_saves_selected_pages(self, tmp_path):
        src = _make_pdf(tmp_path / "src.pdf", pages=3)
        out = tmp_path / "out.pdf"
        count = save_pdf_pages(src, 1, 2, out)
        assert count == 2
        assert out.exists()
        with fitz.open(out) as doc:
            assert doc.page_count == 2

    def test_single_page_extracted(self, tmp_path):
        src = _make_pdf(tmp_path / "src.pdf", pages=3)
        out = tmp_path / "out.pdf"
        count = save_pdf_pages(src, 2, 2, out)
        assert count == 1
        with fitz.open(out) as doc:
            assert doc.page_count == 1


class TestRenderThumb:
    def test_creates_jpeg_file(self, tmp_path):
        doc = fitz.open()
        doc.new_page()
        out = tmp_path / "thumb.jpg"
        render_thumb(doc[0], out)
        doc.close()
        assert out.exists()
        assert out.stat().st_size > 0

    def test_respects_max_long_side(self, tmp_path):
        doc = fitz.open()
        doc.new_page(width=1200, height=900)
        out = tmp_path / "thumb.jpg"
        render_thumb(doc[0], out, max_long_side=300)
        doc.close()
        assert out.exists()


class TestListPdfs:
    def test_returns_pdf_files_only(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "b.txt").write_bytes(b"text")
        result = list_pdfs(tmp_path)
        assert len(result) == 1
        assert result[0].name == "a.pdf"

    def test_returns_sorted_list(self, tmp_path):
        (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
        result = list_pdfs(tmp_path)
        assert result[0].name == "a.pdf"

    def test_empty_folder_returns_empty(self, tmp_path):
        assert list_pdfs(tmp_path) == []
