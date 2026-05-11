# -*- coding: utf-8 -*-
"""デモ用「複合機まとめスキャン風」PDF 生成スクリプト

一般事務所で発生しがちな複数書類（請求書・見積書・議事録・稟議書・出張報告書・
発注書・領収書・契約書）を 1 つの PDF に連続スキャンした体裁で生成する。
README.html / GitHub Pages のデモ素材として利用。

使い方:
    python scripts/generate_demo_pdf.py docs/demo/sample_office_scan.pdf

依存: reportlab（CID フォントで日本語を埋め込み、テキスト抽出可能な PDF を生成）
日本語フォントは Windows / macOS / Linux の代表的なシステムフォントを順に探索。
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# 日本語フォント候補（Windows / macOS / Linux）
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/NotoSansJP-VF.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

_FONT_NAME = "JpFont"


def _register_jp_font() -> str:
    for f in _FONT_CANDIDATES:
        if Path(f).exists():
            try:
                if f.lower().endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont(_FONT_NAME, f, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont(_FONT_NAME, f))
                return f
            except Exception:
                continue
    raise RuntimeError(
        "日本語フォントが見つかりません。_FONT_CANDIDATES に追加してください。"
    )


# A4 ポートレート（ReportLab は下が 0 で上に増える座標系）
_W, _H = A4
_MARGIN = 60


def _draw_lines(c: canvas.Canvas, lines: List[Tuple[float, float, str, float]]) -> None:
    """[(x, y_from_top, text, fontsize), ...] を描画。
    y は『ページ上端から下に何 pt』で受け取り、ReportLab の座標系に変換する。
    """
    for x, y_top, text, size in lines:
        c.setFont(_FONT_NAME, size)
        c.drawString(x, _H - y_top, text)


def _new_page(c: canvas.Canvas) -> None:
    c.setStrokeColorRGB(0.85, 0.85, 0.85)
    c.setLineWidth(0.5)
    c.rect(20, 20, _W - 40, _H - 40)


def _line(y: float, text: str, size: float = 11) -> Tuple[float, float, str, float]:
    return (_MARGIN, y, text, size)


def _build_invoice(c: canvas.Canvas) -> None:
    _new_page(c)
    _draw_lines(c, [
        (380, 70, "No. 2026-0401-001", 10),
        (_MARGIN, 100, "請求書", 28),
        _line(150, "発行日: 2026年4月1日", 12),
        _line(175, "株式会社 山田工業 御中", 13),
        _line(205, "下記のとおりご請求申し上げます。", 11),
        _line(245, "件名: 4月分 業務委託料", 12),
        _line(275, "ご請求金額: ￥330,000-（税込）", 14),
        _line(345, "  項目              数量    単価       金額", 10),
        _line(365, "  業務委託料        1.0    300,000   300,000", 10),
        _line(385, "  消費税(10%)                          30,000", 10),
        _line(425, "  合計                              330,000", 11),
        _line(480, "お振込先: みらい銀行 渋谷支店 普通 1234567", 10),
        _line(500, "        カ）サンプルショウジ", 10),
        _line(550, "支払期限: 2026年4月30日", 11),
        _line(630, "株式会社 サンプル商事", 12),
        _line(650, "〒150-0001 東京都渋谷区神宮前1-2-3", 10),
        _line(665, "TEL: 03-1234-5678  Email: info@example.com", 10),
        _line(685, "登録番号: T1234567890123", 9),
    ])
    c.showPage()


def _build_quotation(c: canvas.Canvas) -> None:
    _new_page(c)
    _draw_lines(c, [
        (380, 70, "見積番号: Q-2026-0408", 10),
        (_MARGIN, 100, "御見積書", 26),
        _line(150, "2026年4月8日", 11),
        _line(180, "鈴木建設株式会社 御中", 13),
        _line(220, "下記のとおりお見積もり申し上げます。", 11),
        _line(255, "件名: オフィス什器一式 納入", 12),
        _line(285, "見積有効期限: 発行日より30日間", 10),
        _line(305, "納期: ご発注後 約2週間", 10),
        _line(365, "  品名                      数量   単価     金額", 10),
        _line(390, "  オフィスデスク W1400      4    35,000   140,000", 10),
        _line(410, "  事務用チェア              4    18,000    72,000", 10),
        _line(430, "  書庫 高さ1800mm           2    42,000    84,000", 10),
        _line(450, "  会議用テーブル W1800      1    58,000    58,000", 10),
        _line(490, "  小計                                    354,000", 10),
        _line(510, "  消費税(10%)                              35,400", 10),
        _line(530, "  合計                                    389,400", 11),
        _line(630, "株式会社 サンプル商事 営業部", 12),
        _line(650, "担当: 田中 一郎  TEL: 03-1234-5678", 10),
    ])
    c.showPage()


def _build_minutes(c: canvas.Canvas) -> None:
    _new_page(c)
    _draw_lines(c, [
        (_MARGIN, 90, "営業部 定例会議 議事録", 22),
        _line(135, "日時: 2026年4月15日（水）10:00〜11:30", 11),
        _line(155, "場所: 本社 3F 会議室A", 11),
        _line(175, "出席者: 部長 佐藤、課長 鈴木、田中、伊藤、高橋", 11),
        _line(195, "欠席者: 中村（出張のため）", 11),
        _line(255, "1. 第1四半期 売上実績報告（鈴木課長）", 13),
        _line(285, "  ・全社目標達成率: 102.3%", 11),
        _line(305, "  ・新規案件: 12件（前年同期 +3件）", 11),
        _line(325, "  ・既存顧客リピート率: 87%", 11),
        _line(365, "2. 第2四半期 重点施策（佐藤部長）", 13),
        _line(395, "  ・中堅製造業向け提案を強化", 11),
        _line(415, "  ・展示会出展（5月25日 ビッグサイト）", 11),
        _line(435, "  ・営業ツール刷新（紙→タブレット）", 11),
        _line(475, "3. 個別案件レビュー", 13),
        _line(505, "  ・A社案件: 来月クロージング見込み（田中）", 11),
        _line(525, "  ・B社案件: 仕様再調整中（伊藤）", 11),
        _line(545, "  ・C社案件: 競合プレゼン勝利、契約書ドラフト中", 11),
    ])
    c.showPage()
    _new_page(c)
    _draw_lines(c, [
        (_MARGIN, 90, "営業部 定例会議 議事録（2/2）", 18),
        _line(135, "4. 決定事項", 13),
        _line(165, "  ・展示会出展メンバー: 佐藤、田中、高橋", 11),
        _line(185, "  ・営業ツール選定: 次回までに3社比較資料を高橋が用意", 11),
        _line(205, "  ・A社向けクロージング資料: 鈴木が4/22までに作成", 11),
        _line(245, "5. 次回開催", 13),
        _line(275, "  日時: 2026年4月22日（水）10:00〜", 11),
        _line(295, "  場所: 本社 3F 会議室A", 11),
        _line(315, "  議題: A社クロージング進捗、展示会準備状況", 11),
        _line(395, "記録: 高橋", 11),
        _line(415, "配布先: 営業部全員、管理部 副本部長", 11),
        _line(730, "以上", 12),
    ])
    c.showPage()


def _build_proposal(c: canvas.Canvas) -> None:
    _new_page(c)
    _draw_lines(c, [
        (_MARGIN, 90, "稟  議  書", 24),
        (380, 90, "稟議番号: R-2026-018", 10),
        _line(135, "起案日: 2026年4月20日", 11),
        _line(155, "起案者: 総務部 渡辺 次郎", 11),
        _line(195, "件名: 複合機（コピー機）リプレイス購入の件", 13),
        _line(235, "1. 目的", 12),
        _line(260, "  現行機の保守期限切れに伴い、後継機種への入替を行いたい。", 11),
        _line(295, "2. 概要", 12),
        _line(320, "  ・機種: ABC-Office MFP X9000", 11),
        _line(340, "  ・台数: 2台（本社1F、3F 各1台）", 11),
        _line(360, "  ・購入金額: ￥1,540,000（税込）", 11),
        _line(380, "  ・契約形態: 5年リース（月額 ￥28,500）", 11),
        _line(415, "3. 効果", 12),
        _line(440, "  ・印刷速度 約1.5倍、カラー印字単価 30%削減見込み", 11),
        _line(460, "  ・スキャン解像度向上により書類電子化の質が改善", 11),
        _line(495, "4. 添付資料", 12),
        _line(520, "  ・ABC-Office 提案書（別添）", 11),
        _line(540, "  ・3社相見積比較表（別添）", 11),
        _line(630, "承認欄:", 11),
        _line(670, "  社長     部長     課長     起案者", 11),
        _line(690, "  ［　］   ［　］   ［　］   ［印］", 11),
    ])
    c.showPage()


def _build_travel_report(c: canvas.Canvas) -> None:
    _new_page(c)
    _draw_lines(c, [
        (_MARGIN, 90, "出 張 報 告 書", 22),
        _line(135, "提出日: 2026年4月22日", 11),
        _line(155, "氏名: 営業部 田中 一郎", 11),
        _line(215, "出張期間: 2026年4月18日（金）〜 4月19日（土）", 12),
        _line(240, "出張先: 大阪市北区 株式会社 関西商会 本社", 12),
        _line(265, "目的: 新規取引先への提案および契約条件の調整", 12),
        _line(305, "■ 訪問先・面談者", 12),
        _line(330, "  株式会社 関西商会  購買部 部長 山本様、課長 西村様", 11),
        _line(370, "■ 主な内容", 12),
        _line(395, "  ・当社サービスの提案プレゼン実施（約60分）", 11),
        _line(415, "  ・先方の現状課題ヒアリング", 11),
        _line(435, "  ・契約条件・見積金額の概要合意", 11),
        _line(475, "■ 結果・次のアクション", 12),
        _line(500, "  ・正式見積を 4/30 までに先方へ提出", 11),
        _line(520, "  ・5/15 週に契約書ドラフトレビュー予定", 11),
        _line(540, "  ・初期導入は 6 月想定", 11),
        _line(590, "■ 経費精算（別紙領収書添付）", 12),
        _line(615, "  交通費(新幹線 往復)  ￥28,640", 11),
        _line(635, "  宿泊費 1泊            ￥12,800", 11),
        _line(655, "  会食代(先方接待)      ￥18,500", 11),
        _line(675, "  合計                  ￥59,940", 12),
    ])
    c.showPage()


def _build_purchase_order(c: canvas.Canvas) -> None:
    _new_page(c)
    _draw_lines(c, [
        (380, 70, "発注番号: PO-2026-0425", 10),
        (_MARGIN, 100, "発  注  書", 26),
        _line(150, "発行日: 2026年4月25日", 11),
        _line(180, "株式会社 オフィスサプライ 御中", 13),
        _line(220, "下記のとおり発注いたします。", 11),
        _line(285, "  品名                      数量   単価     金額", 10),
        _line(310, "  A4 コピー用紙 (5000枚)    4箱  3,200    12,800", 10),
        _line(330, "  ボールペン 黒 (10本)     5箱    980     4,900", 10),
        _line(350, "  クリアファイル A4 (100枚) 3箱  1,500     4,500", 10),
        _line(370, "  封筒 長3 (1000枚)        2箱  4,200     8,400", 10),
        _line(410, "  小計                                     30,600", 10),
        _line(430, "  消費税(10%)                               3,060", 10),
        _line(450, "  合計                                     33,660", 11),
        _line(500, "納期: 2026年5月2日（金）まで", 11),
        _line(520, "納品先: 本社 1F 受付", 11),
        _line(540, "支払条件: 月末締 翌月末払", 11),
        _line(630, "株式会社 サンプル商事 総務部", 12),
        _line(650, "発注担当: 渡辺  TEL: 03-1234-5678 内線 201", 10),
    ])
    c.showPage()


def _build_receipt(c: canvas.Canvas) -> None:
    _new_page(c)
    _draw_lines(c, [
        (_MARGIN, 100, "領  収  書", 26),
        _line(160, "2026年4月28日", 11),
        _line(200, "株式会社 サンプル商事 様", 13),
        _line(250, "金額: ￥18,500-（税込）", 16),
        _line(300, "但し、4月22日 大阪出張時 会食代として", 11),
        _line(320, "上記金額正に領収いたしました。", 11),
        _line(430, "  内訳", 11),
        _line(455, "    会食料金（5名）     16,820", 10),
        _line(475, "    消費税(10%)           1,680", 10),
        _line(495, "    合計                 18,500", 10),
        _line(590, "和食処 みやび", 13),
        _line(615, "〒530-0001 大阪市北区梅田2-3-4", 10),
        _line(635, "TEL: 06-1234-5678", 10),
        _line(655, "登録番号: T9876543210987", 9),
        _line(730, "［収入印紙不要・税込3万円未満］", 9),
    ])
    c.showPage()


def _build_contract(c: canvas.Canvas) -> None:
    _new_page(c)
    _draw_lines(c, [
        (_MARGIN, 90, "業 務 委 託 契 約 書", 22),
        _line(145, "2026年5月1日", 11),
        _line(190, "株式会社 サンプル商事（以下「甲」という）と", 11),
        _line(210, "株式会社 デジタルパートナーズ（以下「乙」という）は、", 11),
        _line(230, "下記のとおり業務委託契約を締結する。", 11),
        _line(275, "第1条（目的）", 13),
        _line(300, "  甲は乙に対し、別紙仕様書に定める業務（以下「本件業務」と", 11),
        _line(320, "  いう）の遂行を委託し、乙はこれを受託する。", 11),
        _line(355, "第2条（委託期間）", 13),
        _line(380, "  本契約の有効期間は 2026年5月1日 から 2027年4月30日 までとする。", 11),
        _line(400, "  ただし、期間満了の30日前までに双方から異議申し立てがない場合、", 11),
        _line(420, "  本契約は同一条件で1年間自動更新されるものとする。", 11),
        _line(455, "第3条（委託料）", 13),
        _line(480, "  甲は乙に対し、本件業務の対価として月額 ￥800,000（税別）を", 11),
        _line(500, "  支払う。支払は当月末締翌月末日までに乙の指定口座へ振込む。", 11),
        _line(535, "第4条（業務内容の変更）", 13),
        _line(560, "  本件業務の内容に変更を要する場合、甲乙協議のうえ書面により", 11),
        _line(580, "  これを定めるものとする。", 11),
        _line(615, "第5条（秘密保持）", 13),
        _line(640, "  甲乙は、本契約の履行に関連して知り得た相手方の業務上の", 11),
        _line(660, "  秘密を、契約期間中はもとより、契約終了後も第三者に漏洩", 11),
        _line(680, "  してはならない。", 11),
    ])
    c.showPage()
    _new_page(c)
    _draw_lines(c, [
        (_MARGIN, 90, "業務委託契約書（2/2）", 18),
        _line(135, "第6条（解除）", 13),
        _line(160, "  甲または乙が本契約に違反し、相当の催告を経ても是正されない", 11),
        _line(180, "  場合、相手方は本契約を解除することができる。", 11),
        _line(215, "第7条（合意管轄）", 13),
        _line(240, "  本契約に関する紛争は、東京地方裁判所を第一審の専属的合意", 11),
        _line(260, "  管轄裁判所とする。", 11),
        _line(295, "第8条（協議事項）", 13),
        _line(320, "  本契約に定めなき事項または疑義が生じた事項については、", 11),
        _line(340, "  甲乙誠意をもって協議のうえ解決するものとする。", 11),
        _line(395, "本契約の成立を証するため、本書2通を作成し、甲乙記名捺印の上、", 11),
        _line(415, "各1通を保有する。", 11),
        _line(475, "  2026年5月1日", 12),
        _line(535, "  甲: 東京都渋谷区神宮前1-2-3", 11),
        _line(555, "      株式会社 サンプル商事", 12),
        _line(575, "      代表取締役 山田 太郎  ［印］", 11),
        _line(635, "  乙: 東京都港区赤坂4-5-6", 11),
        _line(655, "      株式会社 デジタルパートナーズ", 12),
        _line(675, "      代表取締役 高橋 花子  ［印］", 11),
    ])
    c.showPage()


_BUILDERS = [
    ("invoice", _build_invoice),
    ("quotation", _build_quotation),
    ("minutes", _build_minutes),
    ("proposal", _build_proposal),
    ("travel_report", _build_travel_report),
    ("purchase_order", _build_purchase_order),
    ("receipt", _build_receipt),
    ("contract", _build_contract),
]


def make_demo_pdf(output: Path) -> None:
    """一般事務所向けデモ PDF を生成（テキスト抽出可能）"""
    font = _register_jp_font()
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=A4)
    c.setTitle("複合機まとめスキャン サンプル")
    for _name, fn in _BUILDERS:
        fn(c)
    c.save()
    print(f"生成: {output}  (フォント: {font})")
    print("  含まれる書類:")
    for name, _ in _BUILDERS:
        print(f"    - {name}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="一般事務所向け『複合機まとめスキャン風』デモ PDF を生成"
    )
    ap.add_argument(
        "output",
        nargs="?",
        default="docs/demo/sample_office_scan.pdf",
        help="出力 PDF パス (default: docs/demo/sample_office_scan.pdf)",
    )
    args = ap.parse_args(argv)
    make_demo_pdf(Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
