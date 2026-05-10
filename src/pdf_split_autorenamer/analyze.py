# -*- coding: utf-8 -*-
"""PDFを解析して境界候補を提案し、HTML レポートを生成する"""
from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path

import fitz

from . import textops
from .pdfio import (
    extract_text, find_pdftotext,
    list_pdfs, render_thumb,
)

TITLE_MARKER_RE = re.compile(
    r"(第\s*\d+\s*号|Vol\.?\s*\d+|令和\d+年|\d{4}年\s*\d{1,2}月|\d{1,2}月\s*\d{1,2}日)"
)


def _orient(w: float, h: float) -> str:
    return "P" if h >= w else "L"


def _bigram(text: str) -> set[str]:
    t = re.sub(r"\s+", "", text)
    if len(t) < 2:
        return set()
    return {t[i:i + 2] for i in range(len(t) - 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def collect_pages(src_dir: Path, thumb_dir: Path,
                  pdftotext_path: str | None = None,
                  pdf_filter=None) -> list[dict]:
    """フォルダ内の各PDFを開いて、各ページのメタデータ・サムネ・OCRテキストを集める。

    pdf_filter: 関数 (Path) -> bool。True を返すPDFだけ対象にする。
    """
    thumb_dir.mkdir(parents=True, exist_ok=True)
    pdftotext_path = pdftotext_path or find_pdftotext()

    pages: list[dict] = []
    for pdf_path in list_pdfs(src_dir):
        if pdf_filter and not pdf_filter(pdf_path):
            continue
        try:
            doc = fitz.open(stream=pdf_path.read_bytes(), filetype="pdf")
        except Exception as e:
            logging.warning("open failed: %s: %s", pdf_path.name, e)
            continue
        try:
            for i in range(doc.page_count):
                page = doc[i]
                page_no = i + 1
                thumb_name = f"{pdf_path.stem}_p{page_no:03d}.jpg"
                thumb_path = thumb_dir / thumb_name
                if not thumb_path.exists():
                    render_thumb(page, thumb_path)
                text = extract_text(pdf_path, page_no, pdftotext_path)
                head_text = "\n".join(
                    [l for l in textops.fix_mojibake(text).splitlines() if l.strip()][:3]
                )[:200]
                pages.append({
                    "pdf": pdf_path.name,
                    "page": page_no,
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "orient": _orient(page.rect.width, page.rect.height),
                    "thumb": f"thumbs/{thumb_name}",
                    "text": text,
                    "text_head": head_text,
                    "title_markers": list(TITLE_MARKER_RE.findall(
                        "\n".join(text.splitlines()[:5]))),
                    "bigram": _bigram(text),
                })
        finally:
            doc.close()
    return pages


def score_boundary(prev: dict, cur: dict) -> tuple[float, list[str]]:
    """前ページと現ページの間の「境界らしさ」 0..1 と理由を返す"""
    if prev["pdf"] != cur["pdf"]:
        return 1.0, ["別PDF"]
    reasons: list[str] = []
    score = 0.0
    if prev["orient"] != cur["orient"]:
        score += 0.7
        reasons.append("向き変化")
    elif (abs(prev["width"] - cur["width"]) > prev["width"] * 0.05 or
          abs(prev["height"] - cur["height"]) > prev["height"] * 0.05):
        score += 0.4
        reasons.append("サイズ変化")
    j = _jaccard(prev["bigram"], cur["bigram"])
    if j < 0.05:
        score += 0.4
        reasons.append(f"テキスト類似極低 ({j:.2f})")
    elif j < 0.10:
        score += 0.2
        reasons.append(f"テキスト類似低 ({j:.2f})")
    new_titles = set(cur["title_markers"]) - set(prev["title_markers"])
    if new_titles:
        score += 0.5
        reasons.append("新タイトル " + ", ".join(list(new_titles)[:2]))
    if not reasons:
        reasons.append(f"類似 (j={j:.2f})")
    return min(score, 1.0), reasons


def build_initial_groups(pages: list[dict],
                         boundary_threshold: float = 0.5) -> dict[str, list[dict]]:
    """ページ列から初期グループ {pdf: [{range:[a,b], name:""}, ...]} を作る"""
    groups: dict[str, list[dict]] = {}
    if not pages:
        return groups

    cur_pdf = pages[0]["pdf"]
    cur_start = 1
    for i in range(1, len(pages)):
        prev, cur = pages[i - 1], pages[i]
        if cur["pdf"] != cur_pdf:
            groups.setdefault(cur_pdf, []).append(
                {"range": [cur_start, prev["page"]], "name": ""}
            )
            cur_pdf = cur["pdf"]
            cur_start = 1
            continue
        s, _ = score_boundary(prev, cur)
        if s >= boundary_threshold:
            groups.setdefault(cur_pdf, []).append(
                {"range": [cur_start, prev["page"]], "name": ""}
            )
            cur_start = cur["page"]
    groups.setdefault(cur_pdf, []).append(
        {"range": [cur_start, pages[-1]["page"]], "name": ""}
    )
    return groups


def build_boundary_info(pages: list[dict]) -> list[dict]:
    info: list[dict] = []
    for i in range(1, len(pages)):
        s, r = score_boundary(pages[i - 1], pages[i])
        info.append({
            "score": round(s, 2),
            "reasons": r,
            "cross_pdf": pages[i - 1]["pdf"] != pages[i]["pdf"],
        })
    return info


def render_html_report(pages: list[dict], boundary_info: list[dict],
                       initial_groups: dict[str, list[dict]],
                       title: str = "PDF 分割レビュー") -> str:
    """単一HTMLのレビューUIを生成"""
    page_data = [
        {
            "pdf": p["pdf"],
            "page": p["page"],
            "thumb": p["thumb"],
            "orient": p["orient"],
            "size": f"{int(p['width'])}x{int(p['height'])}",
            "head": p["text_head"],
        }
        for p in pages
    ]
    payload = {
        "pages": page_data,
        "boundaries": boundary_info,
        "initial_groups": initial_groups,
    }
    payload_b64 = base64.b64encode(
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    html_doc = HTML_TEMPLATE.replace("__TITLE__", title).replace("__PAYLOAD__", payload_b64)
    return html_doc


HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
:root{ --bg:#fafafa; --fg:#222; --muted:#666; --line:#ddd; --on:#d33; --off:#888; --gbg:#fff8e8; }
body{ font-family: "Segoe UI", "Yu Gothic UI", sans-serif; margin:0; padding:0; background:var(--bg); color:var(--fg);}
header{ position:sticky; top:0; background:#fff; border-bottom:1px solid var(--line); padding:10px 16px; z-index:10; display:flex; gap:14px; align-items:center; flex-wrap:wrap;}
header h1{ font-size:14px; margin:0; }
header button{ font-size:13px; padding:6px 12px; cursor:pointer; }
.stat{ font-size:12px; color:var(--muted); }
main{ max-width:1100px; margin:0 auto; padding:16px;}
.pdf-section{ margin-bottom:32px; }
.pdf-title{ font-size:13px; color:var(--muted); padding:8px 0; border-bottom:1px solid var(--line); margin-bottom:8px;}
.row{ display:flex; gap:12px; align-items:flex-start; padding:8px; background:#fff; border:1px solid var(--line); border-radius:4px; margin-bottom:4px;}
.row.first-of-group{ border-top:3px solid var(--on); background:var(--gbg);}
.row .thumb{ width:220px; flex-shrink:0; }
.row .thumb img{ width:100%; border:1px solid #bbb; display:block;}
.row .meta{ flex:1; min-width:0; }
.row .meta .top{ display:flex; gap:6px; align-items:center; flex-wrap:wrap;}
.row .meta .pgno{ font-weight:bold; font-size:13px; min-width:40px;}
.row .meta .grp{ display:inline-block; padding:2px 8px; background:#eef; border:1px solid #99c; border-radius:3px; font-size:12px;}
.row .meta .info{ color:var(--muted); font-size:11px; margin-top:4px;}
.row .meta pre{ font-size:11px; background:#f6f6f6; padding:6px; border-radius:3px; max-height:80px; overflow:auto; white-space:pre-wrap; word-break:break-all; margin:6px 0 0 0;}
.btns{ display:inline-flex; gap:4px; margin-left:auto;}
.btns button{ font-size:12px; padding:4px 10px; cursor:pointer; border:1px solid var(--line); background:#fff; border-radius:3px;}
.btns button.cut.active{ background:var(--on); color:#fff; border-color:var(--on);}
.btns button.join.active{ background:#cef; border-color:#39c; color:#06a;}
.btns button[disabled]{ background:#f0f0f0; color:#bbb; cursor:not-allowed;}
.namebox{ display:flex; gap:6px; align-items:center; margin-top:6px;}
.namebox label{ font-size:11px; color:var(--muted);}
.namebox input{ flex:1; font-size:13px; padding:4px 6px; border:1px solid #99c; border-radius:3px; min-width:0;}
.preview{ font-size:11px; color:#06a; margin-top:2px;}
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <div class="stat" id="stat"></div>
  <button onclick="saveJson()">groups.json を保存</button>
  <button onclick="resetGroups()">初期境界に戻す</button>
</header>
<main id="main"></main>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const payload = JSON.parse(atob(document.getElementById('payload').textContent.trim()));
const pages = payload.pages;
const boundaries = payload.boundaries;
const initial = payload.initial_groups;

function buildInitialFlags() {
  const flags = new Array(pages.length - 1).fill(false);
  const groupOfPage = new Map();
  for (const [pdfName, groups] of Object.entries(initial)) {
    groups.forEach((g, gi) => {
      const r = g.range || g;
      for (let p = r[0]; p <= r[1]; p++) groupOfPage.set(pdfName + "|" + p, gi);
    });
  }
  for (let i = 1; i < pages.length; i++) {
    const a = pages[i-1], b = pages[i];
    if (a.pdf !== b.pdf) { flags[i-1] = true; continue; }
    const ga = groupOfPage.get(a.pdf + "|" + a.page);
    const gb = groupOfPage.get(b.pdf + "|" + b.page);
    if (ga !== gb) flags[i-1] = true;
  }
  return flags;
}
function buildInitialNames() {
  const names = new Map();
  for (const [pdfName, groups] of Object.entries(initial)) {
    for (const g of groups) {
      const r = g.range || g;
      names.set(pdfName + "|" + r[0], g.name || "");
    }
  }
  return names;
}
let flags = buildInitialFlags();
let names = buildInitialNames();
function isFirstOfGroup(i) {
  if (i === 0) return true;
  if (pages[i].pdf !== pages[i-1].pdf) return true;
  return flags[i-1];
}
function previewFileName(pdfName, firstPage, groupIdx, name) {
  const stem = pdfName.replace(/\.pdf$/i, '');
  const nn = String(groupIdx).padStart(2, '0');
  const safe = (name || '').replace(/[<>:"/\\|?*\x00-\x1f]/g, '').trim();
  return safe ? `→ ${stem}_${nn}_${safe}.pdf` : `→ ${stem}_${nn}.pdf`;
}
function escapeHtml(s){
  return (s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
}
function render() {
  const main = document.getElementById('main');
  main.innerHTML = "";
  let curPdf = null, sec = null;
  let groupIdxByPdf = {};
  const groupNum = new Array(pages.length).fill(1);
  for (let i = 0; i < pages.length; i++) {
    if (i === 0 || pages[i].pdf !== pages[i-1].pdf) groupIdxByPdf[pages[i].pdf] = 1;
    else if (flags[i-1]) groupIdxByPdf[pages[i].pdf] = (groupIdxByPdf[pages[i].pdf]||1) + 1;
    groupNum[i] = groupIdxByPdf[pages[i].pdf];
  }
  for (let i = 0; i < pages.length; i++) {
    const p = pages[i];
    if (p.pdf !== curPdf) {
      curPdf = p.pdf;
      sec = document.createElement('section');
      sec.className = 'pdf-section';
      const title = document.createElement('div');
      title.className = 'pdf-title';
      title.textContent = curPdf;
      sec.appendChild(title);
      main.appendChild(sec);
    }
    const isFirst = isFirstOfGroup(i);
    const samePdfAsPrev = i > 0 && pages[i-1].pdf === p.pdf;
    const bi = samePdfAsPrev ? boundaries[i-1] : null;
    const reasons = bi ? `score=${bi.score} ${bi.reasons.join(' / ')}` : '';
    const row = document.createElement('div');
    row.className = 'row' + (isFirst ? ' first-of-group' : '');
    const thumb = document.createElement('div');
    thumb.className = 'thumb';
    const img = document.createElement('img');
    img.src = p.thumb; img.loading = 'lazy';
    thumb.appendChild(img);
    row.appendChild(thumb);
    const meta = document.createElement('div');
    meta.className = 'meta';
    const top = document.createElement('div');
    top.className = 'top';
    const pgno = document.createElement('span');
    pgno.className = 'pgno'; pgno.textContent = `p${p.page}`;
    top.appendChild(pgno);
    const grp = document.createElement('span');
    grp.className = 'grp'; grp.textContent = `グループ ${groupNum[i]}`;
    top.appendChild(grp);
    const btns = document.createElement('div');
    btns.className = 'btns';
    const joinBtn = document.createElement('button');
    joinBtn.className = 'join' + (samePdfAsPrev && !flags[i-1] ? ' active' : '');
    joinBtn.textContent = '↑ つなぐ';
    const cutBtn = document.createElement('button');
    cutBtn.className = 'cut' + ((!samePdfAsPrev || flags[i-1]) ? ' active' : '');
    cutBtn.textContent = '↑ 切る';
    if (i === 0 || !samePdfAsPrev) {
      joinBtn.disabled = true; cutBtn.disabled = true;
    } else {
      joinBtn.onclick = () => { flags[i-1] = false; render(); };
      cutBtn.onclick = () => { flags[i-1] = true; render(); };
    }
    btns.appendChild(joinBtn); btns.appendChild(cutBtn);
    top.appendChild(btns);
    meta.appendChild(top);
    const info = document.createElement('div');
    info.className = 'info';
    info.textContent = `${p.size} / ${p.orient === 'P' ? '縦' : '横'}`;
    if (reasons) info.textContent += `   |   ${reasons}`;
    meta.appendChild(info);
    if (isFirst) {
      const nameKey = p.pdf + "|" + p.page;
      const nameWrap = document.createElement('div');
      nameWrap.className = 'namebox';
      const lbl = document.createElement('label');
      lbl.textContent = '出力名:';
      const input = document.createElement('input');
      input.type = 'text';
      input.value = names.get(nameKey) || '';
      input.placeholder = '例) 2026-04-06_主日礼拝';
      input.oninput = (e) => {
        names.set(nameKey, e.target.value);
        const sib = nameWrap.nextElementSibling;
        if (sib && sib.classList.contains('preview')) {
          sib.textContent = previewFileName(p.pdf, p.page, groupNum[i], e.target.value);
        }
      };
      nameWrap.appendChild(lbl); nameWrap.appendChild(input);
      meta.appendChild(nameWrap);
      const preview = document.createElement('div');
      preview.className = 'preview';
      preview.textContent = previewFileName(p.pdf, p.page, groupNum[i], input.value);
      meta.appendChild(preview);
    }
    const pre = document.createElement('pre');
    pre.textContent = p.head || '(テキストなし)';
    meta.appendChild(pre);
    row.appendChild(meta);
    sec.appendChild(row);
  }
  const total = Object.values(groupIdxByPdf).reduce((a,b)=>a+b, 0);
  document.getElementById('stat').textContent = `総ページ ${pages.length} / グループ合計 ${total}`;
}
function buildGroupsFromFlags() {
  const out = {};
  let curPdf = null;
  let curStart = 0;
  for (let i = 0; i < pages.length; i++) {
    if (curPdf === null || pages[i].pdf !== curPdf) {
      if (curPdf !== null) {
        const r0 = pages[curStart].page, r1 = pages[i-1].page;
        out[curPdf].push({range:[r0, r1], name: names.get(curPdf+"|"+r0) || ""});
      }
      curPdf = pages[i].pdf;
      out[curPdf] = out[curPdf] || [];
      curStart = i;
      continue;
    }
    if (flags[i-1]) {
      const r0 = pages[curStart].page, r1 = pages[i-1].page;
      out[curPdf].push({range:[r0, r1], name: names.get(curPdf+"|"+r0) || ""});
      curStart = i;
    }
  }
  if (curPdf !== null) {
    const r0 = pages[curStart].page, r1 = pages[pages.length-1].page;
    out[curPdf].push({range:[r0, r1], name: names.get(curPdf+"|"+r0) || ""});
  }
  return out;
}
function saveJson() {
  const data = buildGroupsFromFlags();
  const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'groups.json'; a.click();
  URL.revokeObjectURL(url);
  alert('groups.json をダウンロードしました。\n作業ディレクトリ (.psar) に上書き保存してから\n分割を実行してください。');
}
function resetGroups() {
  if (!confirm('初期境界とファイル名を初期状態に戻します。よろしいですか?')) return;
  flags = buildInitialFlags();
  names = buildInitialNames();
  render();
}
render();
</script>
</body>
</html>
"""


def run_analyze(src_dir: Path, work_dir: Path | None = None,
                pdftotext_path: str | None = None,
                title: str = "PDF 分割レビュー") -> dict:
    """src_dir 配下のPDFを解析し、サムネ・groups.json・report.html を work_dir に出力。
    既に groups.json がある場合は上書きせず初期案を groups.initial.json に保存。"""
    src_dir = Path(src_dir)
    work_dir = Path(work_dir) if work_dir else (src_dir / ".psar")
    thumb_dir = work_dir / "thumbs"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 既存の出力PDF (＝再実行) を除外する filter
    split_re = re.compile(r"_(\d{2,3})(?:_.+)?\.pdf$")

    def _filter(p: Path) -> bool:
        # 出力済みっぽい (`<stem>_NN[_name].pdf`) は対象外
        if split_re.search(p.name):
            return False
        return True

    pages = collect_pages(src_dir, thumb_dir, pdftotext_path, pdf_filter=_filter)
    if not pages:
        return {"pages": 0, "groups": 0}
    boundaries = build_boundary_info(pages)
    groups = build_initial_groups(pages)

    out_json = work_dir / "groups.json"
    if out_json.exists():
        backup = work_dir / "groups.initial.json"
        backup.write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        out_json.write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")

    out_html = work_dir / "report.html"
    out_html.write_text(render_html_report(pages, boundaries, groups, title=title),
                        encoding="utf-8")

    return {
        "pages": len(pages),
        "groups": sum(len(v) for v in groups.values()),
        "report_html": str(out_html),
        "groups_json": str(out_json),
    }
