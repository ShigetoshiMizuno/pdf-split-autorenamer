# HANDOVER - 2026-05-11 EOD（終業時統合）

## What We Were Doing (1-3文)

監督命令で「pdf-split-autorenamer の README.html 一新（一般事務所向け）」を朝から
17 時まで連続自律実行。途中、監督フィードバックで pywebview によるアプリ内編集 UI
（PR #30）も並行実装し、QA レビュー Top 5 まで反映。最後の実機テストでデモ PDF が
テキスト抽出できないバグ（generate_demo_pdf.py の制約）が顕在化、次セッション持ち越し。

## Current State (最重要！)

### Open PRs（4件）
| PR | ブランチ | 状態 | 概要 |
|---|---|---|---|
| **#27** | feat/24-readme-html | OPEN, mergeable, CI green | README.html + Step1 二段構成 + OG画像 |
| **#30** | feat/29-pywebview-inapp-editor | **DRAFT** | pywebview 内蔵 + UX 大幅改善（QA Top5反映済） |
| **#31** | chore/changelog-init | OPEN | CHANGELOG.md 新規 |
| **#33** | chore/flyer-draft | OPEN | 営業チラシ A4 試作 SVG/PNG |

### Open Issues（5件）
| # | タイトル |
|---|---|
| **#28** | 営業チラシ作成（プロンプト + 下絵 PR #33 同梱） |
| **#29** | pywebview 内蔵仕様（PR #30 で対応中） |
| **#32** | v0.4.0 リリース計画（マージ順序・チェックリスト） |
| **#24** | README.html ビジュアル版（PR #27 でクローズ予定） |
| **#2** | Windows コードサイニング（v1.0 持ち越し） |

### 動作状況
- main + PR #27/#30/#31 の統合（test/v0.4-integration ブランチ）で 699 tests passing
- PR #30 のアプリ内編集 UI: WebView 起動・文字化け修正（utf8atob）・自動誘導・文言一新まで完了
- **未解決**: デモ PDF が **テキスト抽出不可** で rename が「日付不明_」連発

## ⚠️ Critical Bug — デモ PDF 生成

### 問題
`scripts/generate_demo_pdf.py`（PR #27 同梱）が PyMuPDF + insert_text + 外部TTF（meiryo.ttc）で生成した PDF は、
`pdftotext` でも `PyMuPDF.get_text()` でも **空文字列**しか返らない（CID マッピングが不完全）。

→ analyze は境界推定だけは動くが、rename は本文から日付・タイプを抽出できず、全ファイルが「日付不明_」になる。

### 試した対応
- ReportLab + TTFont(subfontIndex=0): 同じく空 ❌
- ReportLab + UnicodeCIDFont('HeiseiKakuGo-W5'): PyMuPDF は何かを返すが mojibake ❌

### 推奨対応（次セッション）
1. **A**: pikepdf or pypdf で PDF 後処理（CID to Unicode CMap を後付け追加）
2. **B**: ReportLab で英数字のみのデモ PDF を作って動作実証 → 日本語版は別実装
3. **C**: 実物スキャン PDF（OCR 済み・PDF/A）を `tests/fixtures/demo/` に配置（容量大）
4. **D**: WeasyPrint（HTML→PDF）で日本語 fontface を埋め込み（一番太いが確実）

→ B が短期間で済む。デモは英数字＋日付ベース（"Invoice 2026-04-01" 等）で OK。
   日本語デモは別途、本物のスキャン PDF を使う方針。

### WIP commit
本セッションの `scripts/generate_demo_pdf.py` を ReportLab 版に書き換え済み（テキスト抽出はまだ NG）。
chore/handover-eod-2026-05-11 ブランチに WIP として残してある。

## Key Decisions（午後）

- **「ステップバイステップになっていない」フィードバック → Step1 一本化** を採用。
  「解析を実行」だけ残し、完了後ダイアログで「アプリ内編集ウィンドウを開きますか？」と自動誘導。
- **dry-run / プロファイル** は「詳細オプション」折りたたみへ移動（ボタン数 10→6）
- **「groups.json を保存」→「分割設定を保存」**等、QA レビューに沿って文言を全面改修
- **WebView ウィンドウタイトル** を「PDF 分割設定 — 編集」に
- **文字化け対策**: `atob()` を `TextDecoder('utf-8')` 経由の `utf8atob()` に置換
- **デモ PDF 問題**: 監督指示「ReportLab で作り直し（17時オーバー OK）」 → 実装したが根本解決せず

## Files Changed (午後分・PR #30 系統)

### feat/29-pywebview-inapp-editor（マージ済 → main は未反映）
- `src/pdf_split_autorenamer/inapp_editor.py` (new) — PsarBridge / open_editor / CLI
- `src/pdf_split_autorenamer/gui.py` — 「アプリ内で編集」自動誘導、UI 折りたたみ、文言改修
- `src/pdf_split_autorenamer/analyze.py` — saveJson 分岐 + utf8atob + 文言改修
- `pyproject.toml` — gui-inapp extras
- `tests/test_inapp_editor.py` (new, 13 tests) + `tests/test_gui_extra.py` (2 tests 追加)

### chore/handover-eod-2026-05-11（このブランチ）
- `handover/handover-2026-05-11-eod.md` (new) — このファイル
- `scripts/generate_demo_pdf.py` — ReportLab 版 WIP（次セッションで継続）

## Blockers, Gotchas & Workarounds

### NEW（本セッション発見）
- **PyMuPDF + insert_text + 外部TTF は表示OKでもテキスト抽出NG** → 上記 Critical Bug 参照
- **ReportLab + TTFont(subfontIndex) も同じ問題** → CID to Unicode CMap が入らない
- **ReportLab + UnicodeCIDFont('HeiseiKakuGo-W5') は mojibake** → ビューワー側 cp932 解釈
- **Tk と pywebview の GUI ループ衝突** → subprocess 別プロセス起動で回避（実装済）
- **JS atob() は Latin-1 解釈** → utf8atob() に置換済（PR #30）

### 既知（午前から継続）
- PyMuPDF `insert_text(rotate=...)` は整数 0/90/180/270 のみ受け付ける
- Windows ターミナルが cp932 で日本語パスを文字化け表示（動作影響なし）
- `docs/demo/sample_office_scan.pdf` 8.6MB（GitHub 警告未到達だが大きめ）

## Next Steps（優先度順）

### Critical（次セッション最初）
1. **デモ PDF 生成の根本対応**（上記 4 案から選択）
2. PR #30 の手動 E2E 再開（デモ PDF 解決後）

### High
3. PR #31 / #27 / #33 マージ判断
4. PR #30 を Draft → Ready → マージ
5. v0.4.0 タグ切り（Issue #32 のチェックリストに従う）

### Medium
6. GitHub Pages 有効化（リポジトリ設定変更）
7. Issue #28 のチラシ生成依頼（Midjourney v6 等）
8. T-11 PyPI アップロード（監督承認後）
9. T-12 `.psar/` → `psar_work/` 改名（影響範囲調査済み）

### Low
10. Issue #2: Windows コードサイニング（v1.0）
11. PyInstaller への pywebview 同梱（v1.0）
12. index.html の英語版（i18n）

## Test Status
- main: 685 passing
- feat/29 (PR #30): 699 passing（+13 新規 + 2 修正）
- 統合 (test/v0.4-integration): 699 passing
- カバレッジ 100% 維持

## Risks & Warnings
- **PR #30 の手動 E2E 未完了**（デモ PDF 問題で中断、Draft 維持）
- 文字化け修正（utf8atob）はテストではカバーできていない（JS 側のため）
- 実物スキャン PDF があれば本番フロー検証可

## Context Gaps
- **CLEAR**: PR の中身、文字化け修正、UI 改修、文言一新、QA レビュー結果、午後の経緯
- **FUZZY**: デモ PDF 問題の最良解（4 案のどれが最短）
- **GAPS**: 実物スキャン PDF が手元にないと完全な E2E 不可

## Next Session Instructions

このHANDOVER を全文読み込み、PR #27/#30/#31/#33 の状態と Issue #32 のチェックリストを把握してから作業続行。

**最優先**:
1. デモ PDF 生成のいずれかの解決策を選んで実装
2. 解決後、test/v0.4-integration ブランチで実機 E2E 再開
3. 監督に再テスト依頼
4. PR #30 を Ready for review に
5. Issue #32 のリリース計画に従って v0.4.0 タグ

矛盾・不明点は即監督に質問。secrets は絶対出力しない。
