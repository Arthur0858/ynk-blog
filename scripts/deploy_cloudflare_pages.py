#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

try:
    from blake3 import blake3
except ImportError as exc:  # pragma: no cover - operator guidance
    raise SystemExit(
        "Missing dependency: blake3\n"
        "Install once with:\n"
        "  python3 -m pip install --user blake3"
    ) from exc


API_BASE = "https://api.cloudflare.com/client/v4"
DEFAULT_ACCOUNT_ID = "e6780ef96bb6f53eba1dbc4d6dfa7376"
DEFAULT_PROJECT_NAME = "parenttechchecklist"
DEFAULT_BRANCH = "main"
DEFAULT_TOKEN_FILE = (
    Path.home() / ".config" / "parenttechchecklist" / "cloudflare-pages-write.token"
)
DEFAULT_VERIFY_PATHS = [
    "/",
    "/products/parent-tech-quick-start-kit",
    "/products/personalized-setup-review",
    "/robots.txt",
    "/sitemap.xml",
]
MAX_ASSET_SIZE = 25 * 1024 * 1024
MAX_BUCKET_SIZE = 40 * 1024 * 1024
MAX_BUCKET_FILE_COUNT = 2000
POLL_INTERVAL_SECONDS = 2
POLL_MAX_ATTEMPTS = 30

EXCLUDED_DIR_NAMES = {
    ".git",
    ".wrangler",
    "functions",
    "node_modules",
    "scripts",
}
EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    "_headers",
    "_redirects",
    "_routes.json",
    "_worker.js",
    "CLOUDFLARE_PAGES.md",
    "DESIGN.md",
}


class DeployError(RuntimeError):
    pass


@dataclass(frozen=True)
class FileEntry:
    rel_path: str
    path: Path
    content_type: str
    size_in_bytes: int
    hash_value: str


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    site_dir = script_dir.parent
    parser = argparse.ArgumentParser(
        description="Deploy the Parent Tech Checklist static site to Cloudflare Pages."
    )
    parser.add_argument(
        "--site-dir",
        default=str(site_dir),
        help="Static site directory to upload. Defaults to the repo root.",
    )
    parser.add_argument(
        "--account-id",
        default=os.environ.get("CLOUDFLARE_ACCOUNT_ID", DEFAULT_ACCOUNT_ID),
        help="Cloudflare account id for the Pages project.",
    )
    parser.add_argument(
        "--project-name",
        default=os.environ.get("CLOUDFLARE_PAGES_PROJECT", DEFAULT_PROJECT_NAME),
        help="Cloudflare Pages project name.",
    )
    parser.add_argument(
        "--branch",
        default=os.environ.get("CLOUDFLARE_PAGES_BRANCH", DEFAULT_BRANCH),
        help="Branch label to attach to the deployment.",
    )
    parser.add_argument(
        "--token-file",
        default=os.environ.get("CLOUDFLARE_API_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)),
        help="Path to the Cloudflare Pages write token file.",
    )
    parser.add_argument(
        "--commit-hash",
        default=None,
        help="Override the git commit SHA attached to this deployment.",
    )
    parser.add_argument(
        "--commit-message",
        default=None,
        help="Override the git commit message attached to this deployment.",
    )
    parser.add_argument(
        "--commit-dirty",
        choices=["true", "false"],
        default=None,
        help="Override the git dirty flag attached to this deployment.",
    )
    parser.add_argument(
        "--skip-caching",
        action="store_true",
        help="Force upload of all site assets instead of using Cloudflare hash checks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the manifest and query missing hashes without creating a deployment.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip post-deploy HTTP verification against the deployment URL.",
    )
    parser.add_argument(
        "--verify-aliases",
        action="store_true",
        help="Also verify the live custom-domain aliases returned by Pages.",
    )
    return parser.parse_args()


def log(message: str) -> None:
    print(message, flush=True)


def load_api_token(token_file: Path) -> str:
    env_token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if env_token:
        return env_token

    if not token_file.exists():
        raise DeployError(
            "Cloudflare API token file not found. "
            f"Expected: {token_file}"
        )

    token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise DeployError(f"Cloudflare API token file is empty: {token_file}")
    return token


def run_git(site_dir: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(site_dir), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def detect_git_metadata(
    site_dir: Path,
    commit_hash_override: str | None,
    commit_message_override: str | None,
    commit_dirty_override: str | None,
) -> tuple[str | None, str | None, str]:
    commit_hash = commit_hash_override or run_git(site_dir, "rev-parse", "HEAD")
    commit_message = commit_message_override or run_git(
        site_dir, "log", "-1", "--pretty=%s"
    )

    if commit_dirty_override is not None:
        commit_dirty = commit_dirty_override
    else:
        porcelain = run_git(site_dir, "status", "--porcelain") or ""
        commit_dirty = "true" if porcelain else "false"

    return commit_hash, commit_message, commit_dirty


def hash_file(path: Path) -> str:
    contents = path.read_bytes()
    base64_contents = base64.b64encode(contents).decode("ascii")
    extension = path.suffix[1:]
    return blake3((base64_contents + extension).encode("utf-8")).hexdigest()[:32]


def should_skip_file(rel_path: str) -> bool:
    parts = rel_path.split("/")
    if any(part in EXCLUDED_DIR_NAMES for part in parts[:-1]):
        return True

    name = parts[-1]
    if name.startswith("."):
        return True
    if name in EXCLUDED_FILE_NAMES:
        return True
    if name.endswith(".md"):
        return True
    return False


def collect_site_files(site_dir: Path) -> dict[str, FileEntry]:
    file_map: dict[str, FileEntry] = {}

    for root, dirs, files in os.walk(site_dir, topdown=True):
        root_path = Path(root)
        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDED_DIR_NAMES and not d.startswith(".")
        ]

        for filename in files:
            full_path = root_path / filename
            if full_path.is_symlink():
                continue

            rel_path = full_path.relative_to(site_dir).as_posix()
            if should_skip_file(rel_path):
                continue

            size_in_bytes = full_path.stat().st_size
            if size_in_bytes > MAX_ASSET_SIZE:
                raise DeployError(
                    f"Pages asset too large: {rel_path} ({size_in_bytes} bytes)"
                )

            file_map[rel_path] = FileEntry(
                rel_path=rel_path,
                path=full_path,
                content_type=mimetypes.guess_type(rel_path)[0]
                or "application/octet-stream",
                size_in_bytes=size_in_bytes,
                hash_value=hash_file(full_path),
            )

    return file_map


def stage_wrangler_assets(
    site_dir: Path, file_map: dict[str, FileEntry], stage_dir: Path
) -> None:
    for entry in file_map.values():
        destination = stage_dir / entry.rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry.path, destination)

    for special_name in ("_headers", "_redirects", "_routes.json"):
        source = site_dir / special_name
        if source.exists():
            stage_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, stage_dir / special_name)


def build_wrangler_deploy_command(
    stage_dir: Path, project_name: str, branch: str
) -> list[str]:
    return [
        "npx",
        "--yes",
        "wrangler",
        "pages",
        "deploy",
        str(stage_dir),
        "--project-name",
        project_name,
        "--branch",
        branch,
    ]


def api_json(
    method: str,
    url: str,
    *,
    bearer_token: str,
    body: dict | list | None = None,
    extra_headers: dict[str, str] | None = None,
    timeout: int = 180,
) -> dict:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")

    if extra_headers:
        headers.update(extra_headers)

    request = Request(url, data=data, method=method, headers=headers)

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise DeployError(
            f"Cloudflare API HTTP {exc.code} for {url}: {error_body}"
        ) from exc
    except URLError as exc:
        raise DeployError(f"Cloudflare API request failed for {url}: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DeployError(f"Cloudflare API returned non-JSON for {url}") from exc

    if not data.get("success"):
        raise DeployError(
            f"Cloudflare API error for {url}: "
            f"{json.dumps(data.get('errors', data), ensure_ascii=False)}"
        )

    return data


def encode_multipart(
    fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]
) -> tuple[bytes, str]:
    boundary = f"----parenttechchecklist-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(
                    "utf-8"
                ),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    for name, (filename, content, content_type) in files.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                content,
                b"\r\n",
            ]
        )

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def api_multipart(
    method: str,
    url: str,
    *,
    bearer_token: str,
    fields: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
    timeout: int = 300,
) -> dict:
    body, boundary = encode_multipart(fields, files)
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise DeployError(
            f"Cloudflare API HTTP {exc.code} for {url}: {error_body}"
        ) from exc
    except URLError as exc:
        raise DeployError(f"Cloudflare API request failed for {url}: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DeployError(f"Cloudflare API returned non-JSON for {url}") from exc

    if not data.get("success"):
        raise DeployError(
            f"Cloudflare API error for {url}: "
            f"{json.dumps(data.get('errors', data), ensure_ascii=False)}"
        )

    return data


def get_upload_jwt(account_id: str, project_name: str, api_token: str) -> str:
    url = f"{API_BASE}/accounts/{account_id}/pages/projects/{project_name}/upload-token"
    return api_json("GET", url, bearer_token=api_token)["result"]["jwt"]


def get_missing_hashes(upload_jwt: str, hash_values: Iterable[str]) -> list[str]:
    url = f"{API_BASE}/pages/assets/check-missing"
    return api_json(
        "POST",
        url,
        bearer_token=upload_jwt,
        body={"hashes": list(hash_values)},
        timeout=240,
    )["result"]


def bucket_files(files: list[FileEntry]) -> list[list[FileEntry]]:
    buckets: list[dict[str, object]] = [
        {"files": [], "remaining": MAX_BUCKET_SIZE}  # type: ignore[dict-item]
    ]

    for file_entry in sorted(files, key=lambda item: item.size_in_bytes, reverse=True):
        inserted = False
        for bucket in buckets:
            remaining = bucket["remaining"]  # type: ignore[assignment]
            bucket_files_list = bucket["files"]  # type: ignore[assignment]
            if (
                remaining >= file_entry.size_in_bytes
                and len(bucket_files_list) < MAX_BUCKET_FILE_COUNT
            ):
                bucket_files_list.append(file_entry)
                bucket["remaining"] = remaining - file_entry.size_in_bytes
                inserted = True
                break
        if not inserted:
            buckets.append(
                {
                    "files": [file_entry],
                    "remaining": MAX_BUCKET_SIZE - file_entry.size_in_bytes,
                }
            )

    return [bucket["files"] for bucket in buckets if bucket["files"]]


def upload_missing_files(upload_jwt: str, missing_files: list[FileEntry]) -> None:
    if not missing_files:
        log("Missing assets: 0")
        return

    url = f"{API_BASE}/pages/assets/upload"
    buckets = bucket_files(missing_files)
    log(f"Missing assets: {len(missing_files)} across {len(buckets)} upload batch(es)")

    uploaded = 0
    for index, bucket in enumerate(buckets, start=1):
        payload = []
        for entry in bucket:
            payload.append(
                {
                    "key": entry.hash_value,
                    "value": base64.b64encode(entry.path.read_bytes()).decode("ascii"),
                    "metadata": {"contentType": entry.content_type},
                    "base64": True,
                }
            )
        api_json("POST", url, bearer_token=upload_jwt, body=payload, timeout=300)
        uploaded += len(bucket)
        log(f"Uploaded batch {index}/{len(buckets)} ({uploaded}/{len(missing_files)})")


def upsert_hashes(upload_jwt: str, hash_values: Iterable[str]) -> None:
    url = f"{API_BASE}/pages/assets/upsert-hashes"
    api_json(
        "POST",
        url,
        bearer_token=upload_jwt,
        body={"hashes": list(hash_values)},
        timeout=240,
    )


def create_deployment(
    *,
    account_id: str,
    project_name: str,
    api_token: str,
    branch: str,
    commit_hash: str | None,
    commit_message: str | None,
    commit_dirty: str,
    site_dir: Path,
    file_map: dict[str, FileEntry],
) -> dict:
    manifest = {
        f"/{rel_path}": entry.hash_value for rel_path, entry in sorted(file_map.items())
    }
    fields = {
        "manifest": json.dumps(manifest, separators=(",", ":")),
        "branch": branch,
        "commit_dirty": commit_dirty,
    }
    if commit_hash:
        fields["commit_hash"] = commit_hash
    if commit_message:
        fields["commit_message"] = commit_message

    upload_files: dict[str, tuple[str, bytes, str]] = {}
    for special_name in ("_headers", "_redirects"):
        special_path = site_dir / special_name
        if special_path.exists():
            upload_files[special_name] = (
                special_name,
                special_path.read_bytes(),
                "application/octet-stream",
            )

    routes_path = site_dir / "_routes.json"
    if routes_path.exists():
        upload_files["_routes.json"] = (
            "_routes.json",
            routes_path.read_bytes(),
            "application/json",
        )

    url = f"{API_BASE}/accounts/{account_id}/pages/projects/{project_name}/deployments"
    return api_multipart(
        "POST",
        url,
        bearer_token=api_token,
        fields=fields,
        files=upload_files,
        timeout=300,
    )["result"]


def poll_deployment(
    account_id: str, project_name: str, deployment_id: str, api_token: str
) -> dict:
    url = (
        f"{API_BASE}/accounts/{account_id}/pages/projects/"
        f"{project_name}/deployments/{deployment_id}"
    )
    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        data = api_json("GET", url, bearer_token=api_token)
        result = data["result"]
        latest_stage = result.get("latest_stage") or {}
        status = latest_stage.get("status")
        stage_name = latest_stage.get("name")
        log(f"Poll {attempt}/{POLL_MAX_ATTEMPTS}: {stage_name or 'unknown'} {status or 'unknown'}")
        if status == "success":
            return result
        if status in {"failure", "canceled"}:
            raise DeployError(
                "Cloudflare deployment did not succeed: "
                f"{json.dumps(result, ensure_ascii=False)}"
            )
        time.sleep(POLL_INTERVAL_SECONDS)
    raise DeployError("Timed out waiting for Cloudflare Pages deployment success")


def fetch_url(url: str) -> tuple[int, str]:
    request = Request(
        url,
        method="GET",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def verify_urls(base_urls: list[str]) -> None:
    unique_bases: list[str] = []
    for base_url in base_urls:
        if base_url and base_url not in unique_bases:
            unique_bases.append(base_url.rstrip("/"))

    for base_url in unique_bases:
        for path in DEFAULT_VERIFY_PATHS:
            target = f"{base_url}{path}"
            status, _ = fetch_url(target)
            if status != 200:
                raise DeployError(f"Verification failed for {target}: HTTP {status}")
            log(f"Verified {target} -> HTTP 200")


def main() -> int:
    args = parse_args()
    site_dir = Path(args.site_dir).resolve()
    token_file = Path(args.token_file).expanduser().resolve()

    if not site_dir.exists():
        raise DeployError(f"Site directory not found: {site_dir}")

    api_token = load_api_token(token_file)
    commit_hash, commit_message, commit_dirty = detect_git_metadata(
        site_dir,
        args.commit_hash,
        args.commit_message,
        args.commit_dirty,
    )

    log(f"Site directory: {site_dir}")
    log(f"Cloudflare project: {args.project_name}")
    log(f"Branch label: {args.branch}")
    if commit_hash:
        log(f"Commit hash: {commit_hash}")
    if commit_message:
        log(f"Commit message: {commit_message}")
    log(f"Commit dirty: {commit_dirty}")

    upload_jwt = get_upload_jwt(args.account_id, args.project_name, api_token)
    file_map = collect_site_files(site_dir)
    total_size = sum(entry.size_in_bytes for entry in file_map.values())
    log(f"Static assets: {len(file_map)} file(s), {total_size} bytes")

    if args.skip_caching:
        missing_hashes = {entry.hash_value for entry in file_map.values()}
        log("Cache mode: skip remote hash check")
    else:
        missing_hashes = set(
            get_missing_hashes(
                upload_jwt, (entry.hash_value for entry in file_map.values())
            )
        )
        log(f"Remote missing hashes: {len(missing_hashes)}")

    missing_files = [
        entry for entry in file_map.values() if entry.hash_value in missing_hashes
    ]

    if args.dry_run:
        log("Dry run complete. No deployment created.")
        return 0

    if (site_dir / "functions").is_dir():
        with tempfile.TemporaryDirectory(prefix="parenttech-pages-") as temporary_dir:
            stage_dir = Path(temporary_dir)
            stage_wrangler_assets(site_dir, file_map, stage_dir)
            command = build_wrangler_deploy_command(
                stage_dir, args.project_name, args.branch
            )
            wrangler_env = os.environ.copy()
            wrangler_env["CLOUDFLARE_API_TOKEN"] = api_token
            wrangler_env["CLOUDFLARE_ACCOUNT_ID"] = args.account_id
            log("Pages Functions detected: deploying filtered assets with Wrangler")
            try:
                subprocess.run(
                    command,
                    cwd=site_dir,
                    env=wrangler_env,
                    check=True,
                )
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                raise DeployError(f"Wrangler deployment failed: {exc}") from exc

        if not args.no_verify:
            verify_urls([f"https://{args.project_name}.pages.dev"])
        log("Cloudflare Pages Functions deployment completed")
        return 0

    upload_missing_files(upload_jwt, missing_files)
    upsert_hashes(upload_jwt, [entry.hash_value for entry in file_map.values()])
    log("Hash cache updated")

    deployment = create_deployment(
        account_id=args.account_id,
        project_name=args.project_name,
        api_token=api_token,
        branch=args.branch,
        commit_hash=commit_hash,
        commit_message=commit_message,
        commit_dirty=commit_dirty,
        site_dir=site_dir,
        file_map=file_map,
    )
    deployment_id = deployment["id"]
    log(f"Deployment created: {deployment_id}")
    log(f"Deployment URL: {deployment['url']}")

    final_result = poll_deployment(
        args.account_id, args.project_name, deployment_id, api_token
    )

    if not args.no_verify:
        verify_targets = [final_result["url"]]
        if args.verify_aliases:
            verify_targets.extend(final_result.get("aliases") or [])
        verify_urls(verify_targets)

    log("Cloudflare Pages deployment completed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DeployError as exc:
        log(f"ERROR: {exc}")
        raise SystemExit(1)
