FROM python:3.12-slim

ARG APP_VERSION=0.0.0-dev
ARG APP_BUILD_SHA=local
ARG APP_BUILD_TIME=
ARG IMAGE_EMBEDDING_MODEL_NAME=openai/clip-vit-base-patch32
ARG IMAGE_EMBEDDING_MODEL_REVISION=3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268
ARG HF_TOKEN=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=prod \
    APP_VERSION=${APP_VERSION} \
    APP_BUILD_SHA=${APP_BUILD_SHA} \
    APP_BUILD_TIME=${APP_BUILD_TIME} \
    IMAGE_EMBEDDING_MODEL_NAME=${IMAGE_EMBEDDING_MODEL_NAME} \
    IMAGE_EMBEDDING_MODEL_REVISION=${IMAGE_EMBEDDING_MODEL_REVISION} \
    IMAGE_EMBEDDING_MODEL_LOCAL_PATH=/opt/models/clip-vit-base-patch32 \
    IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY=1 \
    IMAGE_EMBEDDINGS_WARM_ON_STARTUP=1 \
    IMAGE_EMBEDDINGS_STARTUP_FAIL_ON_ERROR=1 \
    FLASK_APP=run:app \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000

WORKDIR /app

RUN apt-get update \
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

EXPOSE 5000

ENTRYPOINT ["./scripts/docker_entrypoint.sh"]
CMD ["python", "-m", "flask", "run"]
