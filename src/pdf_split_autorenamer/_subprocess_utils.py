# -*- coding: utf-8 -*-
"""subprocess 実行の共通ユーティリティ。

Windows でコンソールサブシステムの実行ファイル (tesseract.exe / pdftotext.exe 等) を
呼び出すと既定で CMD ウィンドウが表示される。これを抑止するため
creationflags=CREATE_NO_WINDOW を自動付与するラッパを提供する。

issue #36 対応。
"""
from __future__ import annotations

import subprocess
import sys
from typing import Any


def _build_no_window_kwargs() -> dict[str, Any]:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


_NO_WINDOW_KWARGS = _build_no_window_kwargs()


def run_silent(cmd, **kwargs):
    """subprocess.run のラッパ。Windows でコンソールウィンドウを抑止する。

    呼び出し元が creationflags を明示した場合はそちらを優先する。
    """
    merged: dict[str, Any] = {**_NO_WINDOW_KWARGS, **kwargs}
    return subprocess.run(cmd, **merged)
