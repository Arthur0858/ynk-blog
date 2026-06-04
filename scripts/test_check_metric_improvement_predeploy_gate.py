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
    def run_report(self, local: dict, live: dict, *, head: str = "93a3f3e", approved: bool = False) -> dict:
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
                    return "62f0a29"
                if args == ["rev-list", "--count", "origin/main..HEAD"]:
                    return "1"
                return ""

            original = gate.git_output
            try:
                gate.git_output = fake_git
                return gate.build_report(
                    argparse.Namespace(
                        local_smoke_json=local_path,
                        live_smoke_json=live_path,
                        out_dir=tmp_path / "out",
                        expected_local_commit="93a3f3e",
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
        self.assertEqual(report["rules"]["no_external_publish"], True)

    def test_blocks_unexpected_live_failure(self) -> None:
        live = {"ok": False, "failed": [{"name": "desktop / broken unexpected", "details": {}}]}
        report = self.run_report({"ok": True, "failed": []}, live)

        self.assertEqual(report["status"], "blocked_unexpected_live_regression")
        self.assertEqual(report["live_smoke"]["unexpected_live_failures"], ["desktop / broken unexpected"])

    def test_blocks_failed_local_smoke(self) -> None:
        live = {"ok": False, "failed": [{"name": name, "details": {}} for name in gate.EXPECTED_LIVE_DELTA_FAILURES]}
        report = self.run_report({"ok": False, "failed": [{"name": "local fail"}]}, live)

        self.assertEqual(report["status"], "blocked_local_smoke_failed")


if __name__ == "__main__":
    unittest.main()
