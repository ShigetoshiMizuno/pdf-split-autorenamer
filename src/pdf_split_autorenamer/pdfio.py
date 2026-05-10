# -*- coding: utf-8 -*-
"""PDF入出力ユーティリティ（PyMuPDF + Poppler pdftotext）"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

import fitz  # PyMuPDF


def find_tesseract() -> str | None:
    """tesseract の実行ファイルを探す。環境変数 TESSERACT を最優先。"""
    env_path = os.environ.get("TESSERACT")
    if env_path and Path(env_path).is_file():
        return env_path
    # PATH 上を探す
    p = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if p:
        return p
    # Windows でよくあるインストール先
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ]
    for c in candidates:
        if Path(c).is_file():
            return c
    return None


def has_text_layer(pdf_path: Path) -> bool:
    """PDFにテキストレイヤーがあるか確認する。
    1ページでも空でないテキストがあれば True、全ページ空なら False。"""
    try:
        with fitz.open(stream=pdf_path.read_bytes(), filetype="pdf") as doc:
            for page in doc:
                if page.get_text().strip():
                    return True
    except Exception:
        pass
    return False


def extract_text_tesseract(image_bytes: bytes, lang: str = "jpn") -> str:
    """tesseract を subprocess で呼び出してテキストを返す。
    tesseract が見つからない場合や jpn traineddata がない場合は空文字列を返す。"""
    tess = find_tesseract()
    if not tess:
        return ""
    cmd = [tess, "stdin", "stdout", "-l", lang, "--psm", "3"]
    try:
        result = subprocess.run(
            cmd,
            input=image_bytes,
            capture_output=True,
            timeout=30,
        )
        stderr = result.stderr.decode("utf-8", errors="replace")
        if "tessdata" in stderr:
            logging.warning(
                "Tesseract jpn traineddata が見つかりません。"
                "インストール方法: https://github.com/UB-Mannheim/tesseract/wiki"
            )
            return ""
        return result.stdout.decode("utf-8", errors="replace")
    except Exception:
        return ""


def find_pdftotext() -> str | None:
    """pdftotext (Poppler) の実行ファイルを探す"""
    # 環境変数を優先
    env_path = os.environ.get("PDFTOTEXT")
    if env_path and Path(env_path).is_file():
        return env_path
    # PATH 上を探す
    p = shutil.which("pdftotext") or shutil.which("pdftotext.exe")
    if p:
        return p
    # Windows でよくあるインストール先
    candidates = [
        r"C:\Program Files\Git\mingw64\bin\pdftotext.exe",
        r"C:\Program Files (x86)\poppler\bin\pdftotext.exe",
        r"C:\Program Files\poppler\bin\pdftotext.exe",
        r"C:\poppler\bin\pdftotext.exe",
    ]
    for c in candidates:
        if Path(c).is_file():
            return c
    return None


def extract_text_pdftotext(pdf_path: Path, page_no: int | None = None,
                          pdftotext: str | None = None) -> str:
    """pdftotext (Poppler) で UTF-8 テキストを取得。
    日本語ファイル名対策で ASCII 一時ファイルへコピーしてから渡す。"""
    pdftotext = pdftotext or find_pdftotext()
    if not pdftotext:
        return ""
    tmp_path: Path | None = None
    try:
        fd, name = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        tmp_path = Path(name)
        shutil.copy2(pdf_path, tmp_path)
        cmd = [pdftotext, "-enc", "UTF-8", "-layout"]
        if page_no is not None:
            cmd += ["-f", str(page_no), "-l", str(page_no)]
        cmd += [str(tmp_path), "-"]
        out = subprocess.run(cmd, capture_output=True, timeout=60)
        return out.stdout.decode("utf-8", errors="replace")
    except Exception:
        return ""
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def extract_text_pymupdf(pdf_path: Path, page_no: int | None = None) -> str:
    """PyMuPDF で生テキストを取得（pdftotext がない場合のフォールバック）"""
    try:
        with fitz.open(stream=pdf_path.read_bytes(), filetype="pdf") as doc:
            if page_no is not None:
                if 1 <= page_no <= doc.page_count:
                    return doc[page_no - 1].get_text()
                return ""
            return "\n".join(doc[i].get_text() for i in range(doc.page_count))
    except Exception:
        return ""


def extract_text(pdf_path: Path, page_no: int | None = None,
                 pdftotext: str | None = None,
                 ocr_fallback: bool = True) -> str:
    """テキスト抽出: pdftotext を優先、なければ PyMuPDF。
    ocr_fallback=True の場合、テキストが空なら Tesseract でリトライする。"""
    text = extract_text_pdftotext(pdf_path, page_no, pdftotext)
    if not text.strip():
        text = extract_text_pymupdf(pdf_path, page_no)
    if not text.strip() and ocr_fallback:
        try:
            with fitz.open(stream=pdf_path.read_bytes(), filetype="pdf") as doc:
                if page_no is not None:
                    pages = [doc[page_no - 1]] if 1 <= page_no <= doc.page_count else []
                else:
                    pages = list(doc)
                for page in pages:
                    image_bytes = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
                    ocr_text = extract_text_tesseract(image_bytes)
                    if ocr_text.strip():
                        return ocr_text
        except Exception:
            pass
    return text


def render_thumb(page: fitz.Page, out_path: Path, max_long_side: int = 600,
                 jpeg_quality: int = 70) -> None:
    """ページのサムネを JPEG で保存"""
    rect = page.rect
    long_side = max(rect.width, rect.height)
    zoom = max_long_side / long_side if long_side > 0 else 1.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(str(out_path), jpg_quality=jpeg_quality)


def save_pdf_pages(src_pdf: Path, from_page: int, to_page: int, out_path: Path,
                   garbage: int = 3, deflate: bool = True) -> int:
    """src_pdf の from_page〜to_page (1-based) を out_path に書き出す。
    PyMuPDF の Document.write でバイト経由にして日本語パスを安全に扱う。"""
    with fitz.open(stream=src_pdf.read_bytes(), filetype="pdf") as src_doc:
        new_doc = fitz.open()
        try:
            new_doc.insert_pdf(src_doc, from_page=from_page - 1, to_page=to_page - 1)
            data = new_doc.write(garbage=garbage, deflate=deflate)
        finally:
            new_doc.close()
    out_path.write_bytes(data)
    return to_page - from_page + 1


def list_pdfs(folder: Path) -> list[Path]:
    """フォルダ直下の *.pdf を返す"""
    return sorted(p for p in folder.glob("*.pdf") if p.is_file())


def crop_page_pixmap(page: "fitz.Page", ratio: float = 0.3) -> bytes:
    """ページ上部 ratio * 100% を PNG バイト列で返す（Stage 2 ROI OCR 用）。"""
    rect = page.rect
    ratio = max(0.0, min(1.0, ratio))
    crop_height = rect.height * ratio if ratio > 0 else 1.0
    crop_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + crop_height)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=crop_rect)
    return pix.tobytes("png")


def calc_japanese_ratio(text: str) -> float:
    """テキスト中の日本語文字（U+3040〜U+9FFF）の比率を返す。空文字列は 0.0。"""
    if not text:
        return 0.0
    count = sum(1 for c in text if 0x3040 <= ord(c) <= 0x9FFF)
    return count / len(text)


def get_ocr_cache_path(work_dir: Path, image_bytes: bytes) -> Path:
    """image_bytes の SHA-256 ハッシュを用いて OCR キャッシュファイルパスを返す。
    ocr_cache ディレクトリは自動作成される。"""
    digest = hashlib.sha256(image_bytes).hexdigest()
    cache_dir = work_dir / "ocr_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{digest}.txt"


def write_ocr_cache(cache_path: Path, text: str) -> None:
    """OCR 結果をキャッシュファイルに書き出す。"""
    cache_path.write_text(text, encoding="utf-8")


def read_ocr_cache(cache_path: Path) -> str | None:
    """キャッシュファイルが存在すれば内容を返す。なければ None。"""
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    return None
