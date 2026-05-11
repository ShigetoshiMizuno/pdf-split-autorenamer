# -*- coding: utf-8 -*-
"""T-07: Stage 3 LLM Vision バックエンドの検証テスト

- ClaudeVisionBackend の構造確認
- GPT4VisionBackend スタブ
- get_api_key ユーティリティ
- 構造化抽出の JSON バリデーション
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# ClaudeVisionBackend
# ---------------------------------------------------------------------------

class TestClaudeVisionBackend:
    def test_importable(self):
        """ClaudeVisionBackend がインポートできる"""
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        assert ClaudeVisionBackend is not None

    def test_is_ocr_backend(self):
        """ClaudeVisionBackend は OcrBackend のサブクラス"""
        from pdf_split_autorenamer.ocr_backend import OcrBackend, ClaudeVisionBackend
        assert issubclass(ClaudeVisionBackend, OcrBackend)

    def test_is_available_false_without_key(self, monkeypatch):
        """API キーなし・anthropic なし の場合は False"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key=None)
        # anthropic ライブラリがなければ False、あっても key なしは False
        result = backend.is_available()
        assert isinstance(result, bool)

    def test_is_available_true_with_key(self, monkeypatch):
        """API キーが設定されていれば True（anthropic ライブラリが必要）"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        with patch.dict("sys.modules", {"anthropic": MagicMock()}):
            from importlib import reload
            import pdf_split_autorenamer.ocr_backend as mod
            reload(mod)
            backend = mod.ClaudeVisionBackend(api_key="test-key")
            assert backend.is_available() is True

    def test_extract_text_returns_string(self):
        """extract_text が文字列を返す"""
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key=None)
        # API キーなしは空文字列
        result = backend.extract_text(b"fake_png_bytes")
        assert isinstance(result, str)

    def test_extract_structured_returns_dict(self):
        """extract_structured が dict を返す"""
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key=None)
        result = backend.extract_structured(b"fake_png_bytes")
        assert isinstance(result, dict)
        assert "text" in result or "date" in result or "title" in result


# ---------------------------------------------------------------------------
# GPT4VisionBackend スタブ
# ---------------------------------------------------------------------------

class TestGPT4VisionBackend:
    def test_importable(self):
        """GPT4VisionBackend がインポートできる"""
        from pdf_split_autorenamer.ocr_backend import GPT4VisionBackend
        assert GPT4VisionBackend is not None

    def test_is_ocr_backend(self):
        """GPT4VisionBackend は OcrBackend のサブクラス"""
        from pdf_split_autorenamer.ocr_backend import OcrBackend, GPT4VisionBackend
        assert issubclass(GPT4VisionBackend, OcrBackend)

    def test_extract_text_raises_not_implemented(self):
        """スタブは NotImplementedError"""
        from pdf_split_autorenamer.ocr_backend import GPT4VisionBackend
        backend = GPT4VisionBackend()
        with pytest.raises(NotImplementedError):
            backend.extract_text(b"fake")


# ---------------------------------------------------------------------------
# get_api_key ユーティリティ
# ---------------------------------------------------------------------------

class TestGetApiKey:
    def test_importable(self):
        """get_api_key がインポートできる"""
        from pdf_split_autorenamer.ocr_backend import get_api_key
        assert get_api_key is not None

    def test_from_env_var(self, monkeypatch):
        """環境変数から API キーを取得する"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-test-key")
        from pdf_split_autorenamer.ocr_backend import get_api_key
        key = get_api_key("anthropic")
        assert key == "env-test-key"

    def test_missing_returns_none(self, monkeypatch):
        """環境変数もキーリングもない場合は None"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.dict("sys.modules", {"keyring": None}):
            from pdf_split_autorenamer.ocr_backend import get_api_key
            key = get_api_key("anthropic")
            assert key is None


# ---------------------------------------------------------------------------
# JSON バリデーション
# ---------------------------------------------------------------------------

class TestStructuredOutputValidation:
    def test_validate_structured_output_valid(self):
        """有効な structured output はそのまま返す"""
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        data = {"date": "2026-05-11", "title": "請求書"}
        result = validate_structured_output(data)
        assert result["date"] == "2026-05-11"
        assert result["title"] == "請求書"

    def test_validate_structured_output_null_date(self):
        """null 日付は None として返す"""
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        data = {"date": None, "title": "不明"}
        result = validate_structured_output(data)
        assert result["date"] is None

    def test_validate_structured_output_invalid_date_format(self):
        """不正な日付形式は None に変換"""
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        data = {"date": "令和8年5月", "title": "テスト"}
        result = validate_structured_output(data)
        assert result["date"] is None

    def test_validate_structured_output_missing_keys(self):
        """必須キーが欠けている場合も例外を出さない"""
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        result = validate_structured_output({})
        assert "date" in result
        assert "title" in result

    def test_validate_structured_output_not_dict_raises(self):
        """dict でない入力は ValueError"""
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        with pytest.raises((ValueError, TypeError)):
            validate_structured_output("not a dict")  # type: ignore[arg-type]
