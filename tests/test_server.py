# -*- coding: utf-8 -*-
"""server.py のユニットテスト

対象:
- serve_report() のバリデーション (FileNotFoundError)
- _PSARHandler.do_GET: /report.html, /thumbs/<name>, 不明パス
- _PSARHandler.do_POST: /api/save-groups (正常・JSON不正・不明パス)
- _PSARHandler.do_OPTIONS: CORS プリフライト
- _find_work_dir: work_dir 指定あり/なし
"""
from __future__ import annotations

import io
import json
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pdf_split_autorenamer.server import _PSARHandler, _find_work_dir, serve_report


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _make_handler(method: str, path: str, work_dir: Path,
                  body: bytes = b"") -> _PSARHandler:
    """テスト用の _PSARHandler インスタンスを生成する。
    実際のソケットを使わず、wfile/rfile をモックする。
    """
    handler = _PSARHandler.__new__(_PSARHandler)
    handler.work_dir = work_dir
    handler.command = method
    handler.path = path
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()

    responses = []

    def _send_response(code, message=None):
        responses.append(code)

    def _send_header(key, value):
        pass

    def _end_headers():
        pass

    handler.send_response = _send_response
    handler.send_header = _send_header
    handler.end_headers = _end_headers
    handler._responses = responses
    return handler


# ---------------------------------------------------------------------------
# _find_work_dir
# ---------------------------------------------------------------------------

class TestFindWorkDir:
    def test_returns_work_dir_when_given(self, tmp_path):
        """work_dir が指定されている場合はそのまま返す"""
        custom = tmp_path / "custom"
        result = _find_work_dir(tmp_path, custom)
        assert result == custom

    def test_returns_psar_subdir_when_none(self, tmp_path):
        """work_dir が None の場合は src_dir / '.psar' を返す"""
        result = _find_work_dir(tmp_path, None)
        assert result == tmp_path / ".psar"


# ---------------------------------------------------------------------------
# serve_report — FileNotFoundError
# ---------------------------------------------------------------------------

class TestServeReportValidation:
    def test_raises_file_not_found_if_no_report_html(self, tmp_path):
        """report.html が存在しない場合は FileNotFoundError を送出する"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="report.html"):
            serve_report(tmp_path, work_dir=work_dir, port=8765, auto_open=False)

    def test_starts_server_when_report_html_exists(self, tmp_path):
        """report.html が存在する場合は HTTPServer が起動して serve_forever が呼ばれる"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "report.html").write_text("<html/>", encoding="utf-8")

        mock_httpd = MagicMock()
        mock_httpd.serve_forever.side_effect = KeyboardInterrupt

        with patch("pdf_split_autorenamer.server.HTTPServer", return_value=mock_httpd) as mock_cls:
            serve_report(tmp_path, work_dir=work_dir, port=9999, auto_open=False)

        mock_cls.assert_called_once_with(("localhost", 9999), _PSARHandler)
        mock_httpd.serve_forever.assert_called_once()
        mock_httpd.server_close.assert_called_once()


# ---------------------------------------------------------------------------
# _PSARHandler.do_GET
# ---------------------------------------------------------------------------

class TestHandlerGet:
    def test_get_root_serves_report_html(self, tmp_path):
        """GET / で report.html の内容を返す"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "report.html").write_bytes(b"<html>hello</html>")

        handler = _make_handler("GET", "/", work_dir)
        handler.do_GET()

        assert 200 in handler._responses
        assert b"<html>hello</html>" in handler.wfile.getvalue()

    def test_get_report_html_path(self, tmp_path):
        """GET /report.html で report.html の内容を返す"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "report.html").write_bytes(b"<html>test</html>")

        handler = _make_handler("GET", "/report.html", work_dir)
        handler.do_GET()

        assert 200 in handler._responses

    def test_get_thumb(self, tmp_path):
        """GET /thumbs/img.jpg でサムネイル画像を返す"""
        work_dir = tmp_path / ".psar"
        (work_dir / "thumbs").mkdir(parents=True)
        thumb_data = b"\xff\xd8\xff"  # JPEGマジックバイト
        (work_dir / "thumbs" / "img.jpg").write_bytes(thumb_data)

        handler = _make_handler("GET", "/thumbs/img.jpg", work_dir)
        handler.do_GET()

        assert 200 in handler._responses
        assert thumb_data in handler.wfile.getvalue()

    def test_get_missing_report_html_returns_404(self, tmp_path):
        """report.html が存在しない場合 404 を返す"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()

        handler = _make_handler("GET", "/", work_dir)
        handler.do_GET()

        assert 404 in handler._responses

    def test_get_missing_thumb_returns_404(self, tmp_path):
        """存在しないサムネイルは 404 を返す"""
        work_dir = tmp_path / ".psar"
        (work_dir / "thumbs").mkdir(parents=True)

        handler = _make_handler("GET", "/thumbs/missing.jpg", work_dir)
        handler.do_GET()

        assert 404 in handler._responses

    def test_get_unknown_path_returns_404(self, tmp_path):
        """未知のパスは 404 を返す"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()

        handler = _make_handler("GET", "/unknown/path", work_dir)
        handler.do_GET()

        assert 404 in handler._responses


# ---------------------------------------------------------------------------
# _PSARHandler.do_POST
# ---------------------------------------------------------------------------

class TestHandlerPost:
    def test_post_save_groups_writes_file(self, tmp_path):
        """POST /api/save-groups で groups.json が保存される"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        data = {"test.pdf": [{"range": [1, 3], "name": "テスト"}]}
        body = json.dumps(data).encode("utf-8")

        handler = _make_handler("POST", "/api/save-groups", work_dir, body)
        handler.do_POST()

        assert 200 in handler._responses
        saved = json.loads((work_dir / "groups.json").read_text(encoding="utf-8"))
        assert saved == data

    def test_post_save_groups_json_format(self, tmp_path):
        """保存される groups.json は ensure_ascii=False, indent=2 のフォーマットである"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        data = {"テスト.pdf": [{"range": [1, 1], "name": "日本語"}]}
        body = json.dumps(data).encode("utf-8")

        handler = _make_handler("POST", "/api/save-groups", work_dir, body)
        handler.do_POST()

        raw = (work_dir / "groups.json").read_text(encoding="utf-8")
        # ensure_ascii=False → 日本語がそのまま含まれる
        assert "テスト.pdf" in raw
        assert "日本語" in raw
        # indent=2 → 改行が含まれる
        assert "\n" in raw

    def test_post_invalid_json_returns_500(self, tmp_path):
        """不正な JSON を送ると 500 を返す"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        body = b"not json {{"

        handler = _make_handler("POST", "/api/save-groups", work_dir, body)
        handler.do_POST()

        assert 500 in handler._responses

    def test_post_unknown_path_returns_404(self, tmp_path):
        """未知の POST パスは 404 を返す"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()

        handler = _make_handler("POST", "/unknown", work_dir, b"{}")
        handler.do_POST()

        assert 404 in handler._responses


# ---------------------------------------------------------------------------
# _PSARHandler.do_OPTIONS
# ---------------------------------------------------------------------------

class TestHandlerOptions:
    def test_options_returns_204(self, tmp_path):
        """OPTIONS リクエストに 204 を返す"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()

        handler = _make_handler("OPTIONS", "/api/save-groups", work_dir)
        handler.do_OPTIONS()

        assert 204 in handler._responses


# ---------------------------------------------------------------------------
# _PSARHandler.log_message (line 21)
# ---------------------------------------------------------------------------

class TestHandlerLogMessage:
    def test_log_message_does_not_raise(self, tmp_path):
        """log_message が logging.debug に委譲し例外を起こさない（line 21）"""
        import logging
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        handler = _make_handler("GET", "/", work_dir)
        # 直接呼び出して logging.debug を通ることを確認
        with patch("logging.debug") as mock_debug:
            handler.log_message("GET %s %s", "/", "200")
        mock_debug.assert_called_once()


# ---------------------------------------------------------------------------
# serve_report — auto_open=True (line 95)
# ---------------------------------------------------------------------------

class TestServeReportAutoOpen:
    def test_auto_open_starts_timer(self, tmp_path):
        """auto_open=True のとき Timer が開始される（line 95）"""
        work_dir = tmp_path / ".psar"
        work_dir.mkdir()
        (work_dir / "report.html").write_text("<html/>", encoding="utf-8")

        mock_httpd = MagicMock()
        mock_httpd.serve_forever.side_effect = KeyboardInterrupt

        mock_timer = MagicMock()

        with patch("pdf_split_autorenamer.server.HTTPServer", return_value=mock_httpd):
            with patch("pdf_split_autorenamer.server.Timer", return_value=mock_timer) as mock_timer_cls:
                serve_report(tmp_path, work_dir=work_dir, port=9998, auto_open=True)

        mock_timer_cls.assert_called_once()
        mock_timer.start.assert_called_once()
