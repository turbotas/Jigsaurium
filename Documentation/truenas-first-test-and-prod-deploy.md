# First Test and Prod Container Deploy (One-Shot Runbook)

This runbook gives you one straight path from local dev to first `test` and `prod` TrueNAS app deployments.

## Why the UI currently shows `DEV 0.0.0`

You are currently running the local dev app process, not a release container. The footer/health metadata defaults to dev/local values in that mode.

## What are `APP_BUILD_SHA` and `APP_BUILD_TIME`?

- `APP_BUILD_SHA`: git commit hash used for the built image.
- `APP_BUILD_TIME`: UTC timestamp when the image was built.

You do **not** need to type these manually. The new build scripts calculate them automatically and bake them into the image.

## Prerequisites

- Docker is installed on this machine.
- You can push to GHCR (`ghcr.io`).
- You already have:
  - empty `test` and `prod` databases
  - reverse proxies and certificates ready
  - TrueNAS Apps service running

## Step 1: Prepare test/prod env files

Create and fill local env files:

- `environments/test.env.local`
- `environments/prod.env.local`

Minimum required values for each:

- `APP_ENV` (`test` or `prod`)
- `DATABASE_URL`
- `SECRET_KEY`
- AI/embedding values (because your app requires them):
  - `AI_ENABLED=1`
  - `AI_API_KEY=...`
  - `AI_ENDPOINT_URL=...`
  - `AI_MODEL=...`
  - `IMAGE_EMBEDDINGS_ENABLED=1`
  - `IMAGE_EMBEDDING_MODEL_NAME=...`
  - `IMAGE_EMBEDDING_MODEL_REVISION=...`

Notes:

- Keep `APP_VERSION`, `APP_BUILD_SHA`, and `APP_BUILD_TIME` commented out in env files unless you intentionally want to override image metadata at runtime.

## Step 2: Build first local test container image (no registry push)

This is the first "working local docker container image for test" checkpoint.

### Windows (batch)

```bat
for /f %%i in ('git rev-parse HEAD') do set FULL_SHA=%%i
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')"') do set BUILD_TIME=%%i

docker buildx build --platform linux/amd64 --load ^
  --build-arg APP_VERSION=v0.1.0 ^
  --build-arg APP_BUILD_SHA=%FULL_SHA% ^
  --build-arg APP_BUILD_TIME=%BUILD_TIME% ^
  -t jigsaurium:test-local .
```

### Linux/macOS (shell)

```sh
FULL_SHA="$(git rev-parse HEAD)"
BUILD_TIME="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

docker buildx build --platform linux/amd64 --load \
  --build-arg APP_VERSION=v0.1.0 \
  --build-arg APP_BUILD_SHA="$FULL_SHA" \
  --build-arg APP_BUILD_TIME="$BUILD_TIME" \
  -t jigsaurium:test-local .
```

## Step 3: Local smoke test for test image (required)

Run container:

```sh
docker run --rm --name jigsaurium-test-smoke -p 15000:5000 --env-file environments/test.env.local jigsaurium:test-local
```

Verify in another shell:

```sh
curl http://127.0.0.1:15000/api/v1/health
```

Expected keys include:

- `"environment": "test"`
- `"version": "v0.1.0"`
- `"build_sha": "..."`

If this works, move on to registry and TrueNAS.

## Step 4: Build and push first release image

### Windows (batch script)

```bat
scripts\build_release_image.bat v0.1.0 YOUR_ORG
```

### Linux/macOS (shell script)

```sh
./scripts/build_release_image.sh v0.1.0 YOUR_ORG
```

These scripts auto-generate SHA/time metadata.

## Step 5: Create `test` and `prod` pointer tags

Use the same immutable release image for first deployments.

### Windows (batch script)

```bat
scripts\promote_pointer_tag.bat YOUR_ORG test v0.1.0
scripts\promote_pointer_tag.bat YOUR_ORG prod v0.1.0
```

### Linux/macOS (shell script)

```sh
./scripts/promote_pointer_tag.sh YOUR_ORG test v0.1.0
./scripts/promote_pointer_tag.sh YOUR_ORG prod v0.1.0
```

## Step 6: Deploy in TrueNAS as Custom App (test first)

1. TrueNAS UI -> **Apps** -> **Discover Apps**.
2. Click the three-dot menu -> **Install via YAML**.
3. Paste your compose content (start from `docker-compose.test.yml`).
4. Replace volume host paths with TrueNAS paths, for example:
   - `/mnt/<pool>/apps/jigsaurium/test/instance:/app/instance`
5. Replace image with your real registry tag (`ghcr.io/<org>/jigsaurium:test`).
6. Save/deploy and wait for Running.
7. Verify `/api/v1/health` through your test URL.

## Step 7: Deploy in TrueNAS for prod

Repeat Step 5 with `docker-compose.prod.yml` as baseline and prod paths, for example:

- `/mnt/<pool>/apps/jigsaurium/prod/instance:/app/instance`

Image tag:

- `ghcr.io/<org>/jigsaurium:prod`

Verify via prod URL and `/api/v1/health`.

## Ongoing release flow

For next release (`v0.1.1`):

1. Build/push immutable tag `v0.1.1`.
2. Promote `test` pointer to `v0.1.1`.
3. Validate test.
4. Promote `prod` pointer to `v0.1.1`.

This keeps rollback simple: just repoint `prod` back to prior release tag.
