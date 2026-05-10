# -*- coding: utf-8 -*-
"""Tkinter GUI

3ステップを画面上のボタンで進めるシンプルなUI。
- フォルダ選択
- [解析] → サムネ・HTMLレポート生成 → ブラウザで自動オープン
- [分割 dry-run] / [分割 実行] → groups.json から分割
- [リネーム dry-run] / [リネーム 実行] → 内容ベース自動命名
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
from . import rename as _rename
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
        self.rename_mode_var = tk.StringVar(value="split")
        self.force_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="PDFフォルダ:").pack(side="left")
        ent = ttk.Entry(top, textvariable=self.folder_var)
        ent.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(top, text="参照…", command=self._on_browse).pack(side="left")

        # 操作パネル: 3つのフレームを並べる
        body = ttk.Frame(self, padding=8)
        body.pack(fill="x")

        # Step 1: 解析
        f1 = ttk.LabelFrame(body, text="1. 解析（サムネ・HTMLレポート生成）", padding=8)
        f1.pack(fill="x", **pad)
        ttk.Button(f1, text="解析を実行", command=self._on_analyze).pack(side="left")
        ttk.Button(f1, text="report.html をブラウザで開く",
                   command=self._on_open_report).pack(side="left", padx=8)
        ttk.Label(f1, text="HTMLで境界・出力名を編集 → groups.json を上書き保存").pack(
            side="left", padx=12)

        # Step 2: 分割
        f2 = ttk.LabelFrame(body, text="2. 分割（groups.json に従って）", padding=8)
        f2.pack(fill="x", **pad)
        ttk.Button(f2, text="dry-run", command=lambda: self._on_split(False)).pack(side="left")
        ttk.Button(f2, text="実行", command=lambda: self._on_split(True)).pack(side="left", padx=8)
        ttk.Checkbutton(f2, text="既存ファイルを上書き (--force)",
                        variable=self.force_var).pack(side="left", padx=12)

        # Step 3: リネーム
        f3 = ttk.LabelFrame(body, text="3. 自動リネーム（内容ベース）", padding=8)
        f3.pack(fill="x", **pad)
        ttk.Radiobutton(f3, text="分割直後", variable=self.rename_mode_var,
                        value="split").pack(side="left")
        ttk.Radiobutton(f3, text="日付不明_を再考", variable=self.rename_mode_var,
                        value="unknown").pack(side="left", padx=8)
        ttk.Radiobutton(f3, text="両方", variable=self.rename_mode_var,
                        value="all").pack(side="left", padx=8)
        ttk.Button(f3, text="dry-run", command=lambda: self._on_rename(False)).pack(side="left", padx=12)
        ttk.Button(f3, text="実行", command=lambda: self._on_rename(True)).pack(side="left", padx=4)

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

    def _get_folder(self) -> Path | None:
        v = self.folder_var.get().strip()
        if not v:
            messagebox.showwarning("警告", "PDFフォルダを選択してください。")
            return None
        p = Path(v)
        if not p.is_dir():
            messagebox.showerror("エラー", f"フォルダが存在しません: {p}")
            return None
        return p

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

    @staticmethod
    def _build_rename_summary(res: dict, mode: str) -> str:
        actions = res.get("actions", [])
        targets = res.get("targets", 0)
        lines = [f"対象: {targets} 件 (モード: {mode})", ""]
        limit = 10
        for a in actions[:limit]:
            status = a.get("status", "")
            old = a.get("src_display", a.get("src", ""))
            dst = a.get("dst", "")
            date = a.get("date") or "----"
            kind = a.get("kind", "")
            if status == "skip":
                lines.append(f"  [skip]   {old}  ->  既存ファイルあり")
            else:
                lines.append(f"  [{status}] {old}  ->  {dst}  [{date} / {kind}]")
        if len(actions) > limit:
            lines.append(f"  … 他 {len(actions) - limit} 件")
        lines.append("")
        lines.append("実行してよろしいですか？")
        return "\n".join(lines)

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
            self._log(f"  ページ数: {res.get('pages', 0)}")
            self._log(f"  初期グループ数: {res.get('groups', 0)}")
            html = res.get("report_html")
            if html:
                self._log(f"  report.html: {html}")
                if messagebox.askyesno("解析完了",
                                       f"ページ {res.get('pages')}, グループ {res.get('groups')} を提案しました。\n"
                                       "ブラウザで report.html を開きますか?"):
                    webbrowser.open(Path(html).as_uri())
            self._set_status("解析完了")

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

    def _on_rename(self, apply_: bool) -> None:
        folder = self._get_folder()
        if not folder:
            return
        mode = self.rename_mode_var.get()

        if not apply_:
            # dry-run ボタン: ログに流すだけ（既存動作を維持）
            self._log(f"=== リネーム dry-run (mode={mode}) ===")
            self._set_status("dry-run 中…")

            def do_dry():
                return _rename.run_rename(folder, mode=mode, apply=False)

            def done_dry(res):
                self._log(f"  対象: {res['targets']} 件")
                for a in res["actions"]:
                    old = a.get("src_display", a["src"])
                    self._log(f"  [{a['status']:8}] {old}  ->  {a['dst']}  [{a.get('date') or '----'} / {a.get('kind', '')}]")
                self._set_status("dry-run 完了")

            self._run_async(do_dry, done_dry)
            return

        # 実行ボタン: まず dry-run してサマリを確認ダイアログに表示
        self._log(f"=== リネーム dry-run (確認中…, mode={mode}) ===")
        self._set_status("確認中…")

        def do_preview():
            return _rename.run_rename(folder, mode=mode, apply=False)

        def done_preview(res):
            summary = self._build_rename_summary(res, mode)
            if not messagebox.askyesno("リネームの確認", summary):
                self._set_status("キャンセル")
                return
            # 本番実行
            self._log(f"=== リネーム 実行 (mode={mode}) ===")
            self._set_status("リネーム中…")

            def do_apply():
                return _rename.run_rename(folder, mode=mode, apply=True)

            def done_apply(res2):
                self._log(f"  対象: {res2['targets']} 件")
                for a in res2["actions"]:
                    old = a.get("src_display", a["src"])
                    self._log(f"  [{a['status']:8}] {old}  ->  {a['dst']}  [{a.get('date') or '----'} / {a.get('kind', '')}]")
                self._log(f"  リネーム完了: {res2['applied']} 件")
                self._set_status("リネーム完了")

            self._run_async(do_apply, done_apply)

        self._run_async(do_preview, done_preview)


def main(initial_folder: str | None = None) -> int:
    app = App(initial_folder=initial_folder)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
