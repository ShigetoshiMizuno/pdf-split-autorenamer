# -*- coding: utf-8 -*-
"""T-10: analyze モジュールのユニットテスト

対象関数:
- score_boundary(prev, cur) -> (float, list[str])
- build_initial_groups(pages, boundary_threshold) -> dict[str, list[dict]]

テストは実際の PDF ファイルを使わない pure-Python のユニットテスト。
"""
from __future__ import annotations

import pytest

from pdf_split_autorenamer.analyze import build_initial_groups, score_boundary


# ---------------------------------------------------------------------------
# テスト用ページ dict を生成するヘルパー
# ---------------------------------------------------------------------------

def _make_page(
    pdf: str = "file.pdf",
    page: int = 1,
    orient: str = "portrait",
    width: float = 595.0,
    height: float = 842.0,
    bigram: set[str] | None = None,
    title_markers: list[str] | None = None,
) -> dict:
    """テスト用の最小ページ dict を生成する"""
    return {
        "pdf": pdf,
        "page": page,
        "orient": orient,
        "width": width,
        "height": height,
        "bigram": bigram if bigram is not None else set(),
        "title_markers": title_markers if title_markers is not None else [],
    }


# ---------------------------------------------------------------------------
# score_boundary
# ---------------------------------------------------------------------------

class TestScoreBoundary:
    def test_same_page_low_score(self):
        """同一ページ構成（同じ pdf, orient, bigram, markers なし）はスコアが低い（< 0.5）"""
        shared_bigram = {"ab", "bc", "cd", "de", "ef", "fg"}
        prev = _make_page(bigram=shared_bigram)
        cur = _make_page(page=2, bigram=shared_bigram)
        score, reasons = score_boundary(prev, cur)
        assert score < 0.5

    def test_orient_change_portrait_to_landscape_high_score(self):
        """portrait → landscape の向き変化はスコアが高い（>= 0.7）"""
        prev = _make_page(orient="P", width=595.0, height=842.0)
        cur = _make_page(page=2, orient="L", width=842.0, height=595.0)
        score, reasons = score_boundary(prev, cur)
        assert score >= 0.7

    def test_orient_change_reasons_mention_orient(self):
        """向き変化の reasons に向き関連の文字列が含まれる"""
        prev = _make_page(orient="P", width=595.0, height=842.0)
        cur = _make_page(page=2, orient="L", width=842.0, height=595.0)
        score, reasons = score_boundary(prev, cur)
        assert any("向き" in r for r in reasons), f"reasons に向き関連文字列なし: {reasons}"

    def test_different_pdf_returns_score_1(self):
        """別PDFの場合は score = 1.0 を返す"""
        prev = _make_page(pdf="a.pdf", page=3)
        cur = _make_page(pdf="b.pdf", page=1)
        score, reasons = score_boundary(prev, cur)
        assert score == 1.0

    def test_different_pdf_reasons_mention_pdf(self):
        """別PDFの reasons に PDF関連の文字列が含まれる"""
        prev = _make_page(pdf="a.pdf", page=3)
        cur = _make_page(pdf="b.pdf", page=1)
        score, reasons = score_boundary(prev, cur)
        assert any("PDF" in r or "pdf" in r.lower() for r in reasons), \
            f"reasons に PDF 言及なし: {reasons}"

    def test_different_bigram_raises_score(self):
        """bigram が全く違う（jaccard ≈ 0）とスコアが上がる"""
        prev = _make_page(bigram={"ab", "bc", "cd"})
        cur = _make_page(page=2, bigram={"xy", "yz", "zw"})
        score_diff, _ = score_boundary(prev, cur)

        # 同一bigram と比較して差が出ることを確認
        shared = {"ab", "bc", "cd"}
        prev_same = _make_page(bigram=shared)
        cur_same = _make_page(page=2, bigram=shared)
        score_same, _ = score_boundary(prev_same, cur_same)

        assert score_diff > score_same

    def test_bigram_completely_different_score_at_least_04(self):
        """bigram が全く違う（jaccard=0）と +0.4 以上加算される"""
        prev = _make_page(bigram={"ab", "bc", "cd"}, orient="P")
        cur = _make_page(page=2, bigram={"xy", "yz", "zw"}, orient="P")
        score, _ = score_boundary(prev, cur)
        assert score >= 0.4

    def test_new_title_marker_raises_score(self):
        """title_markers に新しい値が出現するとスコアが上がる"""
        prev = _make_page(title_markers=[], bigram={"ab", "bc"})
        cur = _make_page(page=2, title_markers=["第1号"], bigram={"ab", "bc"})
        score_with_marker, _ = score_boundary(prev, cur)

        prev_no = _make_page(title_markers=[], bigram={"ab", "bc"})
        cur_no = _make_page(page=2, title_markers=[], bigram={"ab", "bc"})
        score_without_marker, _ = score_boundary(prev_no, cur_no)

        assert score_with_marker > score_without_marker

    def test_score_capped_at_1(self):
        """スコアは 1.0 を超えない"""
        # 向き変化 (+0.7) + bigram差 (+0.4) + title_markers (+0.5) = 1.6 → クリップ
        prev = _make_page(
            orient="P", bigram={"ab", "bc"}, title_markers=[]
        )
        cur = _make_page(
            page=2, orient="L", width=842.0, height=595.0,
            bigram={"xy", "yz"}, title_markers=["第1号"]
        )
        score, _ = score_boundary(prev, cur)
        assert score <= 1.0

    def test_returns_tuple_of_float_and_list(self):
        """戻り値は (float, list[str]) のタプルである"""
        prev = _make_page()
        cur = _make_page(page=2)
        result = score_boundary(prev, cur)
        assert isinstance(result, tuple)
        assert len(result) == 2
        score, reasons = result
        assert isinstance(score, float)
        assert isinstance(reasons, list)


# ---------------------------------------------------------------------------
# build_initial_groups
# ---------------------------------------------------------------------------

class TestBuildInitialGroups:
    def test_empty_pages_returns_empty_dict(self):
        """空リストを渡すと空の dict を返す"""
        result = build_initial_groups([])
        assert result == {}

    def test_single_page_returns_one_group(self):
        """1ページだけの場合は {"file.pdf": [{"range": [1, 1], "name": ""}]} を返す"""
        pages = [_make_page(pdf="file.pdf", page=1)]
        result = build_initial_groups(pages)
        assert "file.pdf" in result
        assert len(result["file.pdf"]) == 1
        assert result["file.pdf"][0]["range"] == [1, 1]
        assert result["file.pdf"][0]["name"] == ""

    def test_orient_change_splits_into_two_groups(self):
        """向き変化（portrait → landscape）で 2 グループに分割される"""
        pages = [
            _make_page(pdf="file.pdf", page=1, orient="P", width=595.0, height=842.0),
            _make_page(pdf="file.pdf", page=2, orient="L", width=842.0, height=595.0),
        ]
        result = build_initial_groups(pages, boundary_threshold=0.5)
        assert "file.pdf" in result
        assert len(result["file.pdf"]) == 2
        assert result["file.pdf"][0]["range"] == [1, 1]
        assert result["file.pdf"][1]["range"] == [2, 2]

    def test_threshold_1_no_split(self):
        """閾値 1.0 では一切分割されない（全ページが 1 グループ）"""
        pages = [
            _make_page(pdf="file.pdf", page=1, orient="P", width=595.0, height=842.0),
            _make_page(pdf="file.pdf", page=2, orient="L", width=842.0, height=595.0),
            _make_page(pdf="file.pdf", page=3, orient="P", width=595.0, height=842.0),
        ]
        result = build_initial_groups(pages, boundary_threshold=1.0)
        assert "file.pdf" in result
        assert len(result["file.pdf"]) == 1
        assert result["file.pdf"][0]["range"] == [1, 3]

    def test_multiple_pdfs_split_by_pdf(self):
        """複数 PDF のページは必ず PDF ごとに分かれる"""
        pages = [
            _make_page(pdf="a.pdf", page=1),
            _make_page(pdf="a.pdf", page=2),
            _make_page(pdf="b.pdf", page=1),
            _make_page(pdf="b.pdf", page=2),
        ]
        result = build_initial_groups(pages, boundary_threshold=0.5)
        assert "a.pdf" in result
        assert "b.pdf" in result
        # 各 PDF 内は orient 変化なし・bigram 同じため 1 グループ
        assert len(result["a.pdf"]) == 1
        assert len(result["b.pdf"]) == 1
        assert result["a.pdf"][0]["range"] == [1, 2]
        assert result["b.pdf"][0]["range"] == [1, 2]

    def test_same_orient_and_bigram_no_split(self):
        """同じ向きで bigram も同じ場合は分割されない"""
        shared = {"ab", "bc", "cd", "de"}
        pages = [
            _make_page(pdf="file.pdf", page=1, bigram=shared),
            _make_page(pdf="file.pdf", page=2, bigram=shared),
            _make_page(pdf="file.pdf", page=3, bigram=shared),
        ]
        result = build_initial_groups(pages, boundary_threshold=0.5)
        assert "file.pdf" in result
        assert len(result["file.pdf"]) == 1
        assert result["file.pdf"][0]["range"] == [1, 3]

    def test_group_range_covers_all_pages(self):
        """グループの range が全ページをカバーする"""
        pages = [_make_page(pdf="file.pdf", page=i) for i in range(1, 6)]
        result = build_initial_groups(pages, boundary_threshold=0.5)
        all_pages = set()
        for groups in result.values():
            for g in groups:
                all_pages.update(range(g["range"][0], g["range"][1] + 1))
        assert all_pages == {1, 2, 3, 4, 5}
