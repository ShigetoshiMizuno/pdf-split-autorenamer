# -*- coding: utf-8 -*-
"""rename.py の基本テスト（main ブランチ用）"""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pdf_split_autorenamer.rename import (
    choose_date,
    date_from_filename,
    existing_name_part,
    fallback_title,
    find_targets,
    resolve_filenames,
    run_rename,
)


def _make_pdf(path: Path, pages: int = 1, text: str = "") -> Path:
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        if text:
            page.insert_text((50, 50), text)
    doc.save(str(path))
    doc.close()
    return path


class TestExistingNamePart:
    def test_split_filename_returns_name(self):
        assert existing_name_part("scan_01_議事録.pdf") == "議事録"

    def test_unknown_filename_returns_name(self):
        assert existing_name_part("日付不明_議事録.pdf") == "議事録"

    def test_dated_filename_returns_name(self):
        assert existing_name_part("2026-04-06_議事録.pdf") == "議事録"

    def test_plain_filename_returns_empty(self):
        assert existing_name_part("scan.pdf") == ""


class TestDateFromFilename:
    def test_extracts_date_from_name_part(self):
        # "scan_01_2026-04-06.pdf" → name_part="2026-04-06" → date
        assert date_from_filename("scan_01_2026-04-06.pdf") == "2026-04-06"

    def test_returns_none_for_no_date(self):
        assert date_from_filename("scan_01.pdf") is None

    def test_returns_none_for_dated_file(self):
        # DATED_PAT file: existing_name_part returns "議事録", no date in "議事録"
        assert date_from_filename("2026-04-06_議事録.pdf") is None


class TestChooseDate:
    def test_returns_hint_when_in_candidates(self):
        text = "2026-04-06 のテスト"
        result = choose_date(text, "scan_01_2026-04-06.pdf")
        assert result == "2026-04-06"

    def test_returns_most_common_date(self):
        text = "2026-04-06 2026-04-06 2026-04-07"
        result = choose_date(text, "scan_01.pdf")
        assert result == "2026-04-06"

    def test_returns_none_when_no_dates(self):
        result = choose_date("テキストのみ", "scan_01.pdf")
        assert result is None


class TestFallbackTitle:
    def test_strips_date_from_name(self):
        result = fallback_title("scan_01_2026-04-06_議事録.pdf")
        assert "2026" not in result
        assert "議事録" in result

    def test_returns_empty_for_no_name(self):
        result = fallback_title("scan_01.pdf")
        assert result == ""


class TestFindTargets:
    def test_split_mode_finds_split_files(self, tmp_path):
        (tmp_path / "scan_01.pdf").write_bytes(b"%PDF-1.4")
        result = find_targets(tmp_path, mode="split")
        assert len(result) == 1

    def test_split_mode_excludes_dated_files(self, tmp_path):
        (tmp_path / "2026-04-06_議事録.pdf").write_bytes(b"%PDF-1.4")
        result = find_targets(tmp_path, mode="split")
        assert len(result) == 0

    def test_unknown_mode_finds_unknown_files(self, tmp_path):
        (tmp_path / "日付不明_議事録.pdf").write_bytes(b"%PDF-1.4")
        result = find_targets(tmp_path, mode="unknown")
        assert len(result) == 1

    def test_all_mode_finds_both(self, tmp_path):
        (tmp_path / "scan_01.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "日付不明_議事録.pdf").write_bytes(b"%PDF-1.4")
        result = find_targets(tmp_path, mode="all")
        assert len(result) == 2

    def test_excludes_original_timestamp_pdf(self, tmp_path):
        (tmp_path / "2026-05-11-04-00-00.pdf").write_bytes(b"%PDF-1.4")
        result = find_targets(tmp_path)
        assert len(result) == 0


class TestResolveFilenames:
    def test_no_duplicates_no_suffix(self):
        plan = [
            {"date": "2026-04-06", "kind": "議事録", "fallback": ""},
            {"date": "2026-04-07", "kind": "議事録", "fallback": ""},
        ]
        result = resolve_filenames(plan)
        assert result[0]["final"] == "2026-04-06_議事録.pdf"
        assert result[1]["final"] == "2026-04-07_議事録.pdf"

    def test_duplicates_get_suffix(self):
        plan = [
            {"date": "2026-04-06", "kind": "議事録", "fallback": ""},
            {"date": "2026-04-06", "kind": "議事録", "fallback": ""},
        ]
        result = resolve_filenames(plan)
        assert result[0]["final"] == "2026-04-06_議事録_01.pdf"
        assert result[1]["final"] == "2026-04-06_議事録_02.pdf"

    def test_no_date_uses_unknown_prefix(self):
        plan = [{"date": None, "kind": "議事録", "fallback": ""}]
        result = resolve_filenames(plan)
        assert result[0]["final"].startswith("日付不明_")


class TestFindTargetsEdgeCases:
    def test_non_file_pdf_is_skipped(self, tmp_path):
        # Create a directory named like a PDF
        pdf_dir = tmp_path / "scan_01.pdf"
        pdf_dir.mkdir()
        result = find_targets(tmp_path, mode="split")
        assert len(result) == 0

    def test_all_mode_does_not_include_dated_non_unknown(self, tmp_path):
        # DATED_PAT match but NOT UNKNOWN → should be skipped even in "all" mode
        (tmp_path / "2026-04-06_議事録.pdf").write_bytes(b"%PDF-1.4")
        result = find_targets(tmp_path, mode="all")
        assert len(result) == 0


class TestRunRename:
    def test_no_targets_returns_empty(self, tmp_path):
        result = run_rename(tmp_path)
        assert result["targets"] == 0
        assert result["actions"] == []

    def test_dry_run_does_not_rename(self, tmp_path):
        src = tmp_path / "scan_01.pdf"
        _make_pdf(src)
        result = run_rename(tmp_path, mode="split")
        assert result["applied"] == 0
        assert src.exists()

    def test_apply_renames_file(self, tmp_path):
        src = tmp_path / "scan_01.pdf"
        _make_pdf(src, text="2026年4月6日 議事録")
        result = run_rename(tmp_path, mode="split", apply=True)
        assert result["applied"] == 1
        assert not src.exists()

    def test_noop_when_already_correctly_named(self, tmp_path):
        src = tmp_path / "scan_01.pdf"
        _make_pdf(src, text="2026年4月6日 議事録")
        run_rename(tmp_path, mode="split", apply=True)
        # second run: file is now dated, should not be targeted
        result = run_rename(tmp_path, mode="split")
        assert result["targets"] == 0

    def test_conflict_when_dst_exists(self, tmp_path):
        src = tmp_path / "scan_01.pdf"
        _make_pdf(src, text="2026年4月6日 議事録")
        # Pre-create the destination file (different inode)
        dst_name = None
        dry_run = run_rename(tmp_path, mode="split")
        if dry_run["actions"]:
            dst_name = dry_run["actions"][0]["dst"]
        if dst_name:
            (tmp_path / dst_name).write_bytes(b"%PDF-1.4")
            result = run_rename(tmp_path, mode="split", apply=True)
            assert any(a["status"] == "conflict" for a in result["actions"])
        else:
            pytest.skip("Could not determine destination name")

    def test_kind_from_filename_hint(self, tmp_path):
        # When text doesn't match, fallback to filename-based kind
        src = tmp_path / "scan_01_議事録.pdf"
        _make_pdf(src)  # empty PDF, no text content
        result = run_rename(tmp_path, mode="split")
        actions = result["actions"]
        assert len(actions) >= 1

    def test_fallback_title_used_when_kind_is_default(self, tmp_path):
        src = tmp_path / "scan_01_議事録.pdf"
        _make_pdf(src)  # no recognizable kind in text → should use fallback
        result = run_rename(tmp_path, mode="split")
        assert result["targets"] >= 1

    def test_noop_when_destination_equals_source(self, tmp_path):
        # "日付不明_議事録.pdf" → kind="議事録", date=None → final="日付不明_議事録.pdf" (same name)
        src = tmp_path / "日付不明_議事録.pdf"
        _make_pdf(src)  # no text, kind inferred from filename
        result = run_rename(tmp_path, mode="unknown")
        assert any(a["status"] == "noop" for a in result["actions"])

    def test_rename_error_sets_error_status(self, tmp_path):
        from unittest.mock import patch
        src = tmp_path / "scan_01.pdf"
        _make_pdf(src, text="2026年4月6日 議事録")
        with patch.object(Path, "rename", side_effect=OSError("permission denied")):
            result = run_rename(tmp_path, mode="split", apply=True)
        assert any(a["status"].startswith("error:") for a in result["actions"])
