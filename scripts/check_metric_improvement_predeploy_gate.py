#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


SITE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("/tmp/parenttech-cta-optimization-predeploy-gate")
EXPECTED_LIVE_DELTA_FAILURES = {
    "desktop / text Buy on Gumroad",
    "desktop / text The paid kit is a one-time Gumroad download",
    "desktop / link /go/parent-tech-quick-start-kit",
    "desktop /products/parent-tech-quick-start-kit text 30 minutes this week",
    "desktop /go/parent-tech-quick-start-kit text $9 one-time digital download",
    "desktop /go/parent-tech-quick-start-kit text US Letter worksheet pack",
    "desktop /go/parent-tech-quick-start-kit text US Letter printable worksheets",
    "desktop /go/parent-tech-quick-start-kit text US Letter printable PDF worksheets",
    "desktop /go/parent-tech-quick-start-kit text Checkout fit check",
    "desktop /go/parent-tech-quick-start-kit text No sensitive details needed",
    "desktop /go/parent-tech-quick-start-kit text Printable worksheets",
    "desktop /products/parent-tech-quick-start-kit text First 30 minutes after download",
    "desktop /products/parent-tech-quick-start-kit text US families",
    "desktop /products/parent-tech-quick-start-kit text US Letter PDFs",
    "desktop /products/parent-tech-quick-start-kit text five US Letter PDFs",
    "desktop /products/parent-tech-quick-start-kit text Checkout readiness",
    "desktop /products/parent-tech-quick-start-kit text free worksheet preview first",
    "desktop /products/parent-tech-quick-start-kit text PDF worksheets in a ZIP download",
    "desktop /products/parent-tech-quick-start-kit text Know the files before checkout",
    "desktop /products/parent-tech-quick-start-kit text 01-7-Day-Parent-Tech-Setup-Plan.pdf",
    "desktop /products/parent-tech-quick-start-kit text 05-Living-Alone-Tech-Comparison-Worksheet.pdf",
    "desktop /products/parent-tech-quick-start-kit text Know what to send",
    "desktop /products/parent-tech-quick-start-kit text worksheet name, main family concern, and device category",
    "desktop /products/personalized-setup-review text What you would get back",
    "desktop /products/personalized-setup-review text What to send",
    "desktop /products/personalized-setup-review text worksheet name, the main family concern",
    "desktop /products/personalized-setup-review text device or service category",
    "desktop /products/personalized-setup-review text Example outcome",
    "desktop /products/personalized-setup-review text I will not send passwords",
    "desktop /go/parent-tech-quick-start-kit text What you get",
    "desktop /go/parent-tech-quick-start-kit text What this is not",
    "desktop /go/parent-tech-quick-start-kit text Need to preview the format first?",
    "desktop /go/parent-tech-quick-start-kit text Preview a free worksheet PDF",
    "desktop /go/parent-tech-quick-start-kit text Ready to buy when",
    "desktop /go/parent-tech-quick-start-kit text I understand, continue to Gumroad",
    "desktop /go/parent-tech-quick-start-kit text about five seconds",
    "desktop /go/parent-tech-quick-start-kit text Files included after purchase",
    "desktop /go/parent-tech-quick-start-kit text 01-7-Day-Parent-Tech-Setup-Plan.pdf",
    "desktop /go/parent-tech-quick-start-kit link /downloads/scam-call-safety-checklist.pdf",
    "mobile / text Buy on Gumroad",
    "mobile / text The paid kit is a one-time Gumroad download",
    "mobile / link /go/parent-tech-quick-start-kit",
    "mobile /go/parent-tech-quick-start-kit text $9 one-time digital download",
    "mobile /go/parent-tech-quick-start-kit text US Letter worksheet pack",
    "mobile /go/parent-tech-quick-start-kit text US Letter printable worksheets",
    "mobile /go/parent-tech-quick-start-kit text US Letter printable PDF worksheets",
    "mobile /go/parent-tech-quick-start-kit text No sensitive details needed",
    "mobile /go/parent-tech-quick-start-kit text Printable worksheets",
    "mobile /products/parent-tech-quick-start-kit text 30 minutes this week",
    "mobile /products/parent-tech-quick-start-kit text First 30 minutes after download",
    "mobile /products/parent-tech-quick-start-kit text US families",
    "mobile /products/parent-tech-quick-start-kit text US Letter PDFs",
    "mobile /products/parent-tech-quick-start-kit text five US Letter PDFs",
    "mobile /products/parent-tech-quick-start-kit text Checkout readiness",
    "mobile /products/parent-tech-quick-start-kit text free worksheet preview first",
    "mobile /products/parent-tech-quick-start-kit text PDF worksheets in a ZIP download",
    "mobile /products/parent-tech-quick-start-kit text Know the files before checkout",
    "mobile /products/parent-tech-quick-start-kit text 01-7-Day-Parent-Tech-Setup-Plan.pdf",
    "mobile /products/parent-tech-quick-start-kit text 05-Living-Alone-Tech-Comparison-Worksheet.pdf",
    "mobile /products/parent-tech-quick-start-kit text Know what to send",
    "mobile /products/parent-tech-quick-start-kit text worksheet name, main family concern, and device category",
    "mobile /products/personalized-setup-review text What you would get back",
    "mobile /products/personalized-setup-review text What to send",
    "mobile /products/personalized-setup-review text worksheet name, the main family concern",
    "mobile /products/personalized-setup-review text device or service category",
    "mobile /products/personalized-setup-review text Example outcome",
    "mobile /products/personalized-setup-review text I will not send passwords",
    "mobile /go/parent-tech-quick-start-kit text Checkout fit check",
    "mobile /go/parent-tech-quick-start-kit text What you get",
    "mobile /go/parent-tech-quick-start-kit text What this is not",
    "mobile /go/parent-tech-quick-start-kit text Need to preview the format first?",
    "mobile /go/parent-tech-quick-start-kit text Preview a free worksheet PDF",
    "mobile /go/parent-tech-quick-start-kit text Ready to buy when",
    "mobile /go/parent-tech-quick-start-kit text I understand, continue to Gumroad",
    "mobile /go/parent-tech-quick-start-kit text about five seconds",
    "mobile /go/parent-tech-quick-start-kit text Files included after purchase",
    "mobile /go/parent-tech-quick-start-kit text 01-7-Day-Parent-Tech-Setup-Plan.pdf",
    "mobile /go/parent-tech-quick-start-kit link /downloads/scam-call-safety-checklist.pdf",
}
EXPECTED_LIVE_DELTA_BROKEN_IMAGES = {
    "https://parenttechchecklist.com/assets/medication-reminder-hero.jpg",
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"available": False, "path": str(path), "error": type(exc).__name__}
    if isinstance(data, dict):
        data["available"] = True
        data["path"] = str(path)
        return data
    return {"available": False, "path": str(path), "error": "json_not_object"}


def git_output(args: list[str], *, cwd: Path = SITE_DIR) -> str:
    result = subprocess.run(["git", "-C", str(cwd), *args], text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def failed_names(report: dict[str, Any]) -> set[str]:
    failed = report.get("failed") if isinstance(report.get("failed"), list) else []
    return {str(item.get("name")) for item in failed if isinstance(item, dict) and item.get("name")}


def has_expected_broken_image(report: dict[str, Any], viewport_name: str) -> bool:
    failed = report.get("failed") if isinstance(report.get("failed"), list) else []
    target_name = f"{viewport_name} / images load"
    for item in failed:
        if not isinstance(item, dict) or item.get("name") != target_name:
            continue
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        broken = details.get("broken_images") if isinstance(details.get("broken_images"), list) else []
        if broken and set(map(str, broken)).issubset(EXPECTED_LIVE_DELTA_BROKEN_IMAGES):
            return True
    return False


def is_expected_live_delta_failure(report: dict[str, Any], item: dict[str, Any]) -> bool:
    name = str(item.get("name", ""))
    if name in EXPECTED_LIVE_DELTA_FAILURES:
        return True
    if name in {"desktop / images load", "mobile / images load"}:
        return has_expected_broken_image(report, name.split(" ", 1)[0])
    if name in {"desktop / no console errors", "mobile / no console errors"}:
        return has_expected_broken_image(report, name.split(" ", 1)[0])
    return False


def unexpected_live_failures(report: dict[str, Any]) -> list[str]:
    failed = report.get("failed") if isinstance(report.get("failed"), list) else []
    names: list[str] = []
    for item in failed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        if name and not is_expected_live_delta_failure(report, item):
            names.append(name)
    return sorted(names)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    local_smoke = read_json(args.local_smoke_json)
    live_smoke = read_json(args.live_smoke_json)
    local_head = git_output(["rev-parse", "--short", "HEAD"])
    origin_head = git_output(["rev-parse", "--short", "origin/main"])
    ahead_count_text = git_output(["rev-list", "--count", "origin/main..HEAD"])
    dirty_paths = [line for line in git_output(["status", "--short"]).splitlines() if line.strip()]
    try:
        ahead_count = int(ahead_count_text or "0")
    except ValueError:
        ahead_count = None

    live_failed = failed_names(live_smoke)
    unexpected_failures = unexpected_live_failures(live_smoke)
    missing_expected_live_delta = sorted(EXPECTED_LIVE_DELTA_FAILURES - live_failed)
    local_ok = local_smoke.get("ok") is True
    live_delta_matches = bool(live_failed) and not unexpected_failures
    local_unpublished_change_ready = (
        (
            isinstance(ahead_count, int)
            and ahead_count >= 1
            and bool(local_head)
            and bool(origin_head)
            and local_head != origin_head
        )
        or bool(dirty_paths)
    )
    publish_gate = "awaiting_explicit_publish_approval" if args.external_publish_approved is not True else "publish_approved_by_argument"

    if not local_ok:
        status = "blocked_local_smoke_failed"
        next_action = "repair_local_site_before_publish_or_scale"
    elif not local_unpublished_change_ready:
        status = "healthy_wait_no_unpublished_site_candidate"
        next_action = (
            "continue_parenttech_cta_and_lead_intent_measurement; "
            "no local site publish candidate is pending"
        )
    elif live_delta_matches and args.external_publish_approved is not True:
        status = "ready_for_explicit_publish_approval"
        next_action = "ask_user_before_push_or_deploy_then_run_live_smoke_after_deploy"
    elif live_delta_matches:
        status = "ready_for_publish_execution"
        next_action = "run_the_existing_approved_deploy_path_then_live_smoke"
    else:
        status = "blocked_unexpected_live_regression"
        next_action = "inspect_live_smoke_failures_before_publish"

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": "parenttech_metric_improvement_predeploy_gate",
        "status": status,
        "next_action": next_action,
        "site_dir": str(SITE_DIR),
        "local_head": local_head,
        "origin_main": origin_head,
        "ahead_count": ahead_count,
        "dirty_paths_count": len(dirty_paths),
        "dirty_paths_sample": dirty_paths[:20],
        "local_unpublished_change_ready": local_unpublished_change_ready,
        "publish_gate": publish_gate,
        "local_smoke": {
            "path": str(args.local_smoke_json),
            "available": local_smoke.get("available") is True,
            "ok": local_smoke.get("ok"),
            "failed_count": len(failed_names(local_smoke)),
        },
        "live_smoke": {
            "path": str(args.live_smoke_json),
            "available": live_smoke.get("available") is True,
            "ok": live_smoke.get("ok"),
            "failed_count": len(live_failed),
            "failed_names": sorted(live_failed),
            "expected_predeploy_delta_failures": sorted(EXPECTED_LIVE_DELTA_FAILURES),
            "unexpected_live_failures": unexpected_failures,
            "missing_expected_live_delta": missing_expected_live_delta,
            "live_delta_matches_unpublished_local_copy": live_delta_matches,
        },
        "rules": {
            "read_only": True,
            "no_external_login": True,
            "no_external_publish": True,
            "no_secret_reads": True,
            "does_not_count_as_revenue": True,
            "requires_explicit_publish_approval": True,
        },
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "predeploy-gate.json"
    md_path = out_dir / "predeploy-gate.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Parent Tech Metric Improvement Predeploy Gate",
        "",
        f"- Status: `{report['status']}`",
        f"- Next action: `{report['next_action']}`",
        f"- Local head: `{report['local_head']}`",
        f"- Origin main: `{report['origin_main']}`",
        f"- Ahead count: `{report['ahead_count']}`",
        f"- Local smoke ok: `{report['local_smoke']['ok']}`",
        f"- Live smoke ok: `{report['live_smoke']['ok']}`",
        f"- Live delta matches unpublished local copy: `{report['live_smoke']['live_delta_matches_unpublished_local_copy']}`",
        "",
        "## Safety",
        "",
        "- Read-only gate.",
        "- No deploy, publish, login, or secret read.",
        "- Publish still requires explicit approval.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify Parent Tech metric-driven improvement before publish/deploy.")
    parser.add_argument("--local-smoke-json", type=Path, required=True)
    parser.add_argument("--live-smoke-json", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--external-publish-approved", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    json_path, _ = write_report(args.out_dir, report)
    print(str(json_path))
    print(f"status={report['status']}")
    ok_statuses = {
        "healthy_wait_no_unpublished_site_candidate",
        "ready_for_explicit_publish_approval",
        "ready_for_publish_execution",
    }
    return 0 if report["status"] in ok_statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
