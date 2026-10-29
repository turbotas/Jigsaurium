# First Test and Prod Deploy (Single Working Path)

This is the one supported release path for first deployment.

- Build images in GitHub Actions.
- Promote `test` and `prod` pointers in GitHub Actions.
- Deploy from GHCR in TrueNAS.

Do not use local build/push scripts for first deploy.

## Prerequisites

- You can push commits and tags to `origin/master`.
- `gh` CLI is installed and authenticated (`gh auth status`).
- Docker image package access is enabled for this repository in GitHub.
- TrueNAS Apps is running.
- You have DNS/proxy/TLS ready for test and prod hostnames.
- You have two databases ready (`test` and `prod`).

## 1) Prepare runtime env files

Create:

- `environments/test.env.local`
- `environments/prod.env.local`

Copy from examples and set real values.

Required minimum values in each file:

- `APP_ENV=test` or `APP_ENV=prod`
- `AUTO_MIGRATE=1`
- `DATABASE_URL`
- `SECRET_KEY`
- `AI_ENABLED=1`
- `AI_API_KEY`
- `AI_ENDPOINT_URL`
- `AI_MODEL`
- `IMAGE_EMBEDDINGS_ENABLED=1`
- `IMAGE_EMBEDDING_MODEL_NAME`
- `IMAGE_EMBEDDING_MODEL_REVISION`

Keep `APP_VERSION`, `APP_BUILD_SHA`, and `APP_BUILD_TIME` unset in env files so image metadata stays authoritative.

## 2) Push release code to default branch

The workflow dispatch issue you hit happens when the workflow file is not present on remote default branch.

Run:

```sh
git push origin master
```

## 3) Create and push immutable release tag

Choose version (example `v0.1.0`):

```sh
git tag v0.1.0
git push origin v0.1.0
```

This triggers `Container Release` and publishes:

- `ghcr.io/<owner>/jigsaurium:v0.1.0`
- `ghcr.io/<owner>/jigsaurium:sha-<shortsha>`

Wait for success:

```sh
gh run list --workflow "Container Release" --limit 5
```

## 4) Promote test pointer to the release

Run:

```sh
gh workflow run promote-pointer-tag.yml -f source_ref=v0.1.0 -f target_pointer=test
```

Watch progress:

```sh
gh run list --workflow "Promote Pointer Tag" --limit 5
```

## 5) Deploy test in TrueNAS

1. Apps -> Discover Apps -> three-dot menu -> Install via YAML.
2. Start from `docker-compose.test.yml`.
3. Set image to `ghcr.io/<owner>/jigsaurium:test`.
4. Replace volume host path with your TrueNAS dataset path.
5. Do not rely on `env_file` paths in TrueNAS. In environment section, paste values from `environments/test.env.local`.
6. Deploy and wait for Running.
7. Verify `GET /api/v1/health` through test URL.

If image pull fails and your package is private, add GHCR registry credentials in TrueNAS (`ghcr.io`, GitHub username, PAT with `read:packages`) and attach that pull secret to the app.

Expected key values:

- `environment`: `test`
- `version`: `v0.1.0` (or your release tag)
- `build_sha`: non-empty

## 6) Promote prod pointer to the same release

After test validation:

```sh
gh workflow run promote-pointer-tag.yml -f source_ref=v0.1.0 -f target_pointer=prod
```

## 7) Deploy prod in TrueNAS

1. Install via YAML again.
2. Start from `docker-compose.prod.yml`.
3. Set image to `ghcr.io/<owner>/jigsaurium:prod`.
4. Use prod dataset mount path.
5. Paste prod runtime env values from `environments/prod.env.local` under `environment:`.
6. Deploy and verify `/api/v1/health` on prod URL.

## 8) Next releases

For `v0.1.1` and later, repeat the exact sequence:

1. `git push origin master`
2. `git tag vX.Y.Z`
3. `git push origin vX.Y.Z`
4. Promote `test`
5. Validate test
6. Promote `prod`

Rollback is pointer-only:

- repoint `prod` back to an earlier version with the same promote workflow.

## Troubleshooting

- `gh workflow run ... could not find any workflows named ...`
  - Use filename form exactly: `promote-pointer-tag.yml`.
  - Ensure latest workflow files are on remote default branch: `git push origin master`.
- `/api/v1/health` returns 500 on empty DB
  - Confirm `AUTO_MIGRATE=1` is present in runtime environment.
- Image pull denied in TrueNAS
  - Configure GHCR pull credentials in TrueNAS (`ghcr.io` + GitHub username + PAT `read:packages`).
  - Confirm package visibility/permissions for `ghcr.io/<owner>/jigsaurium`.
