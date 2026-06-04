#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUT_DIR = Path("/tmp/parenttech-traffic-push-gui-preflight-fixture")
EXPECTED_CHANNEL = "@ParentTechChecklist"
CAMPAIGN_ID = "ptc-product-kit-traffic-test"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compact_stamp(value: str) -> str:
    return value.replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ready_publish_task(created_at: str) -> dict[str, Any]:
    return {
        "status": "ready_for_visible_gui_preflight",
        "created_at": created_at,
        "campaign_id": CAMPAIGN_ID,
        "project": "parenttechchecklist",
        "target_app": "youtube_studio",
        "target_account_or_channel": EXPECTED_CHANNEL,
        "expected_account_or_channel": EXPECTED_CHANNEL,
        "action": "visible_read_only_preflight",
        "public_side_effect_allowed": False,
        "mac_project_hub_writer_only": True,
        "fail_closed_gates": [
            "wrong_account_or_channel",
            "captcha_or_2fa",
            "payment_or_kyc",
            "sensitive_data_required",
            "platform_quota_closed",
            "duplicate_publish_uncertain",
        ],
    }


def gui_report(mode: str, created_at: str, screenshot_path: str) -> dict[str, Any]:
    allowed = mode == "allowed"
    report: dict[str, Any] = {
        "status": "success" if allowed else "blocked",
        "started_at": created_at,
        "completed_at": created_at,
        "target_app": "youtube_studio",
        "target_account_or_channel": EXPECTED_CHANNEL if allowed else "@WrongChannel",
        "expected_account_or_channel": EXPECTED_CHANNEL,
        "identity_verified": allowed,
        "duplicate_check": "passed" if allowed else "blocked",
        "action_taken": "read_only_observation",
        "public_side_effect": False,
        "screenshot_paths": [screenshot_path],
        "notes": "Fixture only. Do not treat this as live platform evidence.",
    }
    if not allowed:
        report["blocker"] = "wrong_account_or_channel"
    return report


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Parent Tech GUI Preflight Fixture",
        "",
        f"- Mode: `{summary['mode']}`",
        f"- Task: `{summary['task_json']}`",
        f"- GUI report: `{summary['gui_report_json']}`",
        f"- Reports root: `{summary['reports_root']}`",
        "",
        "This fixture is for adapter verification only. It must not be copied into the live ProjectDataCenter report tree as proof of a real browser observation.",
        "",
    ]
    return "\n".join(lines)


def build_fixture(mode: str, out_dir: Path) -> dict[str, Any]:
    created_at = utc_stamp()
    day = created_at[:10]
    stamp = compact_stamp(created_at)
    fixture_root = out_dir / mode
    task_json = fixture_root / "ready-publish-task.json"
    reports_root = fixture_root / "gui-ops"
    screenshot_path = str(fixture_root / "screenshots" / f"{mode}-parenttech-visible-preflight.png")
    gui_report_json = reports_root / day / f"gui-op-{stamp}-parenttech-traffic-push-preflight.json"

    write_json(task_json, ready_publish_task(created_at))
    write_json(gui_report_json, gui_report(mode, created_at, screenshot_path))
    (fixture_root / "screenshots").mkdir(parents=True, exist_ok=True)

    summary = {
        "status": "created",
        "mode": mode,
        "created_at": created_at,
        "fixture_root": str(fixture_root),
        "task_json": str(task_json),
        "reports_root": str(reports_root),
        "gui_report_json": str(gui_report_json),
        "expected_ingestion_decision": "preflight_allowed" if mode == "allowed" else "blocked",
        "live_evidence": False,
    }
    write_json(fixture_root / "fixture-summary.json", summary)
    (fixture_root / "fixture-summary.md").write_text(render_markdown(summary), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local-only Parent Tech GUI preflight fixtures.")
    parser.add_argument("--mode", choices=["allowed", "blocked"], default="allowed")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    summary = build_fixture(args.mode, args.out_dir)
    print(summary["fixture_root"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
