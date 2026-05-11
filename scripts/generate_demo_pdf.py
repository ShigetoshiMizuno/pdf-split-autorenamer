# -*- coding: utf-8 -*-
"""デモ用「複合機まとめスキャン風」PDF 生成スクリプト（WeasyPrint 版）

一般事務所で発生しがちな複数書類（請求書・見積書・議事録・稟議書・出張報告書・
発注書・領収書・契約書）を 1 つの PDF に連続スキャンした体裁で生成する。
README.html / GitHub Pages のデモ素材として利用。

使い方:
    python scripts/generate_demo_pdf.py docs/demo/sample_office_scan.pdf

依存:
    pip install "pdf-split-autorenamer[demo]"
    Windows: winget install tschoonj.GTKForWindows
      https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Windows 専用: GTK3 Runtime の DLL を Python のロードパスに追加
if sys.platform == "win32":
    import os

    _gtk_bin = r"C:\Program Files\GTK3-Runtime Win64\bin"
    if os.path.isdir(_gtk_bin):
        os.environ["PATH"] = _gtk_bin + os.pathsep + os.environ.get("PATH", "")
        try:
            os.add_dll_directory(_gtk_bin)
        except OSError:
            pass

# WeasyPrint の import（未インストール時は丁寧なエラーで終了）
try:
    from weasyprint import HTML
except ImportError:
    print(
        "WeasyPrint が見つかりません。以下の手順でインストールしてください:\n"
        "  pip install 'pdf-split-autorenamer[demo]'\n"
        "Windows の場合は GTK3 Runtime も必要です:\n"
        "  winget install tschoonj.GTKForWindows\n"
        "  https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases",
        file=sys.stderr,
    )
    sys.exit(1)

# ログレベルを抑制（fontTools / WeasyPrint の情報ログを消す）
logging.getLogger("fontTools").setLevel(logging.ERROR)
logging.getLogger("weasyprint").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# CSS / フォント設定
# ---------------------------------------------------------------------------

_FONT_STACK = '"Meiryo", "Yu Gothic", "Noto Sans CJK JP", "Noto Sans JP", sans-serif'

_CSS = f"""
@page {{
    size: A4;
    margin: 2cm;
}}
body {{
    font-family: {_FONT_STACK};
    font-size: 11pt;
    line-height: 1.5;
    color: #000;
}}
section {{
    page-break-after: always;
}}
section:last-child {{
    page-break-after: avoid;
}}
.page-break {{
    page-break-before: always;
}}
h1 {{
    font-size: 22pt;
    margin-bottom: 0.5em;
}}
h2 {{
    font-size: 16pt;
    margin-bottom: 0.4em;
}}
h3 {{
    font-size: 13pt;
    margin-bottom: 0.3em;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.5em 0;
}}
th, td {{
    padding: 4pt 6pt;
    border: 0.5pt solid #ccc;
}}
th {{
    background: #f0f0f0;
}}
.right {{
    text-align: right;
}}
.meta {{
    font-size: 10pt;
    color: #333;
}}
.amount-large {{
    font-size: 14pt;
    font-weight: bold;
}}
.seal-row td {{
    width: 25%;
    height: 40pt;
    text-align: center;
}}
"""


# ---------------------------------------------------------------------------
# 各書類生成関数（dict を返す）
# ---------------------------------------------------------------------------

def _doc_invoice() -> dict:
    """請求書（1ページ）"""
    html = """
<section class="doc--invoice">
  <p class="meta" style="text-align:right">No. 2026-0401-001</p>
  <h1>請求書</h1>
  <p>発行日: 2026年4月1日</p>
  <p><strong>株式会社 山田工業 御中</strong></p>
  <p>下記のとおりご請求申し上げます。</p>
  <p>件名: 4月分 業務委託料</p>
  <p class="amount-large">ご請求金額: ￥330,000-（税込）</p>
  <table>
    <tr><th>項目</th><th>数量</th><th class="right">単価</th><th class="right">金額</th></tr>
    <tr><td>業務委託料</td><td>1.0</td><td class="right">300,000</td><td class="right">300,000</td></tr>
    <tr><td>消費税(10%)</td><td></td><td></td><td class="right">30,000</td></tr>
    <tr><td><strong>合計</strong></td><td></td><td></td><td class="right"><strong>330,000</strong></td></tr>
  </table>
  <p style="margin-top:1em">
    お振込先: みらい銀行 渋谷支店 普通 1234567<br>
    　　　　　カ）サンプルショウジ
  </p>
  <p>支払期限: 2026年4月30日</p>
  <hr style="margin-top:2em">
  <p>
    株式会社 サンプル商事<br>
    〒150-0001 東京都渋谷区神宮前1-2-3<br>
    TEL: 03-1234-5678　Email: info@example.com<br>
    登録番号: T1234567890123
  </p>
</section>
"""
    return {"klass": "doc--invoice", "html": html}


def _doc_quotation() -> dict:
    """御見積書（1ページ）"""
    html = """
<section class="doc--quotation">
  <p class="meta" style="text-align:right">見積番号: Q-2026-0408</p>
  <h1>御見積書</h1>
  <p>2026年4月8日</p>
  <p><strong>鈴木建設株式会社 御中</strong></p>
  <p>下記のとおりお見積もり申し上げます。</p>
  <p>件名: オフィス什器一式 納入</p>
  <p>見積有効期限: 発行日より30日間　　納期: ご発注後 約2週間</p>
  <table>
    <tr><th>品名</th><th>数量</th><th class="right">単価</th><th class="right">金額</th></tr>
    <tr><td>オフィスデスク W1400</td><td>4</td><td class="right">35,000</td><td class="right">140,000</td></tr>
    <tr><td>事務用チェア</td><td>4</td><td class="right">18,000</td><td class="right">72,000</td></tr>
    <tr><td>書庫 高さ1800mm</td><td>2</td><td class="right">42,000</td><td class="right">84,000</td></tr>
    <tr><td>会議用テーブル W1800</td><td>1</td><td class="right">58,000</td><td class="right">58,000</td></tr>
    <tr><td>小計</td><td></td><td></td><td class="right">354,000</td></tr>
    <tr><td>消費税(10%)</td><td></td><td></td><td class="right">35,400</td></tr>
    <tr><td><strong>合計</strong></td><td></td><td></td><td class="right"><strong>389,400</strong></td></tr>
  </table>
  <hr style="margin-top:2em">
  <p>
    株式会社 サンプル商事 営業部<br>
    担当: 田中 一郎　TEL: 03-1234-5678
  </p>
</section>
"""
    return {"klass": "doc--quotation", "html": html}


def _doc_minutes() -> dict:
    """営業部 定例会議 議事録（2ページ）"""
    html = """
<section class="doc--minutes">
  <h2>営業部 定例会議 議事録</h2>
  <p>日時: 2026年4月15日（水）10:00〜11:30</p>
  <p>場所: 本社 3F 会議室A</p>
  <p>出席者: 部長 佐藤、課長 鈴木、田中、伊藤、高橋</p>
  <p>欠席者: 中村（出張のため）</p>
  <h3>1. 第1四半期 売上実績報告（鈴木課長）</h3>
  <ul>
    <li>全社目標達成率: 102.3%</li>
    <li>新規案件: 12件（前年同期 +3件）</li>
    <li>既存顧客リピート率: 87%</li>
  </ul>
  <h3>2. 第2四半期 重点施策（佐藤部長）</h3>
  <ul>
    <li>中堅製造業向け提案を強化</li>
    <li>展示会出展（5月25日 ビッグサイト）</li>
    <li>営業ツール刷新（紙→タブレット）</li>
  </ul>
  <h3>3. 個別案件レビュー</h3>
  <ul>
    <li>A社案件: 来月クロージング見込み（田中）</li>
    <li>B社案件: 仕様再調整中（伊藤）</li>
    <li>C社案件: 競合プレゼン勝利、契約書ドラフト中</li>
  </ul>

  <div class="page-break"></div>

  <h2>営業部 定例会議 議事録（2/2）</h2>
  <p>日時: 2026年4月15日（水）</p>
  <h3>4. 決定事項</h3>
  <ul>
    <li>展示会出展メンバー: 佐藤、田中、高橋</li>
    <li>営業ツール選定: 次回までに3社比較資料を高橋が用意</li>
    <li>A社向けクロージング資料: 鈴木が4/22までに作成</li>
  </ul>
  <h3>5. 次回開催</h3>
  <p>
    日時: 2026年4月22日（水）10:00〜<br>
    場所: 本社 3F 会議室A<br>
    議題: A社クロージング進捗、展示会準備状況
  </p>
  <p style="margin-top:3em">記録: 高橋</p>
  <p>配布先: 営業部全員、管理部 副本部長</p>
  <p style="margin-top:4em; text-align:right">以上</p>
</section>
"""
    return {"klass": "doc--minutes", "html": html}


def _doc_proposal() -> dict:
    """稟議書（1ページ）"""
    html = """
<section class="doc--proposal">
  <div style="display:flex; justify-content:space-between; align-items:baseline">
    <h2>稟議書</h2>
    <span class="meta">稟議番号: R-2026-018</span>
  </div>
  <p>起案日: 2026年4月20日</p>
  <p>起案者: 総務部 渡辺 次郎</p>
  <p><strong>件名: 複合機（コピー機）リプレイス購入の件</strong></p>
  <h3>1. 目的</h3>
  <p>現行機の保守期限切れに伴い、後継機種への入替を行いたい。</p>
  <h3>2. 概要</h3>
  <ul>
    <li>機種: ABC-Office MFP X9000</li>
    <li>台数: 2台（本社1F、3F 各1台）</li>
    <li>購入金額: ￥1,540,000（税込）</li>
    <li>契約形態: 5年リース（月額 ￥28,500）</li>
  </ul>
  <h3>3. 効果</h3>
  <ul>
    <li>印刷速度 約1.5倍、カラー印字単価 30%削減見込み</li>
    <li>スキャン解像度向上により書類電子化の質が改善</li>
  </ul>
  <h3>4. 添付資料</h3>
  <ul>
    <li>ABC-Office 提案書（別添）</li>
    <li>3社相見積比較表（別添）</li>
  </ul>
  <p style="margin-top:2em">承認欄:</p>
  <table class="seal-row">
    <tr>
      <td>社長</td><td>部長</td><td>課長</td><td>起案者</td>
    </tr>
    <tr>
      <td style="height:40pt"></td>
      <td style="height:40pt"></td>
      <td style="height:40pt"></td>
      <td style="height:40pt">［印］</td>
    </tr>
  </table>
</section>
"""
    return {"klass": "doc--proposal", "html": html}


def _doc_travel_report() -> dict:
    """出張報告書（1ページ）"""
    html = """
<section class="doc--travel-report">
  <h2>出張報告書</h2>
  <p>提出日: 2026年4月22日</p>
  <p>氏名: 営業部 田中 一郎</p>
  <p>出張期間: 2026年4月18日（金）〜 4月19日（土）</p>
  <p>出張先: 大阪市北区 株式会社 関西商会 本社</p>
  <p>目的: 新規取引先への提案および契約条件の調整</p>
  <h3>■ 訪問先・面談者</h3>
  <p>株式会社 関西商会　購買部 部長 山本様、課長 西村様</p>
  <h3>■ 主な内容</h3>
  <ul>
    <li>当社サービスの提案プレゼン実施（約60分）</li>
    <li>先方の現状課題ヒアリング</li>
    <li>契約条件・見積金額の概要合意</li>
  </ul>
  <h3>■ 結果・次のアクション</h3>
  <ul>
    <li>正式見積を 4/30 までに先方へ提出</li>
    <li>5/15 週に契約書ドラフトレビュー予定</li>
    <li>初期導入は 6 月想定</li>
  </ul>
  <h3>■ 経費精算（別紙領収書添付）</h3>
  <table>
    <tr><td>交通費(新幹線 往復)</td><td class="right">￥28,640</td></tr>
    <tr><td>宿泊費 1泊</td><td class="right">￥12,800</td></tr>
    <tr><td>会食代(先方接待)</td><td class="right">￥18,500</td></tr>
    <tr><td><strong>合計</strong></td><td class="right"><strong>￥59,940</strong></td></tr>
  </table>
</section>
"""
    return {"klass": "doc--travel-report", "html": html}


def _doc_purchase_order() -> dict:
    """発注書（1ページ）"""
    html = """
<section class="doc--purchase-order">
  <p class="meta" style="text-align:right">発注番号: PO-2026-0425</p>
  <h1>発注書</h1>
  <p>発行日: 2026年4月25日</p>
  <p><strong>株式会社 オフィスサプライ 御中</strong></p>
  <p>下記のとおり発注いたします。</p>
  <table>
    <tr><th>品名</th><th>数量</th><th class="right">単価</th><th class="right">金額</th></tr>
    <tr><td>A4 コピー用紙 (5000枚)</td><td>4箱</td><td class="right">3,200</td><td class="right">12,800</td></tr>
    <tr><td>ボールペン 黒 (10本)</td><td>5箱</td><td class="right">980</td><td class="right">4,900</td></tr>
    <tr><td>クリアファイル A4 (100枚)</td><td>3箱</td><td class="right">1,500</td><td class="right">4,500</td></tr>
    <tr><td>封筒 長3 (1000枚)</td><td>2箱</td><td class="right">4,200</td><td class="right">8,400</td></tr>
    <tr><td>小計</td><td></td><td></td><td class="right">30,600</td></tr>
    <tr><td>消費税(10%)</td><td></td><td></td><td class="right">3,060</td></tr>
    <tr><td><strong>合計</strong></td><td></td><td></td><td class="right"><strong>33,660</strong></td></tr>
  </table>
  <p>納期: 2026年5月2日（金）まで</p>
  <p>納品先: 本社 1F 受付</p>
  <p>支払条件: 月末締 翌月末払</p>
  <hr style="margin-top:2em">
  <p>
    株式会社 サンプル商事 総務部<br>
    発注担当: 渡辺　TEL: 03-1234-5678 内線 201
  </p>
</section>
"""
    return {"klass": "doc--purchase-order", "html": html}


def _doc_receipt() -> dict:
    """領収書（1ページ）"""
    html = """
<section class="doc--receipt">
  <h1>領収書</h1>
  <p>2026年4月28日</p>
  <p><strong>株式会社 サンプル商事 様</strong></p>
  <p class="amount-large">金額: ￥18,500-（税込）</p>
  <p>但し、4月22日 大阪出張時 会食代として</p>
  <p>上記金額正に領収いたしました。</p>
  <table style="width:60%; margin-top:1em">
    <tr><th colspan="2">内訳</th></tr>
    <tr><td>会食料金（5名）</td><td class="right">16,820</td></tr>
    <tr><td>消費税(10%)</td><td class="right">1,680</td></tr>
    <tr><td><strong>合計</strong></td><td class="right"><strong>18,500</strong></td></tr>
  </table>
  <p style="margin-top:2em">
    <strong>和食処 みやび</strong><br>
    〒530-0001 大阪市北区梅田2-3-4<br>
    TEL: 06-1234-5678<br>
    登録番号: T9876543210987
  </p>
  <p class="meta">［収入印紙不要・税込3万円未満］</p>
</section>
"""
    return {"klass": "doc--receipt", "html": html}


def _doc_contract() -> dict:
    """業務委託契約書（2ページ）"""
    html = """
<section class="doc--contract">
  <h2>業務委託契約書</h2>
  <p>2026年5月1日</p>
  <p>
    株式会社 サンプル商事（以下「甲」という）と<br>
    株式会社 デジタルパートナーズ（以下「乙」という）は、<br>
    下記のとおり業務委託契約を締結する。
  </p>
  <h3>第1条（目的）</h3>
  <p>
    甲は乙に対し、別紙仕様書に定める業務（以下「本件業務」という）の<br>
    遂行を委託し、乙はこれを受託する。
  </p>
  <h3>第2条（委託期間）</h3>
  <p>
    本契約の有効期間は 2026年5月1日 から 2027年4月30日 までとする。<br>
    ただし、期間満了の30日前までに双方から異議申し立てがない場合、<br>
    本契約は同一条件で1年間自動更新されるものとする。
  </p>
  <h3>第3条（委託料）</h3>
  <p>
    甲は乙に対し、本件業務の対価として月額 ￥800,000（税別）を支払う。<br>
    支払は当月末締翌月末日までに乙の指定口座へ振込む。
  </p>
  <h3>第4条（業務内容の変更）</h3>
  <p>
    本件業務の内容に変更を要する場合、甲乙協議のうえ書面によりこれを定めるものとする。
  </p>
  <h3>第5条（秘密保持）</h3>
  <p>
    甲乙は、本契約の履行に関連して知り得た相手方の業務上の秘密を、<br>
    契約期間中はもとより、契約終了後も第三者に漏洩してはならない。
  </p>

  <div class="page-break"></div>

  <h2>業務委託契約書（2/2）</h2>
  <p>2026年5月1日</p>
  <h3>第6条（解除）</h3>
  <p>
    甲または乙が本契約に違反し、相当の催告を経ても是正されない場合、<br>
    相手方は本契約を解除することができる。
  </p>
  <h3>第7条（合意管轄）</h3>
  <p>
    本契約に関する紛争は、東京地方裁判所を第一審の専属的合意管轄裁判所とする。
  </p>
  <h3>第8条（協議事項）</h3>
  <p>
    本契約に定めなき事項または疑義が生じた事項については、<br>
    甲乙誠意をもって協議のうえ解決するものとする。
  </p>
  <p style="margin-top:1.5em">
    本契約の成立を証するため、本書2通を作成し、甲乙記名捺印の上、各1通を保有する。
  </p>
  <p style="margin-top:1em">2026年5月1日</p>
  <table style="width:80%; margin-top:1em">
    <tr>
      <td style="vertical-align:top">
        甲: 東京都渋谷区神宮前1-2-3<br>
        　　株式会社 サンプル商事<br>
        　　代表取締役 山田 太郎　［印］
      </td>
    </tr>
    <tr>
      <td style="vertical-align:top; padding-top:1em">
        乙: 東京都港区赤坂4-5-6<br>
        　　株式会社 デジタルパートナーズ<br>
        　　代表取締役 高橋 花子　［印］
      </td>
    </tr>
  </table>
</section>
"""
    return {"klass": "doc--contract", "html": html}


# ---------------------------------------------------------------------------
# HTML レンダラー
# ---------------------------------------------------------------------------

def _render_html(docs: list[dict]) -> str:
    """book 形式の HTML 文字列を組み立てる"""
    body_parts = [doc["html"] for doc in docs]
    body = "\n".join(body_parts)
    return (
        '<!doctype html>\n'
        '<html lang="ja">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<title>複合機まとめスキャン サンプル</title>\n'
        f'<style>{_CSS}</style>\n'
        '</head>\n'
        '<body>\n'
        f'{body}\n'
        '</body>\n'
        '</html>'
    )


# ---------------------------------------------------------------------------
# 期待キーワード対応表（セルフチェック用）
# ---------------------------------------------------------------------------

_EXPECTED = [
    ("請求書", "2026年4月1日"),
    ("見積書", "2026年4月8日"),
    ("議事録", "2026年4月15日"),   # p3
    ("議事録", "2026年4月15日"),   # p4 (2/2)
    ("稟議", "2026年4月20日"),     # p5
    ("出張報告書", "2026年4月22日"),  # p6
    ("発注書", "2026年4月25日"),   # p7
    ("領収書", "2026年4月28日"),   # p8
    ("契約書", "2026年5月1日"),    # p9
    ("契約書", "2026年5月1日"),    # p10 (2/2)
]


# ---------------------------------------------------------------------------
# メイン API
# ---------------------------------------------------------------------------

def make_demo_pdf(output: Path) -> None:
    """一般事務所向けデモ PDF を生成（テキスト抽出可能）"""
    output.parent.mkdir(parents=True, exist_ok=True)

    docs = [
        _doc_invoice(),
        _doc_quotation(),
        _doc_minutes(),
        _doc_proposal(),
        _doc_travel_report(),
        _doc_purchase_order(),
        _doc_receipt(),
        _doc_contract(),
    ]
    html_str = _render_html(docs)
    HTML(string=html_str).write_pdf(str(output))
    print(f"生成: {output}")

    # ------------------------------------------------------------------
    # セルフチェック: PyMuPDF で開き直して 10 ページ・キーワードを確認
    # ------------------------------------------------------------------
    try:
        import fitz
    except ImportError:
        print("  [警告] PyMuPDF が未インストールのためセルフチェックをスキップします")
        return

    doc = fitz.open(str(output))
    page_count = doc.page_count
    if page_count != 10:
        doc.close()
        raise RuntimeError(
            f"ページ数が想定と異なります: expected 10 pages, got {page_count}"
        )

    errors = []
    for i, (kw1, kw2) in enumerate(_EXPECTED):
        text = doc[i].get_text()
        if len(text) < 50:
            errors.append(f"p{i+1}: テキストが短すぎます ({len(text)} 文字)")
        if kw1 not in text:
            errors.append(f"p{i+1}: キーワード '{kw1}' が見つかりません")
        if kw2 not in text:
            errors.append(f"p{i+1}: キーワード '{kw2}' が見つかりません")
    doc.close()

    if errors:
        raise RuntimeError(
            "セルフチェック失敗:\n" + "\n".join(f"  {e}" for e in errors)
        )

    print("  セルフチェック OK: 10 ページ / 全キーワード確認済み")


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="一般事務所向け『複合機まとめスキャン風』デモ PDF を生成（WeasyPrint 版）"
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
