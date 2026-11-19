#!/usr/bin/env python
"""Delete old container images from GHCR, keeping the ones that recently reached prod or test (issue #109).

Kept:

- the images of the last N successful `prod` deployments and the last N successful `test`
  deployments. GitHub records a deployment each time the promote job runs in an environment; the
  record's commit maps to the `sha-<12>` image tag. (A promotion started by hand, such as a
  rollback, records the workflow's commit instead; its image is still kept because a pointer
  points at it.)
- whatever the `test` and `prod` pointer tags point at now;
- anything pushed in the last few hours, so a build that is not promoted yet is never deleted;
- the untagged parts of every kept image (its platform image and attestation manifests).

Everything else in the package is deleted. Without --delete it only lists what it would delete.
Git tags and GitHub Releases are not touched. GitHub can restore a deleted version within 30 days.

Uses the `gh` CLI (GH_TOKEN) for the GitHub API and `docker buildx imagetools` (logged in to
GHCR) to read image indexes. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

POINTERS = ("prod", "test")


class RefusedError(RuntimeError):
    """The data looks wrong, so nothing is deleted."""


@dataclass
class Plan:
    keep: dict[str, list[str]] = field(default_factory=dict)  # digest -> reasons
    delete: list[dict] = field(default_factory=list)  # package versions

    def add_keep(self, digest: str, reason: str) -> None:
        reasons = self.keep.setdefault(digest, [])
        if reason not in reasons:
            reasons.append(reason)


def _tags(version: dict) -> list[str]:
    return ((version.get("metadata") or {}).get("container") or {}).get("tags") or []


def _created(version: dict) -> datetime:
    return datetime.fromisoformat(version["created_at"].replace("Z", "+00:00"))


def label(version: dict) -> str:
    tags = _tags(version)
    return ", ".join(tags) if tags else "(untagged)"


def deployment_state(statuses: list[dict]) -> str | None:
    """"success" if the deployment ever succeeded, else its latest status (statuses are newest first).

    GitHub marks a deployment "inactive" once a newer one in the same environment succeeds, so the
    latest status alone would drop every image but the newest.
    """
    if any(status.get("state") == "success" for status in statuses or []):
        return "success"
    return statuses[0]["state"] if statuses else None


def recent_successful_shas(deployments: list[dict], count: int) -> list[str]:
    """Commits of the newest `count` deployments whose last status is success, newest first."""
    shas = []
    for deployment in sorted(deployments, key=lambda d: d["created_at"], reverse=True):
        if deployment.get("state") == "success" and deployment["sha"] not in shas:
            shas.append(deployment["sha"])
            if len(shas) == count:
                break
    return shas


def roots_to_keep(
    deployments: dict[str, list[dict]], versions: list[dict], *, keep: int, grace: timedelta, now: datetime
) -> Plan:
    """Choose the tagged images (and recent pushes) to keep. Their children are added later."""
    plan = Plan()
    by_tag = {tag: version for version in versions for tag in _tags(version)}

    for pointer in POINTERS:
        if pointer not in by_tag:
            raise RefusedError(f"No image has the '{pointer}' tag; refusing to delete anything.")
        plan.add_keep(by_tag[pointer]["name"], f"`{pointer}` points at it")

    for environment in POINTERS:
        shas = recent_successful_shas(deployments.get(environment, []), keep)
        if not shas:
            raise RefusedError(f"No successful '{environment}' deployments found; refusing to delete anything.")
        for position, sha in enumerate(shas, start=1):
            version = by_tag.get(f"sha-{sha[:12]}")
            if version:
                plan.add_keep(version["name"], f"{environment} deployment {position} of the last {keep}")

    for version in versions:
        if now - _created(version) < grace:
            plan.add_keep(version["name"], f"pushed in the last {grace.total_seconds() / 3600:g} hours")
    return plan


def finish_plan(plan: Plan, versions: list[dict], children: dict[str, list[str]]) -> Plan:
    """Protect each kept image's parts, then mark everything else for deletion (tagged first)."""
    for root in list(plan.keep):
        for child in children.get(root, []):
            plan.add_keep(child, f"part of {root[:19]}")
    plan.delete = sorted(
        (version for version in versions if version["name"] not in plan.keep),
        key=lambda version: (not _tags(version), version["created_at"]),
    )
    return plan


def render(plan: Plan, versions: list[dict], *, deleting: bool) -> str:
    by_digest = {version["name"]: version for version in versions}
    lines = [
        f"### Old images: {'deleted' if deleting else 'dry run, nothing deleted'}",
        "",
        f"Keeping {len(plan.keep)} package versions, {'deleting' if deleting else 'would delete'} {len(plan.delete)}.",
        "",
        "| Kept | Tags | Why |",
        "| --- | --- | --- |",
    ]
    for digest, reasons in plan.keep.items():
        if any(reason.startswith("part of ") for reason in reasons) and len(reasons) == 1:
            continue  # parts of kept images: counted, not listed
        version = by_digest.get(digest)
        tags = label(version) if version else "(not in the package)"
        lines.append(f"| `{digest[:19]}` | {tags} | {'; '.join(reasons)} |")
    lines += ["", "| To delete | Tags | Pushed |", "| --- | --- | --- |"]
    lines += [f"| `{v['name'][:19]}` | {label(v)} | {v['created_at'][:16].replace('T', ' ')} |" for v in plan.delete if _tags(v)]
    untagged = sum(1 for version in plan.delete if not _tags(version))
    if untagged:
        lines.append(f"| | {untagged} untagged parts of the images above, or left over | |")
    return "\n".join(lines) + "\n"


# --- GitHub and registry access -------------------------------------------------------------------


def gh_api(path: str, *, method: str = "GET", paginate: bool = False):
    command = ["gh", "api", "-X", method, path]
    if paginate:
        command += ["--paginate", "--slurp"]
    output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    if not output.strip():
        return None
    data = json.loads(output)
    return [item for page in data for item in page] if paginate else data


def fetch_deployments(repo: str, environment: str, keep: int) -> list[dict]:
    """Deployments, newest first, with their latest status; stops after `keep` successes."""
    found, successes, page = [], 0, 1
    while successes < keep:
        batch = gh_api(f"repos/{repo}/deployments?environment={environment}&per_page=100&page={page}")
        if not batch:
            break
        for deployment in batch:
            state = deployment_state(gh_api(f"repos/{repo}/deployments/{deployment['id']}/statuses?per_page=100"))
            found.append({"sha": deployment["sha"], "created_at": deployment["created_at"], "state": state})
            successes += state == "success"
            if successes >= keep:
                break
        page += 1
    return found


def child_digests(image: str, digest: str) -> list[str]:
    raw = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", "--raw", f"{image}@{digest}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [entry["digest"] for entry in json.loads(raw).get("manifests", [])]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, help="GitHub owner/name whose deployments to read")
    parser.add_argument("--package", default="jigsaurium", help="GHCR package name")
    parser.add_argument("--keep", type=int, default=5, help="successful deployments to keep per environment")
    parser.add_argument("--grace-hours", type=float, default=3, help="never delete images pushed this recently")
    parser.add_argument("--delete", action="store_true", help="delete; without it, only list what would go")
    args = parser.parse_args(argv)

    owner = args.repo.split("/")[0]
    owner_type = gh_api(f"users/{owner}")["type"]
    package_path = f"{'orgs' if owner_type == 'Organization' else 'users'}/{owner}/packages/container/{args.package}"
    image = f"ghcr.io/{owner.lower()}/{args.package}"

    versions = gh_api(f"{package_path}/versions?per_page=100", paginate=True)
    deployments = {environment: fetch_deployments(args.repo, environment, args.keep) for environment in POINTERS}
    now = datetime.now(timezone.utc)
    try:
        plan = roots_to_keep(deployments, versions, keep=args.keep, grace=timedelta(hours=args.grace_hours), now=now)
    except RefusedError as error:
        print(f"::error::{error}")
        return 1
    children = {digest: child_digests(image, digest) for digest in plan.keep}
    finish_plan(plan, versions, children)

    report = render(plan, versions, deleting=args.delete)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(report)

    if args.delete:
        for version in plan.delete:
            gh_api(f"{package_path}/versions/{version['id']}", method="DELETE")
            print(f"Deleted {version['name']} ({label(version)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
