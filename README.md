# pdf-split-autorenamer

[![PyPI version](https://badge.fury.io/py/pdf-split-autorenamer.svg)](https://pypi.org/project/pdf-split-autorenamer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

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

## ダウンロード（スタンドアロン実行ファイル）

[GitHub Releases](https://github.com/ShigetoshiMizuno/pdf-split-autorenamer/releases) から
プラットフォームに合った実行ファイルをダウンロードできます。

| プラットフォーム | ファイル |
|---|---|
| Windows | `psar-windows.exe` |
| macOS | `psar-macos` |
| Linux | `psar-linux` |

> **注意**: Poppler (`pdftotext`) と Tesseract OCR は **別途インストール**が必要です。
> 実行ファイルには同梱されていません。

---

## インストール（Python パッケージ）

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

**Windows でダブルクリック起動する場合** — リポジトリ同梱の `psar-gui.bat` (v0.3.0) を使います。

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

## 書類タイプのカスタマイズ（プロファイル）

`profiles/church.toml` や `profiles/business.toml` を参考に TOML プロファイルを作成し、
`--profile` オプションで読み込めます。

```sh
psar rename ./scanned_pdfs --profile profiles/my_profile.toml --apply
```

プロファイルのフォーマット:

```toml
[[title_patterns]]
pattern = "議事録"
label = "議事録"

[[body_patterns]]
pattern = "出席者"
label = "議事録"
```

OCR 誤読マップは `profiles/scansnap-s500.toml` を参照してください。

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。

## OCR パイプライン

テキストレイヤーなしの画像 PDF には、3 段階の OCR パイプラインが自動的に使われます。

### Stage 1: pdftotext / PyMuPDF（追加インストール不要）

テキストレイヤーあり PDF はそのまま高速処理します。

### Stage 2: Tesseract OCR（手動インストール必要）

Stage 1 で日本語テキストが取得できなかったページは自動的に Tesseract にフォールバック。

```sh
# Tesseract をインストール後、日本語用データも追加
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS:   brew install tesseract tesseract-lang
# Linux:   apt install tesseract-ocr tesseract-ocr-jpn

# OCR フォールバックを無効化したい場合
psar analyze ./scanned_pdfs --no-ocr-fallback
```

### Stage 3: LLM Vision / PaddleOCR / EasyOCR（オプション）

手書き・縦書き・低解像度スキャンには `--ocr-strategy` を指定します。

```sh
# Claude Vision（クラウド API、精度最高）
pip install "pdf-split-autorenamer[llm]"
export ANTHROPIC_API_KEY=sk-ant-...
psar analyze ./scanned_pdfs --ocr-strategy llm

# EasyOCR（ローカル、PyTorch ベース）
pip install "pdf-split-autorenamer[easyocr]"

# PaddleOCR（ローカル、縦書きに強い）
pip install "pdf-split-autorenamer[paddle]"
```

| `--ocr-strategy` | 動作 |
|-----------------|------|
| `fast` | Stage 1 のみ（テキスト層 PDF 専用） |
| `balanced` | Stage 1 → テキスト空時 Stage 2（既定） |
| `roi` | Stage 1 → 品質低時 Stage 2（ROI クロップ） |
| `llm` | Stage 1 → 2 → Claude LLM Vision の順に試行 |

## 注意

- 自動命名はあくまで補助です。実行前に必ず dry-run で結果を確認してください。
- Windows で日本語ファイル名を扱う際、PyMuPDF は `stream=bytes` 経由で入力することで
  ANSI パス変換の問題を回避しています。PyMuPDF `>=1.23,<1.26` を推奨します。
