from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPT = Path(__file__).with_name("deploy_cloudflare_pages.py")
SPEC = importlib.util.spec_from_file_location("deploy_cloudflare_pages", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {SCRIPT}")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class WranglerStagingTests(unittest.TestCase):
    def test_help_works_without_optional_blake3_dependency(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-S", str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("usage:", completed.stdout)

    def test_builds_pages_deploy_command(self) -> None:
        command = module.build_wrangler_deploy_command(
            Path("/tmp/public"), "parenttechchecklist", "main"
        )

        self.assertEqual(
            command,
            [
                "npx",
                "--yes",
                "wrangler",
                "pages",
                "deploy",
                "/tmp/public",
                "--project-name",
                "parenttechchecklist",
                "--branch",
                "main",
            ],
        )

    def test_stages_only_filtered_public_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "site"
            stage = root / "stage"
            (site / "scripts").mkdir(parents=True)
            (site / "functions" / "api").mkdir(parents=True)
            (site / "index.html").write_text("ok", encoding="utf-8")
            (site / "_headers").write_text("/*\n", encoding="utf-8")
            (site / "scripts" / "private.py").write_text("secret", encoding="utf-8")
            (site / "functions" / "api" / "lead.js").write_text("export {}", encoding="utf-8")
            (site / "notes.md").write_text("private", encoding="utf-8")

            module.stage_wrangler_assets(site, module.collect_site_files(site), stage)

            self.assertTrue((stage / "index.html").exists())
            self.assertTrue((stage / "_headers").exists())
            self.assertFalse((stage / "scripts").exists())
            self.assertFalse((stage / "functions").exists())
            self.assertFalse((stage / "notes.md").exists())

    def test_functions_deploy_does_not_request_static_upload_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "functions" / "api").mkdir(parents=True)
            (site / "functions" / "api" / "lead.js").write_text(
                "export {}", encoding="utf-8"
            )
            (site / "index.html").write_text("ok", encoding="utf-8")
            args = SimpleNamespace(
                site_dir=str(site),
                token_file=str(site / "token"),
                account_id="account-1",
                project_name="parenttechchecklist",
                branch="main",
                commit_hash=None,
                commit_message=None,
                commit_dirty=None,
                skip_caching=False,
                dry_run=False,
                no_verify=True,
                verify_aliases=False,
            )

            with (
                mock.patch.object(module, "parse_args", return_value=args),
                mock.patch.object(module, "load_api_token", return_value="token"),
                mock.patch.object(
                    module,
                    "detect_git_metadata",
                    return_value=("commit", "message", False),
                ),
                mock.patch.object(
                    module,
                    "get_upload_jwt",
                    side_effect=AssertionError("static upload token requested"),
                ),
                mock.patch.object(module.subprocess, "run"),
            ):
                self.assertEqual(module.main(), 0)

    def test_verifies_live_lead_function_contract(self) -> None:
        with mock.patch.object(
            module,
            "fetch_url",
            return_value=(405, '{"success":false,"error":"Method not allowed"}'),
        ):
            module.verify_lead_endpoint("https://parenttechchecklist.pages.dev")


if __name__ == "__main__":
    unittest.main()
