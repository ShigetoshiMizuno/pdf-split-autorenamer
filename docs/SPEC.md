# pdf-split-autorenamer 仕様書

バージョン: 0.2.0
最終更新: 2026-05-12

---

## プロダクト概要

ScanSnap 等で連続スキャンされた、複数書類が混在する PDF ファイル群を「書類グループごとに自動分割」し、「OCR テキストから日付と書類サマリー（カテゴリ・取引先・文書番号）を抽出して `YYYY-MM-DD_書類サマリー.pdf` 形式に自動リネーム」するツール。CUI（`psar` コマンド）と Tkinter GUI の両方を提供し、Python パッケージとして pip 配布する。

**ターゲットユーザ**: 紙書類を定期的にスキャン・整理する個人・小規模団体（教会、NPO、事業者等）。Python 環境を持つユーザおよびスタンドアロン実行ファイルのダウンロードユーザ。

---

## スコープ

### やること

- OCR テキストレイヤーが埋め込まれた PDF の分割・命名後処理
- ヒューリスティック境界判定（向き変化・テキスト類似度・タイトルマーカー）
- HTML レビューレポートによる人間による境界確認・調整
- groups.json を介した分割指示の受け渡し
- 日付・書類サマリー（カテゴリ・取引先・文書番号）の抽出と `YYYY-MM-DD_書類サマリー.pdf` 形式への命名
- カテゴリのプロファイルカスタマイズ
- CUI サブコマンド（`analyze` / `split` / `rename` / `gui`）と Tkinter GUI の提供
- Windows / macOS / Linux 対応

### やらないこと（現バージョン v0.1.0）

- OCR レイヤーを持たない画像のみ PDF の OCR 処理（Tesseract フォールバックは v0.2 以降、Issue #3）
- クラウド OCR / LLM Vision による高品質抽出（v0.3 以降、Issue #4, #5）
- PDF の内容編集・電子署名・フォーム処理
- フォルダ監視・自動バッチ実行
- Web UI・サーバサイド処理

---

## 機能要件

### FR-1: PDF 解析（analyze）

- **FR-1-1** `psar analyze <folder>` で指定フォルダ直下の PDF ファイルを対象に、ページ単位のメタデータ（PDF 名・ページ番号・サイズ・向き）、OCR テキスト（先頭200文字）、サムネイル（JPEG、長辺600px）を収集する。
  - 注: 8x8 平均ハッシュ（phash）は `pdfio` モジュールに残存しているが境界判定では使用しておらず、将来的に重複検出機能を実装するか、削除する（Issue #7）。
- **FR-1-2** OCR テキスト抽出は pdftotext（Poppler）を優先し、利用不可の場合は PyMuPDF にフォールバックする。pdftotext のパスは `PDFTOTEXT` 環境変数 → PATH 自動検出 → Windows 既知パスの順で解決する。
- **FR-1-3** 解析済みの分割出力ファイル（`<stem>_NN[_name].pdf` パターン）は解析対象から自動除外する。
- **FR-1-4** 隣接ページ間の「境界らしさ」スコア（0〜1.0）を以下のヒューリスティックで算出する：

| 条件 | スコア加算 |
|------|-----------|
| 向き変化（P↔L） | +0.7 |
| サイズ変化（5%超） | +0.4 |
| テキスト類似度（Jaccard bigram）< 0.05 | +0.4 |
| テキスト類似度 < 0.10 | +0.2 |
| 新タイトルマーカー出現 | +0.5 |
| 別 PDF ファイル | 1.0（固定） |

スコアは 1.0 でクリップする。閾値 0.5 以上を初期境界とみなす。

- **FR-1-5** 解析結果を `<folder>/.psar/` 以下に出力する（`--work-dir` で変更可）：
  - `thumbs/<pdf_stem>_p<NNN>.jpg`：ページサムネイル
  - `groups.json`：初期グループ定義（既存 groups.json がある場合は `groups.initial.json` にバックアップして groups.json は上書きしない）
  - `report.html`：レビュー UI
- **FR-1-6** report.html はサーバ不要の単一 HTML ファイルとし、ページサムネイル・OCR テキスト先頭・向き・スコア・理由を表示する。ユーザは「↑つなぐ」「↑切る」ボタンで境界を調整し、グループ先頭行で出力名を入力でき、「groups.json を保存」で修正済み groups.json をダウンロードできる。「初期境界に戻す」で初期状態に戻せる。

### FR-2: PDF 分割（split）

- **FR-2-1** `psar split <folder>` で `.psar/groups.json` に従い PDF を分割し、同フォルダに書き出す。
- **FR-2-2** 出力ファイル名は `<src_stem>_<NN>[_<name>].pdf`（NN: 2桁以上のゼロ埋め連番）。name は groups.json の `name` フィールドを `sanitize_filename()` で Windows 安全化したもの。
- **FR-2-3** `--dry-run` でファイル書き出しを行わず計画のみ表示する。
- **FR-2-4** 既存ファイルが存在する場合、`--force` がない限りスキップする。
- **FR-2-5** groups.json は旧スキーマ（`[from, to]` 配列）と新スキーマ（`{range: [from, to], name: ""}` オブジェクト）の両方を受け付ける（`normalize_groups()` で吸収）。
- **FR-2-6** PDF の書き出しは `fitz.Document.write()` のバイト経由で行い、日本語パスを安全に扱う。
- **FR-2-7** groups.json は次の規則で検証する：
  - キーが存在する PDF ファイル名であること（不在は警告ログのみで処理続行、対象スキップ）
  - `range[0] <= range[1]` かつ 1-based でページ範囲内であること（違反は警告ログ＋対象スキップ）
  - 同一 PDF 内のページが複数グループにまたがって重複定義されていないこと（重複検出時は警告）
  - 全ページがいずれかのグループに含まれていること（未カバーページは情報ログ）
- **FR-2-8** 同一 src_stem 配下で出力ファイル名が衝突する場合、name 部の差異により別名となる。`name` が同じ場合は連番 `_NN` で区別する（FR-3-7 と同じ規則）。

### FR-3: 自動リネーム（rename）

- **FR-3-1** `psar rename <folder>` で分割出力ファイル（`SPLIT_PAT = *.+_NN[_name].pdf`）を対象に内容ベースのリネームを行う。
- **FR-3-2** 対象モード：
  - `split`（既定）: 分割直後ファイル（SPLIT_PAT に一致、DATED_PAT と UNKNOWN_PAT を除く）
  - `unknown`: `日付不明_*.pdf` のみ
  - `all`: 上記両方
- **FR-3-3** 日付抽出は以下の形式に対応する：

| 形式 | 例 |
|------|---|
| `YYYY年MM月DD日` | 2026年4月6日 |
| `YYYY.MM.DD` | 2026.04.06 |
| `YYYY/MM/DD` | 2026/04/06 |
| `YYYY-MM-DD` | 2026-04-06 |

全角数字・全角ピリオド・中点・全角スラッシュ・全角ハイフンは正規化して抽出する。有効範囲: 2000年〜2100年、月1〜12、日1〜31。

- **FR-3-4** 日付の選択は「本文中の最頻出日付を優先し、ファイル名ヒント内の日付が候補中にあればそれを使う」ロジックによる。
- **FR-3-5** **カテゴリ判定**はタイトル領域（先頭6行）→ 本文の順で `DEFAULT_TITLE_PATTERNS` / `DEFAULT_BODY_PATTERNS` を適用する。OCR 誤読パターン（`MOJIBAKE_FIX`）適用後に判定する。
- **FR-3-6** **デフォルトプロファイルは業務書類向け**（請求書・見積書・議事録・契約書 等）。ユーザはプロファイルとして正規表現リストを定義してカスタマイズできる（TOML 形式）。教会書類は `profiles/church.toml` で利用可能（後方互換）。
- **FR-3-7** 出力ファイル名は `YYYY-MM-DD_書類サマリー.pdf`（日付不明の場合は `日付不明_書類サマリー.pdf`）。書類サマリーは `カテゴリ-取引先-文書番号` 形式で、取引先・文書番号は揃ったぶんだけハイフンで追加。同名重複時は `_01`, `_02` の連番サフィックスを付与する。
- **FR-3-8** **カテゴリ**が「書類」（デフォルト）のとき、ファイル名の名前部分を fallback タイトルとして使う（日付文字列と記号除去後）。
- **FR-3-9** `--apply` なし（既定）は dry-run。`--apply` を付けると実際にファイルをリネームする。
- **FR-3-10** ファイル名が cp1252/Latin-1 で化けている場合、`fix_broken_unicode()` で UTF-8 日本語文字列への復元を試みる。
- **FR-3-11 取引先抽出**: 文書先頭 10 行から「株式会社○○ 御中」「○○株式会社 様」「(株)○○」「○○ Inc.」等のパターンで取引先名を抽出する。抽出結果は半角空白を除去し、`sanitize_filename` で Windows 安全化後、20 文字でトリムする。
- **FR-3-12 文書番号抽出**: 文書全体から「No. XXX」「PO-XXX」「Q-XXX」「請求番号: XXX」「発注番号: XXX」等のパターンで文書番号を抽出する。最初のマッチを採用し、30 文字でトリムする。
- **FR-3-13 サマリー組み立て**: カテゴリ（必須）に、取引先・文書番号が揃ったぶんだけハイフンで連結する。最終的に `sanitize_filename` で 80 文字以内にクリップする。フォーマット例: `請求書-山田工業-2026-0401-001`（全要素）/ `請求書-山田工業`（文書番号なし）/ `請求書`（カテゴリのみ）。
- **FR-3-14 analyze 段階の候補名**: `psar analyze` は各グループの `name` フィールドにサマリー候補（`YYYY-MM-DD_書類サマリー`）を埋める。UI の input.value に事前入力された状態で表示され、ユーザは編集のみ行う。

### FR-4: OCR 文字化け修復

- **FR-4-1** `fix_mojibake()` でハードコードされた OCR 誤読文字（`MOJIBAKE_FIX` マップ）を置換する。現在のマッピング: 朁→月、拁→拝、紁→旨、迁→迎、曁→曜。
- **FR-4-2** 漢字直後の孤立した `E` 文字を除去する（ScanSnap OCR 特有のアーティファクト対応）。
- **FR-4-3** 置換不能文字（U+FFFD）を除去する。

### FR-5: GUI（Tkinter）

- **FR-5-1** `psar gui` または `psar gui --folder <path>` で Tkinter GUI を起動する。
- **FR-5-2** GUI は 3 ステップのフレームを持つ：Step 1（解析・HTMLレポート表示）、Step 2（分割 dry-run/実行 + --force オプション）、Step 3（リネーム dry-run/実行・モード選択）。
- **FR-5-3** 各操作はバックグラウンドスレッドで実行し、UI をブロックしない。操作結果はログエリア（スクロール可）とステータスバーに表示する。
- **FR-5-4** 解析完了後にブラウザで report.html を開くか確認ダイアログを表示する。
- **FR-5-5** 分割・リネームの実行前に確認ダイアログを表示する。

### FR-6: CLI 全般

- **FR-6-1** エントリポイント `psar` は `analyze` / `split` / `rename` / `gui` のサブコマンドを持つ。
- **FR-6-2** `--pdftotext <path>` オプション（analyze, rename）で pdftotext.exe のパスを明示指定できる。
- **FR-6-3** stdout / stderr を UTF-8 で出力する（Windows の cp932 デフォルトへの対策）。
- **FR-6-4** `--work-dir <path>` オプション（analyze, split）で作業ファイル格納先を変更できる。
- **FR-6-5** `psar rename` の対象モード切替は `--retarget-unknown` / `--all` で行うが、両者は相互排他とする。両方指定された場合は `--all` を優先する（`split` 既定 + unknown を含む）。v0.2 以降で `--mode {split,unknown,all}` への統一を検討する。

### FR-7: エラー処理・ロギング

- **FR-7-1** Python 標準 `logging` モジュールを採用し、`print` 直書きを置き換える（v0.2 着手時に実施）。
- **FR-7-2** ログレベルは `--verbose` (DEBUG)、既定 (INFO)、`--quiet` (WARNING) の 3 段階。
- **FR-7-3** エラー分類:
  - **致命**: コマンド処理を中止し非ゼロ終了コードを返す（例: groups.json が存在しない、入力フォルダが存在しない）
  - **警告**: 個別アイテムをスキップし処理続行（例: 単一PDFのオープン失敗、範囲外グループ）
  - **情報**: 進捗・統計（例: 処理ページ数、スキップ件数）
- **FR-7-4** GUI のログエリアと CLI 標準出力は同一の logging ハンドラを共有する。
- **FR-7-5** 致命エラー時に部分的に書き出されたファイルが残った場合は明示的にユーザに知らせる（ロールバックは行わない）。

### FR-8: 入力検証・冪等性

- **FR-8-1** `run_split` は冪等：同じ groups.json で再実行しても、既存の出力ファイルがある場合は `--force` がない限りスキップ。
- **FR-8-2** `run_rename` は冪等：既に正しい名前のファイルは noop（変更なし）。
- **FR-8-3** groups.json の検証は FR-2-7 の規則に従う。

---

## インターフェース定義

### CLI

```
psar analyze <folder> [--work-dir <dir>] [--pdftotext <path>] [--title <str>]
psar split   <folder> [--work-dir <dir>] [--dry-run] [--force]
psar rename  <folder> [--apply] [--retarget-unknown] [--all] [--pdftotext <path>]
psar gui     [--folder <path>]
```

### groups.json スキーマ

```json
{
  "<pdf_filename>": [
    { "range": [<from_page>, <to_page>], "name": "<optional_name>" }
  ]
}
```

ページ番号は 1-based。`name` は省略可（空文字でも可）。旧スキーマ `[from, to]` も受理する。

### Python パブリック API

```python
# analyze.py
def run_analyze(src_dir: Path, work_dir: Path | None = None,
                pdftotext_path: str | None = None,
                title: str = "PDF 分割レビュー") -> dict:
    # 戻り値: {"pages": int, "groups": int, "report_html": str, "groups_json": str}

# split.py
def run_split(src_dir: Path, work_dir: Path | None = None,
              dry_run: bool = False, force: bool = False) -> dict:
    # 戻り値: {"total_input_pages": int, "total_output_pages": int,
    #          "files_written": int, "files_skipped": int, "actions": list[dict]}

# rename.py
def run_rename(src_dir: Path, mode: str = "split", apply: bool = False,
               pdftotext_path: str | None = None,
               kind_default: str = "書類") -> dict:
    # 戻り値: {"targets": int, "actions": list[dict], "applied": int}

# textops.py（ユーティリティ）
def extract_dates_all(text: str) -> list[str]
def extract_kind(text, title_patterns, body_patterns, default_kind) -> str
def extract_vendor(text: str, max_len: int = 20) -> str | None
    # 文書先頭 10 行から取引先名を抽出。
    # 「株式会社○○ 御中」「○○株式会社 様」「(株)○○」「○○ Inc.」等のパターンで検出。
    # マッチなし → None。最大 max_len 文字でトリム。
def extract_doc_number(text: str, max_len: int = 30) -> str | None
    # 文書全体から文書番号を抽出（最初のマッチ）。
    # 「No. XXX」「PO-XXX」「請求番号: XXX」「Q-XXX」等のパターンで検出。
    # マッチなし → None。最大 max_len 文字でトリム。
def fix_mojibake(s: str) -> str
def fix_broken_unicode(s: str) -> str
def sanitize_filename(name: str, max_length: int = 80) -> str

# analyze.py（ユーティリティ）
def generate_candidate_names(
    pages: dict,
    groups: dict,
    *,
    profile_patterns: tuple[list, list] | None = None,
) -> dict:
    # 各グループの先頭ページ OCR テキストから書類サマリー候補名を生成し、
    # groups[pdf][i]["name"] に in-place で書き込む。
    # サマリー = カテゴリ（必須）+ "-" + 取引先（任意）+ "-" + 文書番号（任意）。
    # 戻り値は更新済みの groups dict。

# pdfio.py（ユーティリティ）
def extract_text(pdf_path: Path, page_no: int | None = None,
                 pdftotext: str | None = None) -> str
def save_pdf_pages(src_pdf: Path, from_page: int, to_page: int,
                   out_path: Path, garbage: int = 3, deflate: bool = True) -> int
def find_pdftotext() -> str | None
```

---

## 非機能要件

| 区分 | 要件 |
|------|------|
| **性能** | 56 ページ程度のスキャンPDF群を1分以内に解析（pdftotext 利用時） |
| **信頼性** | 元ファイル（連続スキャンPDF）は自動削除しない。dry-run を全変更系コマンドに用意 |
| **プライバシー** | 既定はオフライン処理のみ。クラウド/LLM 連携はオプトイン（v0.3+） |
| **OS互換** | Windows 10+ / macOS 12+ / Ubuntu 22.04+ で動作 |
| **依存最小化** | コア依存は PyMuPDF のみ。Poppler は任意推奨 |
| **国際化** | UI言語は日本語先行。英語化は v1.0 以降 |
| **ファイル名安全** | Windows 禁止文字をサニタイズ、80文字上限 |
| **ロギング** | Python 標準 `logging` 採用、`--verbose`/`--quiet` で粒度切替（FR-7） |
| **アクセシビリティ** | HTML レポートに `alt`/`aria-label` 付与、WCAG 2.1 AA を v1.0 で目指す |

## セキュリティ・プライバシー

- **`.psar/` の機密性**: `.psar/` 配下にはサムネ画像・OCR テキストが含まれ、元PDFと同等の機密性を持つ。リポジトリへ誤コミットしないよう `.gitignore` に登録すること（プロジェクトテンプレートに含む）。
- **ローカル処理優先**: 既定の処理（解析・分割・自動リネーム）はすべてローカルで完結する。ネットワーク送信なし。
- **クラウド OCR / LLM Vision (v0.3+)**:
  - 機能を有効化する際は明示的なオプトイン（チェックボックス＋初回送信時の同意ダイアログ）
  - API キーは OS のキーチェーン (`keyring` ライブラリ) に保管。環境変数 `PSAR_API_KEY` でも上書き可（CI 等での利用を想定）
  - ログ出力時は API キーをマスキング
  - クラウド送信時は対象ファイル名・送信予定枚数・想定コストを表示してユーザ確認を取る
- **一時ファイル**: pdftotext 経由で作成する一時ファイルは `tempfile.mkstemp` で生成し、処理完了/例外時に確実に削除する（v0.2 で `tempfile.TemporaryDirectory` への置換を推奨）。

---

## 制約・前提条件

- **Python**: 3.10 以上
- **必須依存**: PyMuPDF >= 1.23
- **任意依存**: Poppler（pdftotext）: OCR 品質向上。なくても動作する
- **OCR 前提（v0.1）**: テキストレイヤーが埋め込まれた PDF を前提とする。画像のみ PDF は非対応
- **OS**: Windows / macOS / Linux
- **PyMuPDF の日本語パス問題**: `Document.write()` のバイト経由書き出しで回避済み
- **OCR 文字化けマップ**: `MOJIBAKE_FIX` はハードコード。ユーザ定義拡張は v0.2 以降

---

## ユースケース

### UC-1: 業務書類の一括処理（主要ユースケース）

**状況**: ScanSnap S500 で 30 ページ（3 PDF）を連続スキャン。請求書・見積書・議事録などが混在している。

**操作手順**:
1. `psar analyze ./scanned_pdfs` → report.html を確認
2. ブラウザで境界を数箇所修正し groups.json をダウンロード・上書き
3. `psar split ./scanned_pdfs`
4. `psar rename ./scanned_pdfs --apply`

**期待結果**: 各グループが `2026-04-01_請求書-山田工業-2026-0401-001.pdf`、`2026-04-05_見積書-株式会社ABC.pdf` 等に命名される。

### UC-1b: 教会書類の一括処理（church.toml プロファイル使用）

**状況**: ScanSnap S500 で 56 ページ（5 PDF）を連続スキャン。教会の週報・メッセージ要旨・会計報告などが混在している。

**操作手順**:
1. `psar analyze ./scanned_pdfs` → report.html を確認
2. ブラウザで境界を数箇所修正し groups.json をダウンロード・上書き
3. `psar split ./scanned_pdfs`
4. `psar rename ./scanned_pdfs --profile profiles/church.toml --apply`

**期待結果**: 30 程度のグループが `2026-04-26_週報.pdf`、`2026-05-10_主日礼拝メッセージ要旨.pdf` 等に命名される。

### UC-2: 日付不明ファイルの再処理

**状況**: UC-1 後に `日付不明_書類.pdf` が複数残った。手動で内容を確認し、OCR ヒントから再度命名を試みたい。

**操作手順**:
1. `psar rename ./scanned_pdfs --retarget-unknown` で dry-run 確認
2. 納得できたら `psar rename ./scanned_pdfs --retarget-unknown --apply`

**期待結果**: 日付が取れたファイルが `YYYY-MM-DD_書類.pdf` にリネームされる。取れなかったものは変化なし。

### UC-3: GUI で非エンジニアが操作

**状況**: Python コマンドラインに不慣れなユーザがスタンドアロン exe を使う。

**操作手順**:
1. `psar gui` 起動 → フォルダ選択 → 「解析を実行」
2. ブラウザで report.html 確認・境界編集 → groups.json 保存
3. GUI で「分割 実行」→「リネーム 実行」

**期待結果**: CLI と同等の処理がボタン操作で完結する。

---

## 書類サマリー概念定義

ファイル名の `日付_` 以降全体を「書類サマリー」と呼ぶ。サマリーは以下の 3 要素で構成される。

| 用語 | 意味 | 例 |
|------|------|----|
| **書類サマリー** | ファイル名の `日付_` 以降全体 | `請求書-山田工業-2026-0401-001` |
| **カテゴリ** | サマリーの第 1 要素（書類種別、必須） | `請求書` |
| **取引先** | サマリーの第 2 要素（任意） | `山田工業` |
| **文書番号** | サマリーの第 3 要素（任意） | `2026-0401-001` |

### ファイル名フォーマット（追加方式）

| 揃った要素 | ファイル名例 |
|------------|-------------|
| 全部 | `2026-04-01_請求書-山田工業-2026-0401-001.pdf` |
| カテゴリ + 取引先 | `2026-04-01_請求書-山田工業.pdf` |
| カテゴリ + 文書番号 | `2026-04-01_請求書-2026-0401-001.pdf` |
| カテゴリのみ | `2026-04-01_請求書.pdf` |
| 全滅 | `日付不明_書類.pdf`（フォールバック） |

---

## 用語集

| 用語 | 定義 |
|------|------|
| グループ | 1 つの書類に相当するページ範囲 |
| 境界 | 連続する 2 ページ間の「ここで書類が切れる」判定点 |
| 向き | ページの Portrait（縦）/ Landscape（横） |
| phash | 8x8 平均ハッシュ。ページ画像の視覚的類似度指標。本ツールでは現状サムネ生成と将来用にのみ計算 |
| Jaccard bigram | テキストの 2-gram 集合の Jaccard 係数。テキスト類似度指標 |
| タイトルマーカー | 第N号・Vol.N・令和N年・YYYY年MM月等の正規表現にマッチする文字列 |
| SPLIT_PAT | `*.+_NN[_name].pdf` 形式（分割出力ファイルの識別パターン） |
| ORIG_PAT | `YYYY-MM-DD-HH-MM-SS.pdf` 形式（ScanSnap 元ファイルの識別パターン） |
| DATED_PAT | `YYYY-MM-DD_*.pdf` 形式（命名済みファイルの識別パターン） |
| work_dir | `.psar/` ディレクトリ（サムネ・JSON・HTMLレポート格納先） |
| dry-run | ファイル書き出し・リネームを行わず計画のみ表示するモード |
| MOJIBAKE_FIX | OCR 誤読文字の置換マップ |
