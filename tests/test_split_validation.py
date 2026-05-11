# -*- coding: utf-8 -*-
"""split.py: _validate_groups / run_split / normalize_groups のテスト（Issue #9 / FR-2-7）"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import fitz
import pytest

from pdf_split_autorenamer.split import _validate_groups, normalize_groups, run_split


def _make_pdf(path: Path, pages: int = 3) -> Path:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


class TestNormalizeGroups:
    def test_dict_schema_passthrough(self):
        raw = {"scan.pdf": [{"range": [1, 3], "name": "test"}]}
        result = normalize_groups(raw)
        assert result["scan.pdf"][0]["range"] == [1, 3]

    def test_list_schema_converted(self):
        raw = {"scan.pdf": [[1, 3]]}
        result = normalize_groups(raw)
        assert result["scan.pdf"][0]["range"] == [1, 3]
        assert result["scan.pdf"][0]["name"] == ""

    def test_invalid_item_skipped(self):
        raw = {"scan.pdf": ["invalid_string"]}
        result = normalize_groups(raw)
        assert result["scan.pdf"] == []

    def test_short_list_skipped(self):
        raw = {"scan.pdf": [[1]]}  # only 1 element, not 2
        result = normalize_groups(raw)
        assert result["scan.pdf"] == []

    def test_none_rng_skipped(self):
        raw = {"scan.pdf": [{"name": "no-range"}]}  # no range/pages key
        result = normalize_groups(raw)
        assert result["scan.pdf"] == []

    def test_pages_key_accepted(self):
        raw = {"scan.pdf": [{"pages": [1, 3], "name": ""}]}
        result = normalize_groups(raw)
        assert result["scan.pdf"][0]["range"] == [1, 3]


class TestRunSplitErrors:
    def test_missing_groups_json_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            run_split(tmp_path)

    def test_out_of_range_logged(self, tmp_path):
        src_pdf = tmp_path / "scan.pdf"
        _make_pdf(src_pdf, pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 10], "name": ""}]}),
            encoding="utf-8",
        )
        summary = run_split(tmp_path, work_dir=work_dir, dry_run=True)
        assert summary["actions"][0]["status"] == "out-of-range"

    def test_skip_existing_file(self, tmp_path):
        src_pdf = tmp_path / "scan.pdf"
        _make_pdf(src_pdf, pages=2)
        # Create the output file so it "already exists"
        (tmp_path / "scan_01.pdf").write_bytes(b"%PDF-1.4")
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        summary = run_split(tmp_path, work_dir=work_dir)
        assert summary["actions"][0]["status"] == "skip-exists"
        assert summary["files_skipped"] == 1

    def test_force_overwrites_existing_file(self, tmp_path):
        src_pdf = tmp_path / "scan.pdf"
        _make_pdf(src_pdf, pages=2)
        # Pre-create the output file
        (tmp_path / "scan_01.pdf").write_bytes(b"%PDF-1.4")
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        summary = run_split(tmp_path, work_dir=work_dir, force=True)
        assert summary["actions"][0]["status"] == "ok"
        assert summary["files_written"] == 1
        assert summary["files_skipped"] == 0

    def test_dry_run_no_files_written(self, tmp_path):
        src_pdf = tmp_path / "scan.pdf"
        _make_pdf(src_pdf, pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        summary = run_split(tmp_path, work_dir=work_dir, dry_run=True)
        assert summary["actions"][0]["status"] == "dry-run"
        assert summary["files_written"] == 0

    def test_actual_split_writes_file(self, tmp_path):
        src_pdf = tmp_path / "scan.pdf"
        _make_pdf(src_pdf, pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        summary = run_split(tmp_path, work_dir=work_dir)
        assert summary["files_written"] == 1
        assert (tmp_path / "scan_01.pdf").exists()

    def test_save_pdf_pages_error_sets_error_status(self, tmp_path):
        from unittest.mock import patch
        src_pdf = tmp_path / "scan.pdf"
        _make_pdf(src_pdf, pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": ""}]}),
            encoding="utf-8",
        )
        with patch("pdf_split_autorenamer.split.save_pdf_pages",
                   side_effect=Exception("disk full")):
            summary = run_split(tmp_path, work_dir=work_dir)
        assert any(a["status"].startswith("error:") for a in summary["actions"])

    def test_named_group_includes_name_in_filename(self, tmp_path):
        src_pdf = tmp_path / "scan.pdf"
        _make_pdf(src_pdf, pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text(
            json.dumps({"scan.pdf": [{"range": [1, 2], "name": "議事録"}]}),
            encoding="utf-8",
        )
        summary = run_split(tmp_path, work_dir=work_dir)
        assert summary["files_written"] == 1
        out_name = summary["actions"][0]["out"]
        assert "議事録" in out_name


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
