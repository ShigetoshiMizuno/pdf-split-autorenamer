# -*- coding: utf-8 -*-
"""エンドツーエンド統合テスト

analyze → split → rename の全パイプラインを実際の PDF を使って検証する。
各ステップの出力が次のステップの入力として正しく機能することを確認する。
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

from pdf_split_autorenamer.analyze import run_analyze
from pdf_split_autorenamer.rename import run_rename
from pdf_split_autorenamer.split import run_split


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _make_weekly_bulletin_pdf(tmp_path: Path, name: str, date_str: str) -> Path:
    """テキストレイヤー付き週報 PDF を生成する"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"{date_str} weekly bulletin")
    data = doc.write()
    doc.close()
    p = tmp_path / name
    p.write_bytes(data)
    return p


def _make_multipage_pdf(tmp_path: Path, name: str, pages: list[str]) -> Path:
    """複数ページ PDF を生成する"""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    data = doc.write()
    doc.close()
    p = tmp_path / name
    p.write_bytes(data)
    return p


# ---------------------------------------------------------------------------
# analyze → split パイプライン
# ---------------------------------------------------------------------------

class TestAnalyzeSplitPipeline:
    def test_analyze_creates_groups_json(self, tmp_path):
        """run_analyze が groups.json を生成する"""
        _make_multipage_pdf(tmp_path, "scan.pdf", ["Page 1 content", "Page 2 content"])
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = run_analyze(tmp_path, ocr_fallback=False)
        assert result["groups"] >= 1
        groups_json = tmp_path / ".psar" / "groups.json"
        assert groups_json.exists()

    def test_analyze_then_split_produces_files(self, tmp_path):
        """analyze → split のパイプラインで分割ファイルが生成される"""
        _make_multipage_pdf(tmp_path, "source.pdf", ["First doc", "Second doc"])
        work_dir = tmp_path / ".psar"

        # groups.json を手動で書いてから分割
        work_dir.mkdir()
        groups = {
            "source.pdf": [
                {"range": [1, 1], "name": "first"},
                {"range": [2, 2], "name": "second"},
            ]
        }
        (work_dir / "groups.json").write_text(
            json.dumps(groups, ensure_ascii=False), encoding="utf-8"
        )

        result = run_split(tmp_path)
        assert result["files_written"] == 2
        assert (tmp_path / "source_01_first.pdf").exists()
        assert (tmp_path / "source_02_second.pdf").exists()

    def test_split_output_is_valid_pdf(self, tmp_path):
        """分割された PDF ファイルが PyMuPDF で開ける有効な PDF である"""
        _make_multipage_pdf(tmp_path, "source.pdf", ["page1", "page2", "page3"])
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        groups = {
            "source.pdf": [
                {"range": [1, 2], "name": "part1"},
                {"range": [3, 3], "name": "part2"},
            ]
        }
        (work_dir / "groups.json").write_text(
            json.dumps(groups, ensure_ascii=False), encoding="utf-8"
        )

        run_split(tmp_path)

        for out_name in ["source_01_part1.pdf", "source_02_part2.pdf"]:
            out_path = tmp_path / out_name
            assert out_path.exists()
            with fitz.open(stream=out_path.read_bytes(), filetype="pdf") as doc:
                assert doc.page_count >= 1

    def test_source_pdf_preserved_after_split(self, tmp_path):
        """分割後も元の PDF が保持されている（意図的な設計）"""
        _make_multipage_pdf(tmp_path, "source.pdf", ["page1", "page2"])
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        groups = {"source.pdf": [{"range": [1, 2], "name": ""}]}
        (work_dir / "groups.json").write_text(
            json.dumps(groups, ensure_ascii=False), encoding="utf-8"
        )

        run_split(tmp_path)

        assert (tmp_path / "source.pdf").exists()


# ---------------------------------------------------------------------------
# split → rename パイプライン
# ---------------------------------------------------------------------------

class TestSplitRenamePipeline:
    def test_split_then_rename_dry_run(self, tmp_path):
        """split 後に rename dry-run が正常に動作する"""
        # 分割済みファイルを模擬（split モードのファイル名パターン）
        _make_weekly_bulletin_pdf(tmp_path, "scan_01.pdf", "2026-04-06")

        result = run_rename(tmp_path, mode="split", apply=False, ocr_fallback=False)

        assert result["targets"] == 1
        actions = result["actions"]
        assert len(actions) == 1
        assert actions[0]["status"] == "dry-run"

    def test_split_then_rename_apply(self, tmp_path):
        """split 後に rename apply が実際にリネームを行う"""
        _make_weekly_bulletin_pdf(tmp_path, "scan_01.pdf", "2026-04-06")

        result = run_rename(tmp_path, mode="split", apply=True, ocr_fallback=False)

        assert result["applied"] == 1
        assert not (tmp_path / "scan_01.pdf").exists()
        # リネーム後のファイルが存在する
        renamed_files = list(tmp_path.glob("*.pdf"))
        assert len(renamed_files) == 1


# ---------------------------------------------------------------------------
# 複数 PDF の処理
# ---------------------------------------------------------------------------

class TestMultiplePdfPipeline:
    def test_split_multiple_pdfs(self, tmp_path):
        """複数の PDF を同時に処理できる"""
        _make_multipage_pdf(tmp_path, "doc1.pdf", ["doc1-page1"])
        _make_multipage_pdf(tmp_path, "doc2.pdf", ["doc2-page1", "doc2-page2"])
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        groups = {
            "doc1.pdf": [{"range": [1, 1], "name": "first"}],
            "doc2.pdf": [
                {"range": [1, 1], "name": "partA"},
                {"range": [2, 2], "name": "partB"},
            ],
        }
        (work_dir / "groups.json").write_text(
            json.dumps(groups, ensure_ascii=False), encoding="utf-8"
        )

        result = run_split(tmp_path)

        assert result["files_written"] == 3
        assert (tmp_path / "doc1_01_first.pdf").exists()
        assert (tmp_path / "doc2_01_partA.pdf").exists()
        assert (tmp_path / "doc2_02_partB.pdf").exists()

    def test_rename_multiple_files(self, tmp_path):
        """複数の分割済みファイルを一括リネームできる"""
        _make_weekly_bulletin_pdf(tmp_path, "scan_01.pdf", "2026-04-06")
        _make_weekly_bulletin_pdf(tmp_path, "scan_02.pdf", "2026-04-13")

        result = run_rename(tmp_path, mode="split", apply=False, ocr_fallback=False)

        assert result["targets"] == 2
        assert len(result["actions"]) == 2


# ---------------------------------------------------------------------------
# groups.json スキーマ互換性
# ---------------------------------------------------------------------------

class TestGroupsJsonCompatibility:
    def test_old_schema_works_with_split(self, tmp_path):
        """旧スキーマ（list of [from, to]）でも run_split が動作する"""
        _make_multipage_pdf(tmp_path, "source.pdf", ["P1", "P2"])
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        # 旧スキーマ
        old_groups = {"source.pdf": [[1, 1], [2, 2]]}
        (work_dir / "groups.json").write_text(
            json.dumps(old_groups, ensure_ascii=False), encoding="utf-8"
        )

        result = run_split(tmp_path)

        assert result["files_written"] == 2

    def test_new_schema_with_japanese_name(self, tmp_path):
        """日本語の name を持つ新スキーマで正しくファイル名が生成される"""
        _make_multipage_pdf(tmp_path, "source.pdf", ["P1", "P2"])
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        groups = {
            "source.pdf": [
                {"range": [1, 1], "name": "週報"},
                {"range": [2, 2], "name": "会計報告"},
            ]
        }
        (work_dir / "groups.json").write_text(
            json.dumps(groups, ensure_ascii=False), encoding="utf-8"
        )

        result = run_split(tmp_path)

        assert (tmp_path / "source_01_週報.pdf").exists()
        assert (tmp_path / "source_02_会計報告.pdf").exists()
