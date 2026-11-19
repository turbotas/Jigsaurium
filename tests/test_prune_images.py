"""scripts/prune_images.py: which GHCR images are kept and which are deleted (issue #109)."""

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
GRACE = timedelta(hours=3)


@pytest.fixture()
def prune(monkeypatch):
    spec = importlib.util.spec_from_file_location("prune_images_under_test", SCRIPTS_DIR / "prune_images.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


def _sha(n):
    return f"{n:02d}" * 20


def _build(n, *extra_tags, days_ago=None):
    """One build as GHCR stores it: a tagged index plus two untagged parts."""
    created = (NOW - timedelta(days=days_ago if days_ago is not None else 40 - n)).isoformat().replace("+00:00", "Z")
    index = {
        "id": n * 10,
        "name": f"sha256:index{n:02d}",
        "created_at": created,
        "metadata": {"container": {"tags": [f"v0.2.{n}", f"sha-{_sha(n)[:12]}", *extra_tags]}},
    }
    parts = [
        {"id": n * 10 + i, "name": f"sha256:part{n:02d}{i}", "created_at": created, "metadata": {"container": {"tags": []}}}
        for i in (1, 2)
    ]
    return [index, *parts], {index["name"]: [part["name"] for part in parts]}


def _registry(builds):
    versions, children = [], {}
    for build_versions, build_children in builds:
        versions += build_versions
        children.update(build_children)
    return versions, children


def _deployments(numbers, state="success"):
    return [
        {"sha": _sha(n), "created_at": (NOW - timedelta(days=40 - n)).isoformat(), "state": state} for n in numbers
    ]


def _plan(prune, deployments, versions, children, keep=5):
    plan = prune.roots_to_keep(deployments, versions, keep=keep, grace=GRACE, now=NOW)
    return prune.finish_plan(plan, versions, children)


@pytest.mark.functional
def test_keeps_the_last_five_prod_and_test_deployments_and_their_parts(prune):
    builds = [_build(n) for n in range(1, 21)]
    builds[19] = _build(20, "test", "prod")
    versions, children = _registry(builds)
    deployments = {
        "test": _deployments(range(1, 21)),
        "prod": _deployments([2, 5, 9, 12, 14, 20]) + _deployments([16, 17], state="waiting"),
    }

    plan = _plan(prune, deployments, versions, children)

    kept_builds = sorted({int(d[-2:]) for d in plan.keep if d.startswith("sha256:index")})
    assert kept_builds == [5, 9, 12, 14, 16, 17, 18, 19, 20]
    for n in kept_builds:
        assert f"sha256:part{n:02d}1" in plan.keep and f"sha256:part{n:02d}2" in plan.keep
    deleted = {v["name"] for v in plan.delete}
    assert "sha256:index02" in deleted and "sha256:part022" in deleted
    assert len(plan.keep) + len(plan.delete) == len(versions)
    assert plan.keep["sha256:index20"][0] == "`prod` points at it"


@pytest.mark.functional
def test_never_approved_prod_runs_do_not_count(prune):
    versions, children = _registry([_build(n) for n in range(1, 4)] + [_build(4, "test", "prod")])
    deployments = {"test": _deployments([4]), "prod": _deployments([4]) + _deployments([1, 2, 3], state="waiting")}

    plan = _plan(prune, deployments, versions, children)

    assert {v["name"] for v in plan.delete if v["metadata"]["container"]["tags"]} == {
        "sha256:index01",
        "sha256:index02",
        "sha256:index03",
    }


@pytest.mark.functional
def test_pointer_targets_are_kept_even_when_older_than_the_last_five(prune):
    builds = [_build(n) for n in range(1, 11)]
    builds[0] = _build(1, "prod")  # rolled back to an old image by hand
    builds[9] = _build(10, "test")
    versions, children = _registry(builds)
    deployments = {"test": _deployments(range(1, 11)), "prod": _deployments(range(2, 11))}

    plan = _plan(prune, deployments, versions, children)

    assert "sha256:index01" in plan.keep and "sha256:part011" in plan.keep


@pytest.mark.functional
def test_recent_pushes_are_kept_until_promoted(prune):
    builds = [_build(n) for n in range(1, 6)] + [_build(6, days_ago=0)]
    builds[4] = _build(5, "test", "prod")
    versions, children = _registry(builds)
    deployments = {"test": _deployments([5]), "prod": _deployments([5])}

    plan = _plan(prune, deployments, versions, children)

    assert {"sha256:index06", "sha256:part061", "sha256:part062"} <= set(plan.keep)


@pytest.mark.functional
def test_tagged_images_are_deleted_before_their_parts(prune):
    versions, children = _registry([_build(1), _build(2), _build(3, "test", "prod")])
    deployments = {"test": _deployments([3]), "prod": _deployments([3])}

    plan = _plan(prune, deployments, versions, children)

    tagged = [bool(v["metadata"]["container"]["tags"]) for v in plan.delete]
    assert tagged == sorted(tagged, reverse=True)


@pytest.mark.functional
@pytest.mark.parametrize(
    "deployments, tags, message",
    [
        ({"test": [], "prod": []}, ("test", "prod"), "No successful 'prod' deployments"),
        ({"test": _deployments([1]), "prod": _deployments([1], state="waiting")}, ("test", "prod"), "No successful 'prod'"),
        ({"test": _deployments([1]), "prod": _deployments([1])}, ("test",), "No image has the 'prod' tag"),
    ],
)
def test_refuses_when_the_records_look_wrong(prune, deployments, tags, message):
    versions, children = _registry([_build(1, *tags)])

    with pytest.raises(prune.RefusedError, match=message):
        prune.roots_to_keep(deployments, versions, keep=5, grace=GRACE, now=NOW)


@pytest.mark.functional
def test_report_lists_kept_and_deleted_images(prune):
    versions, children = _registry([_build(1), _build(2, "test", "prod")])
    deployments = {"test": _deployments([2]), "prod": _deployments([2])}
    plan = _plan(prune, deployments, versions, children)

    report = prune.render(plan, versions, deleting=False)

    assert "dry run, nothing deleted" in report
    assert "Keeping 3 package versions, would delete 3." in report
    assert "| `sha256:index02` | v0.2.2, sha-020202020202, test, prod | `prod` points at it; `test` points at it;" in report
    assert "| `sha256:index01` | v0.2.1, sha-010101010101 |" in report
    assert "2 untagged parts of the images above, or left over" in report


@pytest.mark.functional
@pytest.mark.parametrize(
    "statuses, expected",
    [
        ([{"state": "inactive"}, {"state": "success"}, {"state": "in_progress"}], "success"),  # replaced later
        ([{"state": "success"}, {"state": "in_progress"}], "success"),
        ([{"state": "waiting"}, {"state": "waiting"}], "waiting"),  # prod never approved
        ([{"state": "failure"}, {"state": "in_progress"}], "failure"),
        ([], None),
    ],
)
def test_a_deployment_counts_if_it_ever_succeeded(prune, statuses, expected):
    assert prune.deployment_state(statuses) == expected
