# -*- coding: utf-8 -*-
"""T-10: analyze モジュールのユニットテスト

対象関数:
- score_boundary(prev, cur) -> (float, list[str])
- build_initial_groups(pages, boundary_threshold) -> dict[str, list[dict]]
- build_boundary_info(pages) -> list[dict]
- render_html_report(pages, boundary_info, initial_groups) -> str
- HTML_TEMPLATE: saveJson 関数の http/file:// 分岐

テストは実際の PDF ファイルを使わない pure-Python のユニットテスト。
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from pdf_split_autorenamer.analyze import (
    HTML_TEMPLATE,
    build_boundary_info,
    build_initial_groups,
    render_html_report,
    score_boundary,
)


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
    thumb: str = "",
    text_head: str = "",
    kind: str = "書類",
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
        "thumb": thumb,
        "text_head": text_head,
        "kind": kind,
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

    def test_size_change_same_orient_raises_score(self):
        """同じ向きでもサイズが大きく変化（>5%）するとスコアが上がる"""
        # A4 (595x842) vs A5 (420x595) - どちらも縦向き
        prev = _make_page(orient="P", width=595.0, height=842.0)
        cur = _make_page(page=2, orient="P", width=420.0, height=595.0)
        score, reasons = score_boundary(prev, cur)
        assert any("サイズ" in r for r in reasons), f"サイズ変化が reasons に含まれない: {reasons}"
        assert score >= 0.4

    def test_medium_bigram_similarity_adds_02(self):
        """Jaccard 類似度が 0.05〜0.10 の範囲でスコアに +0.2 が加算される"""
        # prev: {s1,s2} ∪ {p0..p17} = 20 要素
        # cur: {s1,s2} ∪ {q0..q17} = 20 要素
        # intersection=2, union=38 → Jaccard=2/38≈0.053（0.05〜0.10の範囲）
        shared = {"s1", "s2"}
        prev_bigrams = shared | {f"p{i}" for i in range(18)}
        cur_bigrams = shared | {f"q{i}" for i in range(18)}
        prev = _make_page(bigram=prev_bigrams, orient="P")
        cur = _make_page(page=2, bigram=cur_bigrams, orient="P")
        score, reasons = score_boundary(prev, cur)
        # Jaccard≈0.053 → 0.05〜0.10の範囲 → +0.2 加算。reasons に類似度低の文字列が含まれる
        assert any("類似低" in r for r in reasons), f"テキスト類似低が reasons にない: {reasons}"
        assert 0.1 <= score <= 0.5

    def test_empty_bigram_one_side_scores_high(self):
        """一方のページの bigram が空（テキストなし）の場合 Jaccard=0 でスコアが上がる"""
        prev = _make_page(bigram=set(), orient="P")
        cur = _make_page(page=2, bigram={"ab", "bc", "cd"}, orient="P")
        score, _ = score_boundary(prev, cur)
        assert score >= 0.4

    # ----- issue #38: 書類タイプ (kind) 変化を強い境界として扱う -----

    def test_kind_change_raises_score_above_threshold(self):
        """issue #38: kind が変わると境界判定（>= 0.5）を確実に超える"""
        prev = _make_page(orient="P", bigram={"ab", "bc"}, kind="請求書")
        cur = _make_page(page=2, orient="P", bigram={"ab", "bc"}, kind="見積書")
        score, reasons = score_boundary(prev, cur)
        assert score >= 0.5, f"kind 変化で境界閾値を超えない: score={score}"

    def test_kind_change_reasons_mention_kind(self):
        """issue #38: kind 変化が reasons に含まれる"""
        prev = _make_page(kind="請求書", bigram={"a"})
        cur = _make_page(page=2, kind="議事録", bigram={"a"})
        score, reasons = score_boundary(prev, cur)
        assert any("書類タイプ" in r or "kind" in r.lower() for r in reasons), (
            f"reasons に書類タイプ変化が含まれない: {reasons}"
        )

    def test_same_kind_no_extra_score(self):
        """issue #38: kind が同じなら kind 由来の加点はゼロ"""
        shared = {"ab", "bc", "cd", "de", "ef", "fg", "gh", "hi"}
        prev = _make_page(bigram=shared, kind="請求書")
        cur = _make_page(page=2, bigram=shared, kind="請求書")
        score, reasons = score_boundary(prev, cur)
        # bigram 完全一致 + kind 同じ → スコアは低い
        assert score < 0.5

    def test_kind_default_書類_treated_as_no_change(self):
        """issue #38: kind が両方 '書類' (デフォルト) なら kind 由来の加点なし。

        フォールバック分類は「タイプ不明」を意味するため、境界手がかりにしない。
        """
        shared = {"ab", "bc"}
        prev = _make_page(bigram=shared, kind="書類")
        cur = _make_page(page=2, bigram=shared, kind="書類")
        score, _ = score_boundary(prev, cur)
        assert score < 0.5


class TestBigramInternal:
    def test_short_text_returns_empty_set(self):
        """1文字以下のテキストは空の bigram を返す（_bigram の内部動作確認）"""
        from pdf_split_autorenamer.analyze import _bigram
        assert _bigram("a") == set()
        assert _bigram("") == set()
        assert _bigram("  ") == set()  # 空白のみも空

    def test_two_chars_returns_one_bigram(self):
        """2文字テキストは 1 個の bigram を返す"""
        from pdf_split_autorenamer.analyze import _bigram
        assert _bigram("ab") == {"ab"}

    def test_whitespace_stripped_before_bigram(self):
        """空白を除去してから bigram を生成する"""
        from pdf_split_autorenamer.analyze import _bigram
        assert _bigram("a b") == {"ab"}  # 'ab' の空白除去後


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


# ---------------------------------------------------------------------------
# HTML_TEMPLATE の saveJson 関数: http/file:// 分岐
# ---------------------------------------------------------------------------

class TestHtmlTemplateSaveJson:
    def test_fetch_api_call_present(self):
        """HTML_TEMPLATE に fetch('/api/save-groups') の呼び出しが含まれる"""
        assert "fetch('/api/save-groups'" in HTML_TEMPLATE or \
               'fetch("/api/save-groups"' in HTML_TEMPLATE, \
            "fetch('/api/save-groups') が HTML_TEMPLATE に含まれていない"

    def test_http_protocol_check_present(self):
        """HTML_TEMPLATE に window.location.protocol === 'http:' の分岐が含まれる"""
        assert "window.location.protocol" in HTML_TEMPLATE, \
            "window.location.protocol の分岐が HTML_TEMPLATE にない"

    def test_download_fallback_present(self):
        """HTML_TEMPLATE にファイルダウンロードのフォールバックが含まれる"""
        assert "a.download" in HTML_TEMPLATE, \
            "a.download のフォールバック処理が HTML_TEMPLATE にない"

    def test_post_method_in_fetch(self):
        """fetch 呼び出しで method: 'POST' が指定されている"""
        assert "method: 'POST'" in HTML_TEMPLATE or \
               'method: "POST"' in HTML_TEMPLATE, \
            "fetch の method: 'POST' が HTML_TEMPLATE にない"

    def test_content_type_json_in_fetch(self):
        """fetch 呼び出しで Content-Type: application/json が指定されている"""
        assert "application/json" in HTML_TEMPLATE, \
            "Content-Type: application/json が HTML_TEMPLATE にない"

    def test_no_success_alert_in_http_save(self):
        """issue #39: http モード保存成功時の確認アラートを廃止する"""
        # 旧仕様の文字列は HTML_TEMPLATE に含まれてはならない
        assert "groups.json を保存しました" not in HTML_TEMPLATE, (
            "http モード保存成功時の確認アラートが残っている (issue #39)"
        )

    def test_failure_alert_remains(self):
        """issue #39: 失敗時のアラートは残す"""
        assert "保存失敗" in HTML_TEMPLATE, (
            "保存失敗時のアラートが消えている (失敗通知は必要)"
        )

    def test_http_save_closes_window_or_silent(self):
        """issue #39: http 保存成功時は window.close() を試みるか、何もしない（無音）。

        「ダイアログを出して案内」を止めるため、成功分岐に成功通知用 alert（'を保存しました'等）が
        含まれないことを確認する。失敗側の alert は対象外。
        """
        # 保存成功通知用のフレーズが含まれないこと
        forbidden_phrases = [
            "保存しました",
            "保存完了",
            "save complete",
        ]
        for phrase in forbidden_phrases:
            assert phrase not in HTML_TEMPLATE, (
                f"保存成功通知の文言 '{phrase}' が残っている (issue #39)"
            )


# ---------------------------------------------------------------------------
# build_boundary_info
# ---------------------------------------------------------------------------

class TestBuildBoundaryInfo:
    def test_empty_pages_returns_empty(self):
        """ページリストが空の場合は空リストを返す"""
        assert build_boundary_info([]) == []

    def test_single_page_returns_empty(self):
        """1ページだけなら境界情報なし"""
        assert build_boundary_info([_make_page()]) == []

    def test_two_pages_returns_one_boundary(self):
        """2ページなら境界情報が1件"""
        pages = [_make_page(page=1), _make_page(page=2)]
        result = build_boundary_info(pages)
        assert len(result) == 1

    def test_boundary_info_keys(self):
        """境界情報の dict は score / reasons / cross_pdf を持つ"""
        pages = [_make_page(page=1), _make_page(page=2)]
        result = build_boundary_info(pages)
        assert "score" in result[0]
        assert "reasons" in result[0]
        assert "cross_pdf" in result[0]

    def test_cross_pdf_false_for_same_pdf(self):
        """同じ PDF 内の境界は cross_pdf=False"""
        pages = [
            _make_page(pdf="a.pdf", page=1),
            _make_page(pdf="a.pdf", page=2),
        ]
        result = build_boundary_info(pages)
        assert result[0]["cross_pdf"] is False

    def test_cross_pdf_true_for_different_pdf(self):
        """別 PDF をまたぐ境界は cross_pdf=True"""
        pages = [
            _make_page(pdf="a.pdf", page=3),
            _make_page(pdf="b.pdf", page=1),
        ]
        result = build_boundary_info(pages)
        assert result[0]["cross_pdf"] is True

    def test_score_rounded_to_2_decimals(self):
        """score は小数点以下 2 桁に丸められている"""
        pages = [_make_page(page=1), _make_page(page=2)]
        result = build_boundary_info(pages)
        score = result[0]["score"]
        assert score == round(score, 2)

    def test_n_pages_returns_n_minus_1_boundaries(self):
        """n ページなら n-1 件の境界情報"""
        pages = [_make_page(page=i) for i in range(1, 6)]
        result = build_boundary_info(pages)
        assert len(result) == 4


# ---------------------------------------------------------------------------
# render_html_report
# ---------------------------------------------------------------------------

class TestRenderHtmlReport:
    def _make_minimal_pages(self, n: int = 1) -> list[dict]:
        return [_make_page(pdf="a.pdf", page=i, text_head=f"ページ{i}") for i in range(1, n + 1)]

    def test_returns_string(self):
        """render_html_report は文字列を返す"""
        pages = self._make_minimal_pages(1)
        boundaries = build_boundary_info(pages)
        groups = build_initial_groups(pages)
        result = render_html_report(pages, boundaries, groups)
        assert isinstance(result, str)

    def test_html_doctype_present(self):
        """生成 HTML は doctype を含む"""
        pages = self._make_minimal_pages(1)
        result = render_html_report(pages, build_boundary_info(pages), build_initial_groups(pages))
        assert "<!doctype html>" in result.lower()

    def test_title_substituted(self):
        """タイトルが HTML に埋め込まれる"""
        pages = self._make_minimal_pages(1)
        result = render_html_report(
            pages, build_boundary_info(pages), build_initial_groups(pages),
            title="テストレポート"
        )
        assert "テストレポート" in result

    def test_payload_base64_embedded(self):
        """ページデータが base64 として HTML に埋め込まれ、デコードできる"""
        pages = self._make_minimal_pages(2)
        boundaries = build_boundary_info(pages)
        groups = build_initial_groups(pages)
        html = render_html_report(pages, boundaries, groups)
        # __PAYLOAD__ が置換されていること
        assert "__PAYLOAD__" not in html
        # base64 部分を取り出してデコードできることを確認
        import re
        m = re.search(r'atob\("([A-Za-z0-9+/=]+)"\)', html)
        if m:
            decoded = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
            assert "pages" in decoded
            assert len(decoded["pages"]) == 2

    def test_default_title_applied(self):
        """デフォルトタイトルは 'PDF 分割レビュー'"""
        pages = self._make_minimal_pages(1)
        result = render_html_report(
            pages, build_boundary_info(pages), build_initial_groups(pages)
        )
        assert "PDF 分割レビュー" in result


# ---------------------------------------------------------------------------
# run_analyze（統合テスト）
# ---------------------------------------------------------------------------

class TestRunAnalyze:
    def _make_pdf(self, path, text: str = "2026年4月6日の議事録") -> None:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), text)
        data = doc.write()
        doc.close()
        path.write_bytes(data)

    def test_returns_zero_pages_for_empty_dir(self, tmp_path):
        """PDF がないディレクトリでは pages=0 を返す"""
        from pdf_split_autorenamer.analyze import run_analyze
        from unittest.mock import patch
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = run_analyze(tmp_path, ocr_fallback=False)
        assert result == {"pages": 0, "groups": 0}

    def test_returns_dict_with_expected_keys(self, tmp_path):
        """PDF がある場合は pages, groups, report_html, groups_json を含む dict を返す"""
        from pdf_split_autorenamer.analyze import run_analyze
        from unittest.mock import patch
        self._make_pdf(tmp_path / "a.pdf", "2026-04-06 weekly report")
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = run_analyze(tmp_path, ocr_fallback=False)
        for key in ("pages", "groups", "report_html", "groups_json"):
            assert key in result, f"キー '{key}' が結果にない: {result}"

    def test_creates_report_html(self, tmp_path):
        """run_analyze が report.html を生成する"""
        from pdf_split_autorenamer.analyze import run_analyze
        from unittest.mock import patch
        self._make_pdf(tmp_path / "a.pdf")
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = run_analyze(tmp_path, ocr_fallback=False)
        report = result.get("report_html", "")
        if report:
            assert Path(report).exists(), "report.html が生成されていない"

    def test_creates_groups_json(self, tmp_path):
        """run_analyze が groups.json を生成する"""
        from pdf_split_autorenamer.analyze import run_analyze
        from unittest.mock import patch
        self._make_pdf(tmp_path / "a.pdf")
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = run_analyze(tmp_path, ocr_fallback=False)
        groups_json = result.get("groups_json", "")
        if groups_json:
            assert Path(groups_json).exists(), "groups.json が生成されていない"

    def test_second_run_creates_groups_initial_json(self, tmp_path):
        """2回目の run_analyze は groups.json を上書きせず groups.initial.json に保存"""
        from pdf_split_autorenamer.analyze import run_analyze
        from unittest.mock import patch
        self._make_pdf(tmp_path / "a.pdf")
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            run_analyze(tmp_path, ocr_fallback=False)
            run_analyze(tmp_path, ocr_fallback=False)
        work_dir = tmp_path / ".psar"
        groups_json = work_dir / "groups.json"
        initial_json = work_dir / "groups.initial.json"
        assert groups_json.exists()
        assert initial_json.exists(), "groups.initial.json が生成されていない"

    def test_excludes_split_pdfs_from_analysis(self, tmp_path):
        """既に分割済みのファイル（stem_NN.pdf 形式）は解析対象外になる"""
        from pdf_split_autorenamer.analyze import run_analyze
        from unittest.mock import patch
        # 通常のPDF
        self._make_pdf(tmp_path / "scan.pdf")
        # 分割済みのPDF（解析対象外のはず）
        self._make_pdf(tmp_path / "scan_01.pdf", "split document")
        with patch("pdf_split_autorenamer.pdfio.find_pdftotext", return_value=None):
            result = run_analyze(tmp_path, ocr_fallback=False)
        # scan.pdf のみが対象 → pages は scan.pdf の1ページのみのはず
        assert result.get("pages", 0) <= 1, "分割済み PDF が解析対象に含まれている"
