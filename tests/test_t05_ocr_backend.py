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
        "PaddleOCRBackend",
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
