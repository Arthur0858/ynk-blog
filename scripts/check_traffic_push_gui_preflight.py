#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_REPORT_ROOT = Path("/mnt/d/ProjectDataCenter/reports/gui-ops")
EXPECTED_IDENTITIES = {"@ParentTechChecklist", "ParentTechChecklist", "Parent Tech Checklist"}
EXPECTED_GUI_MACHINE = "ArthurNB"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def gui_reports(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.rglob("*.json")):
        if "_templates" in path.parts:
            continue
        payload = read_json(path)
        if payload:
            rows.append((path, payload))
    return rows


def matching_parenttech_report(payload: dict[str, Any]) -> bool:
    target_app = str(payload.get("target_app", "")).lower()
    if "youtube" not in target_app:
        return False
    visible = str(payload.get("target_account_or_channel", ""))
    expected = str(payload.get("expected_account_or_channel", ""))
    combined = f"{visible} {expected}"
    return any(identity in combined for identity in EXPECTED_IDENTITIES)


def newest_matching_report(root: Path) -> tuple[Path | None, dict[str, Any]]:
    matches = [(path, payload) for path, payload in gui_reports(root) if matching_parenttech_report(payload)]
    if not matches:
        return None, {}
    return sorted(matches, key=lambda item: str(item[1].get("completed_at") or item[1].get("started_at") or item[0]))[-1]


def build_report(task_json: Path, reports_root: Path) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    task = read_json(task_json)
    if not task_json.exists() or not task:
        blockers.append("missing_publish_task")
    elif task.get("status") != "ready_for_visible_gui_preflight":
        blockers.append(f"publish_task_not_ready:{task.get('status', 'unknown')}")

    report_path, gui = newest_matching_report(reports_root)
    if not reports_root.exists():
        blockers.append("gui_reports_root_missing")
    if not gui:
        blockers.append("missing_parenttech_gui_preflight_report")
    else:
        if gui.get("status") != "success":
            blockers.append(f"gui_status_not_success:{gui.get('status', 'unknown')}")
        if str(gui.get("machine") or "") != EXPECTED_GUI_MACHINE:
            blockers.append(f"gui_machine_not_arthurnb:{gui.get('machine', 'unknown')}")
        if gui.get("identity_verified") is not True:
            blockers.append("gui_identity_not_verified")
        if gui.get("duplicate_check") != "passed":
            blockers.append(f"duplicate_check_not_passed:{gui.get('duplicate_check', 'unknown')}")
        if gui.get("public_side_effect") is not False:
            blockers.append("gui_report_has_public_side_effect")
        if gui.get("blocking_dialog") or gui.get("blocker"):
            blockers.append("gui_report_has_blocker")
        if not gui.get("screenshot_paths"):
            warnings.append("gui_report_missing_screenshot_paths")

    decision = "preflight_allowed" if not blockers else "blocked"
    return {
        "status": "passed",
        "decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "task_json": str(task_json),
        "reports_root": str(reports_root),
        "selected_gui_report": str(report_path) if report_path else "",
        "selected_gui_summary": {
            "status": gui.get("status", ""),
            "machine": gui.get("machine", ""),
            "target_app": gui.get("target_app", ""),
            "target_account_or_channel": gui.get("target_account_or_channel", ""),
            "expected_account_or_channel": gui.get("expected_account_or_channel", ""),
            "identity_verified": gui.get("identity_verified", False),
            "duplicate_check": gui.get("duplicate_check", ""),
            "public_side_effect": gui.get("public_side_effect", None),
            "screenshot_paths": gui.get("screenshot_paths", []),
        },
        "allowed_next_step": {
            "external_publish_allowed": decision == "preflight_allowed",
            "requires_current_turn_confirmation_for_final_publish": True,
            "mac_project_hub_writer_only": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Parent Tech Traffic Push GUI Preflight",
        "",
        f"- Status: `{report['status']}`",
        f"- Decision: `{report['decision']}`",
        f"- Selected GUI report: `{report['selected_gui_report']}`",
        "",
        "## Blockers",
    ]
    blockers = report.get("blockers", [])
    lines.extend(f"- `{item}`" for item in blockers) if blockers else lines.append("- None")
    warnings = report.get("warnings", [])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- `{item}`" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## GUI Summary"])
    for key, value in report.get("selected_gui_summary", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Parent Tech GUI preflight evidence before any traffic-push publish.")
    parser.add_argument("--task-json", type=Path, required=True)
    parser.add_argument("--reports-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/parenttech-traffic-push-gui-preflight"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args.task_json, args.reports_root)
    (args.out_dir / "gui-preflight.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "gui-preflight.md").write_text(render_markdown(report), encoding="utf-8")
    print(args.out_dir / "gui-preflight.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
