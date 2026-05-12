# Changelog

本プロジェクトの変更履歴。
[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準拠し、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に従う。

## [Unreleased]

（次バージョンに向けた変更がここに入ります）

---

## [0.4.0] - 2026-05-12

業務利用者向けの UX 改善と「書類サマリー命名」への振り切り。

### Added
- **書類サマリー命名（カテゴリ + 取引先 + 文書番号）** [PR #51 / Issue #34]
  - 出力ファイル名を `YYYY-MM-DD_カテゴリ-取引先-文書番号.pdf` 形式で生成
  - `profiles/business.toml` を 8 業務書類（請求書 / 見積書 / 議事録 / 稟議書 / 出張報告書 / 発注書 / 領収書 / 契約書）に拡張
  - `textops.py` に書類サマリー抽出ロジック、`analyze.py` に `generate_candidate_names`
- **アプリ内編集 UI（pywebview による WebView 内蔵）** [PR #30 / Issue #29]
  - `src/pdf_split_autorenamer/inapp_editor.py` — `PsarBridge`（JS↔Python API）
  - GUI に「アプリ内で編集（推奨）」ボタン追加、ブラウザ離脱・分割設定 DL→手動上書きの手間が消える
  - opt-in 依存: `pip install 'pdf-split-autorenamer[gui-inapp]'`
  - `report.html` の `saveJson()` に pywebview 分岐追加（既存の psar serve / file:// DL は維持）
- **入力選択でフォルダ／単一 PDF を両対応** [PR #46 / Issue #35]
  - GUI に「フォルダ…」「ファイル…」両ボタン
  - `analyze.py` / `split.py` が単一 PDF 入力も受け付ける
- **README.html（一般事務所向けビジュアル紹介ページ）** [PR #27]
  - `docs/index.html` — Tailwind + Mermaid + Noto Sans JP の 1 枚 LP（Hero / Problem / 3-step / Tour / OCR / Install / FAQ / CTA）
  - `scripts/generate_demo_pdf.py` — 事務所書類 8 種 10 ページの「複合機まとめスキャン風」PDF 生成（WeasyPrint）
  - `docs/demo/` — デモ素材、`docs/images/` — SVG モックアップ
  - 「ローカル動作・社外送信なし・クラウドサービスではない」を複数箇所で明示
- **営業チラシ A4 縦の試作（SVG / PNG）** [PR #33 / Issue #28]
- **Windows GUI 起動バッチ** [PR #26] — `psar-gui.bat` をダブルクリックで起動
- **CHANGELOG.md（Keep a Changelog 形式）** [PR #31]
- **書類タイプ変化を境界判定に取り込む** [PR #44 / Issue #38]
  - `score_boundary` で書類タイプ変化を強い境界（+0.8）として扱う
  - `collect_pages` に `kind` フィールドを追加

### Changed
- **GUI を 2 ステップ化** [PR #45 / Issue #40] — Step 3「自動リネーム」を Step 2「分割」に統合（自動で連続実行）
- **解析後の確認ダイアログ廃止** [PR #42 / Issue #37] — 解析完了で `report.html` を編集 UI に自動オープン、askyesno を廃止
- **保存後の alert を廃止し window.close を試行** [PR #43 / Issue #39] — pywebview 分岐は `window.pywebview.api.close_window()` で閉じる
- **CMD コンソールウィンドウ抑制** [PR #41 / Issue #36]
  - 新規 `_subprocess_utils.py` の `run_silent` で `pdfio.py` / `ocr_backend.py` の `subprocess.run` をラップ
  - Windows 環境で OCR 解析時に CMD 窓がチラつく問題を解消
- **出力ファイル名から元 PDF 名と連番を省略** [PR #52 / Issue #52] — 候補名があるときは `<name>.pdf` のみ。重複は force/skip-exists で保護
- README.md の冒頭にビジュアル版（docs/index.html）へのリンクを追加
- `.gitignore`: `docs/demo/*.pdf` を例外として許可、`!src/**/_*.py` / `!tests/**/_*.py` の例外を追加

### Tests
- **805 passed, カバレッジ 98%**（gui / analyze / inapp_editor の一部 GUI/CI 不可到達コードを除く）

### Issues opened
- **#28** — 営業チラシ（A4 1 枚）作成、画像生成 AI 用プロンプト同梱
- **#29** — pywebview によるアプリ内編集 UI 統合（PR #30 で完了）
- **#47** — D&D 対応（tkinterdnd2、#35 follow-up）
- **#48** — 入力選択ボタン統一（複数 PDF or フォルダ 1 つ）
- **#49** — 解析後アプリ内プレビュー化
- **#50** — 内部用語の言い換え（groups.json → 分割設定、プロファイル → 用語集 等）

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

[Unreleased]: https://github.com/ShigetoshiMizuno/pdf-split-autorenamer/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/ShigetoshiMizuno/pdf-split-autorenamer/releases/tag/v0.4.0
[0.3.0]: https://github.com/ShigetoshiMizuno/pdf-split-autorenamer/releases/tag/v0.3.0
[0.2.0]: https://github.com/ShigetoshiMizuno/pdf-split-autorenamer/releases/tag/v0.2.0
