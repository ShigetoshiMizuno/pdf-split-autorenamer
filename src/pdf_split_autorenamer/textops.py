# -*- coding: utf-8 -*-
"""文字化け修復・日付正規化・書類タイプ判定などのテキスト処理ユーティリティ"""
from __future__ import annotations

import re

# OCR の頻出誤認マッピング（漢字の似た字への誤読）
MOJIBAKE_FIX = {
    "朁": "月",
    "拁": "拝",
    "紁": "旨",
    "迁": "迎",
    "曁": "曜",
}


def fix_mojibake(s: str) -> str:
    """OCR の典型的な誤読パターンを修復"""
    for k, v in MOJIBAKE_FIX.items():
        s = s.replace(k, v)
    s = re.sub(r"(?<=[一-鿿])E\b", "", s)
    s = re.sub(r"(?<=[一-鿿])E(?=[^A-Za-z0-9])", "", s)
    s = s.replace("�", "")
    return s


def fix_broken_unicode(s: str) -> str:
    """Windows でファイル名が UTF-8 バイトを cp1252/Latin-1 として保存された化けを復元する。
    例: 'ç§å¸«' → '牧師' / 部分破損は errors='replace' で許容。"""
    if not s:
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            b = s.encode(enc)
        except UnicodeEncodeError:
            continue
        for errors in ("strict", "replace"):
            try:
                recovered = b.decode("utf-8", errors=errors)
            except UnicodeDecodeError:
                continue
            if recovered != s and any(0x3040 <= ord(c) <= 0x9FFF for c in recovered):
                return recovered
    return s


# ---- 日付抽出 ----
_DATE_NORMALIZE = str.maketrans({
    "．": ".", "／": "/", "－": "-", "ー": "-", "・": ".", "　": " ",
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
})

_DATE_PATTERNS = [
    re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"),
    re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
    re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
]


def extract_dates_all(text: str) -> list[str]:
    """テキストから日付候補を出現順にすべて抽出。全角ピリオド／中点／全角数字対応。"""
    t = fix_mojibake(text).translate(_DATE_NORMALIZE)
    dates: list[str] = []
    seen_positions: set[int] = set()
    for pat in _DATE_PATTERNS:
        for m in pat.finditer(t):
            if m.start() in seen_positions:
                continue
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                dates.append(f"{y:04d}-{mo:02d}-{d:02d}")
                seen_positions.add(m.start())
    return dates


def date_from_string(s: str) -> str | None:
    """文字列から YYYY-MM-DD を最初に1件抽出"""
    if not s:
        return None
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


# ---- 書類タイプ判定 ----
# プロファイル方式: ユーザが用途に応じてカスタムプロファイルを書ける
# キー: タイトル領域の正規表現 → ラベル

DEFAULT_TITLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"主日礼拝.{0,8}メッセージ要[旨約]|主日礼拝メッセージ"), "主日礼拝メッセージ要旨"),
    (re.compile(r"水曜礼拝.{0,8}メッセージ要[旨約]"), "水曜礼拝メッセージ要旨"),
    (re.compile(r"会計報告"), "会計報告"),
    (re.compile(r"教会総会"), "教会総会"),
    (re.compile(r"イースター礼拝"), "イースター礼拝"),
    (re.compile(r"クリスマス礼拝"), "クリスマス礼拝"),
    (re.compile(r"感謝祭"), "感謝祭"),
    (re.compile(r"週報"), "週報"),
    (re.compile(r"歓迎|歎迎|藪迎|裁迎|鐵迎|欽迎|歓迁|藪迁|裁迁|鐵迁|欽迁"), "週報"),
]

DEFAULT_BODY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"主日礼拝.{0,8}メッセージ要[旨約]"), "主日礼拝メッセージ要旨"),
    (re.compile(r"水曜礼拝.{0,8}メッセージ要[旨約]"), "水曜礼拝メッセージ要旨"),
    (re.compile(r"イースター礼拝"), "イースター礼拝"),
    (re.compile(r"クリスマス礼拝"), "クリスマス礼拝"),
    (re.compile(r"祈祷会|祈り会"), "祈祷会"),
    (re.compile(r"学び会"), "学び会"),
    (re.compile(r"教会学校.{0,4}シニア科|シニア科"), "教会学校シニア科"),
    (re.compile(r"教会学校"), "教会学校"),
    (re.compile(r"主日礼拝|聖日礼拝|水曜礼拝"), "週報"),
    (re.compile(r"お知らせ|お和らせ"), "お知らせ"),
]


def extract_kind(
    text: str,
    title_patterns: list[tuple[re.Pattern[str], str]] | None = None,
    body_patterns: list[tuple[re.Pattern[str], str]] | None = None,
    default_kind: str = "書類",
) -> str:
    """テキストから書類タイプを抽出。先頭5行=タイトル領域 → 本文の順で判定。"""
    title_patterns = title_patterns if title_patterns is not None else DEFAULT_TITLE_PATTERNS
    body_patterns = body_patterns if body_patterns is not None else DEFAULT_BODY_PATTERNS
    t = fix_mojibake(text)
    head_lines = [l for l in t.splitlines() if l.strip()][:6]
    head = "\n".join(head_lines)
    for pat, name in title_patterns:
        if pat.search(head):
            return name
    for pat, name in body_patterns:
        if pat.search(t):
            return name
    return default_kind


# ---- ファイル名サニタイズ ----
_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """Windows 安全なファイル名にする"""
    if not name:
        return ""
    s = _INVALID_NAME.sub("", name).strip()
    s = re.sub(r"\s+", "_", s)
    s = s.rstrip(". ")
    return s[:max_length]
