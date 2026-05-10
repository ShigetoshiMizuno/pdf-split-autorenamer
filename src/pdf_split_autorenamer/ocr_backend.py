# -*- coding: utf-8 -*-
"""プラガブル OCR バックエンド抽象クラスと各実装"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-reattr-module]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

_VALID_STRATEGIES = frozenset({"fast", "balanced", "roi", "thorough", "llm"})


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


class OcrStrategy:
    """OCR 戦略設定。Stage 1〜llm を順次試す方針を保持する。

    strategy:
        "fast"     — Stage 1 のみ（pdftotext / PyMuPDF）
        "balanced" — Stage 1 + テキスト空なら Tesseract
        "roi"      — Stage 1 + 品質低時に上部 ROI クロップ + Tesseract
        "thorough" — roi + 全ページ Tesseract（将来実装）
        "llm"      — roi + LLM Vision（T-07 で実装）
    """

    def __init__(self, strategy: str = "balanced", roi_ratio: float = 0.3) -> None:
        if strategy not in _VALID_STRATEGIES:
            raise ValueError(
                f"不正な OCR 戦略: {strategy!r}。有効値: {sorted(_VALID_STRATEGIES)}"
            )
        self.strategy = strategy
        self.roi_ratio = roi_ratio


def load_psar_config(project_dir: Path) -> dict:
    """project_dir/.psar/config.toml を読み込んで dict で返す。
    ファイルが存在しないか空の場合は空 dict を返す。"""
    config_path = project_dir / ".psar" / "config.toml"
    if not config_path.exists():
        return {}
    if tomllib is None:
        logging.warning("tomllib が利用できないため config.toml を読み込めません")
        return {}
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        return data
    except Exception as e:
        logging.warning("config.toml の読み込みに失敗しました: %s", e)
        return {}


# ---------------------------------------------------------------------------
# API キー管理
# ---------------------------------------------------------------------------

_API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def get_api_key(service: str) -> str | None:
    """指定サービスの API キーを取得する。
    優先順位: 環境変数 → keyring → None
    """
    env_var = _API_KEY_ENV.get(service, f"{service.upper()}_API_KEY")
    key = os.environ.get(env_var)
    if key:
        return key
    try:
        import keyring
        key = keyring.get_password("pdf-split-autorenamer", service)
        if key:
            return key
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# LLM Vision バックエンド
# ---------------------------------------------------------------------------

_STRUCTURED_EXTRACTION_PROMPT = (
    "この画像のPDFページから日付とタイトルを抽出してください。\n"
    'JSON 形式のみで回答してください（説明不要）: {"date": "YYYY-MM-DD または null", "title": "タイトルまたは null"}'
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_structured_output(data: object) -> dict:
    """LLM の構造化出力を検証して正規化する。
    入力が dict でない場合は ValueError/TypeError を送出。
    date が YYYY-MM-DD 形式でない場合は None に変換。
    """
    if not isinstance(data, dict):
        raise TypeError(f"dict が必要ですが {type(data).__name__} が渡されました")
    date_val = data.get("date")
    if date_val is not None:
        if not isinstance(date_val, str) or not _DATE_RE.match(date_val):
            date_val = None
    title_val = data.get("title") or None
    return {"date": date_val, "title": title_val}


class ClaudeVisionBackend(OcrBackend):
    """Claude Vision API を使う LLM OCR バックエンド（T-07 実装）。

    有効化: pip install anthropic
    API キー: 環境変数 ANTHROPIC_API_KEY または keyring
    """

    _MODEL = "claude-haiku-4-5-20251001"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or get_api_key("anthropic")
        self._model = model or self._MODEL

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_text(self, image_bytes: bytes, lang: str = "jpn") -> str:
        if not self.is_available():
            return ""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key)
            b64 = base64.standard_b64encode(image_bytes).decode()
            message = client.messages.create(
                model=self._model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        {"type": "text", "text": "この画像のテキストをすべて読み取ってください。"},
                    ],
                }],
            )
            return message.content[0].text if message.content else ""
        except Exception as e:
            logging.warning("Claude Vision API エラー: %s", e)
            return ""

    def extract_structured(self, image_bytes: bytes, lang: str = "jpn") -> dict:
        if not self.is_available():
            return {"date": None, "title": None, "text": ""}
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key)
            b64 = base64.standard_b64encode(image_bytes).decode()
            message = client.messages.create(
                model=self._model,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        {"type": "text", "text": _STRUCTURED_EXTRACTION_PROMPT},
                    ],
                }],
            )
            raw = message.content[0].text if message.content else "{}"
            data = json.loads(raw)
            return validate_structured_output(data)
        except Exception as e:
            logging.warning("Claude Vision 構造化抽出エラー: %s", e)
            return {"date": None, "title": None}


class GPT4VisionBackend(OcrBackend):
    """GPT-4 Vision バックエンド（スタブ）。

    有効化: pip install openai
    """

    def is_available(self) -> bool:
        if not get_api_key("openai"):
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_text(self, image_bytes: bytes, lang: str = "jpn") -> str:
        raise NotImplementedError(
            "GPT4VisionBackend は未実装です。T-07 v2 で実装予定。"
        )
