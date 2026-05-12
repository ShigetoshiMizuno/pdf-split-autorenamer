# -*- coding: utf-8 -*-
"""run_silent のテスト。

Windows で CMD コンソールウィンドウを開かない (CREATE_NO_WINDOW) ことが目的。
issue #36 対応。
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch

from pdf_split_autorenamer import _subprocess_utils
from pdf_split_autorenamer._subprocess_utils import run_silent


def test_run_silent_passes_command_through():
    """cmd 引数は subprocess.run に透過する。"""
    with patch.object(_subprocess_utils.subprocess, "run") as mrun:
        mrun.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        run_silent(["echo", "hi"])
        called_args, _ = mrun.call_args
        assert called_args[0] == ["echo", "hi"]


def test_run_silent_passes_kwargs_through():
    """capture_output / timeout / input などの kwargs は透過する。"""
    with patch.object(_subprocess_utils.subprocess, "run") as mrun:
        mrun.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        run_silent(["x"], capture_output=True, timeout=30, input=b"data")
        _, kwargs = mrun.call_args
        assert kwargs.get("capture_output") is True
        assert kwargs.get("timeout") == 30
        assert kwargs.get("input") == b"data"


def test_build_no_window_kwargs_windows():
    """sys.platform == 'win32' のとき creationflags=CREATE_NO_WINDOW を返す。"""
    with patch.object(_subprocess_utils.sys, "platform", "win32"):
        kwargs = _subprocess_utils._build_no_window_kwargs()
        assert kwargs == {"creationflags": subprocess.CREATE_NO_WINDOW}


def test_build_no_window_kwargs_linux():
    """sys.platform == 'linux' のとき空 dict を返す。"""
    with patch.object(_subprocess_utils.sys, "platform", "linux"):
        kwargs = _subprocess_utils._build_no_window_kwargs()
        assert kwargs == {}


def test_build_no_window_kwargs_darwin():
    """sys.platform == 'darwin' のとき空 dict を返す。"""
    with patch.object(_subprocess_utils.sys, "platform", "darwin"):
        kwargs = _subprocess_utils._build_no_window_kwargs()
        assert kwargs == {}


def test_run_silent_uses_no_window_kwargs():
    """_NO_WINDOW_KWARGS が run の kwargs にマージされる。"""
    with patch.object(_subprocess_utils, "_NO_WINDOW_KWARGS", {"creationflags": 0x08000000}):
        with patch.object(_subprocess_utils.subprocess, "run") as mrun:
            mrun.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            run_silent(["x"])
            _, kwargs = mrun.call_args
            assert kwargs.get("creationflags") == 0x08000000


def test_run_silent_no_window_kwargs_empty():
    """非 Windows 想定: _NO_WINDOW_KWARGS が空なら creationflags は付かない。"""
    with patch.object(_subprocess_utils, "_NO_WINDOW_KWARGS", {}):
        with patch.object(_subprocess_utils.subprocess, "run") as mrun:
            mrun.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            run_silent(["x"])
            _, kwargs = mrun.call_args
            assert "creationflags" not in kwargs


def test_run_silent_caller_can_override_creationflags():
    """呼び出し元が明示的に creationflags を渡せばそちらを優先する。"""
    with patch.object(_subprocess_utils, "_NO_WINDOW_KWARGS", {"creationflags": 0x08000000}):
        with patch.object(_subprocess_utils.subprocess, "run") as mrun:
            mrun.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            run_silent(["x"], creationflags=0x12345)
            _, kwargs = mrun.call_args
            assert kwargs.get("creationflags") == 0x12345
