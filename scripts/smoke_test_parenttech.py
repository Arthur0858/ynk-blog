#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import socket
import socketserver
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import Browser, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


SITE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LIVE_BASE = "https://parenttechchecklist.com"
DEFAULT_OUT_DIR = Path("/tmp/parenttechchecklist-smoke")

PAGE_CHECKS = [
    {
        "path": "/",
        "required_text": ["Parent Tech Checklists for Families", "Featured guides"],
        "required_links": [
            "/guides/senior-phones",
            "/guides/scam-call-safety",
            "/products/parent-tech-quick-start-kit",
        ],
    },
    {
        "path": "/products/parent-tech-quick-start-kit",
        "required_text": ["Parent Tech Quick-Start Kit", "$9", "Buy on Gumroad"],
        "required_links": [
            "https://parenttechchecklist.gumroad.com/l/hjxqbv",
            "/downloads/scam-call-safety-checklist.pdf",
            "/products/personalized-setup-review",
        ],
    },
    {
        "path": "/products/personalized-setup-review",
        "required_text": ["Personalized Setup Review", "$29", "waitlist"],
        "required_links": [
            "mailto:contact@parenttechchecklist.com",
            "/products/parent-tech-quick-start-kit",
        ],
    },
    {
        "path": "/guides/senior-phones",
        "required_text": ["Best Phones for Seniors"],
        "required_links": ["/downloads/senior-phone-setup-checklist.pdf"],
    },
    {
        "path": "/guides/scam-call-safety",
        "required_text": ["Scam", "Call Safety"],
        "required_links": ["/downloads/scam-call-safety-checklist.pdf"],
    },
    {
        "path": "/guides/video-calling",
        "required_text": ["Video Calling"],
        "required_links": ["/downloads/video-calling-setup-checklist.pdf"],
    },
    {
        "path": "/guides/living-alone-safety",
        "required_text": ["Living Alone"],
        "required_links": ["/downloads/living-alone-tech-checklist.pdf"],
    },
    {"path": "/contact", "required_text": ["Contact"], "required_links": []},
    {"path": "/privacy", "required_text": ["Privacy"], "required_links": []},
    {"path": "/disclosure", "required_text": ["Disclosure"], "required_links": []},
]

ASSET_CHECKS = [
    "/robots.txt",
    "/sitemap.xml",
    "/downloads/senior-phone-setup-checklist.pdf",
    "/downloads/scam-call-safety-checklist.pdf",
    "/downloads/video-calling-setup-checklist.pdf",
    "/downloads/living-alone-tech-checklist.pdf",
]

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1100},
    "mobile": {"width": 390, "height": 844},
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: dict[str, Any] = field(default_factory=dict)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class CloudflareLikeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        self.path = self.route_path(self.path)
        super().do_GET()

    def do_HEAD(self) -> None:
        self.path = self.route_path(self.path)
        super().do_HEAD()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def route_path(self, request_path: str) -> str:
        parsed = urlparse(request_path)
        if parsed.path in {"", "/"} or parsed.path.endswith(".html"):
            return request_path

        candidate = Path(self.translate_path(parsed.path + ".html"))
        if candidate.is_file():
            suffix = f"?{parsed.query}" if parsed.query else ""
            return parsed.path + ".html" + suffix
        return request_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test Parent Tech Checklist local or live site.")
    parser.add_argument("--site-dir", default=str(SITE_DIR))
    parser.add_argument("--base-url", help="Existing base URL to test. If omitted, a local static server is started.")
    parser.add_argument("--live", action="store_true", help=f"Test {DEFAULT_LIVE_BASE}.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--screenshot", action="store_true", help="Save desktop and mobile screenshots.")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    return parser.parse_args()


def find_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextlib.contextmanager
def local_server(site_dir: Path):
    port = find_port()
    handler = lambda *args, **kwargs: CloudflareLikeHandler(  # noqa: E731
        *args,
        directory=str(site_dir),
        **kwargs,
    )
    server = ReusableTCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 5
        base_url = f"http://127.0.0.1:{port}"
        while time.time() < deadline:
            try:
                fetch_status(base_url + "/")
                break
            except Exception:
                time.sleep(0.05)
        yield base_url
    finally:
        server.shutdown()
        server.server_close()


def fetch_status(url: str, timeout: int = 10) -> int:
    req = Request(url, method="GET", headers={"User-Agent": "ParentTechSmoke/1.0"})
    with urlopen(req, timeout=timeout) as response:
        status = int(response.status)
        response.read()
        return status


def normalize_path(href: str) -> str:
    parsed = urlparse(href)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return path


def assert_http_assets(base_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    for path in ASSET_CHECKS:
        url = urljoin(base_url + "/", path.lstrip("/"))
        try:
            status = fetch_status(url)
            results.append(CheckResult(f"asset {path}", 200 <= status < 400, {"status": status}))
        except Exception as exc:
            results.append(CheckResult(f"asset {path}", False, {"error": str(exc)}))
    return results


def page_console_errors(page: Page) -> list[str]:
    errors: list[str] = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)
    return errors


def check_page(
    browser: Browser,
    base_url: str,
    check: dict[str, Any],
    viewport_name: str,
    viewport: dict[str, int],
    out_dir: Path,
    screenshot: bool,
    timeout_ms: int,
) -> list[CheckResult]:
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    errors = page_console_errors(page)
    path = check["path"]
    url = urljoin(base_url + "/", path.lstrip("/"))
    results: list[CheckResult] = []
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_load_state("load", timeout=min(timeout_ms, 5000))
        except PlaywrightTimeoutError:
            pass
        status = response.status if response else 0
        results.append(CheckResult(f"{viewport_name} {path} status", 200 <= status < 400, {"status": status}))

        title = page.title().strip()
        results.append(CheckResult(f"{viewport_name} {path} title", bool(title), {"title": title}))

        body_text = page.locator("body").inner_text(timeout=timeout_ms)
        for text in check.get("required_text", []):
            results.append(
                CheckResult(
                    f"{viewport_name} {path} text {text}",
                    text.lower() in body_text.lower(),
                )
            )

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(a => a.href)")
        normalized_hrefs = {normalize_path(href) for href in hrefs}
        raw_hrefs = set(hrefs)
        for required in check.get("required_links", []):
            if required.startswith("http"):
                ok = any(href.startswith(required) for href in raw_hrefs)
            else:
                ok = normalize_path(required) in normalized_hrefs
            results.append(CheckResult(f"{viewport_name} {path} link {required}", ok))

        bad_hash_links = [href for href in hrefs if href.endswith("#")]
        results.append(
            CheckResult(
                f"{viewport_name} {path} no placeholder links",
                not bad_hash_links,
                {"bad_links": bad_hash_links[:10]},
            )
        )

        broken_images = page.eval_on_selector_all(
            "img",
            """async els => {
                for (const img of els) {
                    img.scrollIntoView({block: 'center'});
                    if (!img.complete) {
                        await new Promise(resolve => {
                            const done = () => resolve();
                            img.addEventListener('load', done, {once: true});
                            img.addEventListener('error', done, {once: true});
                            setTimeout(done, 3000);
                        });
                    }
                }
                return els
                    .filter(img => !img.complete || img.naturalWidth === 0)
                    .map(img => img.getAttribute('src'));
            }""",
        )
        results.append(
            CheckResult(
                f"{viewport_name} {path} images load",
                not broken_images,
                {"broken_images": broken_images},
            )
        )

        overflow = page.evaluate(
            "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)"
        )
        results.append(CheckResult(f"{viewport_name} {path} no horizontal overflow", overflow <= 2, {"overflow_px": overflow}))

        results.append(CheckResult(f"{viewport_name} {path} no console errors", not errors, {"errors": errors[:10]}))

        if screenshot and path in {
            "/",
            "/products/parent-tech-quick-start-kit",
            "/products/personalized-setup-review",
        }:
            filename = f"{viewport_name}-{path.strip('/').replace('/', '-') or 'home'}.png"
            page.screenshot(path=str(out_dir / filename), full_page=True)
    finally:
        context.close()
    return results


def run_smoke(base_url: str, out_dir: Path, screenshot: bool, timeout_ms: int) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[CheckResult] = []
    results.extend(assert_http_assets(base_url))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for viewport_name, viewport in VIEWPORTS.items():
                for check in PAGE_CHECKS:
                    results.extend(
                        check_page(
                            browser,
                            base_url,
                            check,
                            viewport_name,
                            viewport,
                            out_dir,
                            screenshot,
                            timeout_ms,
                        )
                    )
        finally:
            browser.close()

    failed = [result for result in results if not result.ok]
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "base_url": base_url,
        "ok": not failed,
        "total": len(results),
        "failed": [
            {"name": result.name, "details": result.details}
            for result in failed
        ],
        "results": [
            {"name": result.name, "ok": result.ok, "details": result.details}
            for result in results
        ],
    }
    (out_dir / "smoke-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    summary_lines = [
        "# Parent Tech Checklist Smoke Test",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Base URL: {base_url}",
        f"- Result: {'PASS' if report['ok'] else 'FAIL'}",
        f"- Checks: {report['total']}",
        f"- Failed: {len(failed)}",
        "",
    ]
    if failed:
        summary_lines.append("## Failures")
        summary_lines.extend(f"- {item.name}: {item.details}" for item in failed)
        summary_lines.append("")
    (out_dir / "smoke-report.md").write_text("\n".join(summary_lines))
    return report


def git_sha(site_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(site_dir), "rev-parse", "--short", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def main() -> int:
    args = parse_args()
    site_dir = Path(args.site_dir).resolve()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) / f"{stamp}-{git_sha(site_dir)}"

    if args.live and args.base_url:
        raise SystemExit("Use either --live or --base-url, not both.")

    if args.live:
        base_url = DEFAULT_LIVE_BASE
        report = run_smoke(base_url, out_dir, args.screenshot, args.timeout_ms)
    elif args.base_url:
        report = run_smoke(args.base_url.rstrip("/"), out_dir, args.screenshot, args.timeout_ms)
    else:
        with local_server(site_dir) as base_url:
            report = run_smoke(base_url, out_dir, args.screenshot, args.timeout_ms)

    print(json.dumps({"ok": report["ok"], "out_dir": str(out_dir), "failed": len(report["failed"])}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
