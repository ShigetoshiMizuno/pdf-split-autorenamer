# -*- coding: utf-8 -*-
"""analyze → split → rename のフルワークフロー統合テスト"""
from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from pdf_split_autorenamer.analyze import run_analyze
from pdf_split_autorenamer.rename import run_rename
from pdf_split_autorenamer.split import run_split


def _make_pdf(path: Path, pages: int = 3, text: str = "") -> Path:
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        if text:
            page.insert_text((50, 50), text)
    doc.save(str(path))
    doc.close()
    return path


class TestFullWorkflow:
    def test_analyze_creates_groups_json(self, tmp_path):
        src = _make_pdf(tmp_path / "scan.pdf", pages=3, text="議事録")
        work_dir = tmp_path / ".psar"
        result = run_analyze(tmp_path, work_dir=work_dir)
        assert result["pages"] == 3
        assert (work_dir / "groups.json").exists()
        assert (work_dir / "report.html").exists()

    def test_analyze_then_split(self, tmp_path):
        src = _make_pdf(tmp_path / "scan.pdf", pages=4, text="議事録")
        work_dir = tmp_path / ".psar"
        run_analyze(tmp_path, work_dir=work_dir)
        # Manually set simple groups
        groups_json = work_dir / "groups.json"
        groups_json.write_text(
            json.dumps({
                "scan.pdf": [
                    {"range": [1, 2], "name": "第1文書"},
                    {"range": [3, 4], "name": "第2文書"},
                ]
            }),
            encoding="utf-8",
        )
        summary = run_split(tmp_path, work_dir=work_dir)
        assert summary["files_written"] == 2
        # issue #52: 候補名がある分割は name のみで書き出す
        assert (tmp_path / "第1文書.pdf").exists()
        assert (tmp_path / "第2文書.pdf").exists()

    def test_split_then_rename(self, tmp_path):
        # Note: fitz insert_text may not produce extractable CJK text.
        # Test verifies the rename applies without asserting on the exact filename.
        src = _make_pdf(tmp_path / "scan.pdf", pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        split_result = run_split(tmp_path, work_dir=work_dir)
        assert split_result["files_written"] == 1
        assert (tmp_path / "scan_01.pdf").exists()

        rename_result = run_rename(tmp_path, mode="split", apply=True)
        assert rename_result["applied"] == 1
        assert not (tmp_path / "scan_01.pdf").exists()
        # File was renamed to some pattern; verify at least one PDF exists
        assert len(list(tmp_path.glob("*.pdf"))) >= 1

    def test_full_pipeline(self, tmp_path):
        # Full: create PDF → analyze → edit groups → split → rename
        src = _make_pdf(tmp_path / "scan.pdf", pages=2, text="2026年4月6日 議事録")
        work_dir = tmp_path / ".psar"
        run_analyze(tmp_path, work_dir=work_dir)

        # Overwrite groups to split into 1 group (pages 1-2)
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        split_result = run_split(tmp_path, work_dir=work_dir)
        assert split_result["files_written"] == 1

        rename_result = run_rename(tmp_path, mode="split", apply=True)
        assert rename_result["applied"] == 1
        # Original scan_01.pdf should be renamed
        assert not (tmp_path / "scan_01.pdf").exists()

    def test_idempotent_rename(self, tmp_path):
        # Running rename twice should not change anything on second run
        src = _make_pdf(tmp_path / "scan_01.pdf", text="2026年4月6日 議事録")
        first = run_rename(tmp_path, mode="split", apply=True)
        assert first["applied"] == 1
        # Second run: file is now dated, should find no targets
        second = run_rename(tmp_path, mode="split", apply=True)
        assert second["targets"] == 0
