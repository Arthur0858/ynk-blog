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
        self.assertIn("desktop /go/parent-tech-quick-start-kit text $9 one-time digital download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text Printable worksheets", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("desktop /go/parent-tech-quick-start-kit text No sensitive details needed", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text $9 one-time digital download", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text Printable worksheets", gate.EXPECTED_LIVE_DELTA_FAILURES)
        self.assertIn("mobile /go/parent-tech-quick-start-kit text No sensitive details needed", gate.EXPECTED_LIVE_DELTA_FAILURES)

    def test_blocks_unexpected_live_failure(self) -> None:
        live = {"ok": False, "failed": [{"name": "desktop / broken unexpected", "details": {}}]}
        report = self.run_report({"ok": True, "failed": []}, live)

        self.assertEqual(report["status"], "blocked_unexpected_live_regression")
        self.assertEqual(report["live_smoke"]["unexpected_live_failures"], ["desktop / broken unexpected"])

    def test_blocks_failed_local_smoke(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report({"ok": False, "failed": [{"name": "local fail"}]}, live)

        self.assertEqual(report["status"], "blocked_local_smoke_failed")

    def test_blocks_when_local_state_has_no_unpublished_change(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report({"ok": True, "failed": []}, live, head="9f02de6", origin="9f02de6", ahead="0")

        self.assertEqual(report["status"], "blocked_unexpected_local_state")
        self.assertFalse(report["local_unpublished_change_ready"])

    def test_allows_multiple_local_commits_before_publish(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report({"ok": True, "failed": []}, live, ahead="2")

        self.assertEqual(report["status"], "ready_for_explicit_publish_approval")
        self.assertEqual(report["ahead_count"], 2)
        self.assertTrue(report["local_unpublished_change_ready"])


if __name__ == "__main__":
    unittest.main()
