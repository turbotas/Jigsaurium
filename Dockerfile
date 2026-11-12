FROM python:3.12-slim

# Build metadata (APP_VERSION, APP_BUILD_SHA, APP_BUILD_TIME) is set at the end of this file so
# that it does not invalidate the cached OS and Python layers on every build.
ARG IMAGE_EMBEDDING_MODEL_NAME=openai/clip-vit-base-patch32
ARG IMAGE_EMBEDDING_MODEL_REVISION=3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268
ARG HF_TOKEN=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=prod \
    IMAGE_EMBEDDING_MODEL_NAME=${IMAGE_EMBEDDING_MODEL_NAME} \
    IMAGE_EMBEDDING_MODEL_REVISION=${IMAGE_EMBEDDING_MODEL_REVISION} \
    IMAGE_EMBEDDING_MODEL_LOCAL_PATH=/opt/models/clip-vit-base-patch32 \
    IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY=1 \
    IMAGE_EMBEDDINGS_WARM_ON_STARTUP=1 \
    IMAGE_EMBEDDINGS_STARTUP_FAIL_ON_ERROR=1

WORKDIR /app

# Upgrade base-image OS packages so published security fixes are included even when the
# python:3.12-slim tag has not been rebuilt yet. CI passes OS_REFRESH=<ISO week> so this cached
# layer (and the Python layer below it) is rebuilt at least weekly.
ARG OS_REFRESH=
RUN echo "OS package refresh: ${OS_REFRESH:-unset}" \
    && apt-get update \
    && apt-get upgrade --yes \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements ./requirements
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements/prod.txt -c requirements/known-good-prod.txt

COPY . .

RUN chmod +x ./scripts/docker_entrypoint.sh

RUN python - <<'PY'
import os
import shutil

from huggingface_hub import snapshot_download

source = "/app/.hf-models/clip-vit-base-patch32"
target = "/opt/models/clip-vit-base-patch32"

os.makedirs("/opt/models", exist_ok=True)
shutil.rmtree(target, ignore_errors=True)

if os.path.isdir(source):
    shutil.copytree(source, target)
else:
    kwargs = {
        "repo_id": os.environ["IMAGE_EMBEDDING_MODEL_NAME"],
        "revision": os.environ["IMAGE_EMBEDDING_MODEL_REVISION"],
        "local_dir": target,
    }
    token = str(os.environ.get("HF_TOKEN", "") or "").strip()
    if token:
        kwargs["token"] = token
    snapshot_download(**kwargs)
PY

# pip and the ensurepip installer wheels are not used at runtime; they carry an old vendored copy
# of setuptools (pkg_resources) that vulnerability scanners flag.
RUN python -m pip uninstall --yes pip \
    && rm -rf "$(python -c 'import ensurepip, os; print(os.path.dirname(ensurepip.__file__))')/_bundled"

ARG APP_VERSION=0.0.0-dev
ARG APP_BUILD_SHA=local
ARG APP_BUILD_TIME=
ENV APP_VERSION=${APP_VERSION} \
    APP_BUILD_SHA=${APP_BUILD_SHA} \
    APP_BUILD_TIME=${APP_BUILD_TIME}

EXPOSE 5000

ENTRYPOINT ["./scripts/docker_entrypoint.sh"]
# Production WSGI server (settings in gunicorn.conf.py), not the Flask development server.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "run:app"]
