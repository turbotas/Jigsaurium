import argparse
import os
import shutil
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    load_dotenv = None

from huggingface_hub import snapshot_download


REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Prefetch and vendor the embedding model into a local directory."
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Hugging Face model id (defaults to IMAGE_EMBEDDING_MODEL_NAME or openai/clip-vit-base-patch32).",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="Model revision/tag/commit (defaults to IMAGE_EMBEDDING_MODEL_REVISION or main).",
    )
    parser.add_argument(
        "--target-dir",
        default=None,
        help="Target directory for vendored model files (defaults to IMAGE_EMBEDDING_MODEL_LOCAL_PATH).",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Optional Hugging Face token (falls back to HF_TOKEN env var).",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional .env-style file to load first (default: root .env when present).",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not delete target directory before download.",
    )
    return parser.parse_args()


def _load_runtime_environment(env_file):
    if load_dotenv is None:
        return

    if env_file:
        load_dotenv(dotenv_path=Path(env_file), override=True)
        return

    default_env_file = REPO_ROOT / ".env"
    if default_env_file.exists():
        load_dotenv(dotenv_path=default_env_file, override=False)


def _resolve_target_dir(raw_target):
    text = str(raw_target or "").strip()
    if not text:
        text = ".hf-models/clip-vit-base-patch32"
    target_path = Path(text)
    if not target_path.is_absolute():
        target_path = REPO_ROOT / target_path
    return target_path


def _compute_tree_stats(root_path):
    files = [path for path in root_path.rglob("*") if path.is_file()]
    total_bytes = 0
    for path in files:
        total_bytes += path.stat().st_size
    return len(files), total_bytes


def main():
    args = _parse_args()
    _load_runtime_environment(args.env_file)

    model_name = str(
        args.model_name
        or os.getenv("IMAGE_EMBEDDING_MODEL_NAME")
        or "openai/clip-vit-base-patch32"
    ).strip()
    revision = str(
        args.revision
        or os.getenv("IMAGE_EMBEDDING_MODEL_REVISION")
        or "main"
    ).strip()
    target_dir = _resolve_target_dir(args.target_dir or os.getenv("IMAGE_EMBEDDING_MODEL_LOCAL_PATH"))
    token = str(args.token or os.getenv("HF_TOKEN") or "").strip()

    if not args.keep_existing:
        shutil.rmtree(target_dir, ignore_errors=True)

    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"Model: {model_name}")
    print(f"Revision: {revision}")
    print(f"Target: {target_dir}")
    print(f"Auth token: {'set' if token else 'not set'}")

    started = time.perf_counter()
    download_kwargs = {
        "repo_id": model_name,
        "revision": revision,
        "local_dir": str(target_dir),
    }
    if token:
        download_kwargs["token"] = token

    snapshot_download(**download_kwargs)

    duration_seconds = time.perf_counter() - started
    file_count, total_bytes = _compute_tree_stats(target_dir)

    print(f"Completed in {duration_seconds:.2f}s")
    print(f"Files: {file_count}")
    print(f"Bytes: {total_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
