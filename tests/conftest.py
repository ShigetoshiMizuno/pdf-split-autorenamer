# -*- coding: utf-8 -*-
"""pytest 共通フィクスチャ・設定

Windows 環境では GTK3 Runtime の DLL を pytest 起動時点で os.add_dll_directory
に登録しておく。これにより WeasyPrint (cffi ベース) が test_demo_pdf.py の
モジュールレベルで import される際に DLL を見つけられる。
"""
from __future__ import annotations

import os
import sys

if sys.platform == "win32":
    _GTK_BIN = os.environ.get("PSAR_GTK_BIN", r"C:\Program Files\GTK3-Runtime Win64\bin")
    if os.path.isdir(_GTK_BIN):
        # cffi (_load_backend_lib) は ctypes.util.find_library 経由で PATH を見るため
        # os.add_dll_directory だけでは足りない。PATH にも追加する。
        os.environ["PATH"] = _GTK_BIN + os.pathsep + os.environ.get("PATH", "")
        try:
            os.add_dll_directory(_GTK_BIN)
        except OSError:
            pass
