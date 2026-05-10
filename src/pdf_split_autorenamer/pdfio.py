# -*- coding: utf-8 -*-
"""PDF入出力ユーティリティ（PyMuPDF + Poppler pdftotext）"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

import fitz  # PyMuPDF


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
                 pdftotext: str | None = None) -> str:
    """テキスト抽出: pdftotext を優先、なければ PyMuPDF。"""
    text = extract_text_pdftotext(pdf_path, page_no, pdftotext)
    if not text.strip():
        text = extract_text_pymupdf(pdf_path, page_no)
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
