#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_metric_improvement_predeploy_gate.py")
SPEC = importlib.util.spec_from_file_location("check_metric_improvement_predeploy_gate", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(gate)


class ParentTechMetricImprovementPredeployGateTests(unittest.TestCase):
    def run_report(
        self,
        local: dict,
        live: dict,
        *,
        head: str = "49994ff",
        origin: str = "9f02de6",
        ahead: str = "1",
        approved: bool = False,
        dirty: str = "",
    ) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_path = tmp_path / "local.json"
            live_path = tmp_path / "live.json"
            local_path.write_text(json.dumps(local), encoding="utf-8")
            live_path.write_text(json.dumps(live), encoding="utf-8")

            def fake_git(args: list[str], *, cwd=gate.SITE_DIR) -> str:
                if args == ["rev-parse", "--short", "HEAD"]:
                    return head
                if args == ["rev-parse", "--short", "origin/main"]:
                    return origin
                if args == ["rev-list", "--count", "origin/main..HEAD"]:
                    return ahead
                if args == ["status", "--short"]:
                    return dirty
                return ""

            original = gate.git_output
            try:
                gate.git_output = fake_git
                return gate.build_report(
                    argparse.Namespace(
                        local_smoke_json=local_path,
                        live_smoke_json=live_path,
                        out_dir=tmp_path / "out",
                        external_publish_approved=approved,
                    )
                )
            finally:
                gate.git_output = original

    def test_ready_when_only_live_failures_are_expected_predeploy_delta(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report({"ok": True, "failed": []}, live)

        self.assertEqual(report["status"], "ready_for_explicit_publish_approval")
        self.assertTrue(report["live_smoke"]["live_delta_matches_unpublished_local_copy"])
        self.assertTrue(report["local_unpublished_change_ready"])
        self.assertEqual(report["rules"]["no_external_publish"], True)

    def test_ready_when_live_failures_are_expected_subset(self) -> None:
        live = {
            "ok": False,
            "failed": [
                {"name": "desktop /go/parent-tech-quick-start-kit text No sensitive details needed", "details": {}},
                {"name": "mobile /go/parent-tech-quick-start-kit text No sensitive details needed", "details": {}},
            ],
        }
        report = self.run_report({"ok": True, "failed": []}, live)

        self.assertEqual(report["status"], "ready_for_explicit_publish_approval")
        self.assertTrue(report["live_smoke"]["live_delta_matches_unpublished_local_copy"])
        self.assertGreater(len(report["live_smoke"]["missing_expected_live_delta"]), 0)

    def test_expected_delta_covers_checkout_pause_v2_copy(self) -> None:
        self.assertIn("desktop / text Buy on Gumroad", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop / text The paid kit is a one-time Gumroad download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop / link /go/parent-tech-quick-start-kit", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text $9 one-time digital download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text Printable worksheets", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text No sensitive details needed", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/parent-tech-quick-start-kit text First 30 minutes after download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/parent-tech-quick-start-kit text Checkout readiness", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/parent-tech-quick-start-kit text free worksheet preview first", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/parent-tech-quick-start-kit text PDF worksheets in a ZIP download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/parent-tech-quick-start-kit text Know the files before checkout", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/parent-tech-quick-start-kit text 01-7-Day-Parent-Tech-Setup-Plan.pdf", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/parent-tech-quick-start-kit text 05-Living-Alone-Tech-Comparison-Worksheet.pdf", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/parent-tech-quick-start-kit text Know what to send", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/personalized-setup-review text What you would get back", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/personalized-setup-review text worksheet name, the main family concern", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /products/personalized-setup-review text I will not send passwords", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text What you get", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text Ready to buy when", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text I understand, continue to Gumroad", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text about five seconds", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text Files included after purchase", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text 01-7-Day-Parent-Tech-Setup-Plan.pdf", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text $9 one-time digital download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text Printable worksheets", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text No sensitive details needed", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/parent-tech-quick-start-kit text First 30 minutes after download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/parent-tech-quick-start-kit text Checkout readiness", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/parent-tech-quick-start-kit text free worksheet preview first", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/parent-tech-quick-start-kit text PDF worksheets in a ZIP download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/parent-tech-quick-start-kit text Know the files before checkout", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/parent-tech-quick-start-kit text 01-7-Day-Parent-Tech-Setup-Plan.pdf", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/parent-tech-quick-start-kit text 05-Living-Alone-Tech-Comparison-Worksheet.pdf", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/parent-tech-quick-start-kit text Know what to send", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/personalized-setup-review text What you would get back", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/personalized-setup-review text Example outcome", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /products/personalized-setup-review text I will not send passwords", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text What this is not", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text Files included after purchase", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text 01-7-Day-Parent-Tech-Setup-Plan.pdf", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text Need to preview the format first?", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text Preview a free worksheet PDF", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit link /downloads/scam-call-safety-checklist.pdf", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile / text Buy on Gumroad", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile / text The paid kit is a one-time Gumroad download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile / link /go/parent-tech-quick-start-kit", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text Need to preview the format first?", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text Preview a free worksheet PDF", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text Ready to buy when", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text I understand, continue to Gumroad", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text about five seconds", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit link /downloads/scam-call-safety-checklist.pdf", gate.EXPECTED_LIVE_DELTA_FAILURES)

    def test_blocks_unexpected_live_failure(self) -> None:
        live = {"ok": False, "failed": [{"name": "desktop / broken unexpected", "details": {}}]}
        report = self.run_report({"ok": True, "failed": []}, live)

        self.assertEqual(report["status"], "blocked_unexpected_live_regression")
        self.assertEqual(report["live_smoke"]["unexpected_live_failures"], ["desktop / broken unexpected"])

    def test_allows_known_live_medication_image_delta_only(self) -> None:
        live = {
            "ok": False,
            "failed": [
                {
                    "name": "desktop / images load",
                    "details": {"broken_images": ["https://parenttechchecklist.com/assets/medication-reminder-hero.jpg"]},
                },
                {"name": "desktop / no console errors", "details": {"errors": ["Failed to load resource: 404"]}},
                {
                    "name": "mobile / images load",
                    "details": {"broken_images": ["https://parenttechchecklist.com/assets/medication-reminder-hero.jpg"]},
                },
                {"name": "mobile / no console errors", "details": {"errors": ["Failed to load resource: 404"]}},
            ],
        }
        report = self.run_report({"ok": True, "failed": []}, live)

        self.assertEqual(report["status"], "ready_for_explicit_publish_approval")
        self.assertEqual(report["live_smoke"]["unexpected_live_failures"], [])

    def test_blocks_unknown_live_broken_image_delta(self) -> None:
        live = {
            "ok": False,
            "failed": [
                {
                    "name": "desktop / images load",
                    "details": {"broken_images": ["https://parenttechchecklist.com/assets/unknown.jpg"]},
                },
                {"name": "desktop / no console errors", "details": {"errors": ["Failed to load resource: 404"]}},
            ],
        }
        report = self.run_report({"ok": True, "failed": []}, live)

        self.assertEqual(report["status"], "blocked_unexpected_live_regression")
        self.assertIn("desktop / images load", report["live_smoke"]["unexpected_live_failures"])

    def test_blocks_failed_local_smoke(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report({"ok": False, "failed": [{"name": "local fail"}]}, live)

        self.assertEqual(report["status"], "blocked_local_smoke_failed")

    def test_waits_when_local_state_has_no_unpublished_change(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report({"ok": True, "failed": []}, live, head="9f02de6", origin="9f02de6", ahead="0")

        self.assertEqual(report["status"], "healthy_wait_no_unpublished_site_candidate")
        self.assertFalse(report["local_unpublished_change_ready"])
        self.assertEqual(report["rules"]["read_only"], True)

    def test_dirty_local_site_counts_as_unpublished_change(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report(
            {"ok": True, "failed": []},
            live,
            head="9f02de6",
            origin="9f02de6",
            ahead="0",
            dirty=" M index.html\n",
        )

        self.assertEqual(report["status"], "ready_for_explicit_publish_approval")
        self.assertTrue(report["local_unpublished_change_ready"])
        self.assertEqual(report["dirty_paths_count"], 1)

    def test_allows_multiple_local_commits_before_publish(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report({"ok": True, "failed": []}, live, ahead="2")

        self.assertEqual(report["status"], "ready_for_explicit_publish_approval")
        self.assertEqual(report["ahead_count"], 2)
        self.assertTrue(report["local_unpublished_change_ready"])


if __name__ == "__main__":
    unittest.main()
