# -*- coding: utf-8 -*-
"""Tkinter GUI

2ステップを画面上のボタンで進めるシンプルなUI。
- フォルダ選択
- [解析] → サムネ・HTMLレポート生成 → ブラウザで自動オープン
- [分割 dry-run] / [分割 実行] → groups.json から分割（命名は編集ウィンドウで決定）

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


class App(tk.Tk):
    def __init__(self, initial_folder: str | None = None):
        super().__init__()
        self.title("pdf-split-autorenamer")
        self.geometry("760x560")
        self.minsize(640, 480)

        self.folder_var = tk.StringVar(value=initial_folder or "")
        self.force_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="PDFフォルダ／ファイル:").pack(side="left")
        ent = ttk.Entry(top, textvariable=self.folder_var)
        ent.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(top, text="フォルダ…", command=self._on_browse).pack(side="left")
        ttk.Button(top, text="ファイル…", command=self._on_browse_file).pack(side="left", padx=(4, 0))

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

    # ----- イベント -----
    def _on_browse(self) -> None:
        d = filedialog.askdirectory(title="PDFフォルダを選択",
                                    initialdir=self.folder_var.get() or ".")
        if d:
            self.folder_var.set(d)

    def _on_browse_file(self) -> None:
        """issue #35: 単一 PDF ファイルを選択可能にする。"""
        initial = self.folder_var.get() or "."
        if Path(initial).is_file():
            initial = str(Path(initial).parent)
        p = filedialog.askopenfilename(
            title="PDF ファイルを選択",
            initialdir=initial,
            filetypes=[("PDF ファイル", "*.pdf"), ("すべてのファイル", "*.*")],
        )
        if p:
            self.folder_var.set(p)

    def _get_folder(self) -> Path | None:
        """入力パスを返す。フォルダまたは PDF ファイル (issue #35)。"""
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
        folder = self._get_folder()
        if not folder:
            return
        self._log(f"=== 解析開始: {folder} ===")
        self._set_status("解析中…")

        def do():
            return _analyze.run_analyze(folder)

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
        folder = self._get_folder()
        if not folder:
            return
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

        folder = self._get_folder()
        if not folder:
            return
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
        folder = self._get_folder()
        if not folder:
            return
        force = self.force_var.get()

        if not apply_:
            # dry-run ボタン: ログに流すだけ（既存動作を維持）
            self._log("=== 分割 dry-run ===")
            self._set_status("dry-run 中…")

            def do_dry():
                return _split.run_split(folder, dry_run=True, force=force)

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
            return _split.run_split(folder, dry_run=True, force=force)

        def done_preview(res):
            summary = self._build_split_summary(res)
            if not messagebox.askyesno("分割の確認", summary):
                self._set_status("キャンセル")
                return
            # 本番実行
            self._log("=== 分割 実行 ===")
            self._set_status("分割中…")

            def do_apply():
                return _split.run_split(folder, dry_run=False, force=force)

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
