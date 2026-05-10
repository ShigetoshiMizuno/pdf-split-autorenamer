# -*- coding: utf-8 -*-
"""groups.json に従って PDF を分割する"""
from __future__ import annotations

import json
from pathlib import Path

from .pdfio import save_pdf_pages
from .textops import sanitize_filename


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


def run_split(src_dir: Path, work_dir: Path | None = None,
              dry_run: bool = False, force: bool = False) -> dict:
    """work_dir/groups.json に基づいて src_dir のPDFを分割。

    出力: src_dir 直下 `<stem>_NN[_name].pdf`
    既存ファイルは force=False のときスキップ。
    """
    src_dir = Path(src_dir)
    work_dir = Path(work_dir) if work_dir else (src_dir / ".psar")
    groups_path = work_dir / "groups.json"
    if not groups_path.exists():
        raise FileNotFoundError(f"groups.json not found: {groups_path}")

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
            summary["actions"].append(
                {"src": pdf_name, "status": "missing"}
            )
            continue
        import fitz
        with fitz.open(stream=src.read_bytes(), filetype="pdf") as src_doc:
            page_count = src_doc.page_count
        summary["total_input_pages"] += page_count

        for idx, it in enumerate(items, start=1):
            a, b = it["range"]
            if a < 1 or b > page_count or a > b:
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
                    action["status"] = f"error: {e}"
            summary["actions"].append(action)

    return summary
