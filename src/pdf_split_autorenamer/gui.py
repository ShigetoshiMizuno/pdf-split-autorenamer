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
from . import inapp_editor as _inapp
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
        self.profile_var = tk.StringVar()

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

        # Step 1: 解析（解析を実行 → 完了したら自動でアプリ内編集ウィンドウへ）
        f1 = ttk.LabelFrame(body, text="1. 解析（PDFを読み込み、書類の境界を提案）", padding=8)
        f1.pack(fill="x", **pad)
        ttk.Button(f1, text="解析を実行", command=self._on_analyze).pack(side="left")
        ttk.Label(f1,
                  text="押すと内容を読み取り、続けて編集ウィンドウが開きます").pack(
            side="left", padx=12)

        # Step 2: 分割
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

        # Step 3: リネーム
        f3 = ttk.LabelFrame(body, text="3. 自動リネーム（内容から日付・書類タイプを決めて命名）", padding=8)
        f3.pack(fill="x", **pad)
        f3_row1 = ttk.Frame(f3)
        f3_row1.pack(fill="x")
        ttk.Button(f3_row1, text="実行", command=lambda: self._on_rename(True)).pack(side="left")
        # 詳細オプション（折りたたみ）
        self._rename_advanced_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f3_row1, text="詳細オプション", variable=self._rename_advanced_var,
                        command=self._toggle_rename_advanced).pack(side="right")
        self._rename_advanced_frame = ttk.Frame(body)  # 折りたたみコンテンツ
        # モード選択
        adv_row1 = ttk.Frame(self._rename_advanced_frame)
        adv_row1.pack(fill="x", padx=8, pady=2)
        ttk.Label(adv_row1, text="対象:").pack(side="left")
        ttk.Radiobutton(adv_row1, text="分割直後のファイル", variable=self.rename_mode_var,
                        value="split").pack(side="left", padx=4)
        ttk.Radiobutton(adv_row1, text="既存の『日付不明_』を再判定",
                        variable=self.rename_mode_var,
                        value="unknown").pack(side="left", padx=4)
        ttk.Radiobutton(adv_row1, text="両方", variable=self.rename_mode_var,
                        value="all").pack(side="left", padx=4)
        ttk.Button(adv_row1, text="変更内容を確認するだけ（実行しない）",
                   command=lambda: self._on_rename(False)).pack(side="left", padx=8)
        # プロファイル
        adv_row2 = ttk.Frame(self._rename_advanced_frame)
        adv_row2.pack(fill="x", padx=8, pady=2)
        ttk.Label(adv_row2, text="命名ルール（プロファイル）:").pack(side="left")
        ttk.Entry(adv_row2, textvariable=self.profile_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(adv_row2, text="参照…", command=self._on_browse_profile).pack(side="left")
        ttk.Button(adv_row2, text="クリア",
                   command=lambda: self.profile_var.set("")).pack(side="left", padx=(4, 0))

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

    def _on_browse_profile(self) -> None:
        path = filedialog.askopenfilename(
            title="プロファイル TOML を選択",
            filetypes=[("TOML ファイル", "*.toml"), ("すべてのファイル", "*.*")],
        )
        if path:
            self.profile_var.set(path)

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

    # ----- 詳細オプション折りたたみ -----
    def _toggle_split_advanced(self) -> None:
        if self._split_advanced_var.get():
            self._split_advanced_frame.pack(fill="x", padx=8, pady=(0, 4),
                                            after=self._split_advanced_frame.master.winfo_children()[1])
        else:
            self._split_advanced_frame.pack_forget()

    def _toggle_rename_advanced(self) -> None:
        if self._rename_advanced_var.get():
            self._rename_advanced_frame.pack(fill="x", padx=8, pady=(0, 4))
        else:
            self._rename_advanced_frame.pack_forget()

    # ----- アクション -----
    def _on_analyze(self) -> None:
        folder = self._get_folder()
        if not folder:
            return
        self._log(f"=== 解析開始: {folder} ===")
        self._set_status("解析中…")

        def do():
            profile_path = self.profile_var.get().strip() or None
            profile = Path(profile_path) if profile_path else None
            return _analyze.run_analyze(folder, profile=profile)

        def done(res):
            self._log(f"  ページ数: {res.get('pages', 0)}")
            self._log(f"  初期グループ数: {res.get('groups', 0)}")
            html = res.get("report_html")
            self._set_status("解析完了")
            if not html:
                return
            self._log(f"  レポート: {html}")
            pages = res.get("pages")
            groups = res.get("groups")
            # 自動誘導: pywebview があれば確認 → アプリ内編集ウィンドウへ
            if _inapp.is_available():
                if messagebox.askyesno(
                    "解析完了",
                    f"ページ {pages} 件 / 書類グループ {groups} 件を提案しました。\n\n"
                    "続けて編集ウィンドウを開いて、境界とファイル名を確認しますか？\n"
                    "（『はい』でアプリ内に編集画面が開きます）"
                ):
                    self._on_inapp_edit()
            else:
                # フォールバック: pywebview 未導入時はブラウザを案内
                if messagebox.askyesno(
                    "解析完了",
                    f"ページ {pages} 件 / 書類グループ {groups} 件を提案しました。\n\n"
                    "ブラウザで編集画面を開きますか？\n"
                    "（アプリ内編集には pywebview のインストールが必要です）"
                ):
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

    def _on_rename(self, apply_: bool) -> None:
        folder = self._get_folder()
        if not folder:
            return
        mode = self.rename_mode_var.get()
        profile_str = self.profile_var.get()
        profile = Path(profile_str) if profile_str else None

        if not apply_:
            # dry-run ボタン: ログに流すだけ（既存動作を維持）
            self._log(f"=== リネーム dry-run (mode={mode}) ===")
            self._set_status("dry-run 中…")

            def do_dry():
                return _rename.run_rename(folder, mode=mode, apply=False, profile=profile)

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
            return _rename.run_rename(folder, mode=mode, apply=False, profile=profile)

        def done_preview(res):
            summary = self._build_rename_summary(res, mode)
            if not messagebox.askyesno("リネームの確認", summary):
                self._set_status("キャンセル")
                return
            # 本番実行
            self._log(f"=== リネーム 実行 (mode={mode}) ===")
            self._set_status("リネーム中…")

            def do_apply():
                return _rename.run_rename(folder, mode=mode, apply=True, profile=profile)

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
