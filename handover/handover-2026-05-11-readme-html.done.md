# HANDOVER - 2026-05-11 (README.html セッション)

## What We Were Doing (1-3文)

Issue #24「README.html ビジュアル版」を一気通貫で実装。
一般事務所向けの営業色を強めた1枚LP（`docs/index.html`）と、デモ素材一式（事務所書類10ページ混在PDF / SVG モックアップ3枚）を作成し、PR #27 として push 済み。
さらに営業チラシ作成 issue #28 を画像生成AI用プロンプト同梱で起票。

## Current State (最重要！)

- **Branch**: `feat/24-readme-html`（PR #27 として origin に push 済み・open）
- **Working / Functional**:
  - `docs/index.html` … Tailwind + Mermaid + Noto Sans JP の1枚LP。ローカルで表示確認済み
  - `scripts/generate_demo_pdf.py` … 事務所書類8種・10ページのPDFを生成（meiryo フォント自動探索）
  - `docs/demo/` … sample_office_scan.pdf (8.6MB) / sample_groups.json / sample_report.html
  - `docs/images/` … before-after / gui-main / report-preview の3 SVG（実物 CSS に寄せた再現）
  - `psar analyze` を生成 PDF にかけて 10ページ → 8グループの完全一致を確認済み
- **Broken / Incomplete / Untested**:
  - 実機 GUI スクリーンショット（差し替え候補だが当面はモックで運用）
  - GitHub Pages の有効化（リポジトリ設定変更のため監督権限必要）
  - チラシ実物（issue #28 として起票済み・画像生成AIへ依頼予定）
- **Build / Test / Run status**:
  - `python -m pytest -q` 685 tests passed（既存テストへの影響なし）
- **Recent commits**:
  - `9db83d0` docs: Issue #24 README.html 一般事務所向けビジュアル紹介ページを追加
  - `b371c2a` feat: Windows GUI ダブルクリック起動バッチ psar-gui.bat を追加 (#26)
  - `0823dc0` docs(handover): handover-2026-05-11-default (#25)

## Key Decisions & Rationale

- **ターゲットを「一般企業・事務所」に振り切った** → 監督指示。教会向けの旧モチーフは index.html / scripts / SVG すべてから排除。サンプル書類も請求書・見積書・議事録・稟議書・出張報告書・発注書・領収書・業務委託契約書の8種に変更
- **GUI / report のスクショは「モック」を選択し実物に寄せた** → 監督の「ユーザー混乱なきよう」指示を受け、HTML を実物に近づける方針を採用（実装側の改修よりリスク小）。実物 `report.html` の CSS（赤い上罫線・薄黄背景・cut/joinボタン色・220pxサムネ列）を SVG で再現
- **demo PDF をリポジトリに含める例外を `.gitignore` に追加** → `*.pdf` 除外ルールを `!docs/demo/*.pdf` で例外化。理由: GitHub Pages 経由でDL可能にするため。再生成可能（scripts/generate_demo_pdf.py）かつ個人情報なしなのでリスク無し
- **チラシは別 issue で外部画像生成AIに委譲** → 私（Claude Code）はラスタ画像生成不可。Midjourney/FLUX/Imagen/DALL-E向けの日本語+英語プロンプトを issue #28 に同梱
- **handover の `.done.md` リネームを本 PR に同梱** → 前回セッションで止まっていた整理を一括コミット
- **PyMuPDF `insert_text` の rotate は 0/90/180/270 のみ** → スキャン傾き演出は SVG 側でやる方針に変更（PDF生成は真っ直ぐ）

## Files Changed This Session (影響度順)

- `docs/index.html` (new) → 営業向け1枚LP本体（597行）
- `scripts/generate_demo_pdf.py` (new) → 事務所デモPDF生成
- `docs/demo/sample_office_scan.pdf` (new, 8.6MB) → 10p混在スキャン風PDF
- `docs/demo/sample_report.html` (new) → psar analyze 実行結果
- `docs/demo/sample_groups.json` (new) → 8グループ + 候補名サンプル
- `docs/images/before-after.svg` (new) → 1200x520 ヒーロー図
- `docs/images/gui-main.svg` (new) → 760x560 Tkinter風GUIモック
- `docs/images/report-preview.svg` (new) → 1100x720 report.html再現モック
- `README.md` (mod) → 冒頭にビジュアル版リンク追加
- `.gitignore` (mod) → `!docs/demo/*.pdf` 例外を追加
- `handover/*.md` → `.done.md` にリネーム整理

## Blockers, Gotchas & Workarounds

- **PyMuPDF `insert_text(rotate=...)` は整数 0/90/180/270 のみ受け付ける**
  - 小数の傾きを渡すと `ValueError: bad rotate value`
  - 回避: PDF生成時は rotate=0、スキャン傾き演出は SVG 側で実施
- **Windows ターミナルが cp932 で日本語パスを文字化け表示**
  - 動作には影響なし、コマンド実行・ファイル生成は正常
- **`docs/demo/sample_office_scan.pdf` が 8.6MB**
  - GitHub の警告（50MB）・ハード制限（100MB）には未到達だが大きめ
  - 将来 git LFS への移行 or Releases 添付に切り替え検討余地あり
- **handover の `.done.md` は `.gitignore` で除外される設計**
  - リネームすると git 上は単純な「削除」として記録される（意図通り）

## Key Learnings & Gotchas (長期記憶へ移行推奨)

- Tailwind CDN + Mermaid CDN + Google Fonts CDN だけで「素晴らしい」LP は組める。Static HTML 1ファイルで完結
- 画像生成 AI へのプロンプト同梱型 issue は、外部委託タスクとして再現性が高い（A/B/C の3パターンを用意）
- 実機スクショが取れない環境では「実物 CSS に忠実な SVG モック」が次善策。`bg-white` 背景＋実物カラーで「実画面に寄せた」印象を作れる

## Next Steps (優先度順・具体的！)

**High (今日〜明日)**
- PR #27 のレビュー → マージ判断（監督）
- マージ後、リポジトリ設定で GitHub Pages を `docs/` から有効化（監督権限）
- index.html を `https://shigetoshimizuno.github.io/pdf-split-autorenamer/` で公開動作確認
- Issue #28（チラシ）のプロンプトを Midjourney v6 等にかけてヒーロービジュアル生成

**Medium (今週)**
- T-11 PyPI アップロード（監督承認後）
- 実機 GUI スクリーンショットを撮って `docs/images/gui-main.png` に差し替え
- T-12 残件: `.psar/` → `psar_work/` ディレクトリ名変更の可否

**Low**
- Issue #2: Windows コードサイニング（v1.0）
- T-09: 実教会文書 PDF での計測値収集（教会用は v1.0 持ち越し or 別プロファイルに分離）
- index.html の英語版（i18n）

## Risks & Warnings

- 8.6MB の demo PDF が `git clone` を遅くする可能性。気になるなら git LFS への移行検討
- index.html はマーケティング表現を含む。法的リスク確認なし（電帳法対応の言及は「補助になる」と限定的に記述）
- Tailwind CDN を使っているため、オフライン環境では崩れる。完全オフライン配布する場合は Tailwind を pre-build する必要あり

## Context Gaps

- **CLEAR**: index.html / SVG / デモPDF / PR / Issue #28 起票
- **FUZZY**: 監督から見た「素晴らしい」レベルに達しているか（追加要望が出る可能性）
- **GAPS / UNKNOWNS**: GitHub Pages の URL（リポジトリ設定が変わるまで未確定）。チラシの最終デザインは画像生成AI次第

## Next Session Instructions

このHANDOVER.mdを最初に全文読み込み、状態・ブランチ・PR・Issue を完全に把握してから作業続行。

**最優先で確認すべきこと**:
1. PR #27 のレビュー状況（merged / open / changes_requested?）
2. Issue #28 の進捗（チラシ生成依頼が誰かに渡ったか）
3. GitHub Pages の有効化状況

矛盾・不明点は即監督に質問。secrets は絶対出力しない。
