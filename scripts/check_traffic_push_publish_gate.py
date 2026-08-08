#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path("/home/s7551/np3-workspace")
PARENTTECH = ROOT / "parenttechchecklist"
PRODUCT_TRACKER = PARENTTECH / "tracking" / "product-tracker.csv"
CHANNEL_PROFILE = PARENTTECH / "youtube-channel-profile.md"
STATUS_JSON = Path("/tmp/new-project-3-status-aggregator/status.json")
EXPECTED_HANDLE = "@ParentTechChecklist"
EXPECTED_CHANNEL_URL = "https://www.youtube.com/@ParentTechChecklist"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def tracker_campaign_count(campaign: str) -> int:
    if not PRODUCT_TRACKER.exists():
        return 0
    with PRODUCT_TRACKER.open(newline="", encoding="utf-8-sig") as handle:
        return sum(1 for row in csv.DictReader(handle) if row.get("utm_campaign") == campaign)


def channel_identity_evidence() -> dict[str, Any]:
    text = CHANNEL_PROFILE.read_text(encoding="utf-8", errors="replace") if CHANNEL_PROFILE.exists() else ""
    return {
        "path": str(CHANNEL_PROFILE),
        "exists": CHANNEL_PROFILE.exists(),
        "expected_handle": EXPECTED_HANDLE,
        "expected_channel_url": EXPECTED_CHANNEL_URL,
        "handle_present": EXPECTED_HANDLE in text,
        "url_present": EXPECTED_CHANNEL_URL in text,
        "profile_published_evidence": "YouTube Studio accepted and published" in text,
    }


def build_report(package_json: Path) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    package = read_json(package_json)
    assets = package.get("assets", {}) if isinstance(package.get("assets"), dict) else {}
    campaign = str(assets.get("campaign") or "")
    safety = assets.get("safety", {}) if isinstance(assets.get("safety"), dict) else {}
    status = read_json(STATUS_JSON)
    youtube = status.get("youtube_upload", {}) if isinstance(status.get("youtube_upload"), dict) else {}
    identity = channel_identity_evidence()

    if not package_json.exists() or package.get("status") != "passed":
        blockers.append("missing_or_failed_traffic_push_package")
    if not campaign:
        blockers.append("missing_campaign")
    if not safety.get("no_external_publish") or not safety.get("no_vendor_or_affiliate_links"):
        blockers.append("unsafe_package_boundary")
    if not all(identity.get(key) for key in ["exists", "handle_present", "url_present", "profile_published_evidence"]):
        blockers.append("missing_parenttech_channel_identity_evidence")
    campaign_count = tracker_campaign_count(campaign)
    if campaign_count == 0:
        blockers.append("missing_product_tracker_baseline")
    if campaign_count > 1:
        blockers.append("duplicate_product_tracker_campaign")
    if youtube.get("pressure_gate_status") == "blocked_by_daily_limit" or youtube.get("quota_skip_reason"):
        blockers.append("youtube_quota_or_daily_limit_gate")
    remaining_by_project = youtube.get("quota_summary", {}).get("remaining_by_project", {})
    parenttech_remaining = remaining_by_project.get("parenttech") if isinstance(remaining_by_project, dict) else None
    if isinstance(parenttech_remaining, int) and parenttech_remaining <= 0:
        blockers.append("parenttech_daily_quota_exhausted")
    if youtube.get("pending_pressure_status") == "high":
        blockers.append("youtube_pending_pressure_high")
    if not STATUS_JSON.exists():
        warnings.append("status_aggregator_missing")
    handoff_state = "publish_handoff_allowed" if not blockers else "blocked"
    return {
        "status": "passed",
        "handoff_state": handoff_state,
        "blockers": blockers,
        "warnings": warnings,
        "package_json": str(package_json),
        "campaign": campaign,
        "tracker": {
            "path": str(PRODUCT_TRACKER),
            "campaign_count": campaign_count,
        },
        "channel_identity": identity,
        "youtube_gates": {
            "status_json": str(STATUS_JSON),
            "pressure_gate_status": youtube.get("pressure_gate_status", "unknown"),
            "pending_pressure_status": youtube.get("pending_pressure_status", "unknown"),
            "quota_skip_reason": youtube.get("quota_skip_reason", ""),
            "pending_count": youtube.get("pending_count", "unknown"),
            "parenttech_remaining": parenttech_remaining,
        },
        "allowed_handoff": {
            "requires_visible_account_check_before_publish": True,
            "requires_duplicate_check_before_publish": True,
            "external_publish_performed": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Parent Tech Traffic Push Publish Gate",
        "",
        f"- Status: `{report['status']}`",
        f"- Handoff state: `{report['handoff_state']}`",
        f"- Campaign: `{report['campaign']}`",
        f"- Tracker campaign count: `{report['tracker']['campaign_count']}`",
        "",
        "## Blockers",
    ]
    blockers = report.get("blockers", [])
    lines.extend(f"- `{item}`" for item in blockers) if blockers else lines.append("- None")
    lines.extend(["", "## YouTube Gates"])
    for key, value in report.get("youtube_gates", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Handoff Boundary"])
    for key, value in report.get("allowed_handoff", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether a Parent Tech traffic push package can be handed off for publishing.")
    parser.add_argument("--package-json", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/parenttech-traffic-push-publish-gate"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args.package_json)
    (args.out_dir / "publish-gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "publish-gate.md").write_text(render_markdown(report), encoding="utf-8")
    print(args.out_dir / "publish-gate.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
