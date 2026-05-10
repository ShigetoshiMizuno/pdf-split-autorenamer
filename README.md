# pdf-split-autorenamer

OCR テキストが埋め込まれたスキャンPDF群を、**書類ごとのグループに自動分割**し、
**内容ベースで `YYYY-MM-DD_書類タイプ.pdf` に自動リネーム**するツールです。

ScanSnap のように1つのPDFに複数の書類が連続スキャンされて入っているような場合の
後処理（仕分け＋命名）を支援します。CUI と Tkinter GUI の両方を備えています。

## できること

1. **解析** — フォルダ内のPDFを開いてページごとのサムネ・OCRテキスト・向き・サイズなどを集め、
   ヒューリスティック（向き変化／テキスト類似度／タイトルマーカー）で
   「ここで切れ目」候補を提案。**HTMLレポート**で人間が境界を確認・調整できる。
2. **分割** — 確定した境界 (`groups.json`) に従ってPDFをページ範囲ごとに分割。
3. **自動リネーム** — 分割後PDFの内容を読み取り、日付（半角・全角ピリオド・中点・全角数字に対応）
   と書類タイプ（プロファイル方式でカスタマイズ可）から `YYYY-MM-DD_xxx.pdf` の形式に命名。
   表記揺れはフォルダ内で統一されます。

## インストール

### 必要なもの

- Python 3.10+
- [PyMuPDF](https://pypi.org/project/PyMuPDF/)
- (推奨) [Poppler](https://poppler.freedesktop.org/) の `pdftotext` コマンド
  （OCRテキストの抽出精度が大きく向上します。なくても動きますが文字化けしやすくなります）

### セットアップ

```sh
git clone https://github.com/ShigetoshiMizuno/pdf-split-autorenamer.git
cd pdf-split-autorenamer
pip install -e .
```

### Poppler (pdftotext) のインストール

| OS | 方法 |
|---|---|
| Windows | [Git for Windows](https://gitforwindows.org/) に同梱の `pdftotext.exe` で動作確認済み。または [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) を導入し PATH に追加。 |
| macOS | `brew install poppler` |
| Linux | `apt install poppler-utils` など |

`pdftotext` のパスは環境変数 `PDFTOTEXT` で明示指定もできます。

## 使い方

### GUI（推奨）

```sh
psar gui
# または
python -m pdf_split_autorenamer gui
```

3ステップを画面のボタンでぽちぽち進めます。

1. **PDFフォルダ** を選んで「解析を実行」 → ブラウザで `report.html` が開きます。
2. ブラウザ上で各ページの **「↑つなぐ／↑切る」** をクリックして境界を調整。各グループの先頭で
   **出力名** を入力できます（OCRから推定済みの候補が初期値）。
3. 「**groups.json を保存**」ボタンでファイルをダウンロード → `<フォルダ>/.psar/groups.json` に上書き。
4. GUI に戻って「**分割 実行**」 → 「**自動リネーム 実行**」。

### CUI

```sh
# 1. 解析
psar analyze ./scanned_pdfs

# → ブラウザで .psar/report.html を開いて境界を編集
#    groups.json をダウンロード→ .psar/groups.json に上書き

# 2. 分割
psar split ./scanned_pdfs --dry-run     # 確認
psar split ./scanned_pdfs               # 実行

# 3. リネーム
psar rename ./scanned_pdfs              # dry-run
psar rename ./scanned_pdfs --apply      # 実行

# 4. 「日付不明_」になったファイルを後から再考
psar rename ./scanned_pdfs --retarget-unknown --apply
```

## 出力例

入力:
```
scanned_pdfs/
  2026-05-10-11-59-42.pdf  (42ページの連続スキャン)
```

`psar analyze` → `psar split` → `psar rename --apply` 後:
```
scanned_pdfs/
  2026-05-10-11-59-42.pdf                  # 元PDFは保持
  2026-04-26_主日礼拝メッセージ要旨.pdf     # 自動命名された分割結果
  2026-05-10_主日礼拝メッセージ要旨.pdf
  2026-04-26_週報.pdf
  2026-04-19_週報.pdf
  2026-02-23_書類.pdf                       # 内容判定不能なものは「書類」
  日付不明_xxx.pdf                          # 日付検出不能
```

## 書類タイプのカスタマイズ

`pdf_split_autorenamer.textops` の `DEFAULT_TITLE_PATTERNS` / `DEFAULT_BODY_PATTERNS` を
参考に、自分の用途のプロファイルを書けます。
将来的にはコマンドライン／GUI から外部プロファイルを読み込めるようにする予定です。

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。

## 注意

- このツールは「OCRテキストが埋め込まれたPDF」を前提にしています。画像のみのPDFには
  別途 OCR (Tesseract 等) を先にかける必要があります。
- 自動命名はあくまで補助です。実行前に必ず dry-run で結果を確認してください。
- Windows で日本語ファイル名を扱う際、過去のバージョンの PyMuPDF (1.24 等) では
  ANSI フォールバックで化けが起きるケースがありました。本ツールは
  `Document.write()` のバイト経由で書き出すことでこれを回避しています。
