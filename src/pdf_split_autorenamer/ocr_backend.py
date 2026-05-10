# -*- coding: utf-8 -*-
"""プラガブル OCR バックエンド抽象クラスと各実装"""
from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod


class OcrBackend(ABC):
    """OCR バックエンドの抽象基底クラス。"""

    @abstractmethod
    def is_available(self) -> bool:
        """このバックエンドが実行可能な環境かどうかを返す。"""

    @abstractmethod
    def extract_text(self, image_bytes: bytes, lang: str = "jpn") -> str:
        """画像バイト列からテキストを抽出して返す。失敗時は空文字列。"""

    def extract_structured(self, image_bytes: bytes, lang: str = "jpn") -> dict:
        """画像から構造化情報（テキスト等）を抽出して dict で返す。
        デフォルトは extract_text の結果を {"text": ...} にラップ。"""
        return {"text": self.extract_text(image_bytes, lang)}


class TesseractBackend(OcrBackend):
    """Tesseract OCR バックエンド（T-01 の実装を昇格）。"""

    def __init__(self, executable: str | None = None) -> None:
        if executable is not None:
            self._exe: str | None = executable
        else:
            from .pdfio import find_tesseract
            self._exe = find_tesseract()

    def is_available(self) -> bool:
        return self._exe is not None

    def extract_text(self, image_bytes: bytes, lang: str = "jpn") -> str:
        if not self._exe:
            return ""
        cmd = [self._exe, "stdin", "stdout", "-l", lang, "--psm", "3"]
        try:
            result = subprocess.run(
                cmd,
                input=image_bytes,
                capture_output=True,
                timeout=30,
            )
            stderr = result.stderr.decode("utf-8", errors="replace")
            if "tessdata" in stderr:
                logging.warning(
                    "Tesseract jpn traineddata が見つかりません。"
                    "インストール方法: https://github.com/UB-Mannheim/tesseract/wiki"
                )
                return ""
            return result.stdout.decode("utf-8", errors="replace")
        except Exception:
            return ""


class PaddleOCRBackend(OcrBackend):
    """PaddleOCR バックエンド（スタブ）。

    有効化: pip install paddleocr
    """

    def is_available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_text(self, image_bytes: bytes, lang: str = "jpn") -> str:
        raise NotImplementedError(
            "PaddleOCRBackend は未実装です。T-13 で実装予定。"
        )


class AzureReadBackend(OcrBackend):
    """Azure AI Vision Read API バックエンド（スタブ）。

    有効化: pip install azure-cognitiveservices-vision-computervision
    """

    def is_available(self) -> bool:
        return False

    def extract_text(self, image_bytes: bytes, lang: str = "jpn") -> str:
        raise NotImplementedError(
            "AzureReadBackend は未実装です。T-07 で実装予定。"
        )


class GoogleVisionBackend(OcrBackend):
    """Google Cloud Vision OCR バックエンド（スタブ）。

    有効化: pip install google-cloud-vision
    """

    def is_available(self) -> bool:
        return False

    def extract_text(self, image_bytes: bytes, lang: str = "jpn") -> str:
        raise NotImplementedError(
            "GoogleVisionBackend は未実装です。T-07 で実装予定。"
        )
