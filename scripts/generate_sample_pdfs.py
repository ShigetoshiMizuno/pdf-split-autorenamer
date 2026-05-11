# -*- coding: utf-8 -*-
"""ベンチマーク用サンプル PDF 生成スクリプト

業務書類に近い構造の PDF を PyMuPDF で生成する。
テキスト層あり / なし（画像のみ）の両パターンを作成。

使い方:
    python scripts/generate_sample_pdfs.py tests/fixtures/benchmark/
"""
from __future__ import annotations

import sys
from pathlib import Path


def make_digital_pdf(output: Path) -> None:
    """テキスト層あり PDF（印字デジタル文書の模倣）。Stage 1 で完結。"""
    import fitz
    doc = fitz.open()

    pages_data = [
        ("2026年4月1日", "請求書", "株式会社山田工業 御中\nNo. 2026-0401-001\nご請求金額: ￥330,000"),
        ("2026年4月8日", "見積書", "鈴木建設株式会社 様\n見積番号: Q-2026-0408\n御見積金額: ￥389,400"),
        ("2026年4月15日", "営業部 定例会議 議事録", "出席者: 佐藤部長、鈴木課長、田中、伊藤"),
    ]

    for date, title, body in pages_data:
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), date, fontsize=14)
        page.insert_text((72, 100), title, fontsize=18)
        page.insert_text((72, 140), body, fontsize=11)

    doc.save(str(output))
    doc.close()
    print(f"生成: {output} ({len(pages_data)} ページ、テキスト層あり)")


def make_image_only_pdf(output: Path) -> None:
    """テキスト層なし PDF（スキャン文書の模倣）。Stage 2/3 が必要。"""
    import fitz
    doc = fitz.open()

    for i in range(2):
        page = doc.new_page(width=595, height=842)
        page.draw_rect(fitz.Rect(50, 50, 545, 792), color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))

    doc.save(str(output))
    doc.close()
    print(f"生成: {output} ({2} ページ、テキスト層なし・灰色矩形のみ)")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="ベンチマーク用サンプル PDF を生成")
    ap.add_argument("output_dir", help="出力先フォルダ")
    args = ap.parse_args(argv)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    make_digital_pdf(out_dir / "sample_digital.pdf")
    make_image_only_pdf(out_dir / "sample_scan_empty.pdf")

    print()
    print(f"サンプル PDF を {out_dir} に生成しました。")
    print(f"ベンチマーク実行: python scripts/run_benchmark.py {out_dir} --stages 1 2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
