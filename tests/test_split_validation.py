# -*- coding: utf-8 -*-
"""split.py: _validate_groups / run_split 検証ロジックのテスト（Issue #9 / FR-2-7）"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import fitz
import pytest

from pdf_split_autorenamer.split import _validate_groups, run_split


def _make_pdf(path: Path, pages: int = 3) -> Path:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


class TestValidateGroupsDuplicate:
    def test_duplicate_page_emits_warning(self, caplog):
        items = [
            {"range": [1, 2], "name": ""},
            {"range": [2, 3], "name": ""},  # page 2 duplicated
        ]
        with caplog.at_level(logging.WARNING, logger="pdf_split_autorenamer.split"):
            _validate_groups("scan.pdf", items, page_count=3)
        assert any("ページ 2" in r.message for r in caplog.records)

    def test_no_duplicate_no_warning(self, caplog):
        items = [
            {"range": [1, 2], "name": ""},
            {"range": [3, 3], "name": ""},
        ]
        with caplog.at_level(logging.WARNING, logger="pdf_split_autorenamer.split"):
            _validate_groups("scan.pdf", items, page_count=3)
        assert not any(r.levelno == logging.WARNING for r in caplog.records)


class TestValidateGroupsUncovered:
    def test_uncovered_pages_emit_info(self, caplog):
        items = [{"range": [1, 2], "name": ""}]  # page 3 uncovered
        with caplog.at_level(logging.INFO, logger="pdf_split_autorenamer.split"):
            _validate_groups("scan.pdf", items, page_count=3)
        assert any("未カバーページ" in r.message and "3" in r.message for r in caplog.records)

    def test_all_covered_no_info(self, caplog):
        items = [{"range": [1, 3], "name": ""}]
        with caplog.at_level(logging.INFO, logger="pdf_split_autorenamer.split"):
            _validate_groups("scan.pdf", items, page_count=3)
        assert not any("未カバーページ" in r.message for r in caplog.records)

    def test_out_of_range_items_excluded_from_coverage(self, caplog):
        items = [{"range": [0, 5], "name": ""}]  # out-of-range, skipped
        with caplog.at_level(logging.INFO, logger="pdf_split_autorenamer.split"):
            _validate_groups("scan.pdf", items, page_count=3)
        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("未カバーページ" in m for m in info_msgs)


class TestRunSplitMissingPdf:
    def test_missing_pdf_emits_warning(self, tmp_path, caplog):
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        groups_json = work_dir / "groups.json"
        groups_json.write_text(
            json.dumps({"nonexistent.pdf": [{"range": [1, 1], "name": ""}]}),
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="pdf_split_autorenamer.split"):
            summary = run_split(tmp_path, work_dir=work_dir, dry_run=True)
        assert summary["actions"][0]["status"] == "missing"
        assert any("nonexistent.pdf" in r.message for r in caplog.records)

    def test_run_split_with_real_pdf_calls_validate(self, tmp_path, caplog):
        src_pdf = tmp_path / "scan.pdf"
        _make_pdf(src_pdf, pages=4)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        groups_json = work_dir / "groups.json"
        groups_json.write_text(
            json.dumps({
                "scan.pdf": [
                    {"range": [1, 2], "name": ""},
                    {"range": [2, 3], "name": ""},  # page 2 duplicated, page 4 uncovered
                ]
            }),
            encoding="utf-8",
        )
        with caplog.at_level(logging.INFO, logger="pdf_split_autorenamer.split"):
            run_split(tmp_path, work_dir=work_dir, dry_run=True)
        messages = [r.message for r in caplog.records]
        assert any("ページ 2" in m for m in messages)
        assert any("未カバーページ" in m and "4" in m for m in messages)
