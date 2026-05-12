# -*- coding: utf-8 -*-
"""groups.json に従って PDF を分割する"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .pdfio import save_pdf_pages
from .textops import sanitize_filename

logger = logging.getLogger(__name__)


def normalize_groups(raw: dict) -> dict[str, list[dict]]:
    """旧スキーマ ([from,to]) と新スキーマ ({range:[from,to], name:""}) を吸収する"""
    out: dict[str, list[dict]] = {}
    for pdf_name, items in raw.items():
        norm: list[dict] = []
        for it in items:
            if isinstance(it, dict):
                rng = it.get("range") or it.get("pages")
                name = it.get("name", "")
            elif isinstance(it, (list, tuple)) and len(it) == 2:
                rng = list(it)
                name = ""
            else:
                continue
            if not rng or len(rng) != 2:
                continue
            norm.append({"range": [int(rng[0]), int(rng[1])], "name": name or ""})
        out[pdf_name] = norm
    return out


def _validate_groups(pdf_name: str, items: list[dict], page_count: int) -> None:
    """ページ重複と未カバーページを警告する（FR-2-7）"""
    covered: set[int] = set()
    for it in items:
        a, b = it["range"]
        if a < 1 or b > page_count or a > b:
            continue
        for p in range(a, b + 1):
            if p in covered:
                logger.warning("[%s] ページ %d が複数グループに重複しています", pdf_name, p)
            covered.add(p)
    uncovered = sorted(set(range(1, page_count + 1)) - covered)
    if uncovered:
        logger.info("[%s] 未カバーページ（出力なし）: %s", pdf_name, uncovered)


def run_split(src_dir: Path, work_dir: Path | None = None,
              dry_run: bool = False, force: bool = False) -> dict:
    """work_dir/groups.json に基づいて src_dir のPDFを分割。

    出力: src_dir 直下 `<stem>_NN[_name].pdf`
    既存ファイルは force=False のときスキップ。

    issue #35: src_dir が PDF ファイル単体を指している場合はその親ディレクトリを
    src_dir として扱う（work_dir は親/.psar）。
    """
    src_path = Path(src_dir)
    if src_path.is_file() and src_path.suffix.lower() == ".pdf":
        src_dir = src_path.parent
    else:
        src_dir = src_path
    work_dir = Path(work_dir) if work_dir else (src_dir / ".psar")
    groups_path = work_dir / "groups.json"
    if not groups_path.exists():
        raise FileNotFoundError(f"groups.json が見つかりません: {groups_path}")

    raw = json.loads(groups_path.read_text(encoding="utf-8"))
    groups = normalize_groups(raw)

    summary: dict = {
        "total_input_pages": 0,
        "total_output_pages": 0,
        "files_written": 0,
        "files_skipped": 0,
        "actions": [],
    }

    for pdf_name, items in groups.items():
        src = src_dir / pdf_name
        if not src.exists():
            logger.warning("[%s] groups.json に記載されたPDFが見つかりません", pdf_name)
            summary["actions"].append(
                {"src": pdf_name, "status": "missing"}
            )
            continue
        import fitz
        with fitz.open(stream=src.read_bytes(), filetype="pdf") as src_doc:
            page_count = src_doc.page_count
        summary["total_input_pages"] += page_count
        _validate_groups(pdf_name, items, page_count)

        for idx, it in enumerate(items, start=1):
            a, b = it["range"]
            if a < 1 or b > page_count or a > b:
                logger.warning(
                    "範囲外グループをスキップします: %s ページ %s-%s", pdf_name, a, b
                )
                summary["actions"].append({
                    "src": pdf_name, "range": [a, b],
                    "status": "out-of-range",
                })
                continue
            name_part = sanitize_filename(it.get("name", ""))
            if name_part:
                out_name = f"{src.stem}_{idx:02d}_{name_part}.pdf"
            else:
                out_name = f"{src.stem}_{idx:02d}.pdf"
            out_path = src_dir / out_name
            action = {
                "src": pdf_name, "range": [a, b],
                "out": out_name, "pages": b - a + 1,
            }
            if out_path.exists() and not force:
                action["status"] = "skip-exists"
                summary["files_skipped"] += 1
            elif dry_run:
                action["status"] = "dry-run"
            else:
                try:
                    save_pdf_pages(src, a, b, out_path)
                    action["status"] = "ok"
                    summary["files_written"] += 1
                    summary["total_output_pages"] += (b - a + 1)
                except Exception as e:
                    logger.error("書き込みに失敗しました %s: %s", out_name, e)
                    action["status"] = f"error: {e}"
            summary["actions"].append(action)

    return summary
