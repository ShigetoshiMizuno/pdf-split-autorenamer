# -*- coding: utf-8 -*-
"""アプリ内編集 UI（pywebview bridge）の単体テスト。

pywebview 自体の起動はテストしない（GUI が立ち上がるため CI で不可）。
PsarBridge の Python 側ロジック（保存・読み出し・エラーハンドリング）と
is_available() のフォールバック挙動だけを検証する。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdf_split_autorenamer import inapp_editor


# ---------------------------------------------------------------- is_available
def test_is_available_returns_bool():
    """is_available() は bool を返す（環境によって True/False どちらも有効）"""
    result = inapp_editor.is_available()
    assert isinstance(result, bool)


# ---------------------------------------------------------------- save_groups
def test_save_groups_writes_json(tmp_path: Path):
    """JSON 文字列が work_dir/groups.json として保存される"""
    bridge = inapp_editor.PsarBridge(work_dir=tmp_path)
    payload = {
        "sample.pdf": [
            {"range": [1, 1], "name": "2026-04-01_請求書"},
            {"range": [2, 3], "name": "2026-04-15_議事録"},
        ]
    }
    json_str = json.dumps(payload, ensure_ascii=False)

    result = bridge.save_groups(json_str)

    assert result["ok"] is True
    target = tmp_path / "groups.json"
    assert target.exists()
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved == payload
    assert result["path"] == str(target)


def test_save_groups_creates_work_dir_if_missing(tmp_path: Path):
    """work_dir が存在しなくても自動作成して保存できる"""
    sub = tmp_path / "nonexistent" / ".psar"
    bridge = inapp_editor.PsarBridge(work_dir=sub)
    result = bridge.save_groups('{"a.pdf": []}')

    assert result["ok"] is True
    assert sub.exists()
    assert (sub / "groups.json").exists()


def test_save_groups_returns_error_on_invalid_json(tmp_path: Path):
    """不正な JSON はエラー応答する（例外を投げない）"""
    bridge = inapp_editor.PsarBridge(work_dir=tmp_path)
    result = bridge.save_groups("not a json {{{")

    assert result["ok"] is False
    assert "JSON parse error" in result["error"]
    # ファイルは作られていない
    assert not (tmp_path / "groups.json").exists()


def test_save_groups_invokes_on_saved_callback(tmp_path: Path):
    """保存成功時に on_saved コールバックが呼ばれる"""
    captured: list[Path] = []

    bridge = inapp_editor.PsarBridge(
        work_dir=tmp_path,
        on_saved=lambda p: captured.append(p),
    )
    bridge.save_groups('{"x.pdf": []}')

    assert len(captured) == 1
    assert captured[0] == tmp_path / "groups.json"


def test_save_groups_callback_failure_does_not_break_save(tmp_path: Path):
    """on_saved 内の例外は保存自体を失敗させない"""
    def boom(_: Path) -> None:
        raise RuntimeError("callback error")

    bridge = inapp_editor.PsarBridge(work_dir=tmp_path, on_saved=boom)
    result = bridge.save_groups('{"y.pdf": []}')

    assert result["ok"] is True
    assert (tmp_path / "groups.json").exists()


# ----------------------------------------------------------------- get_groups
def test_get_groups_returns_none_when_missing(tmp_path: Path):
    bridge = inapp_editor.PsarBridge(work_dir=tmp_path)
    assert bridge.get_groups() is None


def test_get_groups_round_trip(tmp_path: Path):
    """save → get で同じ内容が読み戻せる"""
    bridge = inapp_editor.PsarBridge(work_dir=tmp_path)
    payload = {"a.pdf": [{"range": [1, 1], "name": "test"}]}
    bridge.save_groups(json.dumps(payload))
    loaded = bridge.get_groups()

    assert loaded is not None
    assert json.loads(loaded) == payload


# ----------------------------------------------------------------- properties
def test_closed_starts_false(tmp_path: Path):
    bridge = inapp_editor.PsarBridge(work_dir=tmp_path)
    assert bridge.closed is False


# ----------------------------------------------------------------- open_editor
def test_open_editor_returns_false_when_unavailable(tmp_path: Path, monkeypatch):
    """pywebview が import できない場合 open_editor は False を返す"""
    monkeypatch.setattr(inapp_editor, "is_available", lambda: False)
    result = inapp_editor.open_editor(
        report_html=tmp_path / "report.html",
        work_dir=tmp_path,
    )
    assert result is False


# --------------------------------------------------------------------- _cli_main
def test_cli_main_errors_when_dir_missing(tmp_path: Path, capsys):
    """存在しないディレクトリを渡すと exit 1"""
    nonexistent = tmp_path / "nope"
    result = inapp_editor._cli_main([str(nonexistent)])
    assert result == 1
    captured = capsys.readouterr()
    assert "ディレクトリが見つかりません" in captured.err


def test_cli_main_errors_when_report_missing(tmp_path: Path, capsys):
    """report.html がない場合 exit 1 でガイダンスを出す"""
    result = inapp_editor._cli_main([str(tmp_path)])
    assert result == 1
    captured = capsys.readouterr()
    assert "report.html が見つかりません" in captured.err


def test_cli_main_errors_when_pywebview_missing(tmp_path: Path, capsys, monkeypatch):
    """pywebview 未導入時は exit 2 と pip コマンドガイダンス"""
    (tmp_path / "report.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(inapp_editor, "is_available", lambda: False)
    result = inapp_editor._cli_main([str(tmp_path)])
    assert result == 2
    captured = capsys.readouterr()
    assert "pywebview" in captured.err
    assert "gui-inapp" in captured.err
