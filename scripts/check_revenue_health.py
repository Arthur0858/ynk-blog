#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


SITE = Path("/Users/mac/Documents/New project 3/parenttechchecklist/site")
PRODUCT_PAGE = SITE / "products" / "parent-tech-quick-start-kit.html"
HOME_PAGE = SITE / "index.html"
HANDOFF_PAGE = SITE / "go" / "parent-tech-quick-start-kit.html"
EXPECTED_GUMROAD_HOST = "parenttechchecklist.gumroad.com"
EXPECTED_GUMROAD_PATH = "/l/hjxqbv"
REQUIRED_UTM_KEYS = {"utm_source", "utm_medium", "utm_campaign"}
EXPECTED_CLICKTHROUGH_PATH = "go/parent-tech-quick-start-kit"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        row = {name.lower(): value or "" for name, value in attrs}
        href = row.get("href", "")
        if href:
            self.links.append({"href": href, "text_hint": row.get("aria-label", "")})


def load_links(path: Path) -> list[dict[str, str]]:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.links


def query_has_utm(href: str) -> bool:
    parsed = urlparse(href)
    params = parse_qs(parsed.query)
    return REQUIRED_UTM_KEYS.issubset(params)


def gumroad_links(links: list[dict[str, str]]) -> list[str]:
    rows = []
    for link in links:
        href = link["href"]
        parsed = urlparse(href)
        if parsed.scheme in {"http", "https"} and parsed.netloc.lower() == EXPECTED_GUMROAD_HOST:
            rows.append(href)
    return rows


def product_cta_links(links: list[dict[str, str]]) -> list[str]:
    return [
        link["href"]
        for link in links
        if "parent-tech-quick-start-kit" in link["href"] and query_has_utm(link["href"])
    ]


def clickthrough_links(links: list[dict[str, str]]) -> list[str]:
    rows = []
    for link in links:
        href = link["href"]
        parsed = urlparse(href)
        path = parsed.path.strip("/")
        params = parse_qs(parsed.query)
        if path.endswith(EXPECTED_CLICKTHROUGH_PATH) and params.get("surface"):
            rows.append(href)
    return rows


def checkout_cta_links(links: list[dict[str, str]]) -> list[str]:
    rows = [
        href
        for href in gumroad_links(links)
        if urlparse(href).path == EXPECTED_GUMROAD_PATH and query_has_utm(href)
    ]
    rows.extend(clickthrough_links(links))
    return rows


def read_affiliate_readiness(out_dir: Path) -> dict[str, Any]:
    script = SITE / "scripts" / "check_affiliate_readiness.py"
    if not script.exists():
        return {"status": "blocked", "blockers": ["missing_affiliate_readiness_script"]}
    spec = importlib.util.spec_from_file_location("parenttech_affiliate_readiness", script)
    if not spec or not spec.loader:
        return {"status": "blocked", "blockers": ["affiliate_readiness_import_failed"]}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.build_report()
    affiliate_out = out_dir / "affiliate-readiness-inline"
    affiliate_out.mkdir(parents=True, exist_ok=True)
    (affiliate_out / "affiliate-readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def build_report(out_dir: Path) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if not PRODUCT_PAGE.exists():
        blockers.append("missing_product_page")
        product_text = ""
        product_links: list[dict[str, str]] = []
    else:
        product_text = PRODUCT_PAGE.read_text(encoding="utf-8", errors="replace")
        product_links = load_links(PRODUCT_PAGE)
    if not HOME_PAGE.exists():
        blockers.append("missing_home_page")
        home_text = ""
        home_links: list[dict[str, str]] = []
    else:
        home_text = HOME_PAGE.read_text(encoding="utf-8", errors="replace")
        home_links = load_links(HOME_PAGE)
    if not HANDOFF_PAGE.exists():
        blockers.append("missing_checkout_handoff_page")
        handoff_links: list[dict[str, str]] = []
    else:
        handoff_links = load_links(HANDOFF_PAGE)

    expected_product_links = checkout_cta_links(product_links)
    expected_home_gumroad_links = checkout_cta_links(home_links)
    home_product_links = product_cta_links(home_links)
    handoff_gumroad_links = checkout_cta_links(handoff_links)

    if not expected_product_links:
        blockers.append("missing_product_page_gumroad_cta_with_utm")
    if not home_product_links:
        blockers.append("missing_home_product_page_cta_with_utm")
    if not handoff_gumroad_links:
        blockers.append("missing_handoff_gumroad_cta_with_utm")
    if "Affiliate disclosure:" not in product_text:
        blockers.append("missing_product_affiliate_disclosure")
    if "Affiliate disclosure:" not in home_text:
        blockers.append("missing_home_affiliate_disclosure")
    if "Product" not in product_text or "priceCurrency" not in product_text:
        warnings.append("product_schema_markup_not_detected")

    affiliate = read_affiliate_readiness(out_dir)
    affiliate_blockers = affiliate.get("blockers", []) if isinstance(affiliate, dict) else []
    if affiliate_blockers:
        blockers.extend(f"affiliate::{item}" for item in affiliate_blockers)

    return {
        "status": "passed" if not blockers else "blocked",
        "blockers": blockers,
        "warnings": warnings,
        "site_root": str(SITE),
        "product_page": str(PRODUCT_PAGE),
        "home_page": str(HOME_PAGE),
        "expected_gumroad_host": EXPECTED_GUMROAD_HOST,
        "expected_gumroad_path": EXPECTED_GUMROAD_PATH,
        "product_gumroad_cta_count": len(expected_product_links),
        "home_gumroad_cta_count": len(expected_home_gumroad_links),
        "home_product_page_cta_count": len(home_product_links),
        "handoff_gumroad_cta_count": len(handoff_gumroad_links),
        "product_gumroad_ctas": expected_product_links,
        "home_gumroad_ctas": expected_home_gumroad_links,
        "home_product_page_ctas": home_product_links,
        "handoff_gumroad_ctas": handoff_gumroad_links,
        "affiliate_readiness": affiliate,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Parent Tech Revenue Health",
        "",
        f"- Status: `{report['status']}`",
        f"- Product Gumroad CTAs: `{report['product_gumroad_cta_count']}`",
        f"- Home Gumroad CTAs: `{report['home_gumroad_cta_count']}`",
        f"- Home product-page CTAs: `{report['home_product_page_cta_count']}`",
        f"- Handoff Gumroad CTAs: `{report['handoff_gumroad_cta_count']}`",
        f"- Product page: `{report['product_page']}`",
        "",
        "## Blockers",
    ]
    blockers = report.get("blockers", [])
    lines.extend(f"- `{item}`" for item in blockers) if blockers else lines.append("- None")
    warnings = report.get("warnings", [])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- `{item}`" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Verified CTAs"])
    for key in ["product_gumroad_ctas", "home_gumroad_ctas", "home_product_page_ctas", "handoff_gumroad_ctas"]:
        values = report.get(key, [])
        lines.append(f"- {key}:")
        if isinstance(values, list) and values:
            lines.extend(f"  - `{value}`" for value in values)
        else:
            lines.append("  - None")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Parent Tech revenue path without logging into external accounts.")
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/parenttech-revenue-health"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args.out_dir)
    (args.out_dir / "revenue-health.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "revenue-health.md").write_text(render_markdown(report), encoding="utf-8")
    print(args.out_dir / "revenue-health.json")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
