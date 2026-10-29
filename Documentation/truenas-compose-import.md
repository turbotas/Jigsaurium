# TrueNAS Compose Import (Production)

Use `docker-compose.prod.yml` as the starting point for TrueNAS **Install via YAML**.

## What to change before import

1. Set the image to your published release, for example:
   - `ghcr.io/your-org/jigsaurium:v1.2.3`
2. Replace bind mounts with TrueNAS host paths:
    - `/mnt/<pool>/apps/jigsaurium/prod/instance:/app/instance`
3. Set `env_file` to absolute NAS paths that TrueNAS can read (for example `/mnt/NAS1Pool1/.../environments/test.env.local`), or replace with explicit `environment:` entries.
4. If the image is private, configure a GHCR pull secret/registry credential in TrueNAS and attach it to the app.

TrueNAS cannot resolve repo-relative `env_file` paths like `./environments/test.env.local` during YAML import. Use absolute `/mnt/...` paths for env files stored on the NAS.

## Private GHCR images

For private `ghcr.io/<owner>/jigsaurium:*` tags, TrueNAS must authenticate to GHCR.

- Registry: `ghcr.io`
- Username: your GitHub username (or machine user)
- Password: GitHub PAT with at least `read:packages`

Also ensure the package permissions in GitHub allow that account/token to read the `jigsaurium` container package.

## Required runtime variables

At minimum, set:

- `APP_ENV=prod`
- `AUTO_MIGRATE=1`
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
- Container startup runs `alembic upgrade head` when `AUTO_MIGRATE=1`, which supports empty databases.
- Vendored model files are expected inside the container image at `/opt/models/clip-vit-base-patch32`.
- Keep outbound egress restricted to required AI/model endpoints where possible.
