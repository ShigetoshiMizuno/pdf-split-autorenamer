# Changelog

本プロジェクトの変更履歴。
[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準拠し、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に従う。

## [Unreleased]

### Added
- **README.html (一般事務所向けビジュアル紹介ページ)** [PR #27]
  - `docs/index.html` — Tailwind + Mermaid + Noto Sans JP の1枚LP（Hero / Problem / 3-step / Tour / OCR / Install / FAQ / CTA）
  - `scripts/generate_demo_pdf.py` — 事務所書類8種10ページの「複合機まとめスキャン風」PDF 生成
  - `docs/demo/` — デモ素材（sample_office_scan.pdf / sample_groups.json / sample_report.html）
  - `docs/images/` — SVG モックアップ（before-after / gui-main / report-preview / gui-analyze-highlight）
  - 「ローカル動作・社外送信なし・クラウドサービスではない」を複数箇所で明示
- **アプリ内編集 UI（pywebview による WebView 内蔵）** [PR #30 / Issue #29]
  - `src/pdf_split_autorenamer/inapp_editor.py` — `PsarBridge`（JS↔Python API）
  - GUI に「アプリ内で編集（推奨）」ボタン追加、ブラウザ離脱・groups.json DL→手動上書きの手間が消える
  - opt-in 依存: `pip install 'pdf-split-autorenamer[gui-inapp]'`
  - `report.html` の `saveJson()` に pywebview 分岐追加（既存の psar serve / file:// DL は維持）
- **Windows GUI 起動バッチ** [PR #26] — `psar-gui.bat` をダブルクリックで起動

### Changed
- README.md の冒頭にビジュアル版（docs/index.html）へのリンクを追加
- `.gitignore`: `docs/demo/*.pdf` を例外として許可

### Issues opened
- **#28** — 営業チラシ（A4 1枚）作成、画像生成AI用プロンプト同梱（Midjourney / FLUX / DALL-E / Imagen）
- **#29** — pywebview によるアプリ内編集 UI 統合（PR #30 で対応中）

---

## [0.3.0] - 2026-05-11

### Added
- **T-13** PaddleOCR・EasyOCR バックエンド実装 [PR #21]
  - `pip install 'pdf-split-autorenamer[paddle]'` / `[easyocr]` で利用可
  - 既存 Tesseract バックエンドと並列で `--ocr-backend` 切替可能
- **T-12** psar `--version` フラグ・FAQ・OCR 空ページ警告・`psar serve` サブコマンド追加
- **T-09** ベンチマークスクリプト [PR #19]
  - `scripts/run_benchmark.py`
  - `docs/benchmark.md`
- **T-08** OcrStrategy（fast / balanced / roi / thorough / llm）の選択肢追加
- **T-07** Stage 3 LLM Vision（ClaudeVisionBackend / GPT4VisionBackend）[PR #17]
- **T-06** Stage 2 ROI OCR（crop_page_pixmap / ocr_cache）
- **T-05** OcrBackend 抽象クラス（TesseractBackend + スタブ）
- **T-04** MOJIBAKE_FIX の外部 TOML 化
- **T-02** 外部 TOML プロファイル方式（`profiles/church.toml` / `profiles/business.toml` / `profiles/scansnap-s500.toml`）
- **T-01** Tesseract フォールバック（`has_text_layer` / `find_tesseract`）
- **T-00** PyMuPDF 入力側 ANSI 対策（`fitz.open(stream=...)` 経由でWindows 日本語パスに対応）

### Changed
- **T-10b** `print` → `logging` への全面移行、`--verbose` / `--quiet` フラグ追加
- **T-04b** `_KEEP_CHARS` 削除（プロファイル方式に統合）
- **T-07b** phash 関連コード削除

### Fixed
- **PR #16** `__main__.py` のカバレッジ 0% → 100%、`.gitignore` の `_*.py` パターンが `__main__.py` を誤除外していた問題を修正（`!**/__main__.py` 例外を追加）

### Tests
- 685 tests, **カバレッジ 100%**（全モジュール）

---

## [0.2.0] - earlier

ベース機能（解析・分割・自動リネーム・GUI）の初期実装。

[Unreleased]: https://github.com/ShigetoshiMizuno/pdf-split-autorenamer/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/ShigetoshiMizuno/pdf-split-autorenamer/releases/tag/v0.3.0
[0.2.0]: https://github.com/ShigetoshiMizuno/pdf-split-autorenamer/releases/tag/v0.2.0
