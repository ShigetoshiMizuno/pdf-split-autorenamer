# pdf-split-autorenamer 技術メモ・知見集

最終更新: 2026-05-11

本ドキュメントは開発中に判明した技術的知見・落とし穴・設計判断の根拠をまとめたものです。
コードの動作を変更する際は必ず本ドキュメントを参照し、矛盾しないか確認してください。

---

## 1. ScanSnap 埋め込み OCR の特徴と化けパターン

### 概要

ScanSnap（S500 等）はスキャン時に自前の OCR エンジンでテキストレイヤーを埋め込む。
このテキストレイヤーは精度が不安定であり、以下の化けパターンが頻出する。

### 化けパターン一覧

| 誤読文字 | 正解文字 | 出現箇所の例 | 備考 |
|----------|----------|--------------|------|
| `朁` | `月` | 「4朁6日」 | 月の異体字様の誤読 |
| `拁` | `拝` | 「礼拁」 | 礼拝の「拝」 |
| `紁` | `旨` | 「要紁」 | メッセージ要旨の「旨」 |
| `迁` | `迎` | 「歓迁」 | 歓迎の「迎」 |
| `曁` | `曜` | 「水曁日」 | 曜日の「曜」 |
| `歎` / `藪` / `裁` / `鐵` / `欽` | `歓` | 「歎迎」「藪迎」等 | 歓の異体字様誤読（T-04 で追加） |

### 孤立 E の問題

漢字の直後に半角 `E` が孤立して現れる場合がある（例: `礼拝E`、`要旨E`）。
これは ScanSnap OCR エンジン特有のアーティファクトとみられる。

修復コード（`textops.fix_mojibake()`）:
```python
s = re.sub(r"(?<=[一-鿿])E\b", "", s)
s = re.sub(r"(?<=[一-鿿])E(?=[^A-Za-z0-9])", "", s)
```

### 注意事項

- `MOJIBAKE_FIX` マップは ScanSnap S500 でのみ確認したパターン。機種・ファームウェアが異なると別の化けが生じる可能性がある
- 化け修復は「置換」なので、偶然その文字が正しく使われているケースには誤修復のリスクがある（実用上は問題ないと判断済み）
- 外部 TOML 対応は **T-04 で実装済み**。`profiles/scansnap-s500.toml` が標準の ScanSnap S500 用マップを提供しており、`fix_mojibake(s, extra_map=load_mojibake_map(path))` で追加マップを合成できる

---

## 2. PyMuPDF の Windows ANSI パス問題と回避策

### 問題の詳細

PyMuPDF 1.24 以前（および一部の 1.24 以降）では、`fitz.open(path)` で
Windows の「現在のコードページ（cp932 など）」でエンコードできない文字を含むパスを渡した場合、
内部で ANSI フォールバックが発生してファイルのオープンや書き出しが文字化けまたは失敗することがある。

具体的には `doc.save(path_str)` のようにパスを文字列で渡すとこの問題を踏む。

### 回避策（採用済み）

`pdfio.save_pdf_pages()` では以下のバイト経由の書き出しを採用している：

```python
data = new_doc.write(garbage=garbage, deflate=deflate)  # bytes を返す
out_path.write_bytes(data)  # pathlib.Path.write_bytes() は OS の ANSI 変換を経由しない
```

`pathlib.Path.write_bytes()` は Python が直接ファイルシステムに書き込むため、
PyMuPDF 内部の ANSI 変換を回避できる。

### 注意点

- `fitz.open()` の入力パス問題は **T-00 で解消済み**。`pdfio.py` / `analyze.py` / `split.py` 内のすべての `fitz.open()` を `fitz.open(stream=path.read_bytes(), filetype="pdf")` のバイト経由に統一した
- PyMuPDF のバージョンを上げる際は必ず Windows + 日本語パスで動作確認すること
- `pyproject.toml` で PyMuPDF バージョンを `>=1.23,<1.26` に固定済み（T-00 で実施）

---

## 3. 日本語ファイル名が cp1252 で化けるメカニズム

### 背景

Windows 日本語環境でアプリケーションがシステムデフォルトエンコーディングを使って
ファイル名を扱うと、UTF-8 で書かれたバイト列を cp1252（Windows Western European）として
誤解釈してしまう場合がある。

### 具体例

`牧師` (UTF-8: `E7 89 A7 E5 B8 AB`) が cp1252 で解釈されると `ç§å¸«` となる。

```python
# 化けの再現
"牧師".encode("utf-8").decode("cp1252")  # → 'ç§å¸«'
```

### 復元ロジック（`textops.fix_broken_unicode()`）

1. 入力文字列を cp1252 または Latin-1 としてバイト列にエンコードする
2. そのバイト列を UTF-8 としてデコードする
3. デコード後に日本語文字（U+3040〜U+9FFF）が含まれ、かつ元の文字列と異なれば復元成功

```python
for enc in ("cp1252", "latin-1"):
    b = s.encode(enc)
    recovered = b.decode("utf-8", errors="strict")
    if recovered != s and any(0x3040 <= ord(c) <= 0x9FFF for c in recovered):
        return recovered
```

### 適用箇所

`rename.py` の `existing_name_part()` と `run_rename()` の `src_display` 計算時。
分割直後のファイル名が化けていても、リネーム処理と表示で正しい文字列に復元される。

### 注意点

- この復元は「仮説ベース」の処理であり、すべての化けを正確に戻せるわけではない
- 部分的に化けている場合は `errors='replace'` で許容している
- ファイル名が化けた状態でも `src.rename(dst)` は OS レベルで行えるので、
  表示上の化け修復とファイル操作は独立している
- **誤判定リスク**: 復元の発動条件は「結果が日本語文字を含む」のみ。理論上、英語ファイル名の cp1252 バイト列を UTF-8 として誤解釈した結果、偶然日本語と判定されるケースが起こりうる（実用上は極稀）。逆に、復元すべきだが結果に日本語を含まない（記号のみなど）ケースは復元されない。
  - **v0.2 実装済み**: `_BROKEN_UNICODE_CHARS`（`ç, å, ï, Ã` など）が含まれる場合のみ復元を試みる事前チェックを追加。これにより英語ファイル名への誤適用を防止している。

---

## 4. pdftotext（Poppler）の `-enc UTF-8 -layout` 推奨理由

### なぜ PyMuPDF だけでは不十分か

`fitz.Page.get_text()` は PDF の内部文字列エンコーディングを解釈して Unicode を返すが、
ScanSnap 等が生成する PDF では以下の問題が生じることがある：

1. **ToUnicode テーブルが不完全**: 一部の文字が正しく Unicode に変換されない
2. **埋め込みフォントのグリフ → Unicode マッピングが欠落**: 文字化けの直接原因
3. **レイアウト情報の欠落**: 文字の読み順（左右・縦横）が崩れる

### pdftotext の優位点

`pdftotext -enc UTF-8 -layout` は Poppler の成熟した PDF テキスト抽出エンジンを使う：

- `-enc UTF-8`: 出力文字コードを明示的に UTF-8 指定（Windows のコードページに依存しない）
- `-layout`: ページレイアウトを保持した読み順でテキストを抽出する。これにより見出しが先頭行に来やすく、`extract_kind()` のタイトル領域判定精度が向上する

### 日本語パスの回避策

pdftotext は日本語ファイルパスを引数に渡すと失敗することがある（Windows）。
`pdfio.extract_text_pdftotext()` では ASCII 名の一時ファイルにコピーしてから渡している：

```python
fd, name = tempfile.mkstemp(suffix=".pdf")
shutil.copy2(pdf_path, tmp_path)  # ASCII パスの tmp にコピー
cmd = [pdftotext, "-enc", "UTF-8", "-layout", str(tmp_path), "-"]
```

### フォールバック順序

```
pdftotext（Poppler）
  → 利用不可 or 出力空 → PyMuPDF（fitz.Page.get_text()）
```

両方とも取得できない場合は空文字列を返す。境界判定はテキスト類似度以外の指標（向き・サイズ・タイトルマーカー）で行われるため、テキストなしでも完全には機能しなくなるわけではない。

---

## 5. ヒューリスティック境界判定における各指標の有効性

### 指標の一覧と根拠

#### 向き変化（+0.7）— 有効性: 高

縦書き（A4縦）と横書き（A4横）の書類が混在するスキャンでは、
書類の切れ目で向きが変化することが多い。
スコアが最も高く設定されているのはこの理由による。

ただし「縦長のカラー写真付き月報」と「同じ向きの週報」が連続している場合は向き変化が起きないため、
他の指標との組み合わせが必要。

#### テキスト類似度（Jaccard bigram）（+0.2〜+0.4）— 有効性: 中

2-gram の Jaccard 係数は計算コストが低く、同一書類内のページ（例: 2 ページ目以降も同じ語彙が頻出する）では高くなり、異なる書類間では低くなる傾向がある。

閾値 0.05 未満（+0.4）と 0.10 未満（+0.2）の 2 段階設定は、教会書類での実験から調整した値。

**制限**: テキストが非常に少ないページ（白紙、大きな写真のみ等）では bigram が空になり、`_jaccard` が 0.0 を返すため誤った境界を示すことがある。

#### タイトルマーカー出現（+0.5）— 有効性: 中〜高

```
TITLE_MARKER_RE = re.compile(
    r"(第\s*\d+\s*号|Vol\.?\s*\d+|令和\d+年|\d{4}年\s*\d{1,2}月|\d{1,2}月\s*\d{1,2}日)"
)
```

号数・巻数・年号・月日の出現は「新しい書類の冒頭」を強く示す。
教会の週報は「第 NNN 号」「令和 N 年 M 月」のような表記を持つことが多い。

#### 画像ハッシュ（phash）— 有効性: 低（連続スキャンでは使えない）→ **削除済み（T-07b）**

**`avg_phash()` および `hamming()` 関数は T-07b で `analyze.py` から削除された。**

削除の理由:
- 連続スキャンでは同一書類の複数ページも「別々の画像」であり、ハッシュ差が大きくなる
- 書類 A の最終ページと書類 B の先頭ページの間に特別なハッシュ類似度の変化は生じない
- 書類内でも図表のあるページとないページではハッシュ差が大きく、誤検知の原因になる
- `score_boundary()` では境界判定に使われておらず、計算コストのみが発生していた

サムネイル生成には引き続き PyMuPDF の `render_thumb()` を使っており、
HTML レポートで人間が目視確認するための表示用途（JPEG 保存）には影響なし。

### 境界スコアの調整

`boundary_threshold = 0.5` が現在の閾値。
書類のグループ数が多すぎる場合は閾値を上げ（0.6〜0.7）、
少なすぎる場合は下げる（0.3〜0.4）ことで調整できる。
閾値は `build_initial_groups()` の引数で変更できるが、現時点では CLI/GUI に公開していない。
将来の設定ファイル（`.psar/config.toml`）での設定を検討中（TODO T-08）。

---

## 6. その他の注意事項

### groups.json のスキーマ互換性

旧スキーマ（配列 `[from, to]`）と新スキーマ（オブジェクト `{range: [...], name: ""}`）の
両方を `normalize_groups()` で吸収している。
HTML レポートから保存される groups.json は常に新スキーマで出力される。
新スキーマに統一する移行が完了したら旧スキーマ対応は削除して構わないが、
外部ツールとの互換性のため現時点は維持する。

### 元ファイルの保持

`run_split()` は元の連続スキャン PDF を削除しない設計。
誤った分割の場合でも元ファイルから再実行できる。
これは意図的な設計判断であり、変更する場合は明示的な `--delete-original` オプションとして
ユーザの同意を得る形にすること。

### stdout のエンコーディング

Windows の PowerShell / コマンドプロンプトでは stdout のデフォルトエンコーディングが
cp932 になることがある。`cli.py` の冒頭で `sys.stdout.reconfigure(encoding="utf-8")` を
呼んでいるが、リダイレクト先（ファイル等）では効かない場合がある。
`PYTHONIOENCODING=utf-8` を環境変数に設定することを README に記載すること（TODO T-12）。

### `_KEEP_CHARS` 未使用問題 — **解消済み（T-04b）**

`textops.py` に `_KEEP_CHARS` 正規表現が定義されていたが、`sanitize_filename()` 内で
参照されておらず、実装途上の残骸だった。T-04b でこの未使用定義を削除した。
サニタイズは `_INVALID_NAME` による禁止文字除去のみで行われており、動作に変更なし。

---

## 8. テスト戦略・カバレッジ知見

### 達成状況（2026-05-11 時点）

- **429 テスト、全体 100%**（1052/1052 statements）
- feature/v1.0-ux ブランチ（PR #12）にて達成

### Tkinter GUI のテスト方法

`gui.py`（`App(tk.Tk)` サブクラス）を headless 環境でテストするために以下の戦略を使用：

1. **`App.__init__` をモック + 属性を手動注入**（`test_gui_profile.py` / `test_gui_extra.py`）
   ```python
   with patch.object(gui_module.App, "__init__", return_value=None):
       app = gui_module.App()
   app.__dict__.update({"folder_var": _StringVar(), ...})
   ```

2. **`ttk` / `tk` を MagicMock に置換して `_build_ui` を実行**
   - `patch.object(gui_module, "ttk", MagicMock())` でウィジェット生成を無害化
   - `logging.getLogger` もモックしてハンドラ登録を防ぐ

3. **`if __name__ == "__main__"` ガードの実行**（line 375）
   - `runpy.run_module("pdf_split_autorenamer.gui", run_name="__main__")` は fresh namespace を使うため `patch("gui.App")` が効かない
   - 解決策: `tkinter.Tk` / `tkinter.ttk.*` を直接パッチしてから `runpy.run_module` を呼ぶ

4. **`_run_async`（スレッド）のテスト**
   - `patch.object(app, "after", side_effect=lambda delay, fn, *a: fn(*a))` で `after()` を同期的に実行
   - `threading.Event` で非同期完了を待機（`event.wait(timeout=3)`）

### `importlib.reload` を使うモジュールレベルコードのカバレッジ

```python
# cli.py lines 13-14: stdout.reconfigure の例外握り潰し
import importlib
sys.stdout.reconfigure = lambda encoding: raise_exception()
importlib.reload(cli_mod)
# ← reload 後は必ず restore すること
```

### `runpy.run_module` で `if __name__ == "__main__"` をカバー

```python
with patch("sys.argv", ["psar", "analyze", str(tmp_path)]):
    with patch("pdf_split_autorenamer.analyze.run_analyze", return_value=mock_result):
        with pytest.raises(SystemExit):
            runpy.run_module("pdf_split_autorenamer.cli", run_name="__main__")
```

注意: 既存モジュールを再実行するため `RuntimeWarning` が出ることがある（無害）。

### 実質的に到達不可能な行

以下は実環境テストでは到達できないが、上記テクニックでカバー：
- `cli.py` lines 13-14: `sys.stdout.reconfigure` が失敗する環境（一部 IDLE / embedded Python）
- `textops.py` lines 10-14: Python < 3.11 の tomllib 代替インポートチェーン
- `gui.py` line 375: `if __name__ == "__main__"` ガード（直接スクリプト実行のみ）

### Python 3.11 editable install で `__main__` サブモジュールが見えない

`from pdf_split_autorenamer.__main__ import main` は Python 3.12 では動くが、
Python 3.11 + setuptools editable install 環境では
`ModuleNotFoundError: No module named 'pdf_split_autorenamer.__main__'` になる。

**原因**: Python 3.11 の setuptools editable finder が `__main__` を特殊名として除外している。

**対処**: テストを削除し、`__main__.py` line 6 (`raise SystemExit(main())`) の
1 statement は未カバーとして受け入れる（総カバレッジ 99%）。
CI を 3.12 に切り替えれば解消するが、3.11 サポートを続ける限りはこの制限が残る。
