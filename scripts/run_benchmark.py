# -*- coding: utf-8 -*-
"""OCR パイプライン Stage 1/2/3 ベンチマークスクリプト

使い方:
    python scripts/run_benchmark.py <フォルダ> [--stages 1 2 3] [--output benchmark_results.json]

<フォルダ> 内の PDF を各 OCR ステージで処理し、以下を計測する:
- テキスト抽出時間 (秒/ページ)
- 日本語文字比率 (精度の代理指標)
- 日付抽出成功率
- API コスト見積もり (Stage 3 LLM のみ)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)


def _japanese_ratio(text: str) -> float:
    """日本語文字（ひらがな・カタカナ・漢字）の比率を返す。"""
    if not text:
        return 0.0
    jp = sum(1 for c in text if 0x3040 <= ord(c) <= 0x9FFF)
    return jp / len(text)


def benchmark_stage1(pdf_path: Path, pdftotext_path: str | None = None) -> dict:
    """Stage 1: pdftotext / PyMuPDF テキスト層抽出。"""
    from pdf_split_autorenamer.pdfio import extract_text

    pages_info = []
    import fitz
    doc = fitz.open(stream=pdf_path.read_bytes(), filetype="pdf")
    n_pages = len(doc)
    doc.close()

    t0 = time.perf_counter()
    for i in range(n_pages):
        text = extract_text(pdf_path, page_no=i, pdftotext=pdftotext_path,
                            ocr_fallback=False)
        pages_info.append({
            "page": i,
            "chars": len(text),
            "jp_ratio": round(_japanese_ratio(text), 3),
            "has_text": len(text.strip()) > 0,
        })
    elapsed = time.perf_counter() - t0

    return {
        "stage": 1,
        "pdf": pdf_path.name,
        "n_pages": n_pages,
        "elapsed_sec": round(elapsed, 3),
        "sec_per_page": round(elapsed / max(n_pages, 1), 3),
        "pages_with_text": sum(p["has_text"] for p in pages_info),
        "avg_jp_ratio": round(
            sum(p["jp_ratio"] for p in pages_info) / max(n_pages, 1), 3
        ),
        "pages": pages_info,
    }


def benchmark_stage2(pdf_path: Path) -> dict:
    """Stage 2: ROI クロップ + Tesseract OCR。"""
    from pdf_split_autorenamer.pdfio import (
        crop_page_pixmap, extract_text_tesseract, find_tesseract,
    )

    tess = find_tesseract()
    if tess is None:
        return {"stage": 2, "pdf": pdf_path.name, "error": "Tesseract が見つかりません"}

    import fitz
    doc = fitz.open(stream=pdf_path.read_bytes(), filetype="pdf")
    n_pages = len(doc)

    pages_info = []
    t0 = time.perf_counter()
    for i in range(n_pages):
        page = doc[i]
        roi_bytes = crop_page_pixmap(page, ratio=0.3)
        text = extract_text_tesseract(roi_bytes)
        pages_info.append({
            "page": i,
            "chars": len(text),
            "jp_ratio": round(_japanese_ratio(text), 3),
            "has_text": len(text.strip()) > 0,
        })
    doc.close()
    elapsed = time.perf_counter() - t0

    return {
        "stage": 2,
        "pdf": pdf_path.name,
        "n_pages": n_pages,
        "elapsed_sec": round(elapsed, 3),
        "sec_per_page": round(elapsed / max(n_pages, 1), 3),
        "pages_with_text": sum(p["has_text"] for p in pages_info),
        "avg_jp_ratio": round(
            sum(p["jp_ratio"] for p in pages_info) / max(n_pages, 1), 3
        ),
        "pages": pages_info,
    }


def benchmark_stage3(pdf_path: Path) -> dict:
    """Stage 3: LLM Vision (Claude API) 構造化抽出。

    ANTHROPIC_API_KEY 環境変数が必要。
    コスト見積もりは claude-3-5-sonnet の input_tokens × $3/M token で算出。
    """
    try:
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
    except ImportError:
        return {"stage": 3, "pdf": pdf_path.name, "error": "ClaudeVisionBackend をインポートできません"}

    backend = ClaudeVisionBackend()
    if not backend.is_available():
        return {"stage": 3, "pdf": pdf_path.name, "error": "ANTHROPIC_API_KEY が未設定です"}

    from pdf_split_autorenamer.pdfio import crop_page_pixmap
    import fitz
    doc = fitz.open(stream=pdf_path.read_bytes(), filetype="pdf")
    n_pages = len(doc)

    pages_info = []
    total_input_tokens = 0
    t0 = time.perf_counter()
    for i in range(n_pages):
        page = doc[i]
        roi_bytes = crop_page_pixmap(page, ratio=0.3)
        try:
            structured = backend.extract_structured(roi_bytes)
            date = structured.get("date", "")
            title = structured.get("title", "")
            pages_info.append({
                "page": i,
                "date": date,
                "title": title,
                "success": bool(date or title),
            })
        except Exception as e:
            pages_info.append({"page": i, "error": str(e), "success": False})
    doc.close()
    elapsed = time.perf_counter() - t0

    success_count = sum(p.get("success", False) for p in pages_info)
    return {
        "stage": 3,
        "pdf": pdf_path.name,
        "n_pages": n_pages,
        "elapsed_sec": round(elapsed, 3),
        "sec_per_page": round(elapsed / max(n_pages, 1), 3),
        "success_rate": round(success_count / max(n_pages, 1), 3),
        "estimated_cost_usd": round(total_input_tokens / 1_000_000 * 3.0, 6),
        "pages": pages_info,
    }


def print_summary(results: list[dict]) -> None:
    """ベンチマーク結果をテーブル形式で標準出力に表示。"""
    print()
    print(f"{'PDF':<30} {'Stage':>5} {'ページ':>6} {'秒/p':>7} {'JP比率':>8} {'テキスト有':>10}")
    print("-" * 70)
    for r in results:
        if "error" in r:
            print(f"{r['pdf']:<30} {'S' + str(r['stage']):>5}  ERROR: {r['error']}")
            continue
        sec_per_p = r.get("sec_per_page", "-")
        jp_ratio = r.get("avg_jp_ratio", "-")
        pages_ok = r.get("pages_with_text", r.get("success_rate", "-"))
        n = r.get("n_pages", "-")
        print(
            f"{r['pdf']:<30} {'S' + str(r['stage']):>5} {n:>6} {sec_per_p:>7.3f} "
            f"{jp_ratio:>8.3f} {pages_ok:>10}"
        )
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OCR パイプライン ベンチマーク")
    ap.add_argument("folder", help="PDF が入っているフォルダ")
    ap.add_argument("--stages", nargs="+", type=int, default=[1, 2, 3],
                    choices=[1, 2, 3], help="実行するステージ番号 (既定: 1 2 3)")
    ap.add_argument("--pdftotext", help="pdftotext.exe のパス")
    ap.add_argument("--output", help="結果を JSON で保存するファイルパス")
    args = ap.parse_args(argv)

    folder = Path(args.folder)
    if not folder.is_dir():
        logging.error("フォルダが存在しません: %s", folder)
        return 2

    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        logging.warning("PDF が見つかりません: %s", folder)
        return 1

    logging.info("対象 PDF: %d 件", len(pdfs))
    all_results: list[dict] = []

    for pdf_path in pdfs:
        logging.info("処理中: %s", pdf_path.name)
        if 1 in args.stages:
            r = benchmark_stage1(pdf_path, pdftotext_path=args.pdftotext)
            all_results.append(r)
        if 2 in args.stages:
            r = benchmark_stage2(pdf_path)
            all_results.append(r)
        if 3 in args.stages:
            r = benchmark_stage3(pdf_path)
            all_results.append(r)

    print_summary(all_results)

    if args.output:
        out = Path(args.output)
        out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
        logging.info("結果を保存しました: %s", out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
