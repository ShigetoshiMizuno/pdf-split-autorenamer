# -*- coding: utf-8 -*-
"""T-05: OcrBackend 抽象クラスの検証テスト

- OcrBackend ABC の定義確認
- TesseractBackend の is_available / extract_text
- スタブバックエンドの存在確認
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# OcrBackend ABC
# ---------------------------------------------------------------------------

class TestOcrBackendABC:
    def test_ocr_backend_importable(self):
        """ocr_backend モジュールがインポートできる"""
        from pdf_split_autorenamer import ocr_backend  # noqa: F401

    def test_ocr_backend_class_exists(self):
        """OcrBackend クラスが存在する"""
        from pdf_split_autorenamer.ocr_backend import OcrBackend
        assert OcrBackend is not None

    def test_ocr_backend_is_abstract(self):
        """OcrBackend は直接インスタンス化できない"""
        from pdf_split_autorenamer.ocr_backend import OcrBackend
        with pytest.raises(TypeError):
            OcrBackend()  # type: ignore[abstract]

    def test_ocr_backend_has_is_available(self):
        """OcrBackend に is_available メソッドがある"""
        from pdf_split_autorenamer.ocr_backend import OcrBackend
        assert hasattr(OcrBackend, "is_available")

    def test_ocr_backend_has_extract_text(self):
        """OcrBackend に extract_text メソッドがある"""
        from pdf_split_autorenamer.ocr_backend import OcrBackend
        assert hasattr(OcrBackend, "extract_text")

    def test_ocr_backend_has_extract_structured(self):
        """OcrBackend に extract_structured メソッドがある"""
        from pdf_split_autorenamer.ocr_backend import OcrBackend
        assert hasattr(OcrBackend, "extract_structured")


# ---------------------------------------------------------------------------
# TesseractBackend
# ---------------------------------------------------------------------------

class TestTesseractBackend:
    def test_tesseract_backend_importable(self):
        """TesseractBackend がインポートできる"""
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        assert TesseractBackend is not None

    def test_tesseract_backend_is_ocr_backend(self):
        """TesseractBackend は OcrBackend のサブクラス"""
        from pdf_split_autorenamer.ocr_backend import OcrBackend, TesseractBackend
        assert issubclass(TesseractBackend, OcrBackend)

    def test_tesseract_backend_instantiable(self):
        """TesseractBackend がインスタンス化できる"""
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        backend = TesseractBackend()
        assert backend is not None

    def test_is_available_returns_bool(self):
        """is_available() が bool を返す"""
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        backend = TesseractBackend()
        result = backend.is_available()
        assert isinstance(result, bool)

    def test_is_available_false_when_not_installed(self, monkeypatch):
        """Tesseract が見つからない場合は False"""
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        backend = TesseractBackend(executable=None)
        monkeypatch.setattr(backend, "_exe", None)
        assert backend.is_available() is False

    def test_extract_text_returns_string(self, monkeypatch):
        """extract_text が文字列を返す"""
        from unittest.mock import patch, MagicMock
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        backend = TesseractBackend(executable="/fake/tesseract")
        monkeypatch.setattr(backend, "_exe", "/fake/tesseract")
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"OCR text output\n"
        with patch("subprocess.run", return_value=mock_proc):
            result = backend.extract_text(b"fake_image_bytes")
        assert isinstance(result, str)
        assert "OCR text output" in result

    def test_extract_text_unavailable_returns_empty(self, monkeypatch):
        """Tesseract が利用不可の場合は空文字を返す"""
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        backend = TesseractBackend(executable=None)
        monkeypatch.setattr(backend, "_exe", None)
        result = backend.extract_text(b"fake_image_bytes")
        assert result == ""

    def test_extract_structured_returns_dict(self, monkeypatch):
        """extract_structured が dict を返す"""
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        backend = TesseractBackend(executable=None)
        monkeypatch.setattr(backend, "_exe", None)
        result = backend.extract_structured(b"fake")
        assert isinstance(result, dict)
        assert "text" in result


# ---------------------------------------------------------------------------
# スタブバックエンド
# ---------------------------------------------------------------------------

class TestStubBackends:
    @pytest.mark.parametrize("cls_name", [
        "PaddleOCRBackend",
        "AzureReadBackend",
        "GoogleVisionBackend",
    ])
    def test_stub_backend_importable(self, cls_name):
        """スタブバックエンドがインポートできる"""
        import importlib
        mod = importlib.import_module("pdf_split_autorenamer.ocr_backend")
        assert hasattr(mod, cls_name), f"{cls_name} が ocr_backend に存在しない"

    @pytest.mark.parametrize("cls_name", [
        "PaddleOCRBackend",
        "AzureReadBackend",
        "GoogleVisionBackend",
    ])
    def test_stub_backend_is_ocr_backend(self, cls_name):
        """スタブバックエンドは OcrBackend のサブクラス"""
        import importlib
        from pdf_split_autorenamer.ocr_backend import OcrBackend
        mod = importlib.import_module("pdf_split_autorenamer.ocr_backend")
        cls = getattr(mod, cls_name)
        assert issubclass(cls, OcrBackend)

    @pytest.mark.parametrize("cls_name", [
        "AzureReadBackend",
        "GoogleVisionBackend",
    ])
    def test_stub_backend_extract_text_raises_not_implemented(self, cls_name):
        """スタブバックエンドの extract_text は NotImplementedError を発生させる"""
        import importlib
        mod = importlib.import_module("pdf_split_autorenamer.ocr_backend")
        cls = getattr(mod, cls_name)
        backend = cls()
        with pytest.raises(NotImplementedError):
            backend.extract_text(b"fake")

    def test_azure_is_available_returns_false(self):
        """AzureReadBackend.is_available は常に False"""
        from pdf_split_autorenamer.ocr_backend import AzureReadBackend
        assert AzureReadBackend().is_available() is False

    def test_google_is_available_returns_false(self):
        """GoogleVisionBackend.is_available は常に False"""
        from pdf_split_autorenamer.ocr_backend import GoogleVisionBackend
        assert GoogleVisionBackend().is_available() is False

    def test_paddle_is_available_false_when_not_installed(self):
        """PaddleOCR が未インストールの場合は False"""
        import sys
        from pdf_split_autorenamer.ocr_backend import PaddleOCRBackend
        # paddleocr が存在しない環境で False になることを確認
        orig = sys.modules.get("paddleocr")
        sys.modules["paddleocr"] = None  # type: ignore[assignment]
        try:
            backend = PaddleOCRBackend()
            result = backend.is_available()
            assert result is False
        finally:
            if orig is None:
                sys.modules.pop("paddleocr", None)
            else:
                sys.modules["paddleocr"] = orig

    def test_paddle_is_available_true_when_installed(self, monkeypatch):
        """paddleocr が import できる場合は True"""
        import sys
        from unittest.mock import MagicMock
        fake_paddle = MagicMock()
        monkeypatch.setitem(sys.modules, "paddleocr", fake_paddle)
        from pdf_split_autorenamer.ocr_backend import PaddleOCRBackend
        backend = PaddleOCRBackend()
        assert backend.is_available() is True


# ---------------------------------------------------------------------------
# TesseractBackend 追加カバレッジ
# ---------------------------------------------------------------------------

class TestTesseractBackendEdgeCases:
    def test_tessdata_warning_returns_empty(self, monkeypatch):
        """tessdata が見つからない場合は警告して空文字を返す（lines 68-72）"""
        from unittest.mock import patch, MagicMock
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        backend = TesseractBackend(executable="/fake/tesseract")
        monkeypatch.setattr(backend, "_exe", "/fake/tesseract")
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = b""
        mock_proc.stderr = b"Error, could not initialize tesseract tessdata"
        with patch("subprocess.run", return_value=mock_proc):
            result = backend.extract_text(b"fake_image_bytes")
        assert result == ""

    def test_subprocess_exception_returns_empty(self, monkeypatch):
        """subprocess.run が例外を送出した場合は空文字を返す（lines 74-75）"""
        from unittest.mock import patch
        from pdf_split_autorenamer.ocr_backend import TesseractBackend
        backend = TesseractBackend(executable="/fake/tesseract")
        monkeypatch.setattr(backend, "_exe", "/fake/tesseract")
        with patch("subprocess.run", side_effect=OSError("not found")):
            result = backend.extract_text(b"fake_image_bytes")
        assert result == ""


# ---------------------------------------------------------------------------
# load_psar_config
# ---------------------------------------------------------------------------

class TestLoadPsarConfig:
    def test_returns_empty_when_no_config_file(self, tmp_path):
        """config.toml が存在しない場合は空 dict"""
        from pdf_split_autorenamer.ocr_backend import load_psar_config
        result = load_psar_config(tmp_path)
        assert result == {}

    def test_returns_config_when_file_exists(self, tmp_path):
        """config.toml が存在する場合は内容を返す"""
        from pdf_split_autorenamer.ocr_backend import load_psar_config
        psar = tmp_path / ".psar"
        psar.mkdir()
        (psar / "config.toml").write_text('[ocr]\nstrategy = "balanced"\n', encoding="utf-8")
        result = load_psar_config(tmp_path)
        assert result.get("ocr", {}).get("strategy") == "balanced"

    def test_returns_empty_when_tomllib_none(self, tmp_path, monkeypatch):
        """tomllib が None（未インストール）の場合は空 dict（lines 154-155）"""
        import pdf_split_autorenamer.ocr_backend as mod
        psar = tmp_path / ".psar"
        psar.mkdir()
        (psar / "config.toml").write_text('[ocr]\nstrategy = "balanced"\n', encoding="utf-8")
        orig = mod.tomllib
        monkeypatch.setattr(mod, "tomllib", None)
        try:
            result = mod.load_psar_config(tmp_path)
        finally:
            mod.tomllib = orig
        assert result == {}

    def test_returns_empty_on_parse_error(self, tmp_path):
        """config.toml が壊れている場合は空 dict（lines 160-162）"""
        from pdf_split_autorenamer.ocr_backend import load_psar_config
        psar = tmp_path / ".psar"
        psar.mkdir()
        (psar / "config.toml").write_bytes(b"\xff\xfe invalid toml")
        result = load_psar_config(tmp_path)
        assert result == {}


# ---------------------------------------------------------------------------
# get_api_key
# ---------------------------------------------------------------------------

class TestGetApiKey:
    def test_returns_env_var(self, monkeypatch):
        """環境変数が設定されている場合はそれを返す"""
        from pdf_split_autorenamer.ocr_backend import get_api_key
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-abc")
        result = get_api_key("anthropic")
        assert result == "test-key-abc"

    def test_returns_none_when_no_key(self, monkeypatch):
        """環境変数も keyring もない場合は None"""
        import sys
        from pdf_split_autorenamer.ocr_backend import get_api_key
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # keyring が未インストールの場合をシミュレート
        orig = sys.modules.get("keyring")
        sys.modules["keyring"] = None  # type: ignore[assignment]
        try:
            result = get_api_key("anthropic")
        finally:
            if orig is None:
                sys.modules.pop("keyring", None)
            else:
                sys.modules["keyring"] = orig
        assert result is None

    def test_uses_keyring_fallback(self, monkeypatch):
        """keyring にキーがある場合は keyring から返す（lines 185-187）"""
        import sys
        from unittest.mock import MagicMock
        from pdf_split_autorenamer.ocr_backend import get_api_key
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        fake_keyring = MagicMock()
        fake_keyring.get_password.return_value = "keyring-key-xyz"
        monkeypatch.setitem(sys.modules, "keyring", fake_keyring)
        result = get_api_key("anthropic")
        assert result == "keyring-key-xyz"


# ---------------------------------------------------------------------------
# ClaudeVisionBackend
# ---------------------------------------------------------------------------

class TestClaudeVisionBackend:
    def test_is_available_false_when_no_api_key(self, monkeypatch):
        """APIキーなしは False"""
        import sys
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        sys.modules.pop("keyring", None)
        backend = ClaudeVisionBackend(api_key=None)
        assert backend.is_available() is False

    def test_is_available_true_when_anthropic_importable(self, monkeypatch):
        """anthropic が import できて API キーがある場合は True（lines 239-240）"""
        import sys
        from unittest.mock import MagicMock
        fake_anthropic = MagicMock()
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key="test-key")
        assert backend.is_available() is True

    def test_is_available_false_when_anthropic_not_importable(self, monkeypatch):
        """anthropic が import できない場合は False（lines 239-240 ImportError 分岐）"""
        import sys
        # anthropic を一時的に import 不可にする
        if "anthropic" in sys.modules:
            monkeypatch.delitem(sys.modules, "anthropic")
        from unittest.mock import patch
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key="test-key")
        with patch("builtins.__import__", side_effect=lambda name, *a, **kw: (
            (_ for _ in ()).throw(ImportError("No module named 'anthropic'"))
            if name == "anthropic" else __import__(name, *a, **kw)
        )):
            result = backend.is_available()
        assert result is False

    def test_extract_text_returns_empty_when_unavailable(self, monkeypatch):
        """利用不可のとき extract_text は空文字"""
        import sys
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        sys.modules.pop("keyring", None)
        backend = ClaudeVisionBackend(api_key=None)
        assert backend.extract_text(b"fake") == ""

    def test_extract_text_calls_api(self, monkeypatch):
        """利用可能なとき API を呼び出してテキストを返す（lines 245-263）"""
        import sys
        from unittest.mock import MagicMock, patch
        fake_anthropic = MagicMock()
        mock_client = MagicMock()
        fake_anthropic.Anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="OCR結果テキスト")]
        mock_client.messages.create.return_value = mock_message
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key="test-key")
        result = backend.extract_text(b"fake_image")
        assert result == "OCR結果テキスト"

    def test_extract_text_exception_returns_empty(self, monkeypatch):
        """API 呼び出しで例外が発生した場合は空文字（lines 261-263）"""
        import sys
        from unittest.mock import MagicMock
        fake_anthropic = MagicMock()
        mock_client = MagicMock()
        fake_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("API error")
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key="test-key")
        result = backend.extract_text(b"fake_image")
        assert result == ""

    def test_extract_structured_returns_empty_when_unavailable(self, monkeypatch):
        """利用不可のとき extract_structured はデフォルト dict"""
        import sys
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        sys.modules.pop("keyring", None)
        backend = ClaudeVisionBackend(api_key=None)
        result = backend.extract_structured(b"fake")
        assert result == {"date": None, "title": None, "text": ""}

    def test_extract_structured_calls_api(self, monkeypatch):
        """利用可能なとき構造化 API を呼び出す（lines 268-288）"""
        import sys
        from unittest.mock import MagicMock
        fake_anthropic = MagicMock()
        mock_client = MagicMock()
        fake_anthropic.Anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"date": "2026-05-11", "title": "週報"}')]
        mock_client.messages.create.return_value = mock_message
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key="test-key")
        result = backend.extract_structured(b"fake_image")
        assert result["date"] == "2026-05-11"
        assert result["title"] == "週報"

    def test_extract_structured_exception_returns_default(self, monkeypatch):
        """構造化 API で例外が発生した場合はデフォルト dict"""
        import sys
        from unittest.mock import MagicMock
        fake_anthropic = MagicMock()
        mock_client = MagicMock()
        fake_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("API error")
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
        from pdf_split_autorenamer.ocr_backend import ClaudeVisionBackend
        backend = ClaudeVisionBackend(api_key="test-key")
        result = backend.extract_structured(b"fake_image")
        assert result == {"date": None, "title": None}


# ---------------------------------------------------------------------------
# GPT4VisionBackend
# ---------------------------------------------------------------------------

class TestGPT4VisionBackend:
    def test_is_available_false_when_no_api_key(self, monkeypatch):
        """API キーなしは False"""
        from pdf_split_autorenamer.ocr_backend import GPT4VisionBackend
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        backend = GPT4VisionBackend()
        assert backend.is_available() is False

    def test_is_available_true_when_openai_importable(self, monkeypatch):
        """openai が import できて API キーがある場合は True（lines 298-304）"""
        import sys
        from unittest.mock import MagicMock
        fake_openai = MagicMock()
        monkeypatch.setitem(sys.modules, "openai", fake_openai)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from pdf_split_autorenamer.ocr_backend import GPT4VisionBackend
        backend = GPT4VisionBackend()
        assert backend.is_available() is True

    def test_is_available_false_when_openai_not_importable(self, monkeypatch):
        """openai が import できない場合は False（lines 303-304 ImportError 分岐）"""
        import sys
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        if "openai" in sys.modules:
            monkeypatch.delitem(sys.modules, "openai")
        from unittest.mock import patch
        from pdf_split_autorenamer.ocr_backend import GPT4VisionBackend
        backend = GPT4VisionBackend()
        with patch("builtins.__import__", side_effect=lambda name, *a, **kw: (
            (_ for _ in ()).throw(ImportError("No module named 'openai'"))
            if name == "openai" else __import__(name, *a, **kw)
        )):
            result = backend.is_available()
        assert result is False

    def test_extract_text_raises_not_implemented(self):
        """GPT4VisionBackend.extract_text は NotImplementedError"""
        from pdf_split_autorenamer.ocr_backend import GPT4VisionBackend
        with pytest.raises(NotImplementedError):
            GPT4VisionBackend().extract_text(b"fake")


# ---------------------------------------------------------------------------
# OcrStrategy
# ---------------------------------------------------------------------------

class TestOcrStrategy:
    def test_valid_strategy_accepted(self):
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        s = OcrStrategy("balanced")
        assert s.strategy == "balanced"

    def test_invalid_strategy_raises(self):
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        with pytest.raises(ValueError):
            OcrStrategy("invalid_strategy")

    def test_roi_ratio_default(self):
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        s = OcrStrategy()
        assert s.roi_ratio == 0.3


# ---------------------------------------------------------------------------
# validate_structured_output
# ---------------------------------------------------------------------------

class TestValidateStructuredOutput:
    def test_valid_dict_passthrough(self):
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        result = validate_structured_output({"date": "2026-05-11", "title": "週報"})
        assert result["date"] == "2026-05-11"
        assert result["title"] == "週報"

    def test_invalid_date_replaced_with_none(self):
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        result = validate_structured_output({"date": "不明", "title": "テスト"})
        assert result["date"] is None

    def test_non_dict_raises_type_error(self):
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        with pytest.raises(TypeError):
            validate_structured_output("not a dict")

    def test_none_title_preserved(self):
        from pdf_split_autorenamer.ocr_backend import validate_structured_output
        result = validate_structured_output({"date": None, "title": None})
        assert result["title"] is None


# ---------------------------------------------------------------------------
# PaddleOCRBackend（T-13）
# ---------------------------------------------------------------------------

class TestPaddleOCRBackend:
    def test_extract_text_returns_empty_when_not_installed(self, monkeypatch):
        """paddleocr 未インストール時は空文字を返す"""
        import sys
        from pdf_split_autorenamer.ocr_backend import PaddleOCRBackend
        monkeypatch.setitem(sys.modules, "paddleocr", None)  # type: ignore[arg-type]
        backend = PaddleOCRBackend()
        result = backend.extract_text(b"fake_image")
        assert result == ""

    def test_extract_text_success_with_mock(self, monkeypatch):
        """paddleocr が利用可能な場合、テキストを結合して返す"""
        import sys
        from unittest.mock import MagicMock
        fake_paddle_mod = MagicMock()
        fake_ocr_instance = MagicMock()
        fake_paddle_mod.PaddleOCR.return_value = fake_ocr_instance
        fake_ocr_instance.ocr.return_value = [
            [
                [[0, 0, 1, 1], ("2026年4月6日", 0.99)],
                [[0, 20, 1, 40], ("主日礼拝", 0.95)],
            ]
        ]
        monkeypatch.setitem(sys.modules, "paddleocr", fake_paddle_mod)
        from pdf_split_autorenamer.ocr_backend import PaddleOCRBackend
        backend = PaddleOCRBackend()
        result = backend.extract_text(b"fake_image")
        assert "2026年4月6日" in result
        assert "主日礼拝" in result

    def test_extract_text_empty_result(self, monkeypatch):
        """OCR 結果が空の場合は空文字を返す"""
        import sys
        from unittest.mock import MagicMock
        fake_paddle_mod = MagicMock()
        fake_ocr_instance = MagicMock()
        fake_paddle_mod.PaddleOCR.return_value = fake_ocr_instance
        fake_ocr_instance.ocr.return_value = [None]
        monkeypatch.setitem(sys.modules, "paddleocr", fake_paddle_mod)
        from pdf_split_autorenamer.ocr_backend import PaddleOCRBackend
        backend = PaddleOCRBackend()
        result = backend.extract_text(b"fake_image")
        assert result == ""

    def test_extract_text_exception_returns_empty(self, monkeypatch):
        """OCR 実行時に例外が発生した場合は空文字を返す"""
        import sys
        from unittest.mock import MagicMock
        fake_paddle_mod = MagicMock()
        fake_paddle_mod.PaddleOCR.side_effect = RuntimeError("GPU エラー")
        monkeypatch.setitem(sys.modules, "paddleocr", fake_paddle_mod)
        from pdf_split_autorenamer.ocr_backend import PaddleOCRBackend
        backend = PaddleOCRBackend()
        result = backend.extract_text(b"fake_image")
        assert result == ""


# ---------------------------------------------------------------------------
# EasyOCRBackend（T-13）
# ---------------------------------------------------------------------------

class TestEasyOCRBackend:
    def test_is_available_false_when_not_installed(self, monkeypatch):
        """easyocr 未インストール時は False"""
        import sys
        monkeypatch.setitem(sys.modules, "easyocr", None)  # type: ignore[arg-type]
        from pdf_split_autorenamer.ocr_backend import EasyOCRBackend
        backend = EasyOCRBackend()
        assert backend.is_available() is False

    def test_is_available_true_when_installed(self, monkeypatch):
        """easyocr がインポートできる場合は True"""
        import sys
        from unittest.mock import MagicMock
        monkeypatch.setitem(sys.modules, "easyocr", MagicMock())
        from pdf_split_autorenamer.ocr_backend import EasyOCRBackend
        backend = EasyOCRBackend()
        assert backend.is_available() is True

    def test_extract_text_returns_empty_when_not_installed(self, monkeypatch):
        """easyocr 未インストール時は空文字を返す"""
        import sys
        monkeypatch.setitem(sys.modules, "easyocr", None)  # type: ignore[arg-type]
        from pdf_split_autorenamer.ocr_backend import EasyOCRBackend
        backend = EasyOCRBackend()
        result = backend.extract_text(b"fake_image")
        assert result == ""

    def test_extract_text_success_with_mock(self, monkeypatch):
        """easyocr が利用可能な場合、テキストを結合して返す"""
        import sys
        from unittest.mock import MagicMock, patch
        fake_easyocr = MagicMock()
        fake_reader = MagicMock()
        fake_easyocr.Reader.return_value = fake_reader
        fake_reader.readtext.return_value = ["2026年4月6日", "主日礼拝"]
        monkeypatch.setitem(sys.modules, "easyocr", fake_easyocr)
        with patch("PIL.Image.open") as mock_open:
            mock_open.return_value = MagicMock()
            from pdf_split_autorenamer.ocr_backend import EasyOCRBackend
            backend = EasyOCRBackend()
            result = backend.extract_text(b"fake_image")
        assert "2026年4月6日" in result
        assert "主日礼拝" in result

    def test_extract_text_exception_returns_empty(self, monkeypatch):
        """OCR 実行時に例外が発生した場合は空文字を返す"""
        import sys
        from unittest.mock import MagicMock
        fake_easyocr = MagicMock()
        fake_easyocr.Reader.side_effect = RuntimeError("モデル読み込みエラー")
        monkeypatch.setitem(sys.modules, "easyocr", fake_easyocr)
        from pdf_split_autorenamer.ocr_backend import EasyOCRBackend
        backend = EasyOCRBackend()
        result = backend.extract_text(b"fake_image")
        assert result == ""
