#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path("/home/s7551/np3-workspace/parenttechchecklist")
SITE = ROOT / "site"
REGISTRATION_STATUS = ROOT / "affiliate" / "registration-status.csv"
LINK_TRACKING_MAP = ROOT / "affiliate" / "link-tracking-map.md"
CONTENT_TRACKER = ROOT / "tracking" / "content-tracker.csv"

AFFILIATE_OR_VENDOR_DOMAINS = {
    "amazon.com",
    "amzn.to",
    "bestbuy.com",
    "lively.com",
    "shareasale.com",
    "awin1.com",
    "medicalcarealert.com",
    "cj.com",
    "anrdoezrs.net",
    "jdoqocy.com",
    "tkqlhce.com",
    "dpbolvw.net",
}
ALLOWED_NON_AFFILIATE_DOMAINS = {
    "parenttechchecklist.com",
    "parenttechchecklist.gumroad.com",
    "gumroad.com",
    "youtube.com",
    "youtu.be",
}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)


def domain_matches(hostname: str, candidates: set[str]) -> bool:
    host = hostname.lower().removeprefix("www.")
    return any(host == domain or host.endswith("." + domain) for domain in candidates)


def read_registration_rows() -> list[dict[str, str]]:
    if not REGISTRATION_STATUS.exists():
        return []
    with REGISTRATION_STATUS.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_content_rows() -> list[dict[str, str]]:
    if not CONTENT_TRACKER.exists():
        return []
    with CONTENT_TRACKER.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def html_links() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(SITE.rglob("*.html")):
        parser = LinkParser()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        for href in parser.links:
            parsed = urlparse(href)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            rows.append(
                {
                    "path": str(path.relative_to(SITE)),
                    "href": href,
                    "host": parsed.netloc.lower().removeprefix("www."),
                }
            )
    return rows


def build_report() -> dict[str, object]:
    registration_rows = read_registration_rows()
    content_rows = read_content_rows()
    links = html_links()
    public_affiliate_like_links = [
        link for link in links if domain_matches(link["host"], AFFILIATE_OR_VENDOR_DOMAINS)
    ]
    unexpected_external_links = [
        link
        for link in links
        if not domain_matches(link["host"], ALLOWED_NON_AFFILIATE_DOMAINS)
        and not domain_matches(link["host"], AFFILIATE_OR_VENDOR_DOMAINS)
    ]
    ready_programs = [
        row
        for row in registration_rows
        if row.get("application_status") in {"approved", "review_pending_after_3_qualified_sales"}
        and row.get("tracking_status") == "active"
        and row.get("terms_status") in {"approved", "reviewed"}
    ]
    pending_programs = [
        {
            "program": row.get("program", ""),
            "network": row.get("network", ""),
            "status": row.get("status", ""),
            "application_status": row.get("application_status", ""),
            "tracking_status": row.get("tracking_status", ""),
            "terms_status": row.get("terms_status", ""),
            "next_action": row.get("next_action", ""),
        }
        for row in registration_rows
        if row not in ready_programs
    ]
    tracker_programs = sorted({row.get("affiliate_program", "") for row in content_rows if row.get("affiliate_program")})
    blockers: list[str] = []
    if not REGISTRATION_STATUS.exists():
        blockers.append("missing_registration_status")
    if not LINK_TRACKING_MAP.exists():
        blockers.append("missing_link_tracking_map")
    if not CONTENT_TRACKER.exists():
        blockers.append("missing_content_tracker")
    if public_affiliate_like_links and not ready_programs:
        blockers.append("affiliate_links_live_without_approved_tracking")
    return {
        "status": "passed" if not blockers else "blocked",
        "blockers": blockers,
        "registration_status_path": str(REGISTRATION_STATUS),
        "link_tracking_map_path": str(LINK_TRACKING_MAP),
        "content_tracker_path": str(CONTENT_TRACKER),
        "ready_program_count": len(ready_programs),
        "pending_program_count": len(pending_programs),
        "tracker_programs": tracker_programs,
        "public_affiliate_like_links": public_affiliate_like_links,
        "unexpected_external_links": unexpected_external_links,
        "pending_programs": pending_programs,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Parent Tech Affiliate Readiness",
        "",
        f"- Status: `{report['status']}`",
        f"- Ready programs: `{report['ready_program_count']}`",
        f"- Pending programs: `{report['pending_program_count']}`",
        f"- Registration status: `{report['registration_status_path']}`",
        f"- Link tracking map: `{report['link_tracking_map_path']}`",
        f"- Content tracker: `{report['content_tracker_path']}`",
        "",
        "## Blockers",
    ]
    blockers = report.get("blockers", [])
    if isinstance(blockers, list) and blockers:
        lines.extend(f"- `{item}`" for item in blockers)
    else:
        lines.append("- None")
    links = report.get("public_affiliate_like_links", [])
    lines.extend(["", "## Public Affiliate-Like Links"])
    if isinstance(links, list) and links:
        for item in links:
            if isinstance(item, dict):
                lines.append(f"- `{item.get('path')}` -> `{item.get('host')}`")
    else:
        lines.append("- None")
    lines.extend(["", "## Pending Programs"])
    pending = report.get("pending_programs", [])
    if isinstance(pending, list) and pending:
        for item in pending[:10]:
            if isinstance(item, dict):
                lines.append(
                    f"- `{item.get('program')}` via `{item.get('network')}`: "
                    f"`{item.get('application_status')}` / `{item.get('tracking_status')}`; "
                    f"next `{item.get('next_action')}`"
                )
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Parent Tech affiliate readiness without publishing links.")
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/parenttech-affiliate-readiness"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report()
    (args.out_dir / "affiliate-readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "affiliate-readiness.md").write_text(render_markdown(report), encoding="utf-8")
    print(args.out_dir / "affiliate-readiness.json")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
