# -*- coding: utf-8 -*-
"""analyze.py の基本テスト（main ブランチ用）"""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pdf_split_autorenamer.analyze import (
    _bigram,
    _jaccard,
    _orient,
    build_boundary_info,
    build_initial_groups,
    collect_pages,
    render_html_report,
    run_analyze,
    score_boundary,
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


class TestOrient:
    def test_portrait_when_height_greater(self):
        assert _orient(100, 200) == "P"

    def test_landscape_when_width_greater(self):
        assert _orient(200, 100) == "L"

    def test_square_is_portrait(self):
        assert _orient(100, 100) == "P"


class TestBigram:
    def test_simple_bigram(self):
        result = _bigram("abc")
        assert "ab" in result
        assert "bc" in result

    def test_empty_returns_empty(self):
        assert _bigram("") == set()

    def test_single_char_returns_empty(self):
        assert _bigram("a") == set()

    def test_strips_whitespace(self):
        result = _bigram("a b")
        assert "ab" in result


class TestJaccard:
    def test_identical_sets(self):
        s = {"ab", "bc"}
        assert _jaccard(s, s) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard({"ab"}, {"cd"}) == 0.0

    def test_both_empty(self):
        assert _jaccard(set(), set()) == 1.0

    def test_one_empty(self):
        assert _jaccard(set(), {"ab"}) == 0.0

    def test_partial_overlap(self):
        a = {"ab", "bc"}
        b = {"bc", "cd"}
        result = _jaccard(a, b)
        assert 0 < result < 1


class TestScoreBoundary:
    def _make_page(self, pdf="scan.pdf", orient="P", w=595, h=842,
                   text="", markers=None, phash=0):
        return {
            "pdf": pdf,
            "orient": orient,
            "width": w,
            "height": h,
            "bigram": {text[i:i+2] for i in range(len(text)-1)} if len(text) >= 2 else set(),
            "title_markers": markers or [],
            "phash": phash,
            "text_head": text,
        }

    def test_different_pdf_returns_1(self):
        p1 = self._make_page(pdf="a.pdf")
        p2 = self._make_page(pdf="b.pdf")
        score, reasons = score_boundary(p1, p2)
        assert score == 1.0
        assert "別PDF" in reasons

    def test_same_pdf_similar_pages_low_score(self):
        text = "これはテスト文書です議事録二〇二六年"
        p1 = self._make_page(text=text)
        p2 = self._make_page(text=text)
        score, _ = score_boundary(p1, p2)
        assert score < 0.5

    def test_orientation_change_raises_score(self):
        p1 = self._make_page(orient="P")
        p2 = self._make_page(orient="L", w=842, h=595)
        score, reasons = score_boundary(p1, p2)
        assert score >= 0.5
        assert any("向き" in r for r in reasons)

    def test_size_change_same_orient_raises_score(self):
        # Same orient but >5% size difference → サイズ変化 branch (lines 104-105)
        p1 = self._make_page(orient="P", w=595, h=842)
        p2 = self._make_page(orient="P", w=595, h=1000)
        score, reasons = score_boundary(p1, p2)
        assert any("サイズ" in r for r in reasons)

    def test_new_title_raises_score(self):
        p1 = self._make_page(markers=[])
        p2 = self._make_page(markers=["第1号"])
        score, reasons = score_boundary(p1, p2)
        assert score > 0
        assert any("タイトル" in r for r in reasons)

    def test_default_similar_reason_when_no_other_signal(self):
        # j=1.0 (identical text), same orient/size, no new titles → default "類似" reason
        text = "議事録 二〇二六年四月六日"
        p1 = self._make_page(text=text)
        p2 = self._make_page(text=text)
        score, reasons = score_boundary(p1, p2)
        assert any("類似" in r for r in reasons)
        assert score == 0.0

    def test_score_capped_at_1(self):
        # Multiple signals → score would exceed 1 without min() cap
        p1 = self._make_page(orient="P", text="abc", markers=[])
        p2 = self._make_page(orient="L", w=842, h=595, text="", markers=["第1号"])
        score, _ = score_boundary(p1, p2)
        assert score <= 1.0

    def test_very_low_jaccard_similarity(self):
        # j = 0.0 (one side empty) → "テキスト類似極低" branch (lines 108-109)
        p1 = self._make_page(text="abcdefg")  # non-empty bigrams
        p2 = self._make_page(text="")         # empty bigrams → _jaccard returns 0.0
        score, reasons = score_boundary(p1, p2)
        assert any("極低" in r for r in reasons)

    def test_low_jaccard_similarity_branch(self):
        # |A ∩ B| = 1, |A ∪ B| = 14 → j = 1/14 ≈ 0.071 → "テキスト類似低" (lines 110-112)
        shared = "xx"
        bigram_a = {f"a{i}" for i in range(7)} | {shared}   # 8 elements
        bigram_b = {f"b{i}" for i in range(6)} | {shared}   # 7 elements
        assert _jaccard(bigram_a, bigram_b) == pytest.approx(1/14, rel=1e-6)
        p1 = {"pdf": "scan.pdf", "orient": "P", "width": 595, "height": 842,
              "bigram": bigram_a, "title_markers": [], "phash": 0}
        p2 = {"pdf": "scan.pdf", "orient": "P", "width": 595, "height": 842,
              "bigram": bigram_b, "title_markers": [], "phash": 0}
        score, reasons = score_boundary(p1, p2)
        assert any("類似低" in r for r in reasons)


class TestBuildInitialGroups:
    def test_empty_pages_returns_empty(self):
        result = build_initial_groups([])
        assert result == {}

    def test_single_page_single_group(self):
        pages = [{"pdf": "a.pdf", "page": 1, "orient": "P",
                  "width": 595, "height": 842, "bigram": set(),
                  "title_markers": [], "phash": 0, "text_head": ""}]
        result = build_initial_groups(pages)
        assert "a.pdf" in result
        assert result["a.pdf"][0]["range"] == [1, 1]

    def test_two_pdfs_separate_groups(self):
        page = {"orient": "P", "width": 595, "height": 842,
                "bigram": set(), "title_markers": [], "phash": 0, "text_head": ""}
        pages = [
            {**page, "pdf": "a.pdf", "page": 1},
            {**page, "pdf": "b.pdf", "page": 1},
        ]
        result = build_initial_groups(pages)
        assert "a.pdf" in result
        assert "b.pdf" in result

    def test_boundary_splits_same_pdf_into_multiple_groups(self):
        # Two pages in same PDF with orientation change → boundary detected (lines 143-146)
        pages = [
            {"pdf": "a.pdf", "page": 1, "orient": "P", "width": 595, "height": 842,
             "bigram": set(), "title_markers": [], "phash": 0, "text_head": ""},
            {"pdf": "a.pdf", "page": 2, "orient": "L", "width": 842, "height": 595,
             "bigram": set(), "title_markers": [], "phash": 0xFFFF, "text_head": ""},
        ]
        result = build_initial_groups(pages, boundary_threshold=0.5)
        assert len(result["a.pdf"]) == 2


class TestBuildBoundaryInfo:
    def test_single_page_no_boundaries(self):
        pages = [{"pdf": "a.pdf", "page": 1, "orient": "P",
                  "width": 595, "height": 842, "bigram": set(),
                  "title_markers": [], "phash": 0}]
        result = build_boundary_info(pages)
        assert result == []

    def test_two_pages_one_boundary(self):
        page = {"pdf": "a.pdf", "orient": "P", "width": 595, "height": 842,
                "bigram": set(), "title_markers": [], "phash": 0}
        pages = [{**page, "page": 1}, {**page, "page": 2}]
        result = build_boundary_info(pages)
        assert len(result) == 1
        assert "score" in result[0]


class TestRenderHtmlReport:
    def test_returns_html_string(self):
        result = render_html_report([], [], {})
        assert "<html" in result

    def test_title_in_html(self):
        result = render_html_report([], [], {}, title="テストタイトル")
        assert "テストタイトル" in result

    def test_contains_payload(self):
        result = render_html_report([], [], {})
        assert "__PAYLOAD__" not in result  # placeholder should be replaced


class TestRunAnalyze:
    def test_empty_folder_returns_zero_pages(self, tmp_path):
        result = run_analyze(tmp_path)
        assert result["pages"] == 0
        assert result["groups"] == 0

    def test_with_pdf_creates_output_files(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=2)
        work_dir = tmp_path / ".psar"
        result = run_analyze(tmp_path, work_dir=work_dir)
        assert result["pages"] == 2
        assert (work_dir / "groups.json").exists()
        assert (work_dir / "report.html").exists()

    def test_existing_groups_json_creates_backup(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=2)
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "groups.json").write_text("{}", encoding="utf-8")
        run_analyze(tmp_path, work_dir=work_dir)
        assert (work_dir / "groups.initial.json").exists()

    def test_split_files_excluded_by_filter(self, tmp_path):
        # scan_01.pdf matches split_re → excluded (line 453 in run_analyze)
        _make_pdf(tmp_path / "scan.pdf", pages=1)
        _make_pdf(tmp_path / "scan_01.pdf", pages=1)
        work_dir = tmp_path / ".psar"
        result = run_analyze(tmp_path, work_dir=work_dir)
        assert result["pages"] == 1  # only scan.pdf processed


class TestCollectPages:
    def test_empty_folder_returns_empty(self, tmp_path):
        thumb_dir = tmp_path / "thumbs"
        result = collect_pages(tmp_path, thumb_dir)
        assert result == []

    def test_pdf_yields_pages(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=2)
        thumb_dir = tmp_path / "thumbs"
        result = collect_pages(tmp_path, thumb_dir)
        assert len(result) == 2
        assert result[0]["pdf"] == "scan.pdf"
        assert result[0]["page"] == 1

    def test_creates_thumbnails(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=1)
        thumb_dir = tmp_path / "thumbs"
        collect_pages(tmp_path, thumb_dir)
        assert any(thumb_dir.glob("*.jpg"))

    def test_pdf_filter_applied(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=2)
        _make_pdf(tmp_path / "scan_01.pdf", pages=1)
        thumb_dir = tmp_path / "thumbs"
        result = collect_pages(tmp_path, thumb_dir, pdf_filter=lambda p: "01" not in p.name)
        pdfs_collected = {r["pdf"] for r in result}
        assert "scan_01.pdf" not in pdfs_collected

    def test_corrupted_pdf_skipped(self, tmp_path):
        # corrupt file → fitz.open fails → printed and skipped (lines 58-60)
        (tmp_path / "bad.pdf").write_bytes(b"not a pdf at all")
        thumb_dir = tmp_path / "thumbs"
        result = collect_pages(tmp_path, thumb_dir)
        assert result == []

    def test_thumbnail_reused_when_exists(self, tmp_path):
        _make_pdf(tmp_path / "scan.pdf", pages=1)
        thumb_dir = tmp_path / "thumbs"
        collect_pages(tmp_path, thumb_dir)
        # Second call should reuse existing thumbnail (no re-render)
        collect_pages(tmp_path, thumb_dir)
        assert len(list(thumb_dir.glob("*.jpg"))) == 1
