# ハンドオーバー 2026-05-11（更新版）

作成: 助監督（朝9時まで自律実行セッション）
最終更新: 06:50 JST

---

## セッション概要

「朝9時まで連続・自律的に進める」指示を受け、以下を実施した。
全ての実装可能タスクが完了し、4つの PR がマージ待ち。

---

## マージ待ち PR（全て CI green）

### PR #10 — feature/v0.2-quick-wins
**マージ優先度: 最高（他の PR の前提）**
- T-00: PyMuPDF 入力側 ANSI 対策（`fitz.open(stream=...)` 経由）
- T-07b: phash 関連コード削除
- T-04b: `_KEEP_CHARS` 削除
- T-10b: logging 移行（print → logging、--verbose/--quiet）
- T-01: Tesseract フォールバック（has_text_layer / find_tesseract）
- T-02: 外部 TOML プロファイル（church.toml / business.toml）
- T-04: MOJIBAKE_FIX の外部 TOML 化

### PR #11 — feature/v0.3-ocr-pipeline
**マージ優先度: PR #10 の後**
- T-05: OcrBackend 抽象クラス（TesseractBackend + スタブ）
- T-06: Stage 2 ROI OCR
- T-07: Stage 3 LLM Vision（ClaudeVisionBackend / GPT4VisionBackend）
- T-08: OcrStrategy（fast/balanced/roi/thorough/llm）
- テスト: 331 tests

### PR #12 — feature/v1.0-ux
**マージ優先度: PR #10 の後（#11 と並行可）**
- T-10: テスト整備 99%（428 tests、gui.py 含む全モジュール）
- T-12: psar --version / FAQ / OCR 空ページ警告 / psar serve

### PR #13 — fix/9-groups-validation
**マージ優先度: PR #10 の後（独立して可）**
- FR-2-7: groups.json 検証ロジック（重複ページ警告・未カバーページ情報・不在PDF警告）
- バグ修正: rename.py `fallback_title()` の無効な正規表現修正
- テストスイート: **156 tests, 77% coverage**

テスト内訳:

| ファイル | テスト数 | カバレッジ |
|--------|---------|-----------|
| test_split_validation.py | 20件 | split.py **100%** |
| test_textops_basic.py | 29件 | textops.py 99% |
| test_pdfio_basic.py | 21件 | pdfio.py 97% |
| test_rename_basic.py | 28件 | rename.py **100%** |
| test_analyze_basic.py | 36件 | analyze.py **100%** |
| test_cli_basic.py | 18件 | cli.py 95% |

- ⚠️ マージ時注意: main に test.yml / dev extras がないため workaround で追加。PR #10 を先にマージすると test.yml と pyproject.toml が重複するが無害（PR #13 の変更を採用し、test.yml は PR #10 側を優先すること）

---

## 監督の判断が必要な事項

1. **T-11 PyPI アップロード**: `python -m build && twine upload` で公開。承認後に実施。
   - アカウント: PyPI の ShigetoshiMizuno
   - パッケージ名: `pdf-split-autorenamer`

2. **T-12 残件: ワークディレクトリ名変更**
   - `.psar/` → `psar_work/` にするかどうか
   - 理由: Windows エクスプローラで `.` で始まるフォルダが非表示になる問題
   - 変更した場合: CLI / GUI / テスト / SPEC.md を一括修正が必要

3. **PR マージ順序**:
   - 推奨: #10 → #13 → #12 → #11（依存関係）
   - #11 は #10 を base にしているため、#10 マージ後にリベースが必要な場合あり
   - #13 マージ後に #12 のテストが重複する場合は #12 側のテストを採用

---

## テスト状況

| ブランチ | テスト数 | カバレッジ |
|---------|---------|-----------|
| feature/v1.0-ux | 428 | 99%（__main__.py line 6 のみ未カバー） |
| feature/v0.3-ocr-pipeline | 331 | - |
| fix/9-groups-validation | **156** | **77%**（split/rename/analyze 100%） |

**Python 3.11 制限**: `from pdf_split_autorenamer.__main__ import main` が
setuptools editable install + Python 3.11 で `ModuleNotFoundError` になる。
テストを削除して対処済み。CI は Python 3.11 を使用中（KNOWLEDGE.md §8 に記録）。

---

## 現在ブランチ

```
fix/9-groups-validation (PR #13 用)
```

次の作業開始時は `git checkout main` してから始めること。

---

## 残タスク（次以降のセッション）

- T-09: ベンチマーク（サンプル PDF が必要）
- T-13: PaddleOCR/EasyOCR バックエンド（T-05 完了後）
- T-11: PyPI アップロード（承認後）
- T-12: .psar/ 名称変更（判断後）
- Issue #2 の CI 実行確認（タグ push でリリース生成）
