# -*- coding: utf-8 -*-
"""コマンドラインインターフェース"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def _setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=level,
        stream=sys.stderr,
        force=True,
    )


def cmd_analyze(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose, args.quiet)
    from . import analyze
    src = Path(args.folder).resolve()
    if not src.is_dir():
        logging.error("not a directory: %s", src)
        return 2
    work = Path(args.work_dir).resolve() if args.work_dir else None
    print(f"Analyzing PDFs in: {src}")
    res = analyze.run_analyze(src, work_dir=work, pdftotext_path=args.pdftotext,
                              title=args.title,
                              ocr_fallback=not args.no_ocr_fallback)
    print(f"  pages: {res.get('pages', 0)}")
    print(f"  initial groups: {res.get('groups', 0)}")
    print(f"  report: {res.get('report_html', '')}")
    print(f"  groups.json: {res.get('groups_json', '')}")
    print()
    print(f"次の手順: ブラウザで report.html を開き、境界とファイル名を編集して")
    print(f"          groups.json を保存。完了したら `psar split` を実行。")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose, args.quiet)
    from . import split
    src = Path(args.folder).resolve()
    work = Path(args.work_dir).resolve() if args.work_dir else None
    try:
        res = split.run_split(src, work_dir=work, dry_run=args.dry_run, force=args.force)
    except FileNotFoundError as e:
        logging.error("%s", e)
        return 2

    print(f"入力ページ合計: {res['total_input_pages']}")
    if not args.dry_run:
        print(f"書き出し: {res['files_written']} ファイル / {res['total_output_pages']} ページ")
        print(f"スキップ: {res['files_skipped']} ファイル")
    n_show = 0
    for a in res["actions"]:
        st = a.get("status", "")
        if args.dry_run or st in ("ok", "error", "out-of-range"):
            print(f"  [{st}] {a.get('out', a.get('src', ''))}  pages {a.get('range', '?')}")
            n_show += 1
    if not args.dry_run and res["files_written"] != res["total_input_pages"] - sum(
        # スキップ分は計算外
        0 for _ in res["actions"]
    ):
        pass
    return 0


def cmd_rename(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose, args.quiet)
    from . import rename
    src = Path(args.folder).resolve()
    if args.retarget_unknown:
        mode = "unknown"
    elif args.all:
        mode = "all"
    else:
        mode = "split"
    profile = Path(args.profile) if args.profile else None
    res = rename.run_rename(src, mode=mode, apply=args.apply,
                            pdftotext_path=args.pdftotext,
                            ocr_fallback=not args.no_ocr_fallback,
                            profile=profile)
    print(f"対象: {res['targets']} 件 / モード: {mode}")
    print()
    print(f"{'STATUS':10} OLD -> NEW")
    print("-" * 100)
    for a in res["actions"]:
        st = a["status"]
        old = a.get("src_display", a["src"])
        new = a["dst"]
        date = a.get("date") or "----"
        kind = a.get("kind", "")
        print(f"{st:10} {old}  ->  {new}  [{date} / {kind}]")
    print()
    if args.apply:
        print(f"完了: {res['applied']} 件 リネーム済み")
    else:
        print("→ dry-run。実行するには --apply を付けてください。")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from . import server
    src = Path(args.folder).resolve()
    work = Path(args.work_dir).resolve() if args.work_dir else None
    try:
        server.serve_report(src, work_dir=work, port=args.port, auto_open=not args.no_open)
    except FileNotFoundError as e:
        logging.error("%s", e)
        return 2
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    from . import gui
    return gui.main(initial_folder=args.folder)


def _get_version() -> str:
    try:
        from importlib.metadata import version
        return version("pdf-split-autorenamer")
    except Exception:
        return "0.2.0"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="psar",
        description="pdf-split-autorenamer: PDFをグループ別に分割し、内容ベースで自動リネーム",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {_get_version()}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("analyze", help="PDFを解析してHTMLレポートを生成")
    sp.add_argument("folder", help="PDFが入っているフォルダ")
    sp.add_argument("--work-dir", help="作業ファイル格納先 (既定: <folder>/.psar)")
    sp.add_argument("--pdftotext", help="pdftotext.exe のパス (省略時は自動検出)")
    sp.add_argument("--title", default="PDF 分割レビュー", help="HTMLレポートのタイトル")
    sp.add_argument("--no-ocr-fallback", action="store_true",
                    help="Tesseract による OCR フォールバックを無効化")
    sp.add_argument("--verbose", action="store_true", help="詳細ログを表示 (DEBUG)")
    sp.add_argument("--quiet", action="store_true", help="警告以上のみ表示 (WARNING)")
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("split", help="groups.json に従って分割を実行")
    sp.add_argument("folder", help="PDFが入っているフォルダ")
    sp.add_argument("--work-dir", help="作業ファイル格納先 (既定: <folder>/.psar)")
    sp.add_argument("--dry-run", action="store_true", help="計画のみ表示")
    sp.add_argument("--force", action="store_true", help="既存ファイルを上書き")
    sp.add_argument("--verbose", action="store_true", help="詳細ログを表示 (DEBUG)")
    sp.add_argument("--quiet", action="store_true", help="警告以上のみ表示 (WARNING)")
    sp.set_defaults(func=cmd_split)

    sp = sub.add_parser("rename", help="内容ベースで自動リネーム")
    sp.add_argument("folder", help="PDFが入っているフォルダ")
    sp.add_argument("--apply", action="store_true", help="実際にリネームを実行（既定はdry-run）")
    sp.add_argument("--retarget-unknown", action="store_true",
                    help="日付不明_*.pdf を再考対象にする")
    sp.add_argument("--all", action="store_true", help="分割直後＋日付不明 両方")
    sp.add_argument("--pdftotext", help="pdftotext.exe のパス (省略時は自動検出)")
    sp.add_argument("--no-ocr-fallback", action="store_true",
                    help="Tesseract による OCR フォールバックを無効化")
    sp.add_argument("--profile", help="書類タイプ判定プロファイル TOML のパス")
    sp.add_argument("--verbose", action="store_true", help="詳細ログを表示 (DEBUG)")
    sp.add_argument("--quiet", action="store_true", help="警告以上のみ表示 (WARNING)")
    sp.set_defaults(func=cmd_rename)

    sp = sub.add_parser("serve", help="report.html をローカルHTTPで配信（groups.json 直接保存）")
    sp.add_argument("folder", help="PDFが入っているフォルダ")
    sp.add_argument("--work-dir", help="作業ファイル格納先 (既定: <folder>/.psar)")
    sp.add_argument("--port", type=int, default=8765, help="HTTPポート番号 (既定: 8765)")
    sp.add_argument("--no-open", action="store_true", help="ブラウザを自動で開かない")
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("gui", help="Tkinter GUI を起動")
    sp.add_argument("--folder", help="初期フォルダ")
    sp.set_defaults(func=cmd_gui)

    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
