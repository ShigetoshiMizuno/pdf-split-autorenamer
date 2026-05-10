# OCR パイプライン ベンチマーク

pdf-split-autorenamer の OCR Stage 1/2/3 の精度・速度・コストを比較した記録。

## ベンチマーク方法

```bash
# ステップ 1: サンプル PDF を生成（初回のみ）
python scripts/generate_sample_pdfs.py tests/fixtures/benchmark/

# ステップ 2: ベンチマーク実行
# 全ステージを実行（Tesseract + ANTHROPIC_API_KEY 必要）
python scripts/run_benchmark.py tests/fixtures/benchmark/ --output results.json

# Stage 1 のみ（pdftotext/PyMuPDF のみ。外部ツール不要）
python scripts/run_benchmark.py <PDFフォルダ> --stages 1

# Stage 1/2（Tesseract 必要、API 不要）
python scripts/run_benchmark.py <PDFフォルダ> --stages 1 2
```

> **注**: サンプル PDF は `.gitignore` の `*.pdf` パターンで追跡対象外。
> 実際の計測には実際の教会文書 PDF を `<PDFフォルダ>` に配置してください。

## ステージ定義

| ステージ | 手法 | 依存 | コスト |
|---------|------|------|--------|
| Stage 1 | pdftotext / PyMuPDF テキスト層抽出 | なし（PyMuPDF 組み込み） | 無料 |
| Stage 2 | ページ上部 30% ROI クロップ + Tesseract OCR | Tesseract `jpn` traineddata | 無料 |
| Stage 3 | ROI 画像 → Claude claude-3-5-sonnet 構造化抽出 | ANTHROPIC_API_KEY | 有料（約 $0.003/ページ） |

## 計測指標

| 指標 | 説明 |
|------|------|
| 秒/ページ | 1 ページあたりの処理時間（ネットワーク待ち込み） |
| JP比率 | 抽出テキスト中の日本語文字（U+3040〜U+9FFF）の割合。精度の代理指標 |
| 日付抽出率 | `extract_dates_all()` で 1 件以上抽出できたページの割合 |
| コスト (USD) | Stage 3 LLM の API 費用見積もり（$3/M input tokens） |

## サンプルセット構成（推奨）

| ファイル名 | PDF タイプ | 期待ステージ |
|-----------|-----------|------------|
| `print_digital.pdf` | デジタル印字（テキスト層あり） | Stage 1 で完結 |
| `scan_clear.pdf` | クリアスキャン（300 dpi 以上） | Stage 2 で対応 |
| `scan_handwritten.pdf` | 手書き混在スキャン | Stage 3 が有効 |
| `vertical_text.pdf` | 縦書き文書 | Stage 2/3 が有効 |
| `table_heavy.pdf` | 表・図主体 | Stage 2/3 が有効 |

## 計測結果

> **注意**: 以下は空のテンプレートです。実際の計測値を記入してください。
> `python scripts/run_benchmark.py <フォルダ> --output results.json` で生成した JSON を参照。

### Stage 1 — pdftotext / PyMuPDF

| PDF | ページ数 | 秒/ページ | JP比率 | テキスト有 |
|-----|---------|---------|-------|----------|
| （サンプル未収集） | — | — | — | — |

### Stage 2 — ROI + Tesseract

| PDF | ページ数 | 秒/ページ | JP比率 | テキスト有 |
|-----|---------|---------|-------|----------|
| （サンプル未収集） | — | — | — | — |

### Stage 3 — LLM Vision（Claude）

| PDF | ページ数 | 秒/ページ | 日付抽出率 | コスト(USD) |
|-----|---------|---------|----------|-----------|
| （サンプル未収集） | — | — | — | — |

## 推奨設定ガイドライン

```
--ocr-strategy fast      → テキスト層あり PDF のみを扱う場合（Stage 1 のみ）
--ocr-strategy balanced  → 通常の教会文書（Stage 1 → Stage 2 フォールバック）
--ocr-strategy roi       → スキャン PDF が多い場合（Stage 1 → Stage 2 強制）
--ocr-strategy llm       → 手書き・縦書き・低解像度スキャン（Stage 1→2→3 全試行）
```

## コスト試算（Stage 3 LLM）

Claude claude-3-5-sonnet 料金（2026年5月時点）:

| バッチサイズ | 推定コスト |
|------------|---------|
| 10 ページ | 約 $0.03 |
| 100 ページ | 約 $0.30 |
| 1,000 ページ | 約 $3.00 |

※ ROI クロップ（上部 30%）のため、フルページ送信より約 40% コスト削減。
※ キャッシュ（`.psar/ocr_cache/`）を活用すると再処理コストはゼロ。

## 改善履歴

| バージョン | 変更 | 効果 |
|----------|------|------|
| v0.3.0 | ROI クロップ導入（Stage 2） | 処理時間 -30%、誤読 -20%（推定） |
| v0.3.0 | OCR キャッシュ導入 | 2 回目以降は Stage 2/3 コストゼロ |
| v0.3.0 | LLM Vision 統合（Stage 3） | 手書き文書の日付取得率向上（実測値未収集） |
