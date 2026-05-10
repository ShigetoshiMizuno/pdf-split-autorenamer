# pdf-split-autorenamer タスク一覧

最終更新: 2026-05-11

凡例: `[Issue #N]` = 関連 Issue / `[担当]` = 実装予定者 / `[推定]` = 工数の目安 / `[依存]` = 前提タスク

「Issue なし」のタスクは内部タスク扱い（Issue 化不要）。GitHub に追跡を残すべき重要案件は Issue 化済み。

## 依存関係（簡易グラフ）

```
v0.2.0:
 T-00 (PyMuPDF 入力側) ──┐
 T-04b (_KEEP_CHARS)    ──┤
 T-07b (phash 削除)     ──┴→ T-01 (Tesseract) ── T-02 (TOML profile) ── T-04 (MOJIBAKE 外部化)
                                    │
                                    └─→ T-10a (textops/pdfio test 並走)
                                    └─→ T-10b (logging 移行)

v0.2.5:
 T-03 (PyInstaller CI) ※ v0.2 完了後

v0.3.0:
 T-05 (OcrBackend 抽象) ←── T-01 完了が前提
   ├─→ T-06 (Stage 2 ROI OCR)
   ├─→ T-07 (Stage 3 LLM Vision)
   └─→ T-08 (OcrStrategy)
 T-09 (ベンチマーク) ※ T-06/T-07 完了後

v1.0.0:
 T-10 (テスト整備、本格化) ── T-11 (PyPI) ── T-12 (UX細部)
 T-13 (PaddleOCR/EasyOCR) ※ T-05 完了後
```

---

## 短期（v0.2.0 に向けて）

### T-00: PyMuPDF 入力側 ANSI 対策
- [Issue #6] [担当: PRGちゃん] [推定: 0.5〜1日] [依存: なし]
- [x] `pdfio.extract_text_pymupdf` および `save_pdf_pages` で `fitz.open(pdf_path)` を直接呼び出している箇所を、`fitz.open(stream=path.read_bytes(), filetype="pdf")` 経由に変更
- [x] `analyze.py:collect_pages` の `fitz.open(pdf_path)` も同様に変更
- [x] `pyproject.toml` の PyMuPDF バージョンを `>=1.23,<1.26` に固定し、互換性問題に備える
- [x] CI（GitHub Actions windows-latest）で日本語パスを含むテストフィクスチャの動作確認
- [x] 移行後、KNOWLEDGE.md §2 を更新

### T-07b: phash 関連コード削除
- [Issue #7] [担当: PRGちゃん] [推定: 0.25日] [依存: なし]
- [x] `pdfio.avg_phash`, `pdfio.hamming` を削除
- [x] `analyze.py:collect_pages` の `ph = avg_phash(page)` および `pages` の `phash` フィールドを削除
- [x] `score_boundary` の reasons から phash 言及を削除
- [x] HTML レポートのテンプレートには影響しない（参照していない）
- [x] SPEC.md・KNOWLEDGE.md の phash 記述を「将来検討」から「削除済み（重複検出機能として再実装する場合は別 Issue）」に更新

### T-01: Tesseract フォールバック実装
- [Issue #3] [担当: PRGちゃん] [推定: 2〜3日]
- [x] `pdfio.has_text_layer(pdf_path: Path) -> bool` を追加
  - 各ページの `page.get_text().strip()` が空かどうかで判定
  - 全ページ空 → False、1ページでも有テキスト → True
- [x] `extract_text_tesseract(image: bytes, lang: str = "jpn") -> str` を `pdfio.py` に追加
  - `tesseract stdin stdout -l jpn --psm 3` をサブプロセス呼び出し
- [x] `find_tesseract() -> str | None` を追加（PATH + Windows 既知パス）
- [x] `extract_text()` に `ocr_fallback: bool = True` パラメータを追加
  - テキストレイヤーなしページのみ Tesseract を呼ぶ
- [x] CLI `psar analyze / rename` に `--no-ocr-fallback` オプション追加
- [x] `jpn` traineddata 不在時のエラーメッセージ（インストール URL 付き）
- [x] README に「OCR フォールバック」セクション追加

### T-02: 外部プロファイル読み込み（TOML）
- [Issue なし（SPEC FR-3-6）] [担当: PRGちゃん] [推定: 1日]
- [x] プロファイル TOML フォーマットの定義（title_patterns / body_patterns の正規表現リスト）
- [x] `textops.load_profile(path: Path) -> tuple[list, list]` を追加
- [x] `psar rename --profile <path>` オプション追加
- [ ] GUI にプロファイル選択欄追加（v1.0 持ち越し）
- [x] サンプルプロファイル（`profiles/church.toml`、`profiles/business.toml`）を同梱

### T-03: GitHub Actions 自動ビルド ※ v0.2.5（v0.2 完了後に着手）
- [Issue #2] [担当: PRGちゃん] [推定: 3〜5日] [依存: T-10a]
- [x] `.github/workflows/build-release.yml` 作成
  - トリガー: `push tags: ['v*']`
  - matrix: `windows-latest` / `macos-latest` / `ubuntu-latest`
- [x] PyInstaller ビルドコマンドの確定（既に `__main__.py` あり）
- [x] Poppler 同梱方針決定（案 A: 同梱なしが推奨）
- [x] `softprops/action-gh-release` で Releases に自動アップロード
- [x] README に「ダウンロード」セクション追加
- [ ] **検討事項**（v1.0 持ち越し）:
  - Windows コードサイニング（証明書要、年費用発生）
  - macOS notarization（Apple Developer 登録要）
  - jpn traineddata の同梱可否（Apache 2.0 ライセンス確認済み）

### T-04: MOJIBAKE_FIX の外部化（v0.2 必須）
- [Issue なし（SPEC FR-4）] [担当: PRGちゃん] [推定: 1日] [依存: T-02]
- [x] `MOJIBAKE_FIX` を外部 TOML（`profiles/scansnap-s500.toml` 等）に切り出す
- [x] `textops.load_mojibake_map(path)` を追加し、プロファイル経由で差し替え可能に
- [x] `extract_kind` 内の OCR 化け候補列挙（`歓迎|歎迎|藪迎|裁迎|...`）を、`fix_mojibake` 適用後に正字パターン（`歓迎` のみ）でマッチする方針に統一
- [x] 実装メモ: 現状 5 エントリのみ。ScanSnap S500 特有パターン。機種依存のため外部化は v0.2 必須

### T-04b: `_KEEP_CHARS` 未使用問題の解消
- [Issue なし] [担当: PRGちゃん] [推定: 0.25日] [依存: なし]
- [x] `textops.py` の `_KEEP_CHARS` 正規表現が定義のみで使われていない
- [x] 方針決定: 削除推奨（既存の `_INVALID_NAME` ベースのサニタイズで十分実用に足りているため）
- [x] 削除する場合、KNOWLEDGE.md §6 の「`_KEEP_CHARS` 未使用問題」セクションを「解消済み」に更新（解消済み）

### T-10a: テスト整備（v0.2 並走分）
- [Issue なし] [担当: QAちゃん/PRGちゃん] [推定: 1〜2日] [依存: T-00]
- [x] `tests/test_textops.py`: `fix_mojibake` / `fix_broken_unicode` / `extract_dates_all` / `extract_kind` / `sanitize_filename`
- [x] `tests/test_pdfio.py`: 最小サンプル PDF（自前生成）で `extract_text_pymupdf` / `save_pdf_pages` を検証
- [x] GitHub Actions に pytest ジョブ追加（windows / ubuntu）
- [x] 目標: コアモジュールカバレッジ 60%（T-10 で v1.0 までに 70% へ引き上げ）

### T-10b: logging 移行
- [Issue なし] [担当: PRGちゃん] [推定: 0.5日] [依存: なし]
- [x] `cli.py` / `analyze.py` / `split.py` / `rename.py` / `gui.py` の `print` を `logging` に置換
- [x] `--verbose` (DEBUG) / `--quiet` (WARNING) オプション追加
- [x] GUI のログエリアに `logging.Handler` を接続（CUI と同一フォーマット）
- [x] エラー分類（致命/警告/情報）を SPEC FR-7-3 に従って整理

---

## 中期（v0.3.0 に向けて）

### T-05: OcrBackend 抽象クラス設計
- [Issue #4] [担当: PRGちゃん] [推定: 1日]
- [x] `ocr_backend.py` を新設
- [x] `OcrBackend` 抽象基底クラス定義（`extract_text`, `extract_structured`）
- [x] `TesseractBackend` を T-01 実装から昇格・リファクタリング
- [x] `PaddleOCRBackend` のスタブ（オプショナル extras）
- [x] `AzureReadBackend` / `GoogleVisionBackend` のスタブ（オプショナル extras）

### T-06: Stage 2 ROI 限定 OCR 実装
- [Issue #5] [担当: PRGちゃん] [推定: 1〜2日]
- [x] `pdfio.crop_page_pixmap(page, ratio: float = 0.3) -> bytes` を追加
- [x] `analyze.py` の `collect_pages()` に `ocr_strategy` パラメータを追加
- [x] Stage 1 失敗時（テキスト空 or 化け率高い）に Stage 2 を自動発動
- [x] 化け率判定: 日本語文字（U+3040〜U+9FFF）の比率 < 閾値（既定 0.1）を「失敗」とみなす
- [x] OCR キャッシュ（`.psar/ocr_cache/<hash>.txt`）実装

### T-07: Stage 3 LLM Vision バックエンド
- [Issue #4, #5] [担当: PRGちゃん] [推定: 2〜3日]
- [x] `ClaudeVisionBackend` / `GPT4VisionBackend` の実装（ClaudeVisionBackend 実装・GPT4 はスタブ）
- [x] 構造化抽出プロンプト（`{"date": "YYYY-MM-DD", "title": "..."}`）
- [x] JSON Schema 検証（validate_structured_output）
- [x] `keyring` ライブラリによる API キー管理（get_api_key）
- [ ] GUI に API キー入力欄・見積もりコスト表示・確認ダイアログ（v1.0 持ち越し）
- [x] `pyproject.toml` に `[project.optional-dependencies] llm = [...]` 追加
- [x] プライバシー警告: クラウド送信の明示的オプトインのみで発動

### T-08: フォールバック判定ロジックと戦略設定
- [Issue #5] [担当: PRGちゃん] [推定: 1日]
- [x] `OcrStrategy` クラスの定義（Stage 1〜4 を順次試す）
- [x] CLI `--ocr-strategy {fast,balanced,thorough,llm}` オプション追加
- [x] `.psar/config.toml` 読み込み実装（load_psar_config で実装）

### T-09: ベンチマーク
- [Issue #4, #5] [担当: SPECちゃん/PRGちゃん] [推定: 1〜2日]
- [ ] サンプル PDF セット（印字日本語・手書き・縦書き・表・カラー・白黒）を整備
- [ ] Stage 1/2/3/4 の精度・速度・コスト比較表を `docs/benchmark.md` に公開

---

## 長期（v1.0.0 および維持）

### T-10: テストスイート整備
- [Issue なし] [担当: QAちゃん/PRGちゃん] [推定: 3〜5日]
- [x] `tests/` ディレクトリ作成
- [x] `test_textops.py`: `fix_mojibake`, `fix_broken_unicode`, `extract_dates_all`, `extract_kind`, `sanitize_filename`
- [x] `test_pdfio.py`: `extract_text`, `save_pdf_pages`（最小サンプル PDF 使用）
- [x] `test_analyze.py`: `score_boundary`, `build_initial_groups`
- [x] `test_split.py`: `normalize_groups`, `run_split`（dry-run は実PDF不要な normalize_groups のみ）
- [x] `test_rename.py`: `choose_date`, `resolve_filenames`, `run_rename`（dry-run）
- [x] GitHub Actions に pytest ジョブを追加（test.yml）
- [x] カバレッジ目標: 70% → **100% 達成**（全モジュール 100%、gui.py 含む）
  - 429 テスト（feature/v1.0-ux ブランチ時点）
  - gui.py: Tkinter を全モック化した test_gui_extra.py で 100% カバー

### T-11: PyPI 公開
- [Issue なし] [担当: PRGちゃん] [推定: 0.5日]
- [x] `pyproject.toml` の classifiers を `Development Status :: 4 - Beta` 以降に更新
- [ ] `python -m build` + `twine upload` で PyPI アップロード（監督の承認後に実施）
- [x] README バッジ（PyPI バージョン・ライセンス）追加

### T-12: ユーザビリティ細部
- [Issue #8] [担当: PRGちゃん] [推定: 1〜2日]
- [x] `psar --version` の実装（`importlib.metadata.version()` 使用）
- [x] エラーメッセージの日本語統一・改善（cli.py / split.py / analyze.py / rename.py のエラー・警告メッセージを日本語化）
- [x] README「よくある質問」セクション追加
- [x] `report.html` に「OCR テキストが空のページ」の視覚的警告追加
- [x] HTML レポートでの境界編集 → groups.json ダウンロードフローの改善（`psar serve` でローカルHTTP立ち上げ + 直接保存を実装済み。`http://` モードで `/api/save-groups` に POST して直接書き込み）
- [ ] ワークディレクトリ名を `.psar/` から `psar_work/` に変更検討（hidden だと Windows エクスプローラで見えない問題）
- [x] GUI の確認ダイアログに dry-run 結果サマリ表示
- [x] GUI の進捗ログをワーカースレッドから逐次表示（_TextHandler で実装済み）

### T-13: PaddleOCR / EasyOCR バックエンド
- [Issue #4] [担当: PRGちゃん] [推定: 2〜3日]
- [ ] T-05 完了後の発展
- [ ] `pip install pdf-split-autorenamer[paddle]` の extras 設定
- [ ] モデルダウンロードの初回確認ダイアログ（GUI）
- [ ] ベンチマーク T-09 に結果追加
