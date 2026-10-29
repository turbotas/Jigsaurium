# TrueNAS Compose Import (Production)

Use `docker-compose.prod.yml` as the starting point for TrueNAS **Install via YAML**.

## What to change before import

1. Set the image to your published release, for example:
   - `ghcr.io/your-org/jigsaurium:v1.2.3`
2. Replace bind mounts with TrueNAS host paths:
    - `/mnt/<pool>/apps/jigsaurium/prod/instance:/app/instance`
3. Replace `env_file` with explicit `environment:` entries in TrueNAS if you do not want to manage a host-side env file.

The compose file loads `environments/prod.env.local` when present, then falls back to `environments/prod.env.example`.

## Required runtime variables

At minimum, set:

- `APP_ENV=prod`
- `DATABASE_URL=...`
- `SECRET_KEY=...`

`APP_VERSION`, `APP_BUILD_SHA`, and `APP_BUILD_TIME` are normally baked into the image by the build scripts and do not need runtime overrides.

And for AI/embeddings-enabled production:

- `AI_ENABLED=1`
- `AI_API_KEY=...`
- `AI_ENDPOINT_URL=...`
- `AI_MODEL=...`
- `IMAGE_EMBEDDINGS_ENABLED=1`
- `IMAGE_EMBEDDING_MODEL_NAME=...`
- `IMAGE_EMBEDDING_MODEL_REVISION=...`
- `IMAGE_EMBEDDING_MODEL_LOCAL_PATH=/opt/models/clip-vit-base-patch32`
- `IMAGE_EMBEDDINGS_LOCAL_FILES_ONLY=1`
- `IMAGE_EMBEDDINGS_WARM_ON_STARTUP=1`
- `IMAGE_EMBEDDINGS_STARTUP_FAIL_ON_ERROR=1`

`HF_TOKEN` is only needed at image build time if model download requires authenticated Hugging Face access.

## Notes

- The healthcheck uses `GET /api/v1/health`.
- Vendored model files are expected inside the container image at `/opt/models/clip-vit-base-patch32`.
- Keep outbound egress restricted to required AI/model endpoints where possible.
