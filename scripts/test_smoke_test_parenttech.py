#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("smoke_test_parenttech.py")
SPEC = importlib.util.spec_from_file_location("smoke_test_parenttech", SCRIPT)
smoke = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = smoke
SPEC.loader.exec_module(smoke)


class FakeBrowser:
    def close(self) -> None:
        pass


class FakeChromium:
    def launch(self, headless: bool = True) -> FakeBrowser:
        return FakeBrowser()


class FailingChromium:
    def launch(self, headless: bool = True) -> FakeBrowser:
        raise RuntimeError("browser missing")


class FakePlaywright:
    chromium = FakeChromium()


class FailingPlaywright:
    chromium = FailingChromium()


class FakeSyncPlaywright:
    def __init__(self, playwright=None) -> None:
        self.playwright = playwright or FakePlaywright()

    def __enter__(self) -> FakePlaywright:
        return self.playwright

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class SmokeTestParentTechTests(unittest.TestCase):
    def test_run_smoke_writes_report_when_page_check_raises(self) -> None:
        original_assets = smoke.assert_http_assets
        original_sync = smoke.sync_playwright
        original_check_page = smoke.check_page
        original_page_checks = smoke.PAGE_CHECKS
        original_viewports = smoke.VIEWPORTS
        smoke.assert_http_assets = lambda base_url: []
        smoke.sync_playwright = lambda: FakeSyncPlaywright()
        smoke.check_page = lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("page timeout"))
        smoke.PAGE_CHECKS = [{"path": "/disclosure"}]
        smoke.VIEWPORTS = {"desktop": {"width": 1440, "height": 1100}}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = smoke.run_smoke("https://example.test", Path(tmp), False, 100)
                self.assertFalse(report["ok"])
                self.assertEqual(len(report["failed"]), 1)
                self.assertIn("desktop /disclosure page check", report["failed"][0]["name"])
                self.assertTrue((Path(tmp) / "smoke-report.json").exists())
                self.assertTrue((Path(tmp) / "smoke-report.md").exists())
        finally:
            smoke.assert_http_assets = original_assets
            smoke.sync_playwright = original_sync
            smoke.check_page = original_check_page
            smoke.PAGE_CHECKS = original_page_checks
            smoke.VIEWPORTS = original_viewports

    def test_run_smoke_writes_report_when_browser_launch_fails(self) -> None:
        original_assets = smoke.assert_http_assets
        original_sync = smoke.sync_playwright
        smoke.assert_http_assets = lambda base_url: []
        smoke.sync_playwright = lambda: FakeSyncPlaywright(FailingPlaywright())
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = smoke.run_smoke("https://example.test", Path(tmp), False, 100)
                self.assertFalse(report["ok"])
                self.assertEqual(len(report["failed"]), 1)
                self.assertEqual(report["failed"][0]["name"], "browser smoke runner")
                self.assertEqual(report["failed"][0]["details"]["error_type"], "RuntimeError")
                self.assertTrue((Path(tmp) / "smoke-report.json").exists())
                self.assertTrue((Path(tmp) / "smoke-report.md").exists())
        finally:
            smoke.assert_http_assets = original_assets
            smoke.sync_playwright = original_sync


if __name__ == "__main__":
    unittest.main()
