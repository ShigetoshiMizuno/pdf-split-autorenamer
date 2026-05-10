# pdf-split-autorenamer ロードマップ

最終更新: 2026-05-11

---

## フェーズ概要

| バージョン | 状態 | 説明 |
|-----------|------|------|
| v0.1.0 | リリース済み | コア機能（analyze/split/rename/gui）、教会書類プロファイル |
| v0.2.0 | 計画中 | OCR レイヤーなし PDF 対応（Tesseract）、外部プロファイル読み込み、実行ファイル配布 |
| v0.3.0 | 計画中 | プラガブル OCR 設計、段階的 OCR パイプライン |
| v1.0.0 | 計画中 | 安定リリース、テスト整備、PyPI 公開 |

---

## v0.1.0（リリース済み）

### 達成条件（達成済み）

- [x] `psar analyze / split / rename / gui` の 4 サブコマンドが動作する
- [x] report.html で境界を確認・調整できる
- [x] groups.json の旧/新スキーマ互換吸収
- [x] pdftotext + PyMuPDF の二重抽出による OCR テキスト取得
- [x] Windows 日本語パス問題の回避（`Document.write()` バイト経由）
- [x] cp1252 化けファイル名の復元（`fix_broken_unicode()`）
- [x] OCR 誤読修復（MOJIBAKE_FIX + 孤立 E 除去）
- [x] Tkinter GUI の 3 ステップ UI

---

## v0.2.0（次期リリース）

**テーマ**: 画像のみ PDF への対応 + 安定化

> レビュー指摘により、v0.1 のスコープが過大と判明したため、配布性関連（PyInstaller 自動ビルド）は v0.2.5 に切り出す。v0.2 ではテスト整備と既知のリスクの解消を優先する。

### マイルストーン

1. **既知の重大リスク対処**（最優先）
   - `fitz.open()` 入力側の Windows ANSI 問題（Issue #6）への対処
   - phash 不採用なら関連コード削除（Issue #7）
   - `_KEEP_CHARS` 未使用問題の解消（TODO T-04b）
   - `MOJIBAKE_FIX` の外部 TOML 化（TODO T-04）
   - `extract_kind` の OCR 化け候補列挙を `MOJIBAKE_FIX` 経由に統一

2. **Tesseract フォールバック実装**（Issue #3）
   - `pdfio.has_text_layer(pdf_path) -> bool` の追加
   - テキストレイヤーなしページに対して Tesseract でテキスト取得
   - CLI `--no-ocr-fallback` オプション
   - `tesseract` 自動検出（PATH + Windows 既知パス）
   - `jpn` traineddata 不在時の案内メッセージ

3. **外部プロファイル読み込み**（SPEC FR-3-6）
   - TOML を第一候補として実装
   - `--profile <path>` オプション
   - サンプル: `profiles/church.toml`、`profiles/business.toml`

4. **テスト整備の並走**（FR-7/FR-8 を担保するため）
   - `textops`（化け修復・日付・書類タイプ判定）のユニットテスト
   - `pdfio`（入出力・ROI クロップ）のユニットテスト
   - GitHub Actions に pytest ジョブ追加
   - 目標カバレッジ: コアモジュール 60%

5. **logging 移行**（FR-7）
   - `print` を `logging` に置換、`--verbose` / `--quiet` 追加

### 達成条件

- [x] Issue #6（PyMuPDF 入力側 ANSI）が修正され、CI で日本語パス + Windows のテストが通る
- [x] phash 関連コードが削除されているか、重複検出機能として実装されている
- [x] `has_text_layer()` が OCR なし PDF を正しく判定できる（テストケース: 全ページ画像、混在、全ページテキスト の3種）
- [x] Tesseract で日本語 PDF のテキスト抽出が機能する
- [x] `--no-ocr-fallback` で Tesseract を無効化できる
- [x] 外部プロファイル（TOML）を指定してカスタム書類タイプ判定ができる
- [x] `--verbose` / `--quiet` でログレベルが切り替わる
- [x] コアモジュールのテストカバレッジ 60%

## v0.2.5（実行ファイル配布）

**テーマ**: 配布性向上（v0.2 から切り出し）

### マイルストーン

- **スタンドアロン実行ファイルビルド**（Issue #2）
  - GitHub Actions `build-release.yml`（matrix: windows/macos/ubuntu）
  - PyInstaller ビルド
  - Poppler 同梱方針の決定（案 A: 同梱なしが推奨。Mac/Linux は OS 標準の Tesseract も任意）
  - Windows コードサイニング・macOS notarization は v1.0 以降
  - GitHub Releases への自動アップロード

### 達成条件

- [x] タグ push 時に 3 プラットフォームの実行ファイルが Releases に公開される（ワークフロー作成完了）
- [ ] 各プラットフォームの実行ファイルがダブルクリック起動で GUI を表示する（CI 実行待ち）

---

## v0.3.0

**テーマ**: 段階的 OCR パイプライン（Stage 2 + Stage 3）

### マイルストーン

1. **`OcrBackend` 抽象クラスの設計**（Issue #4）
   - `OcrBackend.extract_text(image_or_pdf_path) -> str`
   - `OcrBackend.extract_structured(image_or_pdf_path) -> dict` （LLM 向け）
   - v0.2 の `TesseractBackend` を昇格・リファクタリング

2. **Stage 2: ROI 限定 OCR**（Issue #5）
   - 上部 30% ROI クロップ + Tesseract での高速 OCR
   - クロップ比率を `--roi-ratio` で設定可能（既定 0.3）
   - OCR キャッシュ（`.psar/ocr_cache/`）

3. **Stage 3: Vision LLM フォールバック**（Issue #4, #5）
   - `ClaudeVisionBackend` / `GPT4VisionBackend`
   - 構造化抽出プロンプト（日付・タイトルを JSON で返す）
   - API キーの OS キーチェーン管理（`keyring` ライブラリ）
   - GUI に API キー入力欄と見積もりコスト表示
   - オプショナル extras: `pip install pdf-split-autorenamer[llm]`

4. **Stage 1〜4 フォールバック判定ロジック**（Issue #5）
   - 成功条件: 日付が取れた / タイトルが取れた
   - 化け率判定（日本語文字比率 < 閾値 → 失敗とみなす）
   - `--ocr-strategy {fast,balanced,thorough,llm}` プリセット
   - `.psar/config.toml` でプロジェクトごとに戦略を保存

### 達成条件

- [ ] `OcrBackend` 抽象クラスが定義され、`TesseractBackend` が動作する
- [ ] Stage 2 ROI OCR が Stage 1 失敗時に自動発動する
- [ ] LLM バックエンドが API キー設定済みの環境で動作する
- [ ] Stage 1 のみで動く既存環境で挙動が変わらない（既定の互換性）

### 関連 Issue

Issue #3, #4, #5

---

## v1.0.0

**テーマ**: 安定版リリース・品質保証

### マイルストーン

1. **品質保証**
   - ユニットテスト整備（textops / pdfio / analyze / split / rename）
   - CI でテスト自動実行（GitHub Actions）
   - カバレッジ 70% 以上

2. **ユーザビリティ向上**
   - エラーメッセージの日本語統一
   - `psar --version` の実装
   - 設定ファイル（`.psar/config.toml`）の完全サポート
   - README の「よくある質問」セクション

3. **配布**
   - PyPI への公式アップロード（`pip install pdf-split-autorenamer`）
   - Windows / macOS / Linux 実行ファイルの安定配布

### 達成条件

- [ ] `pip install pdf-split-autorenamer` でインストールして使えること
- [ ] 3 プラットフォーム実行ファイルが GitHub Releases で配布されていること
- [ ] ユニットテストカバレッジ 70% 以上
- [ ] README だけ読めばインストール〜基本操作まで完結すること
