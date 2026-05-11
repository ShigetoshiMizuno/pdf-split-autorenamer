# -*- coding: utf-8 -*-
"""文字化け修復・日付正規化・書類タイプ判定などのテキスト処理ユーティリティ"""
from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore[no-reattr-module]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

# OCR の頻出誤認マッピング（漢字の似た字への誤読）
# ScanSnap S500 固有の誤読を含む。profiles/scansnap-s500.toml で外部管理も可能。
MOJIBAKE_FIX = {
    "朁": "月",
    "拁": "拝",
    "紁": "旨",
    "迁": "迎",
    "曁": "曜",
    # 「歓」の OCR 誤読バリアント（週報の「歓迎」を正規化するため）
    "歎": "歓",
    "藪": "歓",
    "裁": "歓",
    "鐵": "歓",
    "欽": "歓",
}


def fix_mojibake(s: str, extra_map: dict[str, str] | None = None) -> str:
    """OCR の典型的な誤読パターンを修復。extra_map で追加置換を指定可能。"""
    merged = {**MOJIBAKE_FIX, **(extra_map or {})}
    for k, v in merged.items():
        s = s.replace(k, v)
    s = re.sub(r"(?<=[一-鿿])E\b", "", s)
    s = re.sub(r"(?<=[一-鿿])E(?=[^A-Za-z0-9])", "", s)
    s = s.replace("�", "")
    return s


# UTF-8→cp1252 化けで頻出する典型文字（事前フィルタ用）
_BROKEN_UNICODE_CHARS = frozenset("çåïÃ»æèéÂÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß")


def fix_broken_unicode(s: str) -> str:
    """Windows でファイル名が UTF-8 バイトを cp1252/Latin-1 として保存された化けを復元する。
    例: 'ç§å¸«' → '牧師' / 部分破損は errors='replace' で許容。"""
    if not s:
        return s
    # 典型的な化け文字が含まれていない場合は復元を試みない（誤判定防止）
    if not any(c in _BROKEN_UNICODE_CHARS for c in s):
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
            if m.start() in seen_positions:  # pragma: no cover
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
    (re.compile(r"請求書|御請求書"), "請求書"),
    (re.compile(r"見積書|御見積書"), "見積書"),
    (re.compile(r"注文書|発注書"), "発注書"),
    (re.compile(r"領収書|受領書"), "領収書"),
    (re.compile(r"業務委託契約書|契約書"), "契約書"),
    (re.compile(r"議事録|会議録"), "議事録"),
    (re.compile(r"稟議書"), "稟議書"),
    (re.compile(r"出張報告書"), "出張報告書"),
    (re.compile(r"報告書"), "報告書"),
    (re.compile(r"通知書|案内"), "通知書"),
    (re.compile(r"納品書"), "納品書"),
]

DEFAULT_BODY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"請求"), "請求書"),
    (re.compile(r"見積"), "見積書"),
    (re.compile(r"注文|発注"), "発注書"),
    (re.compile(r"領収"), "領収書"),
    (re.compile(r"契約"), "契約書"),
    (re.compile(r"議事"), "議事録"),
    (re.compile(r"報告"), "報告書"),
    (re.compile(r"お知らせ|連絡"), "通知書"),
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


# ---- プロファイル読み込み ----

# ---- 取引先抽出 ----

_VENDOR_PATTERNS = [
    # パターン1: 前置会社形態 + 社名（敬称あり必須）
    # 括弧・引用符・改行を含まない範囲で敬称まで取得（W-2 修正）
    re.compile(
        r"(?:株式会社|有限会社|合同会社|（株）|\(株\))\s*([^（「【\n]{1,20}?)"
        r"\s*(?:御中|様|殿)"
    ),
    # パターン1b: 前置会社形態 + 社名（敬称なし、行末か括弧の前まで）
    # 空白を含まない社名専用（例: 株式会社デジタルパートナーズ）
    re.compile(
        r"(?:株式会社|有限会社|合同会社|（株）|\(株\))\s*([^\s（「【\n]{1,20})"
        r"(?=\s*(?:\n|$|（|「|【))"
    ),
    # パターン2: 社名 + 後置会社形態（敬称あり or なし）
    # [^\S\n]* を使って改行をまたぐマッチを防止（W-1 修正）
    re.compile(
        r"(.{1,20}?)[^\S\n]*(?:株式会社|有限会社|合同会社|（株）|\(株\))[^\S\n]*(?:御中|様|殿)?"
    ),
    # パターン3: 英語社名 + 会社形態
    re.compile(
        r"(.{1,20}?)\s+(?:Inc\.|Co\.,?\s*Ltd\.?|Corp\.?|Ltd\.?)\s*(?:御中|様|殿)?"
    ),
]

# 部署・役職・担当者名の境界を示すパターン（社名の後に続く場合に切り詰める）
# 具体的な部署名・役職名のみリストアップ。".{1,4}?部" のような汎用パターンは誤爆するため使わない
_DEPT_ROLE_PATTERN = re.compile(
    r"(?:部長|課長|係長|主任|担当者?|室長|本部長|社長|代表取締役?|専務|常務|理事|"
    r"営業部|総務部|経理部|購買部|人事部|開発部|技術部|製造部|品質管理部|管理部)"
)

# 日付パターン（extract_vendor の戻り値フィルタ用）
_DATE_IN_VENDOR = re.compile(r"\d{4}[年/\-]\d{1,2}")


def _trim_dept_role(name: str) -> str:
    """社名候補から部署/役職パターンが始まる位置以降を除去し、空白を除去して返す。

    空白除去**前**のテキストに対してパターンを適用することで正確な境界を検出する。
    """
    m = _DEPT_ROLE_PATTERN.search(name)
    if m:
        name = name[: m.start()]
    # 全角空白・半角空白を除去
    return name.replace("　", "").replace(" ", "").strip()


def extract_vendor(text: str, max_len: int = 20) -> str | None:
    """文書テキスト先頭 10 行から取引先名を抽出する。

    優先パターン（前置会社形態 → 後置会社形態 → 英語形態）の順に走査し、
    最初にマッチした候補を返す。半角空白を除去し、max_len でトリムする。
    部署/役職パターンが混入している場合は社名手前で切り詰める（W-2 修正）。
    日付パターンが含まれる場合は None を返す（W-1 追加防衛）。
    マッチなしの場合は None を返す。
    """
    if not text:
        return None
    lines = [line for line in text.splitlines() if line.strip()][:10]
    head = "\n".join(lines)
    for pat in _VENDOR_PATTERNS:
        m = pat.search(head)
        if m:
            raw = m.group(1)
            # group(1) が敬称のみの場合は後置パターンの誤マッチ → スキップ
            if raw.strip() in ("御中", "様", "殿"):
                continue
            # 空白除去前に部署/役職で切り詰め（W-2）、その後空白除去
            name = _trim_dept_role(raw)
            if not name:
                continue
            # 日付パターンが含まれていたら除外（W-1 追加防衛）
            if _DATE_IN_VENDOR.search(name):
                continue
            name = sanitize_filename(name, max_length=max_len)
            if name:
                return name
    return None


# ---- 文書番号抽出 ----

_DOCNO_PATTERNS = [
    # パターン1: No. / NO. / 全角Ｎｏ. / Ｎｏ．（全角ピリオド）+ 番号
    re.compile(r"(?:Ｎｏ[．.]?|No\.?|NO\.?)\s*[:：]?\s*([A-Z0-9][-A-Z0-9_/]{2,28})"),
    # パターン2: 書類種別 + 番号
    re.compile(
        r"(?:請求|発注|見積|注文|契約|管理|稟議)番号\s*[:：]?\s*([-A-Z0-9_/]{3,30})"
    ),
    # パターン3: PO-XXX, Q-XXX, R-XXX 等のアルファベット略語
    re.compile(r"\b([A-Z]{1,3}-\d{2,4}-?\d{2,4}-?\d*)\b"),
]


def extract_doc_number(text: str, max_len: int = 30) -> str | None:
    """文書テキスト全体から文書番号を抽出する。

    複数のパターンを順に試し、最初にマッチした番号を返す。
    max_len でトリムする。マッチなしの場合は None を返す。
    """
    if not text:
        return None
    for pat in _DOCNO_PATTERNS:
        m = pat.search(text)
        if m:
            number = m.group(1).strip()
            if number:
                return number[:max_len]
    return None


def load_profile(
    path: Path,
) -> tuple[list[tuple[re.Pattern[str], str]], list[tuple[re.Pattern[str], str]]]:
    """TOML プロファイルファイルを読み込み、(title_patterns, body_patterns) を返す。

    各要素は (コンパイル済み正規表現, ラベル文字列) のタプル。
    フォーマットエラー時は ValueError を送出。
    tomllib が利用できない場合は ImportError を送出。
    """
    if tomllib is None:
        raise ImportError(
            "TOML サポートには Python 3.11+ または `pip install tomli` が必要です"
        )
    with open(path, "rb") as f:
        data = tomllib.load(f)
    title_patterns = [
        (re.compile(entry["pattern"]), entry["label"])
        for entry in data.get("title_patterns", [])
    ]
    body_patterns = [
        (re.compile(entry["pattern"]), entry["label"])
        for entry in data.get("body_patterns", [])
    ]
    return title_patterns, body_patterns


def load_mojibake_map(path: Path) -> dict[str, str]:
    """TOML ファイルから mojibake 置換マップを読み込む。

    TOML フォーマット:
        [[replacements]]
        wrong = "X"
        correct = "Y"

    戻り値: {wrong: correct} の dict。
    """
    if tomllib is None:
        raise ImportError(
            "TOML サポートには Python 3.11+ または `pip install tomli` が必要です"
        )
    with open(path, "rb") as f:
        data = tomllib.load(f)
    result: dict[str, str] = {}
    for entry in data.get("replacements", []):
        result[entry["wrong"]] = entry["correct"]
    return result
