#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


ROOT = Path("/Users/mac/Documents/New project 3/parenttechchecklist")
PRODUCT_TRACKER = ROOT / "tracking" / "product-tracker.csv"
PRODUCT_PAGE = "https://parenttechchecklist.com/products/parent-tech-quick-start-kit"
GUMROAD_URL = "https://parenttechchecklist.gumroad.com/l/hjxqbv"
DEFAULT_CAMPAIGN = "ptc-product-kit-traffic-test"


def tracked_url(source: str, medium: str, campaign: str) -> str:
    return f"{PRODUCT_PAGE}?{urlencode({'utm_source': source, 'utm_medium': medium, 'utm_campaign': campaign})}"


def build_assets(campaign: str) -> dict[str, Any]:
    community_url = tracked_url("youtube", "community", campaign)
    shorts_url = tracked_url("youtube", "shorts", campaign)
    video_url = tracked_url("youtube", "video", campaign)
    return {
        "campaign": campaign,
        "safety": {
            "no_login": True,
            "no_external_publish": True,
            "no_vendor_or_affiliate_links": True,
            "no_sensitive_data": True,
        },
        "urls": {
            "community": community_url,
            "shorts": shorts_url,
            "video_description": video_url,
            "gumroad_checkout": GUMROAD_URL,
        },
        "community_post": {
            "surface": "youtube_community",
            "status": "draft_only",
            "copy": (
                "If you help an aging parent with phones, scam texts, video calls, or living-alone tech, "
                "which setup problem is hardest this week?\n\n"
                "- Picking the right phone\n"
                "- Avoiding scam calls and texts\n"
                "- Making video calls one tap\n"
                "- Setting up living-alone check-ins\n\n"
                "I am testing a small Parent Tech Quick-Start Kit: a $9 printable setup pack for families "
                "who want a calmer checklist before buying more technology.\n\n"
                f"{community_url}\n\n"
                "General technology guidance only. No device can guarantee safety or stop every scam."
            ),
        },
        "shorts_caption": {
            "surface": "youtube_shorts",
            "status": "draft_only",
            "copy": (
                "Before buying more tech for an aging parent, test the routine first.\n\n"
                f"7-day printable setup kit: {shorts_url}\n\n"
                "General technology guidance only. No vendor or affiliate links.\n\n"
                "#AgingParents #CaregiverTips #SeniorTech #FamilyCaregiving"
            ),
        },
        "video_description_block": {
            "surface": "youtube_video_description",
            "status": "draft_only",
            "copy": (
                "Parent Tech Quick-Start Kit:\n"
                f"{video_url}\n\n"
                "Printable setup worksheets for families helping aging parents compare phones, scam-call routines, "
                "video calls, and living-alone check-ins.\n\n"
                "General technology guidance only. No device can guarantee safety or stop every scam."
            ),
        },
    }


def tracker_rows(path: Path = PRODUCT_TRACKER) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def tracker_fieldnames(path: Path = PRODUCT_TRACKER) -> list[str]:
    if not path.exists():
        return [
            "date",
            "offer",
            "status",
            "traffic_source",
            "utm_campaign",
            "page_url",
            "cta_url",
            "visits",
            "cta_clicks",
            "purchases",
            "intent_replies",
            "revenue_usd",
            "notes",
        ]
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or [])


def planned_tracker_row(campaign: str, generated_date: str) -> dict[str, str]:
    return {
        "date": generated_date,
        "offer": "Parent Tech Quick-Start Kit",
        "status": "planned",
        "traffic_source": "youtube-community-short-description",
        "utm_campaign": campaign,
        "page_url": PRODUCT_PAGE,
        "cta_url": tracked_url("youtube", "community", campaign),
        "visits": "0",
        "cta_clicks": "0",
        "purchases": "0",
        "intent_replies": "0",
        "revenue_usd": "0",
        "notes": "Auto-generated low-risk traffic push baseline; update after publication/measurement; no external publish performed.",
    }


def upsert_tracker_row(campaign: str, generated_date: str, update_tracker: bool) -> dict[str, Any]:
    rows = tracker_rows()
    fieldnames = tracker_fieldnames()
    row = planned_tracker_row(campaign, generated_date)
    exists = any(item.get("utm_campaign") == campaign for item in rows)
    if not update_tracker:
        return {"status": "planned_not_written", "row_exists": exists, "row": row}
    if exists:
        return {"status": "already_exists", "row_exists": True, "row": row}
    PRODUCT_TRACKER.parent.mkdir(parents=True, exist_ok=True)
    write_header = not PRODUCT_TRACKER.exists()
    with PRODUCT_TRACKER.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return {"status": "written", "row_exists": False, "row": row}


def render_markdown(report: dict[str, Any]) -> str:
    assets = report["assets"]
    lines = [
        "# Parent Tech Traffic Push Package",
        "",
        f"- Status: `{report['status']}`",
        f"- Campaign: `{assets['campaign']}`",
        f"- Tracker update: `{report['tracker_update']['status']}`",
        "",
        "## Community Post",
        "",
        assets["community_post"]["copy"],
        "",
        "## Shorts Caption",
        "",
        assets["shorts_caption"]["copy"],
        "",
        "## Video Description Block",
        "",
        assets["video_description_block"]["copy"],
        "",
        "## Tracking URLs",
    ]
    for name, url in assets["urls"].items():
        lines.append(f"- `{name}`: `{url}`")
    return "\n".join(lines) + "\n"


def build_report(campaign: str, out_dir: Path, update_tracker: bool) -> dict[str, Any]:
    generated = datetime.now().astimezone()
    assets = build_assets(campaign)
    tracker_update = upsert_tracker_row(campaign, generated.date().isoformat(), update_tracker)
    return {
        "status": "passed",
        "generated_at": generated.isoformat(timespec="seconds"),
        "assets": assets,
        "tracker_update": tracker_update,
        "outputs": {
            "json": str(out_dir / "traffic-push-package.json"),
            "markdown": str(out_dir / "traffic-push-package.md"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a low-risk Parent Tech traffic push package without publishing.")
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/parenttech-traffic-push-package"))
    parser.add_argument("--campaign", default=DEFAULT_CAMPAIGN)
    parser.add_argument("--update-tracker", action="store_true")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args.campaign, args.out_dir, args.update_tracker)
    (args.out_dir / "traffic-push-package.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "traffic-push-package.md").write_text(render_markdown(report), encoding="utf-8")
    print(args.out_dir / "traffic-push-package.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
