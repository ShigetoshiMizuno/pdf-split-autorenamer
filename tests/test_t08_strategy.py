# -*- coding: utf-8 -*-
"""T-08: OcrStrategy クラスと .psar/config.toml 読み込みの検証テスト"""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# OcrStrategy クラス
# ---------------------------------------------------------------------------

class TestOcrStrategy:
    def test_importable(self):
        """OcrStrategy がインポートできる"""
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        assert OcrStrategy is not None

    def test_default_strategy_balanced(self):
        """デフォルト戦略は balanced"""
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        s = OcrStrategy()
        assert s.strategy == "balanced"

    def test_valid_strategy_values(self):
        """fast / balanced / roi / thorough / llm が受け付けられる"""
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        for strategy in ("fast", "balanced", "roi", "thorough", "llm"):
            s = OcrStrategy(strategy=strategy)
            assert s.strategy == strategy

    def test_invalid_strategy_raises(self):
        """不正な strategy は ValueError"""
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        with pytest.raises(ValueError):
            OcrStrategy(strategy="unknown")

    def test_roi_ratio_default(self):
        """roi_ratio のデフォルトは 0.3"""
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        s = OcrStrategy()
        assert s.roi_ratio == pytest.approx(0.3)

    def test_roi_ratio_custom(self):
        """roi_ratio をカスタム設定できる"""
        from pdf_split_autorenamer.ocr_backend import OcrStrategy
        s = OcrStrategy(roi_ratio=0.5)
        assert s.roi_ratio == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# .psar/config.toml 読み込み
# ---------------------------------------------------------------------------

class TestPsarConfig:
    def test_load_psar_config(self, tmp_path):
        """load_psar_config が .psar/config.toml を読む"""
        from pdf_split_autorenamer.ocr_backend import load_psar_config
        config_dir = tmp_path / ".psar"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text(
            '[analyze]\nocr_strategy = "roi"\nroi_ratio = 0.4\n'
            '[rename]\nprofile = "profiles/church.toml"\n',
            encoding="utf-8",
        )
        cfg = load_psar_config(tmp_path)
        assert cfg["analyze"]["ocr_strategy"] == "roi"
        assert cfg["analyze"]["roi_ratio"] == pytest.approx(0.4)
        assert cfg["rename"]["profile"] == "profiles/church.toml"

    def test_load_psar_config_missing(self, tmp_path):
        """config.toml がない場合は空 dict"""
        from pdf_split_autorenamer.ocr_backend import load_psar_config
        cfg = load_psar_config(tmp_path)
        assert cfg == {}

    def test_load_psar_config_empty(self, tmp_path):
        """空の config.toml は空 dict"""
        from pdf_split_autorenamer.ocr_backend import load_psar_config
        config_dir = tmp_path / ".psar"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text("", encoding="utf-8")
        cfg = load_psar_config(tmp_path)
        assert cfg == {}

    def test_ocr_strategy_from_config(self, tmp_path):
        """OcrStrategy が config.toml から設定を読める"""
        from pdf_split_autorenamer.ocr_backend import OcrStrategy, load_psar_config
        config_dir = tmp_path / ".psar"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text(
            '[analyze]\nocr_strategy = "roi"\nroi_ratio = 0.5\n',
            encoding="utf-8",
        )
        cfg = load_psar_config(tmp_path)
        analyze_cfg = cfg.get("analyze", {})
        s = OcrStrategy(
            strategy=analyze_cfg.get("ocr_strategy", "balanced"),
            roi_ratio=analyze_cfg.get("roi_ratio", 0.3),
        )
        assert s.strategy == "roi"
        assert s.roi_ratio == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# CLI --ocr-strategy 拡張
# ---------------------------------------------------------------------------

class TestCliOcrStrategyChoices:
    def test_cli_accepts_thorough(self):
        """CLI が --ocr-strategy thorough を受け付ける"""
        import argparse
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["analyze", ".", "--ocr-strategy", "thorough"])
        assert args.ocr_strategy == "thorough"

    def test_cli_accepts_llm(self):
        """CLI が --ocr-strategy llm を受け付ける"""
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["analyze", ".", "--ocr-strategy", "llm"])
        assert args.ocr_strategy == "llm"

    def test_cli_rejects_invalid(self):
        """CLI が不正な --ocr-strategy を拒否する"""
        import sys
        from pdf_split_autorenamer.cli import build_parser
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["analyze", ".", "--ocr-strategy", "invalid"])
