# -*- coding: utf-8 -*-
"""Tkinter GUI

2ステップを画面上のボタンで進めるシンプルなUI。
- フォルダ選択
- [解析] → サムネ・HTMLレポート生成 → ブラウザで自動オープン
- [分割 dry-run] / [分割 実行] → 分割設定から分割（命名は編集ウィンドウで決定）

issue #40: かつての Step 3 「自動リネーム」は Step 2 分割に取り込まれた。
CLI の `psar rename` は引き続き利用可能。
"""
from __future__ import annotations

import logging
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import analyze as _analyze
from . import inapp_editor as _inapp
from . import split as _split

try:
    import tkinterdnd2
    _BaseApp = tkinterdnd2.TkinterDnD.Tk
    _DND_AVAILABLE = True
except ImportError:
    _BaseApp = tk.Tk
    _DND_AVAILABLE = False


class _TextHandler(logging.Handler):
    """logging のメッセージを Tkinter の Text ウィジェットに転送するハンドラ"""

    def __init__(self, text_widget):
        super().__init__()
        self._widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self._widget.after(0, self._append, msg)

    def _append(self, msg):
        self._widget.insert("end", msg + "\n")
        self._widget.see("end")


class App(_BaseApp):
    def __init__(self, initial_folder: str | None = None):
        super().__init__()
        self.title("pdf-split-autorenamer")
        self.geometry("760x560")
        self.minsize(640, 480)

        self.folder_var = tk.StringVar(value=initial_folder or "")
        self.profile_var = tk.StringVar(value="")
        self.force_var = tk.BooleanVar(value=False)
        # issue #48: 実際の入力パスリスト（複数 PDF 選択時に使用）
        self._input_paths: list[Path] = []

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="PDFフォルダ／ファイル:").pack(side="left")
        ent = ttk.Entry(top, textvariable=self.folder_var)
        ent.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self._register_dnd(ent)
        # issue #48: 2 ボタンを Menubutton（ドロップダウン）に統合
        browse_menu = tk.Menu(self, tearoff=False)
        browse_menu.add_command(label="PDF を選ぶ（複数選択可）…",
                                command=self._on_browse_files)
        browse_menu.add_command(label="フォルダを選ぶ…",
                                command=self._on_browse)
        browse_btn = ttk.Menubutton(top, text="参照… ▼", menu=browse_menu)
        browse_btn.pack(side="left")

        # 用語集（任意）: issue #50
        profile_row = ttk.Frame(self, padding=(8, 0, 8, 4))
        profile_row.pack(fill="x")
        ttk.Label(profile_row, text="用語集（任意）:").pack(side="left")
        ttk.Entry(profile_row, textvariable=self.profile_var).pack(
            side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(profile_row, text="参照…",
                   command=self._on_browse_profile).pack(side="left")

        # 操作パネル: 2つのフレームを並べる
        body = ttk.Frame(self, padding=8)
        body.pack(fill="x")

        # Step 1: 解析（解析を実行 → 完了したら自動でアプリ内編集ウィンドウへ）
        f1 = ttk.LabelFrame(body, text="1. 解析（PDFを読み込み、書類の境界を提案）", padding=8)
        f1.pack(fill="x", **pad)
        ttk.Button(f1, text="解析を実行", command=self._on_analyze).pack(side="left")
        ttk.Label(f1,
                  text="押すと内容を読み取り、続けて編集ウィンドウが開きます").pack(
            side="left", padx=12)

        # Step 2: 分割（編集ウィンドウで決めた候補名でそのまま書き出す）
        f2 = ttk.LabelFrame(body, text="2. 分割（編集した内容に従って書類ごとに切り出し）", padding=8)
        f2.pack(fill="x", **pad)
        ttk.Button(f2, text="実行", command=lambda: self._on_split(True)).pack(side="left")
        ttk.Checkbutton(f2, text="既存ファイルを上書きする",
                        variable=self.force_var).pack(side="left", padx=12)
        # 詳細オプション（折りたたみ）
        self._split_advanced_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f2, text="詳細オプション", variable=self._split_advanced_var,
                        command=self._toggle_split_advanced).pack(side="right")
        self._split_advanced_frame = ttk.Frame(body)  # 折りたたみコンテンツ
        ttk.Button(self._split_advanced_frame, text="変更内容を確認するだけ（実行しない）",
                   command=lambda: self._on_split(False)).pack(side="left", padx=8)

        # ログエリア
        log_frame = ttk.LabelFrame(self, text="ログ", padding=4)
        log_frame.pack(fill="both", expand=True, padx=8, pady=4)
        self.log = tk.Text(log_frame, wrap="word", height=15, font=("Consolas", 10))
        sb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        # logging ハンドラをログエリアに接続
        handler = _TextHandler(self.log)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logging.getLogger().addHandler(handler)

        # ステータスバー
        self.status_var = tk.StringVar(value="待機中")
        ttk.Label(self, textvariable=self.status_var, relief="sunken",
                  anchor="w", padding=4).pack(fill="x", side="bottom")

    # ----- D&D -----
    def _register_dnd(self, widget) -> None:
        """issue #47: ウィジェットを D&D ドロップターゲットとして登録する。

        _DND_AVAILABLE=False（tkinterdnd2 未インストール）の場合は何もしない。
        """
        if not _DND_AVAILABLE:
            return
        widget.drop_target_register("DND_Files")
        widget.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event) -> None:
        """issue #47: D&D ドロップイベントを処理して _input_paths と folder_var を更新する。

        event.data の形式（tkinterdnd2）:
          - 単一: C:/path/to/file.pdf
          - 複数またはスペース含み: {C:/path with space.pdf} {C:/another.pdf}

        self.tk.splitlist を使ってパースする（tk 組み込み機能で堅牢）。
        """
        raw = event.data
        paths = [Path(p) for p in self.tk.splitlist(raw) if p]

        if not paths:
            return

        if len(paths) == 1:
            p = paths[0]
            # PDF 以外の単一ファイル: エラーを表示して状態変更なし
            if p.is_file() and p.suffix.lower() != ".pdf":
                messagebox.showerror(
                    "エラー",
                    f"PDF ファイルまたはフォルダをドロップしてください: {p.name}"
                )
                return
            # 単一 PDF またはフォルダ
            self._input_paths = [p]
            self.folder_var.set(str(p))
        else:
            # 複数パス（PDF・フォルダ混在も含む、B 案警告に委ねる）
            self._input_paths = paths
            first = paths[0].name
            self.folder_var.set(f"({len(paths)} ファイル) {first} 他 {len(paths) - 1} 件")

    # ----- イベント -----
    def _on_browse(self) -> None:
        """フォルダを選択する。issue #48: _input_paths も更新する。"""
        d = filedialog.askdirectory(title="PDFフォルダを選択",
                                    initialdir=self.folder_var.get() or ".")
        if d:
            self.folder_var.set(d)
            self._input_paths = [Path(d)]

    def _on_browse_files(self) -> None:
        """issue #48: PDF ファイルを複数選択する。"""
        initial = self.folder_var.get() or "."
        if Path(initial).is_file():
            initial = str(Path(initial).parent)
        elif Path(initial).is_dir():
            pass
        else:
            initial = "."
        paths = filedialog.askopenfilenames(
            title="PDF ファイルを選択（複数選択可）",
            initialdir=initial,
            filetypes=[("PDF ファイル", "*.pdf"), ("すべてのファイル", "*.*")],
        )
        if not paths:
            return
        pdf_paths = [Path(p) for p in paths]
        self._input_paths = pdf_paths
        if len(pdf_paths) == 1:
            self.folder_var.set(str(pdf_paths[0]))
        else:
            first = pdf_paths[0].name
            self.folder_var.set(f"({len(pdf_paths)} ファイル) {first} 他 {len(pdf_paths) - 1} 件")

    def _on_browse_file(self) -> None:
        """後方互換のため残す。issue #35 の単一 PDF 選択（内部的には _on_browse_files を呼ぶ）。"""
        self._on_browse_files()

    def _on_browse_profile(self) -> None:
        """issue #50: 用語集 TOML ファイルを選択する。"""
        p = filedialog.askopenfilename(
            title="用語集 TOML ファイルを選択",
            filetypes=[("TOML ファイル", "*.toml"), ("すべてのファイル", "*.*")],
        )
        if p:
            self.profile_var.set(p)

    def _get_folder(self) -> Path | None:
        """入力パスを返す。フォルダまたは PDF ファイル (issue #35)。

        後方互換のため維持。新規コードは _get_inputs() を使うこと。
        """
        result = self._get_inputs()
        if result is None:
            return None
        if isinstance(result, list):
            # 複数 PDF の場合は最初の PDF の親ディレクトリを返す（_get_folder の契約を守る）
            return result[0]
        return result

    def _get_inputs(self) -> Path | list[Path] | None:
        """issue #48: 入力を返す。

        - フォルダ: Path（ディレクトリ）
        - 単一 PDF: Path（ファイル）
        - 複数 PDF: list[Path]
        - 未選択: None（警告ダイアログ表示）
        """
        # _input_paths が設定されていれば優先
        if self._input_paths:
            if len(self._input_paths) == 1:
                p = self._input_paths[0]
                if p.is_dir():
                    return p
                if p.is_file() and p.suffix.lower() == ".pdf":
                    return p
                # issue #58: 単一だが無効（削除済み等）→ silent fallthrough を回避
                messagebox.showerror(
                    "エラー", f"選択されたパスが見つかりません: {p}"
                )
                return None
            # 複数: 有効な PDF とディレクトリに分けてチェック
            valid = [
                p for p in self._input_paths
                if p.is_file() and p.suffix.lower() == ".pdf"
            ]
            dirs = [p for p in self._input_paths if p.is_dir()]
            if not valid:
                # issue #58: 全て無効 → silent fallthrough を回避
                messagebox.showerror(
                    "エラー", "選択された PDF ファイルが見つかりません。"
                )
                return None
            # issue #63: ディレクトリと PDF が混在 → 確認ダイアログ（B 案）
            if dirs:
                ok = messagebox.askokcancel(
                    "警告",
                    f"ディレクトリ {len(dirs)} 件が含まれています。\n"
                    "ディレクトリを除外して PDF のみ処理しますか？",
                )
                if not ok:
                    return None
            return valid

        # フォールバック: folder_var の文字列から判断
        v = self.folder_var.get().strip()
        if not v:
            messagebox.showwarning(
                "警告", "PDFフォルダまたは PDF ファイルを選択してください。"
            )
            return None
        p = Path(v)
        if p.is_dir():
            return p
        if p.is_file() and p.suffix.lower() == ".pdf":
            return p
        messagebox.showerror(
            "エラー", f"フォルダまたは PDF ファイルが存在しません: {p}"
        )
        return None

    def _log(self, msg: str) -> None:
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.update_idletasks()

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)
        self.update_idletasks()

    def _run_async(self, target, on_done=None) -> None:
        def worker():
            try:
                result = target()
            except Exception as e:
                self.after(0, self._log, f"ERROR: {e}")
                self.after(0, self._set_status, "エラー")
                return
            if on_done:
                self.after(0, lambda: on_done(result))
        threading.Thread(target=worker, daemon=True).start()

    # ----- サマリ組み立て -----
    @staticmethod
    def _build_split_summary(res: dict) -> str:
        actions = res.get("actions", [])
        files_written = res.get("files_written", 0)
        total_output_pages = res.get("total_output_pages", 0)
        lines = [f"書き出し予定: {files_written} ファイル / {total_output_pages} ページ", ""]
        limit = 10
        for a in actions[:limit]:
            st = a.get("status", "")
            out = a.get("out", a.get("src", ""))
            rng = a.get("range", "?")
            lines.append(f"  [{st}] {out}  pages {rng}")
        if len(actions) > limit:
            lines.append(f"  … 他 {len(actions) - limit} 件")
        lines.append("")
        lines.append("実行してよろしいですか？")
        return "\n".join(lines)

    # ----- 詳細オプション折りたたみ -----
    def _toggle_split_advanced(self) -> None:
        if self._split_advanced_var.get():
            self._split_advanced_frame.pack(fill="x", padx=8, pady=(0, 4),
                                            after=self._split_advanced_frame.master.winfo_children()[1])
        else:
            self._split_advanced_frame.pack_forget()

    # ----- アクション -----
    def _on_analyze(self) -> None:
        inputs = self._get_inputs()
        if not inputs:
            return
        label = str(inputs) if not isinstance(inputs, list) else f"{len(inputs)} ファイル"
        self._log(f"=== 解析開始: {label} ===")
        self._set_status("解析中…")

        def do():
            # issue #50: profile_var に TOML パスが入っていれば run_analyze に渡す
            profile_str = self.profile_var.get().strip()
            profile = Path(profile_str) if profile_str else None
            return _analyze.run_analyze(inputs, profile=profile)

        def done(res):
            pages = res.get("pages", 0)
            groups = res.get("groups", 0)
            html = res.get("report_html")
            self._log(f"  ページ数: {pages}")
            self._log(f"  初期グループ数: {groups}")
            self._set_status("解析完了")

            if pages == 0:
                messagebox.showwarning(
                    "解析完了",
                    "PDF からテキストを取得できませんでした。\n"
                    "OCR バックエンドの設定または PDF 内容をご確認ください。"
                )
                return
            if groups == 0:
                messagebox.showwarning(
                    "解析完了",
                    "書類グループを提案できませんでした。\n"
                    "用語集の設定をご確認ください。"
                )
                return
            if not html:
                messagebox.showwarning(
                    "解析完了",
                    "レポートが生成されませんでした。\n"
                    "ログを確認してください。"
                )
                return

            self._log(f"  レポート: {html}")
            # issue #37: 確認ダイアログなしで自動遷移。pywebview があればアプリ内、無ければブラウザ。
            if _inapp.is_available():
                self._on_inapp_edit()
            else:
                webbrowser.open(Path(html).as_uri())

        self._run_async(do, done)

    def _on_open_report(self) -> None:
        inputs = self._get_inputs()
        if not inputs:
            return
        # フォルダまたは先頭 PDF の親ディレクトリを使う
        folder = inputs if isinstance(inputs, Path) and inputs.is_dir() else (
            inputs[0].parent if isinstance(inputs, list) else inputs.parent
        )
        html = folder / ".psar" / "report.html"
        if not html.exists():
            messagebox.showwarning("警告", f"レポートが未生成です。先に「解析を実行」を押してください。\n{html}")
            return
        webbrowser.open(html.as_uri())

    def _on_inapp_edit(self) -> None:
        """pywebview を別プロセスで起動してアプリ内編集 UI を表示する。

        Tk のメインループと pywebview の GUI ループが衝突するのを避けるため、
        別プロセスで `python -m pdf_split_autorenamer.inapp_editor <work_dir>` を呼ぶ。
        """
        if not _inapp.is_available():
            messagebox.showwarning(
                "編集ウィンドウを開けません",
                "アプリ内編集には pywebview のインストールが必要です。\n\n"
                "  pip install 'pdf-split-autorenamer[gui-inapp]'\n\n"
                "を実行してからアプリを再起動してください。"
            )
            return

        inputs = self._get_inputs()
        if not inputs:
            return
        # work_dir: フォルダ/.psar または PDF の親/.psar
        if isinstance(inputs, list):
            folder = inputs[0].parent
        elif inputs.is_dir():
            folder = inputs
        else:
            folder = inputs.parent
        work_dir = folder / ".psar"
        html = work_dir / "report.html"
        if not html.exists():
            messagebox.showwarning(
                "解析が完了していません",
                "先に「1. 解析 → 解析を実行」を押してください。"
            )
            return

        self._log("=== 編集ウィンドウを開いています… ===")
        self._set_status("編集ウィンドウを開いています…")

        import subprocess

        def runner():
            try:
                proc = subprocess.Popen(
                    [sys.executable, "-m", "pdf_split_autorenamer.inapp_editor", str(work_dir)],
                )
                proc.wait()
                return proc.returncode
            except Exception as e:  # noqa: BLE001
                return f"起動失敗: {e}"

        def done(result):
            if isinstance(result, int) and result == 0:
                self._log("=== 編集ウィンドウを閉じました ===")
                self._set_status("編集完了。続けて「2. 分割 → 実行」を押してください")
            else:
                self._log(f"=== 編集ウィンドウ 異常終了: {result} ===")
                self._set_status("編集ウィンドウでエラー")

        self._run_async(runner, done)

    def _on_split(self, apply_: bool) -> None:
        inputs = self._get_inputs()
        if not inputs:
            return
        force = self.force_var.get()

        if not apply_:
            # dry-run ボタン: ログに流すだけ（既存動作を維持）
            self._log("=== 分割 dry-run ===")
            self._set_status("dry-run 中…")

            def do_dry():
                return _split.run_split(inputs, dry_run=True, force=force)

            def done_dry(res):
                for a in res["actions"]:
                    st = a.get("status", "")
                    self._log(f"  [{st}] {a.get('out', a.get('src', ''))}  pages {a.get('range', '?')}")
                self._log(f"  入力ページ合計: {res['total_input_pages']}")
                self._set_status("dry-run 完了")

            self._run_async(do_dry, done_dry)
            return

        # 実行ボタン: まず dry-run してサマリを確認ダイアログに表示
        self._log("=== 分割 dry-run (確認中…) ===")
        self._set_status("確認中…")

        def do_preview():
            return _split.run_split(inputs, dry_run=True, force=force)

        def done_preview(res):
            summary = self._build_split_summary(res)
            if not messagebox.askyesno("分割の確認", summary):
                self._set_status("キャンセル")
                return
            # 本番実行
            self._log("=== 分割 実行 ===")
            self._set_status("分割中…")

            def do_apply():
                return _split.run_split(inputs, dry_run=False, force=force)

            def done_apply(res2):
                for a in res2["actions"]:
                    st = a.get("status", "")
                    self._log(f"  [{st}] {a.get('out', a.get('src', ''))}  pages {a.get('range', '?')}")
                self._log(f"  入力ページ合計: {res2['total_input_pages']}")
                self._log(f"  書き出し: {res2['files_written']} ファイル / {res2['total_output_pages']} ページ")
                self._log(f"  スキップ: {res2['files_skipped']} ファイル")
                self._set_status("分割完了")

            self._run_async(do_apply, done_apply)

        self._run_async(do_preview, done_preview)


def main(initial_folder: str | None = None) -> int:
    app = App(initial_folder=initial_folder)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
