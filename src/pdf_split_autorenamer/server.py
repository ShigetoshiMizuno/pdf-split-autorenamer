# -*- coding: utf-8 -*-
"""psar serve: report.html を HTTP で配信し、groups.json の直接保存を提供する"""
from __future__ import annotations

import json
import logging
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Timer


def _find_work_dir(src_dir: Path, work_dir: Path | None = None) -> Path:
    return work_dir if work_dir else src_dir / ".psar"


class _PSARHandler(BaseHTTPRequestHandler):
    work_dir: Path  # set as class attribute before instantiation

    def log_message(self, fmt, *args):
        logging.debug(fmt, *args)  # suppress stdout noise

    def do_GET(self):
        if self.path in ("/", "/report.html"):
            self._serve_file(self.work_dir / "report.html", "text/html; charset=utf-8")
        elif self.path.startswith("/thumbs/"):
            name = self.path[len("/thumbs/"):]
            self._serve_file(self.work_dir / "thumbs" / name, "image/jpeg")
        else:
            self._send(404, b"Not Found")

    def do_POST(self):
        if self.path == "/api/save-groups":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                groups_path = self.work_dir / "groups.json"
                groups_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                logging.info("groups.json を保存しました: %s", groups_path)
                self._send(200, b"OK")
            except Exception as e:
                logging.error("groups.json 保存失敗: %s", e)
                self._send(500, str(e).encode())
        else:
            self._send(404, b"Not Found")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self._send(404, b"Not Found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _send(self, code: int, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_report(src_dir: Path, work_dir: Path | None = None,
                 port: int = 8765, auto_open: bool = True) -> None:
    """report.html を HTTP で配信してサーバーをブロック実行する。Ctrl+C で停止。"""
    wdir = _find_work_dir(src_dir, work_dir)
    if not (wdir / "report.html").exists():
        raise FileNotFoundError(
            f"report.html が見つかりません: {wdir / 'report.html'}\n"
            "先に psar analyze を実行してください。"
        )

    _PSARHandler.work_dir = wdir

    httpd = HTTPServer(("localhost", port), _PSARHandler)
    url = f"http://localhost:{port}/"
    print(f"psar serve 起動: {url}")
    print(f"  work_dir: {wdir}")
    print(f"  Ctrl+C で停止")
    print()

    if auto_open:
        Timer(0.5, webbrowser.open, args=(url,)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("\npsar serve を停止しました。")
