#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_HANDOFF_DIR = Path("/tmp/new-project-3-parenttech-traffic-push-handoff")
EXPECTED_CHANNEL_HANDLE = "@ParentTechChecklist"
EXPECTED_CHANNEL_URL = "https://www.youtube.com/@ParentTechChecklist"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_task(gate_json: Path, package_json: Path, handoff_dir: Path, write_handoff: bool) -> dict[str, Any]:
    generated = datetime.now().astimezone()
    gate = read_json(gate_json)
    package = read_json(package_json)
    assets = package.get("assets", {}) if isinstance(package.get("assets"), dict) else {}
    blockers = []
    if not gate_json.exists() or not gate:
        blockers.append("missing_publish_gate_report")
    if not package_json.exists() or not package:
        blockers.append("missing_traffic_push_package")
    blockers.extend(gate.get("blockers", []) if isinstance(gate.get("blockers"), list) else [])
    state = "ready_for_visible_gui_preflight" if gate.get("handoff_state") == "publish_handoff_allowed" and not blockers else "blocked"
    task = {
        "task_id": f"parenttech-traffic-push-{assets.get('campaign', 'unknown')}",
        "status": state,
        "generated_at": generated.isoformat(timespec="seconds"),
        "blockers": blockers,
        "public_side_effect": False,
        "target": {
            "platform": "youtube",
            "surface": "community_or_shorts_or_description",
            "expected_channel_handle": EXPECTED_CHANNEL_HANDLE,
            "expected_channel_url": EXPECTED_CHANNEL_URL,
        },
        "required_preflight": [
            "visible_account_or_channel_matches_expected_parenttech",
            "duplicate_campaign_or_post_check_passes",
            "no_captcha_or_2fa_prompt",
            "no_account_switch_required",
            "no_quota_or_pending_pressure_gate",
        ],
        "inputs": {
            "gate_json": str(gate_json),
            "package_json": str(package_json),
            "campaign": assets.get("campaign", ""),
            "community_post": assets.get("community_post", {}),
            "shorts_caption": assets.get("shorts_caption", {}),
            "video_description_block": assets.get("video_description_block", {}),
            "tracking_urls": assets.get("urls", {}),
        },
        "handoff": {
            "write_handoff_requested": write_handoff,
            "handoff_dir": str(handoff_dir),
            "executor_boundary": "GUI executor must write visible-account and duplicate-check proof before any publish.",
        },
    }
    if write_handoff and state == "ready_for_visible_gui_preflight":
        handoff_dir.mkdir(parents=True, exist_ok=True)
        task_path = handoff_dir / f"{task['task_id']}.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        task["handoff"]["task_path"] = str(task_path)
    return task


def render_markdown(task: dict[str, Any]) -> str:
    lines = [
        "# Parent Tech Traffic Push Publish Task",
        "",
        f"- Task ID: `{task['task_id']}`",
        f"- Status: `{task['status']}`",
        f"- Public side effect: `{task['public_side_effect']}`",
        f"- Expected channel: `{task['target']['expected_channel_handle']}`",
        "",
        "## Blockers",
    ]
    blockers = task.get("blockers", [])
    lines.extend(f"- `{item}`" for item in blockers) if blockers else lines.append("- None")
    lines.extend(["", "## Required Preflight"])
    for item in task.get("required_preflight", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Inputs"])
    lines.append(f"- Gate: `{task['inputs']['gate_json']}`")
    lines.append(f"- Package: `{task['inputs']['package_json']}`")
    lines.append(f"- Campaign: `{task['inputs']['campaign']}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an observable Parent Tech traffic-push publish task after fail-closed gates.")
    parser.add_argument("--gate-json", type=Path, required=True)
    parser.add_argument("--package-json", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/parenttech-traffic-push-publish-task"))
    parser.add_argument("--handoff-dir", type=Path, default=DEFAULT_HANDOFF_DIR)
    parser.add_argument("--write-handoff", action="store_true")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    task = build_task(args.gate_json, args.package_json, args.handoff_dir, args.write_handoff)
    (args.out_dir / "publish-task.json").write_text(
        json.dumps(task, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "publish-task.md").write_text(render_markdown(task), encoding="utf-8")
    print(args.out_dir / "publish-task.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
