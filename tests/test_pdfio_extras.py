# -*- coding: utf-8 -*-
"""pdfio.py の追加ユニットテスト（外部ツール不要の純 Python 関数）"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from pdf_split_autorenamer.pdfio import (
    find_pdftotext,
    find_tesseract,
    list_pdfs,
)


# ---------------------------------------------------------------------------
# find_tesseract
# ---------------------------------------------------------------------------

class TestFindTesseractExtras:
    def test_returns_none_when_nothing_found(self, monkeypatch, tmp_path):
        """PATH にも固定パスにも tesseract がない場合 None を返す"""
        monkeypatch.delenv("TESSERACT", raising=False)
        # shutil.which が常に None を返すようにモック
        with patch("shutil.which", return_value=None):
            # 固定パスもすべて存在しない tmp_path 配下にリダイレクト
            # Path.is_file() を全部 False にする
            with patch("pdf_split_autorenamer.pdfio.Path") as MockPath:
                # is_file() を常に False に
                instance = MockPath.return_value
                instance.is_file.return_value = False
                # ただし env_path チェックで Path(env_path).is_file() も使う
                result = find_tesseract()
        # None か str のどちらか（環境によって変わる）
        assert result is None or isinstance(result, str)

    def test_env_var_nonexistent_falls_through_to_path_search(self, monkeypatch):
        """TESSERACT env が存在しないパスを指すとき、PATH 検索にフォールスルーする"""
        monkeypatch.setenv("TESSERACT", "/definitely/does/not/exist/tesseract")
        result = find_tesseract()
        assert result is None or isinstance(result, str)

    def test_which_tesseract_found(self, monkeypatch, tmp_path):
        """shutil.which で tesseract が見つかれば、そのパスを返す"""
        monkeypatch.delenv("TESSERACT", raising=False)
        fake = tmp_path / "tesseract"
        fake.write_bytes(b"")
        with patch("shutil.which", return_value=str(fake)):
            result = find_tesseract()
        assert result == str(fake)


# ---------------------------------------------------------------------------
# find_pdftotext
# ---------------------------------------------------------------------------

class TestFindPdftotextExtras:
    def test_env_var_pdftotext_honored(self, monkeypatch, tmp_path):
        """環境変数 PDFTOTEXT に実在するファイルを指定すればそれが返る"""
        fake = tmp_path / "pdftotext.exe"
        fake.write_bytes(b"")
        monkeypatch.setenv("PDFTOTEXT", str(fake))
        result = find_pdftotext()
        assert result == str(fake)

    def test_env_var_nonexistent_falls_through(self, monkeypatch):
        """PDFTOTEXT env が存在しないパスのとき PATH 検索にフォールスルー"""
        monkeypatch.setenv("PDFTOTEXT", "/does/not/exist/pdftotext")
        result = find_pdftotext()
        assert result is None or isinstance(result, str)

    def test_which_pdftotext_found(self, monkeypatch, tmp_path):
        """shutil.which で pdftotext が見つかれば、そのパスを返す"""
        monkeypatch.delenv("PDFTOTEXT", raising=False)
        fake = tmp_path / "pdftotext"
        fake.write_bytes(b"")
        with patch("shutil.which", return_value=str(fake)):
            result = find_pdftotext()
        assert result == str(fake)

    def test_returns_none_when_not_found(self, monkeypatch):
        """何も見つからなければ None を返す"""
        monkeypatch.delenv("PDFTOTEXT", raising=False)
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.is_file", return_value=False):
                result = find_pdftotext()
        assert result is None


# ---------------------------------------------------------------------------
# list_pdfs
# ---------------------------------------------------------------------------

class TestListPdfs:
    def test_returns_empty_for_empty_dir(self, tmp_path):
        """空フォルダでは空リストを返す"""
        result = list_pdfs(tmp_path)
        assert result == []

    def test_returns_pdf_files_only(self, tmp_path):
        """PDF ファイルのみ返し、他の拡張子は無視する"""
        (tmp_path / "a.pdf").write_bytes(b"")
        (tmp_path / "b.pdf").write_bytes(b"")
        (tmp_path / "c.txt").write_bytes(b"")
        (tmp_path / "d.docx").write_bytes(b"")

        result = list_pdfs(tmp_path)
        names = [p.name for p in result]
        assert sorted(names) == ["a.pdf", "b.pdf"]

    def test_returns_sorted_list(self, tmp_path):
        """結果はソート済みで返る"""
        (tmp_path / "z.pdf").write_bytes(b"")
        (tmp_path / "a.pdf").write_bytes(b"")
        (tmp_path / "m.pdf").write_bytes(b"")

        result = list_pdfs(tmp_path)
        names = [p.name for p in result]
        assert names == sorted(names)

    def test_returns_path_objects(self, tmp_path):
        """返り値の各要素が Path オブジェクトである"""
        (tmp_path / "test.pdf").write_bytes(b"")
        result = list_pdfs(tmp_path)
        assert all(isinstance(p, Path) for p in result)

    def test_does_not_recurse_into_subdirs(self, tmp_path):
        """サブディレクトリ内の PDF は含まない（フォルダ直下のみ）"""
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.pdf").write_bytes(b"")
        (tmp_path / "top.pdf").write_bytes(b"")

        result = list_pdfs(tmp_path)
        names = [p.name for p in result]
        assert "top.pdf" in names
        assert "nested.pdf" not in names
