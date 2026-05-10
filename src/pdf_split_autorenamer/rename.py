# -*- coding: utf-8 -*-
"""PDFの内容（OCR埋め込みテキスト）から日付・書類タイプを推定して自動リネームする"""
from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

from . import textops
from .pdfio import extract_text, find_pdftotext

# ファイル名パターン
ORIG_PAT = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.pdf$")
SPLIT_PAT = re.compile(r"^.+_(\d{2,3})(?:_.+)?\.pdf$")
UNKNOWN_PAT = re.compile(r"^日付不明_.+\.pdf$")
DATED_PAT = re.compile(r"^\d{4}-\d{2}-\d{2}_.+\.pdf$")


def existing_name_part(filename: str) -> str:
    """ファイル名から「名前部分」を取り出す。複数の形式に対応＋化け修復。"""
    fixed = textops.fix_broken_unicode(filename)
    # 1) 分割直後 (タイムスタンプ的 prefix を含むもの) <stem>_NN_<name>.pdf
    m = re.match(r"^.+?_\d{2,3}_(.+)\.pdf$", fixed)
    if m and not DATED_PAT.match(fixed) and not UNKNOWN_PAT.match(fixed):
        return m.group(1)
    # 2) 日付不明_<name>(_NN).pdf
    m = re.match(r"^日付不明_(.+?)(?:_\d{2})?\.pdf$", fixed)
    if m:
        return m.group(1)
    # 3) YYYY-MM-DD_<name>(_NN).pdf
    m = re.match(r"^\d{4}-\d{2}-\d{2}_(.+?)(?:_\d{2})?\.pdf$", fixed)
    if m:
        return m.group(1)
    return ""


def date_from_filename(filename: str) -> str | None:
    """ファイル名の名前部分や全体から YYYY-MM-DD を取り出す"""
    fixed = textops.fix_broken_unicode(filename)
    name_part = existing_name_part(fixed)
    d = textops.date_from_string(name_part)
    if d:
        return d
    return None


def choose_date(text: str, hint_filename: str) -> str | None:
    """本文 + ファイル名ヒント から最良の日付を選択"""
    hint = date_from_filename(hint_filename)
    candidates = textops.extract_dates_all(text)
    if hint and hint in candidates:
        return hint
    if candidates:
        cnt = Counter(candidates)
        top = cnt.most_common(1)[0][1]
        for d in candidates:
            if cnt[d] == top:
                return d
    return hint


def fallback_title(hint_filename: str) -> str:
    """書類タイプが「書類」のとき、現ファイル名から日付を除いた残りを使う"""
    name = textops.fix_mojibake(existing_name_part(hint_filename))
    if not name:
        return ""
    name = re.sub(r"\d{4}-\d{1,2}-\d{1,2}_?", "", name)
    name = re.sub(r"[�-ÿ]", "", name)  # U+FFFD と Latin-1 残骸を除去
    name = name.strip("_ ")
    return name[:30]


def find_targets(src_dir: Path, mode: str = "split") -> list[Path]:
    """対象PDFを返す。
    mode='split'   分割直後のもの（連番が入っているもの）
    mode='unknown' 日付不明_*.pdf
    mode='all'     上記両方
    """
    out: list[Path] = []
    for p in sorted(src_dir.glob("*.pdf")):
        if not p.is_file():
            continue
        n = p.name
        if ORIG_PAT.match(n):
            continue
        # 既に YYYY-MM-DD_*.pdf 形式は触らない
        if DATED_PAT.match(n) and not UNKNOWN_PAT.match(n):
            if mode == "all":
                pass  # all のときは含めるか? → 通常は触らない
            continue
        if mode in ("split", "all") and SPLIT_PAT.match(n) and not UNKNOWN_PAT.match(n) and not DATED_PAT.match(n):
            out.append(p)
        elif mode in ("unknown", "all") and UNKNOWN_PAT.match(n):
            out.append(p)
    return out


def make_plan(targets: list[Path], pdftotext_path: str | None = None,
              kind_default: str = "書類") -> list[dict]:
    """各PDFについて (date, kind, fallback_title, head) を計算する"""
    pdftotext_path = pdftotext_path or find_pdftotext()
    plan: list[dict] = []
    for p in targets:
        text = extract_text(p, pdftotext=pdftotext_path)
        head = "\n".join(
            [l for l in textops.fix_mojibake(text).splitlines() if l.strip()][:3]
        )[:120]
        date = choose_date(text, p.name)
        kind = textops.extract_kind(text, default_kind=kind_default)
        if kind == kind_default:
            # ファイル名ヒントからも探す
            name_part = textops.fix_mojibake(existing_name_part(p.name))
            kind2 = textops.extract_kind(name_part, default_kind=kind_default)
            if kind2 != kind_default:
                kind = kind2
        fb = fallback_title(p.name) if kind == kind_default else ""
        plan.append({
            "src": p, "date": date, "kind": kind, "head": head,
            "fallback": fb,
        })
    return plan


def resolve_filenames(plan: list[dict]) -> list[dict]:
    """重複名に連番を付与して final 名を確定"""
    bases: list[str] = []
    for item in plan:
        kind_part = item["kind"]
        if item.get("fallback") and kind_part in ("書類", "Document", "unknown"):
            kind_part = item["fallback"]
        if item["date"]:
            bases.append(f"{item['date']}_{kind_part}")
        else:
            bases.append(f"日付不明_{kind_part}")
    cnt = Counter(bases)
    seen: Counter[str] = Counter()
    for item, base in zip(plan, bases):
        if cnt[base] > 1:
            seen[base] += 1
            item["final"] = f"{base}_{seen[base]:02d}.pdf"
        else:
            item["final"] = f"{base}.pdf"
    return plan


def run_rename(src_dir: Path, mode: str = "split", apply: bool = False,
               pdftotext_path: str | None = None,
               kind_default: str = "書類") -> dict:
    """PDFを内容ベースで自動リネームする。

    mode: 'split' (分割直後) / 'unknown' (日付不明_) / 'all' (両方)
    apply=False は dry-run。
    """
    src_dir = Path(src_dir)
    targets = find_targets(src_dir, mode=mode)
    if not targets:
        return {"targets": 0, "actions": [], "applied": 0}

    plan = make_plan(targets, pdftotext_path=pdftotext_path, kind_default=kind_default)
    plan = resolve_filenames(plan)

    actions: list[dict] = []
    applied = 0
    for item in plan:
        src: Path = item["src"]
        dst = src_dir / item["final"]
        action = {
            "src": src.name,
            "src_display": textops.fix_broken_unicode(src.name),
            "dst": item["final"],
            "date": item["date"],
            "kind": item["kind"],
            "head": item["head"],
        }
        if dst.exists() and dst.resolve() != src.resolve():
            action["status"] = "conflict"
        elif src.resolve() == dst.resolve():
            action["status"] = "noop"
        elif apply:
            try:
                src.rename(dst)
                action["status"] = "ok"
                applied += 1
            except Exception as e:
                logging.error("failed to rename %s: %s", src.name, e)
                action["status"] = f"error: {e}"
        else:
            action["status"] = "dry-run"
        actions.append(action)
    return {"targets": len(targets), "actions": actions, "applied": applied}
