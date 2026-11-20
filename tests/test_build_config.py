"""Image build and CI settings that once caused build warnings (issue #108)."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
# Name parts Docker's SecretsUsedInArgOrEnv check treats as sensitive.
SECRET_NAME = re.compile(r"(?i)(token|secret|passw(or)?d|api_?key|auth|credential)")


@pytest.mark.functional
def test_dockerfile_passes_no_secret_through_arg_or_env():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    joined = re.sub(r"\\\r?\n", " ", dockerfile)  # one line per instruction
    names = []
    for arguments in re.findall(r"^(?:ARG|ENV)\s+(.+)$", joined, re.M):
        names += [part.split("=", 1)[0] for part in arguments.split()]

    assert names, "the Dockerfile should declare some ARG/ENV names"
    assert [name for name in names if SECRET_NAME.search(name)] == []


@pytest.mark.functional
def test_model_download_reads_the_token_from_a_buildkit_secret():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "RUN --mount=type=secret,id=hf_token " in dockerfile
    assert "/run/secrets/hf_token" in dockerfile


@pytest.mark.functional
def test_ci_does_not_cache_pip_when_installs_skip_the_cache():
    for workflow in (REPO_ROOT / ".github" / "workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        if "--no-cache-dir" in text:
            assert not re.search(r"^\s*cache:\s*[\"']?pip", text, re.M), workflow.name
