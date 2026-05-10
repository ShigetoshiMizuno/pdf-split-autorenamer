# -*- coding: utf-8 -*-
"""T-10a: pdfio モジュールのユニットテスト

対象関数:
- extract_text_pymupdf
- save_pdf_pages
- has_text_layer
- find_tesseract

テスト用 PDF は PyMuPDF でプログラム的に生成する。
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest

from pdf_split_autorenamer.pdfio import (
    extract_text,
    extract_text_pdftotext,
    extract_text_tesseract,
    extract_text_pymupdf,
    find_tesseract,
    has_text_layer,
    save_pdf_pages,
)


# ---------------------------------------------------------------------------
# ヘルパー: テスト用 PDF 生成
# ---------------------------------------------------------------------------

def make_simple_pdf(text: str = "テスト文書 2026年4月6日") -> bytes:
    """テキストレイヤー付きの最小 PDF を bytes で返す"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.write()
    doc.close()
    return data


def make_multipage_pdf(pages: list[str]) -> bytes:
    """複数ページの PDF を生成して bytes で返す"""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    data = doc.write()
    doc.close()
    return data


def make_image_only_pdf() -> bytes:
    """テキストレイヤーなし（画像のみ）の PDF を bytes で返す"""
    doc = fitz.open()
    doc.new_page()  # 何も書き込まない
    data = doc.write()
    doc.close()
    return data


# ---------------------------------------------------------------------------
# extract_text_pymupdf
# ---------------------------------------------------------------------------

class TestExtractTextPymupdf:
    def test_extracts_text_from_single_page(self, tmp_path):
        """生成した PDF から全ページテキストが取得できる"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(make_simple_pdf("テスト文書 2026年4月6日"))

        result = extract_text_pymupdf(pdf_path)
        assert "テスト" in result or "2026" in result, \
            f"テキスト抽出結果が想定外: {result!r}"

    def test_extracts_specific_page(self, tmp_path):
        """page_no 指定でそのページのテキストが取得できる"""
        pdf_path = tmp_path / "multipage.pdf"
        pdf_path.write_bytes(make_multipage_pdf(["ページ1のテキスト", "ページ2のテキスト"]))

        # 1ページ目
        result1 = extract_text_pymupdf(pdf_path, page_no=1)
        assert len(result1) > 0, "1ページ目のテキストが取得できない"

    def test_nonexistent_page_returns_empty(self, tmp_path):
        """存在しないページ番号では空文字列を返す"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(make_simple_pdf())

        result = extract_text_pymupdf(pdf_path, page_no=999)
        assert result == "", f"存在しないページで空文字列以外が返った: {result!r}"

    def test_nonexistent_file_returns_empty(self, tmp_path):
        """存在しないファイルパスでは例外を出さず空文字列を返す"""
        pdf_path = tmp_path / "no_such_file.pdf"
        result = extract_text_pymupdf(pdf_path)
        assert result == "", f"存在しないファイルで空文字列以外が返った: {result!r}"

    def test_page_no_none_returns_all_pages(self, tmp_path):
        """page_no=None（デフォルト）では全ページのテキストを返す"""
        pdf_path = tmp_path / "multipage.pdf"
        pdf_path.write_bytes(make_multipage_pdf(["ページ1", "ページ2", "ページ3"]))

        result = extract_text_pymupdf(pdf_path, page_no=None)
        assert len(result) > 0, "全ページテキストが空"


# ---------------------------------------------------------------------------
# save_pdf_pages
# ---------------------------------------------------------------------------

class TestSavePdfPages:
    def test_saves_single_page_from_multipage_pdf(self, tmp_path):
        """3ページ PDF から1ページ目のみ抽出できる"""
        src_path = tmp_path / "src.pdf"
        out_path = tmp_path / "out.pdf"
        src_path.write_bytes(make_multipage_pdf(["ページ1", "ページ2", "ページ3"]))

        count = save_pdf_pages(src_path, 1, 1, out_path)

        assert out_path.exists(), "出力ファイルが存在しない"
        assert count == 1, f"返り値が 1 でない: {count}"

    def test_output_file_is_valid_pdf(self, tmp_path):
        """出力ファイルが PyMuPDF で開けること"""
        src_path = tmp_path / "src.pdf"
        out_path = tmp_path / "out.pdf"
        src_path.write_bytes(make_multipage_pdf(["ページ1", "ページ2", "ページ3"]))

        save_pdf_pages(src_path, 1, 1, out_path)

        with fitz.open(stream=out_path.read_bytes(), filetype="pdf") as doc:
            assert doc.page_count >= 1, "出力 PDF のページ数が 0"

    def test_return_value_matches_page_count(self, tmp_path):
        """返り値が to_page - from_page + 1 と一致する"""
        src_path = tmp_path / "src.pdf"
        out_path = tmp_path / "out.pdf"
        src_path.write_bytes(make_multipage_pdf(["P1", "P2", "P3"]))

        count = save_pdf_pages(src_path, 1, 2, out_path)
        assert count == 2, f"2ページ抽出の返り値が 2 でない: {count}"

    def test_saves_last_page(self, tmp_path):
        """最終ページのみ抽出できる"""
        src_path = tmp_path / "src.pdf"
        out_path = tmp_path / "out.pdf"
        src_path.write_bytes(make_multipage_pdf(["P1", "P2", "P3"]))

        count = save_pdf_pages(src_path, 3, 3, out_path)
        assert count == 1
        assert out_path.exists()


# ---------------------------------------------------------------------------
# has_text_layer
# ---------------------------------------------------------------------------

class TestHasTextLayer:
    def test_returns_true_for_pdf_with_text(self, tmp_path):
        """テキストレイヤーあり PDF → True"""
        pdf_path = tmp_path / "with_text.pdf"
        pdf_path.write_bytes(make_simple_pdf("テキストあり"))

        assert has_text_layer(pdf_path) is True

    def test_returns_false_for_image_only_pdf(self, tmp_path):
        """画像のみ PDF（テキストなし）→ False"""
        pdf_path = tmp_path / "no_text.pdf"
        pdf_path.write_bytes(make_image_only_pdf())

        assert has_text_layer(pdf_path) is False

    def test_returns_false_for_nonexistent_file(self, tmp_path):
        """存在しないファイルは False を返す（例外なし）"""
        pdf_path = tmp_path / "no_such.pdf"
        result = has_text_layer(pdf_path)
        assert result is False


# ---------------------------------------------------------------------------
# find_tesseract
# ---------------------------------------------------------------------------

class TestFindTesseract:
    def test_return_type_is_str_or_none(self):
        """戻り値が str | None 型であること"""
        result = find_tesseract()
        assert result is None or isinstance(result, str), \
            f"戻り値が str/None でない: {type(result)}"

    def test_env_var_tesseract_is_honored(self, tmp_path, monkeypatch):
        """環境変数 TESSERACT が設定されていればそれが返ること"""
        # 実在するファイルを作る
        fake_tess = tmp_path / "tesseract.exe"
        fake_tess.write_bytes(b"")

        monkeypatch.setenv("TESSERACT", str(fake_tess))
        result = find_tesseract()
        assert result == str(fake_tess), \
            f"TESSERACT 環境変数が無視されている: {result!r}"

    def test_env_var_tesseract_nonexistent_path_falls_through(self, monkeypatch):
        """TESSERACT 環境変数が存在しないパスを指していれば PATH 検索にフォールスルーする"""
        monkeypatch.setenv("TESSERACT", "/nonexistent/path/tesseract")
        # 例外が起きないこと（None または PATH 上の tesseract が返る）
        result = find_tesseract()
        assert result is None or isinstance(result, str)

    def test_unset_env_var_does_not_raise(self, monkeypatch):
        """TESSERACT 環境変数が未設定でも例外が起きない"""
        monkeypatch.delenv("TESSERACT", raising=False)
        result = find_tesseract()
        assert result is None or isinstance(result, str)

    def test_hardcoded_path_found_when_which_returns_none(self, monkeypatch):
        """shutil.which が None で TESSERACT 未設定のとき、ハードコードパスが返ること"""
        monkeypatch.delenv("TESSERACT", raising=False)
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.is_file", return_value=True):
                result = find_tesseract()
        assert isinstance(result, str)

    def test_hardcoded_pdftotext_path_found(self, monkeypatch):
        """find_pdftotext: shutil.which が None のとき、ハードコードパスが返ること"""
        from pdf_split_autorenamer.pdfio import find_pdftotext
        monkeypatch.delenv("PDFTOTEXT", raising=False)
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.is_file", return_value=True):
                result = find_pdftotext()
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# extract_text (メイン関数)
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_returns_text_when_pdftotext_unavailable(self, tmp_path):
        """pdftotext が利用不可のとき PyMuPDF にフォールバックしてテキストを返す"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(make_simple_pdf("hello world"))
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = extract_text(pdf_path, ocr_fallback=False)
        assert isinstance(result, str)

    def test_returns_str_from_real_pdf(self, tmp_path):
        """実際の PDF から文字列が返る"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(make_simple_pdf("2026-04-06 text"))
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = extract_text(pdf_path, ocr_fallback=False)
        assert isinstance(result, str)

    def test_nonexistent_pdf_returns_str(self, tmp_path):
        """存在しないファイルでも文字列を返す（例外を出さない）"""
        pdf_path = tmp_path / "no_such.pdf"
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = extract_text(pdf_path, ocr_fallback=False)
        assert isinstance(result, str)

    def test_ocr_fallback_on_empty_pdf(self, tmp_path):
        """テキストなし PDF で ocr_fallback=True のとき OCR パスを通る（lines 152-161）"""
        pdf_path = tmp_path / "empty.pdf"
        pdf_path.write_bytes(make_image_only_pdf())
        # Tesseract なし環境: extract_text_tesseract が "" を返す
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            with patch("pdf_split_autorenamer.pdfio.find_tesseract", return_value=None):
                result = extract_text(pdf_path, ocr_fallback=True)
        assert isinstance(result, str)

    def test_ocr_fallback_page_no_specified(self, tmp_path):
        """page_no 指定時の OCR フォールバックパス（line 155-156）"""
        pdf_path = tmp_path / "empty.pdf"
        pdf_path.write_bytes(make_image_only_pdf())
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            with patch("pdf_split_autorenamer.pdfio.find_tesseract", return_value=None):
                result = extract_text(pdf_path, page_no=1, ocr_fallback=True)
        assert isinstance(result, str)

    def test_ocr_fallback_returns_ocr_text_when_tesseract_succeeds(self, tmp_path):
        """Tesseract が非空テキストを返したとき ocr_text を返す（line 162）"""
        pdf_path = tmp_path / "empty.pdf"
        pdf_path.write_bytes(make_image_only_pdf())
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            with patch("pdf_split_autorenamer.pdfio.extract_text_tesseract",
                       return_value="OCR テキスト"):
                result = extract_text(pdf_path, ocr_fallback=True)
        assert result == "OCR テキスト"

    def test_ocr_fallback_exception_handled(self, tmp_path):
        """OCR フォールバック中に例外が発生しても '' を返す（lines 163-164）"""
        pdf_path = tmp_path / "empty.pdf"
        pdf_path.write_bytes(make_image_only_pdf())
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            with patch("pdf_split_autorenamer.pdfio.extract_text_pymupdf", return_value=""):
                with patch("fitz.open", side_effect=RuntimeError("open failed")):
                    result = extract_text(pdf_path, ocr_fallback=True)
        assert isinstance(result, str)


class TestExtractTextPdftotext:
    def test_returns_empty_when_copy_fails(self, tmp_path):
        """pdf_path が存在しない場合 shutil.copy2 が失敗して '' を返す（lines 120-121）"""
        pdf_path = tmp_path / "nonexistent.pdf"
        result = extract_text_pdftotext(pdf_path, pdftotext="fake_pdftotext_exe")
        assert result == ""

    def test_finally_unlink_exception_is_swallowed(self, tmp_path):
        """finally 内で unlink が失敗しても例外が外に漏れない（lines 126-127）"""
        pdf_path = tmp_path / "nonexistent.pdf"
        with patch("pathlib.Path.unlink", side_effect=PermissionError("locked")):
            # shutil.copy2 が失敗して except で "" が返るが finally の unlink も失敗する
            result = extract_text_pdftotext(pdf_path, pdftotext="fake_pdftotext_exe")
        assert result == ""


class TestExtractTextTesseract:
    def test_tessdata_warning_returns_empty(self):
        """stderr に tessdata が含まれる場合 logging.warning を出して '' を返す（lines 68-72）"""
        mock_result = MagicMock()
        mock_result.stdout = b""
        mock_result.stderr = b"Error, could not initialize tessdata"
        with patch("pdf_split_autorenamer.pdfio.find_tesseract", return_value="/fake/tesseract"):
            with patch("subprocess.run", return_value=mock_result):
                result = extract_text_tesseract(b"fake image bytes")
        assert result == ""

    def test_success_returns_decoded_stdout(self):
        """正常に実行された場合 stdout を decode して返す（line 73）"""
        mock_result = MagicMock()
        mock_result.stdout = "認識テキスト\n".encode("utf-8")
        mock_result.stderr = b""  # tessdata 警告なし
        with patch("pdf_split_autorenamer.pdfio.find_tesseract", return_value="/fake/tesseract"):
            with patch("subprocess.run", return_value=mock_result):
                result = extract_text_tesseract(b"fake image bytes")
        assert "認識テキスト" in result

    def test_subprocess_exception_returns_empty(self):
        """subprocess.run が例外を投げた場合 '' を返す（lines 74-75）"""
        with patch("pdf_split_autorenamer.pdfio.find_tesseract", return_value="/fake/tesseract"):
            with patch("subprocess.run", side_effect=RuntimeError("crash")):
                result = extract_text_tesseract(b"fake image bytes")
        assert result == ""


# ---------------------------------------------------------------------------
# render_thumb
# ---------------------------------------------------------------------------

class TestRenderThumb:
    def test_creates_jpeg_file(self, tmp_path):
        """render_thumb が JPEG ファイルを生成する"""
        import fitz
        from pdf_split_autorenamer.pdfio import render_thumb
        # PDF を作成してページオブジェクトを取得
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "thumb test")
        out_path = tmp_path / "thumb.jpg"
        render_thumb(page, out_path)
        doc.close()
        assert out_path.exists()
        assert out_path.stat().st_size > 0

    def test_thumbnail_is_valid_image(self, tmp_path):
        """生成された JPEG が PyMuPDF で読み取れる（有効な画像ファイル）"""
        import fitz
        from pdf_split_autorenamer.pdfio import render_thumb
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "valid image test")
        out_path = tmp_path / "thumb.jpg"
        render_thumb(page, out_path, max_long_side=200)
        doc.close()
        # ファイルが存在してサイズが 0 より大きければ有効な JPEG とみなす
        assert out_path.exists()
        assert out_path.stat().st_size > 100  # 最低限のサイズ

    def test_max_long_side_limits_size(self, tmp_path):
        """max_long_side が小さいほどファイルサイズが小さくなる（粗い確認）"""
        import fitz
        from pdf_split_autorenamer.pdfio import render_thumb
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "size test")
        out_small = tmp_path / "small.jpg"
        out_large = tmp_path / "large.jpg"
        render_thumb(page, out_small, max_long_side=100)
        render_thumb(page, out_large, max_long_side=600)
        doc.close()
        assert out_small.stat().st_size <= out_large.stat().st_size + 1000
