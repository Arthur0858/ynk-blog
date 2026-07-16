from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("deploy_cloudflare_pages.py")
SPEC = importlib.util.spec_from_file_location("deploy_cloudflare_pages", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {SCRIPT}")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class WranglerStagingTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
