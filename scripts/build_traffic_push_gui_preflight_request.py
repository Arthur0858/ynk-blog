#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_REQUEST_DIR = Path("/Users/mac/Mounts/ProjectDataCenter/inputs/gui-ops/parenttech")
EXPECTED_CHANNEL_HANDLE = "@ParentTechChecklist"
EXPECTED_CHANNEL_URL = "https://www.youtube.com/@ParentTechChecklist"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def build_request(task_json: Path, request_dir: Path, write_request: bool) -> dict[str, Any]:
    generated = datetime.now().astimezone()
    task = read_json(task_json)
    blockers: list[str] = []
    if not task_json.exists() or not task:
        blockers.append("missing_publish_task")
    elif task.get("status") != "ready_for_visible_gui_preflight":
        blockers.append(f"publish_task_not_ready:{task.get('status', 'unknown')}")

    state = "request_ready" if not blockers else "blocked"
    request = {
        "request_id": f"parenttech-gui-preflight-{task.get('inputs', {}).get('campaign', 'unknown')}",
        "status": state,
        "generated_at": generated.isoformat(timespec="seconds"),
        "blockers": blockers,
        "public_side_effect_allowed": False,
        "operator_surface": "windows-codex-computer-use",
        "machine": "ArthurNB",
        "target_app": "youtube_studio",
        "expected_account_or_channel": EXPECTED_CHANNEL_HANDLE,
        "expected_channel_url": EXPECTED_CHANNEL_URL,
        "task_scope": "read_only_verification",
        "required_result_fields": {
            "identity_verified": True,
            "duplicate_check": "passed",
            "public_side_effect": False,
            "status": "success",
        },
        "stop_conditions": [
            "wrong_account_or_channel",
            "login_or_captcha_or_2fa",
            "password_or_otp_or_recovery_code_prompt",
            "duplicate_post_or_campaign_detected",
            "any_public_side_effect_would_be_required",
        ],
        "inputs": task.get("inputs", {}),
        "result_artifact_contract": {
            "write_under": "D:\\ProjectDataCenter\\reports\\gui-ops\\YYYY-MM-DD\\",
            "template": "D:\\ProjectDataCenter\\reports\\gui-ops\\_templates\\gui-op-result-template.json",
            "must_include_screenshot_paths": True,
        },
    }
    if write_request and state == "request_ready":
        request_dir.mkdir(parents=True, exist_ok=True)
        request_path = request_dir / f"{request['request_id']}.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        request["request_path"] = str(request_path)
    return request


def render_markdown(request: dict[str, Any]) -> str:
    lines = [
        "# Parent Tech GUI Preflight Request",
        "",
        f"- Request ID: `{request['request_id']}`",
        f"- Status: `{request['status']}`",
        f"- Expected account/channel: `{request['expected_account_or_channel']}`",
        f"- Public side effect allowed: `{request['public_side_effect_allowed']}`",
        "",
        "## Blockers",
    ]
    blockers = request.get("blockers", [])
    lines.extend(f"- `{item}`" for item in blockers) if blockers else lines.append("- None")
    lines.extend(["", "## Stop Conditions"])
    for item in request.get("stop_conditions", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Result Artifact Contract"])
    for key, value in request.get("result_artifact_contract", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an ArthurNB GUI preflight request for Parent Tech traffic push publishing.")
    parser.add_argument("--task-json", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/parenttech-traffic-push-gui-preflight-request"))
    parser.add_argument("--request-dir", type=Path, default=DEFAULT_REQUEST_DIR)
    parser.add_argument("--write-request", action="store_true")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    request = build_request(args.task_json, args.request_dir, args.write_request)
    (args.out_dir / "gui-preflight-request.json").write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "gui-preflight-request.md").write_text(render_markdown(request), encoding="utf-8")
    print(args.out_dir / "gui-preflight-request.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
