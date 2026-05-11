# -*- coding: utf-8 -*-
"""E2E 候補名生成テスト: sample_office_scan.pdf を入力に run_analyze 相当を検証する。

GTK / WeasyPrint 不要。fitz (PyMuPDF) のみ使用。
"""
import json
import re
import shutil
import tempfile
from pathlib import Path

import pytest

# sample_office_scan.pdf の絶対パス（リポジトリルートからの相対パス固定）
_REPO_ROOT = Path(__file__).parent.parent
_SAMPLE_PDF = _REPO_ROOT / "docs" / "demo" / "sample_office_scan.pdf"

# ファイル名パターン: YYYY-MM-DD_カテゴリ[-取引先[-文書番号]]
# または 日付不明_書類（フォールバック）
_NAME_PATTERN = re.compile(
    r"^(?:\d{4}-\d{2}-\d{2}|日付不明)_[\w\-（）()]+$"
)


@pytest.fixture(scope="module")
def analyzed_groups():
    """sample_office_scan.pdf を一時ディレクトリで run_analyze し、groups を返す。"""
    fitz = pytest.importorskip("fitz", reason="PyMuPDF (fitz) が必要です")
    from pdf_split_autorenamer.analyze import run_analyze

    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(_SAMPLE_PDF, tmp)
        run_analyze(tmp)
        groups_path = tmp / ".psar" / "groups.json"
        data = json.loads(groups_path.read_text(encoding="utf-8"))
        # groups.json は {pdf_name: [group, ...]} 形式
        all_groups = []
        for groups in data.values():
            all_groups.extend(groups)
        return all_groups
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.skipif(
    not _SAMPLE_PDF.exists(),
    reason="docs/demo/sample_office_scan.pdf が存在しません",
)
class TestE2ECandidateNames:
    """sample_office_scan.pdf を入力に候補名生成の E2E 検証"""

    def test_groups_are_generated(self, analyzed_groups):
        """グループが 1 件以上生成される"""
        assert len(analyzed_groups) >= 1

    def test_all_names_are_filled(self, analyzed_groups):
        """全グループの name フィールドが空でない"""
        for g in analyzed_groups:
            assert g.get("name", "") != "", f"name が空: {g}"

    def test_all_names_match_format(self, analyzed_groups):
        """全グループの name が YYYY-MM-DD_カテゴリ[-...] 形式に合致する"""
        for g in analyzed_groups:
            name = g.get("name", "")
            assert _NAME_PATTERN.match(name), (
                f"name のフォーマット不正: {name!r}"
            )

    def test_seikyu_sho_appears(self, analyzed_groups):
        """請求書グループが候補名に含まれる（1ページ目: 請求書）"""
        names = [g["name"] for g in analyzed_groups]
        assert any("請求書" in n for n in names), f"請求書グループが見つからない: {names}"

    def test_date_in_seikyu_sho(self, analyzed_groups):
        """請求書グループに発行日 2026-04-01 が含まれる"""
        for g in analyzed_groups:
            if "請求書" in g.get("name", ""):
                assert "2026-04-01" in g["name"], (
                    f"請求書の日付が不正: {g['name']!r}"
                )
                break

    def test_vendor_in_seikyu_sho(self, analyzed_groups):
        """請求書グループに取引先名（山田工業）が含まれる"""
        for g in analyzed_groups:
            if "請求書" in g.get("name", ""):
                assert "山田工業" in g["name"], (
                    f"請求書の取引先が不正: {g['name']!r}"
                )
                break

    def test_docno_in_seikyu_sho(self, analyzed_groups):
        """請求書グループに文書番号（2026-0401-001）が含まれる"""
        for g in analyzed_groups:
            if "請求書" in g.get("name", ""):
                assert "2026-0401-001" in g["name"], (
                    f"請求書の文書番号が不正: {g['name']!r}"
                )
                break

    def test_no_windows_forbidden_chars_in_names(self, analyzed_groups):
        """全候補名に Windows 禁止文字が含まれない"""
        forbidden = set('<>:"/\\|?*')
        for g in analyzed_groups:
            name = g.get("name", "")
            bad = forbidden & set(name)
            assert not bad, f"禁止文字 {bad} が含まれる: {name!r}"

    def test_names_within_max_length(self, analyzed_groups):
        """全候補名が 80 文字以内"""
        for g in analyzed_groups:
            name = g.get("name", "")
            assert len(name) <= 80, f"name が 80 文字超: {name!r} ({len(name)}文字)"
