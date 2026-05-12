# -*- coding: utf-8 -*-
"""アプリ内編集 UI（pywebview による WebView 内蔵）

既存の analyze で生成される report.html を、ブラウザではなく pywebview の
WebView ウィンドウで開く。JS から `window.pywebview.api.save_groups(json_str)` を
呼ぶと PsarBridge.save_groups が直接 .psar/groups.json に書き込む。

ブラウザ離脱・ファイルダウンロード・手動上書きが不要になる。

pywebview は optional 依存（gui-inapp extras）。未インストール時は
is_available() == False を返し、呼び出し側でフォールバックを選ぶ。
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """pywebview が import 可能かを返す。未導入なら False。"""
    try:
        import webview  # noqa: F401
    except ImportError:
        return False
    return True


class PsarBridge:
    """JS から呼べる Python API。

    pywebview の create_window(js_api=...) として渡される。
    JS 側からは `window.pywebview.api.save_groups(...)` のように呼ばれる。
    """

    def __init__(
        self,
        work_dir: Path,
        on_saved: Callable[[Path], None] | None = None,
    ) -> None:
        self.work_dir = Path(work_dir)
        self._on_saved = on_saved
        self._closed = False

    # ------------------------------------------------------------------ JS API

    def save_groups(self, json_str: str) -> dict[str, Any]:
        """JS から渡された groups.json 文字列を .psar/groups.json に書き込む。

        戻り値は JS Promise として受け取られる。
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"JSON parse error: {exc}"}

        target = self.work_dir / "groups.json"
        try:
            self.work_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            return {"ok": False, "error": f"write failed: {exc}"}

        logger.info("[inapp] groups.json を保存: %s", target)
        if self._on_saved is not None:
            try:
                self._on_saved(target)
            except Exception:  # noqa: BLE001
                logger.exception("on_saved callback failed")
        return {"ok": True, "path": str(target)}

    def get_groups(self) -> str | None:
        """既存の groups.json を文字列で返す（編集再開時に使う）。なければ None。"""
        target = self.work_dir / "groups.json"
        if not target.exists():
            return None
        try:
            return target.read_text(encoding="utf-8")
        except OSError:
            return None

    def close_window(self) -> dict[str, Any]:
        """JS から呼ばれて WebView ウィンドウを閉じる。"""
        self._closed = True
        try:
            import webview

            for w in list(webview.windows):
                w.destroy()
        except Exception:  # noqa: BLE001
            logger.exception("close_window failed")
            return {"ok": False}
        return {"ok": True}

    # --------------------------------------------------------------- internal

    @property
    def closed(self) -> bool:
        return self._closed


def open_editor(
    report_html: Path,
    work_dir: Path,
    *,
    title: str = "PDF 分割設定 — 編集",
    width: int = 1200,
    height: int = 820,
    on_saved: Callable[[Path], None] | None = None,
) -> bool:
    """pywebview ウィンドウで report.html を開く。

    Returns:
        True: ウィンドウを開いて閉じるまで完了した
        False: pywebview が導入されておらず開けなかった
    """
    if not is_available():
        logger.warning("pywebview が未導入のため inapp editor を起動できません")
        return False

    import webview

    bridge = PsarBridge(work_dir=work_dir, on_saved=on_saved)
    url = report_html.resolve().as_uri()
    logger.info("[inapp] WebView を開きます: %s", url)

    webview.create_window(
        title,
        url=url,
        js_api=bridge,
        width=width,
        height=height,
        resizable=True,
        text_select=True,
    )
    # gui=None は OS 既定（Win=Edge WebView2 / mac=WebKit / Linux=GTK WebKit2）
    # debug=False で本番表示（コンソール非表示）
    webview.start(debug=False)
    return True


# ---------------------------------------------------------------------------
# CLI からも単体で起動できるエントリポイント（デバッグ用）
# ---------------------------------------------------------------------------
def _cli_main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="pdf-split-autorenamer のアプリ内編集 UI を起動"
    )
    ap.add_argument("work_dir", help=".psar ディレクトリへのパス")
    args = ap.parse_args(argv)

    work_dir = Path(args.work_dir)
    if not work_dir.is_dir():
        print(f"エラー: ディレクトリが見つかりません: {work_dir}", file=sys.stderr)
        return 1

    report = work_dir / "report.html"
    if not report.exists():
        print(f"エラー: report.html が見つかりません: {report}", file=sys.stderr)
        print("先に `psar analyze` を実行してください。", file=sys.stderr)
        return 1

    if not is_available():
        print(
            "エラー: pywebview が導入されていません。\n"
            "  pip install 'pdf-split-autorenamer[gui-inapp]'\n"
            "を実行してください。",
            file=sys.stderr,
        )
        return 2

    open_editor(report, work_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
