# TrueNAS Test and Prod Deployment

How Jigsaurium gets from a merged PR to the TrueNAS test and prod apps. Design and reasoning:
`ci-cd-pipeline-playbook.md`. Versioning: `release-and-versioning.md`. Deploy agent internals:
`deploy/agent/README.md`.

## How it works

```
merge to master
  -> CI (all tests, image build + smoke test + Trivy)            GitHub
  -> Build and Promote: image built once, version vX.Y.Z,         GitHub
     tag + GitHub Release, `test` pointer moved
  -> deploy agent (cron, every 5 min) sees new `test` digest:     TrueNAS
     DB backup -> app pinned to the digest -> wait healthy -> rollback on failure
  -> "Promote to prod" waits for your approval                    GitHub
  -> approve -> `prod` pointer moved -> agent deploys prod         GitHub / TrueNAS
```

- Nothing is built on a desktop and GitHub never connects to the NAS; the NAS pulls.
- The apps run a fixed digest (`ghcr.io/turbotas/jigsaurium@sha256:...`), never a moving tag.
- The running version is shown in the app's environment banner (version, build SHA, build time).

## Day-to-day

| You want to... | Do this |
|---|---|
| Ship a change to test | Merge the PR. Test updates itself in about 25 minutes. |
| Ship to prod | Actions -> newest **Build and Promote** run -> **Review deployments** -> approve `prod`. Only the run whose image is currently on test can promote; older runs refuse. |
| Start a new minor/major version | Push the tag on the latest master commit, e.g. `git tag v0.3.0 && git push origin v0.3.0`. Later builds continue `v0.3.1`, ... |
| Roll prod back | `gh workflow run promote-pointer-tag.yml -f source_ref=v0.2.1 -f target_pointer=prod`, then approve. **Not across a database migration** (see Troubleshooting). |
| See what the agent did | On the NAS: `tail -n 20 /mnt/NAS1Pool1/apps/deploy-agent/agent.log` |

Dependency updates arrive as PRs on their own (weekly refresh on Monday, GitHub Actions updates on
Sunday) and merge themselves when CI passes, so they flow to test the same way.

## One-time setup (per environment)

Already done for **test**. Use the same steps for **prod**, replacing `test` with `prod`.

### 1. Runtime env file

`environments/<env>.env.local` on the NAS (never in Git), copied from `environments/<env>.env.example`.
At minimum: `APP_ENV`, `AUTO_MIGRATE=1`, `DATABASE_URL`, `SECRET_KEY` (16+ random characters),
`CANONICAL_HOST`, and the `AI_*` / `IMAGE_EMBEDDING*` values you use. Leave `APP_VERSION`,
`APP_BUILD_SHA` and `APP_BUILD_TIME` unset; the image provides them.

### 2. Point the pointer at an image

The app needs the pointer tag to exist before it is installed. For prod, approve the `prod`
step of the newest **Build and Promote** run (or use the promote workflow above).

### 3. Instance folder

```bash
mkdir -p /mnt/NAS1Pool1/apps/jigsaurium-prod-instance
```

It lives on the `NAS1Pool1/apps` dataset (include that dataset in your snapshot tasks), never
under `/mnt/.ix-apps`, which belongs to TrueNAS.

### 4. Install the TrueNAS Custom App

Apps -> Discover Apps -> three-dot menu -> **Install via YAML**, name it `jigsaurium-prod`, and
paste `docker-compose.prod.yml`. Check before saving:

- `image: ghcr.io/turbotas/jigsaurium:prod` (the agent pins it to a digest on its first run)
- `env_file` is the absolute path to `prod.env.local`
- the volume is the absolute instance folder from step 3
- healthcheck `start_period: 600s` (model warm-up and migrations take minutes)
- the host port (`5000` for prod, `15000` for test) is free

If the image is private, attach the GHCR registry credential (Apps -> Configuration ->
Container Registries: `https://ghcr.io`, user `turbotas`, a PAT with `read:packages`).

### 5. Deploy agent config

The agent is already installed for all apps at `/mnt/NAS1Pool1/apps/deploy-agent` with a
5-minute cron job. Add a config for the new app by copying the test one:

```bash
cd /mnt/NAS1Pool1/apps/deploy-agent/conf && sed -e 's/jigsaurium-test/jigsaurium-prod/g' -e 's/^WATCH_TAG=test/WATCH_TAG=prod/' -e 's#127.0.0.1:15000#127.0.0.1:5000#' -e 's#test.env.local#prod.env.local#' jigsaurium-test.conf > jigsaurium-prod.conf && chmod 600 jigsaurium-prod.conf
```

Then prove it without changing anything, and run it once for real:

```bash
/mnt/NAS1Pool1/apps/deploy-agent/deploy-agent.sh --dry-run /mnt/NAS1Pool1/apps/deploy-agent/conf/jigsaurium-prod.conf
```

```bash
/mnt/NAS1Pool1/apps/deploy-agent/deploy-agent.sh /mnt/NAS1Pool1/apps/deploy-agent/conf/jigsaurium-prod.conf
```

From then on the cron job handles it.

## Troubleshooting

- **App flips between Deploying and Stopped / agent logs `did not become healthy`.** Look at
  the app itself: `docker logs --tail 80 <container>`. `421` on `/api/v1/health` was a bug fixed in
  v0.2.2. A slow start needs a longer `start_period` (app YAML) and `HEALTH_TIMEOUT` (agent conf).
- **`Can't locate revision identified by '...'` in the container log.** An older image is
  running against a database a newer image already migrated (a rollback across a migration).
  Fix forward: deploy a newer image (`deploy-agent.sh --force <conf>`), or restore the pre-deploy
  dump from `/mnt/NAS1Pool1/backups/deploy-agent/<app>/` (restore command in `deploy/agent/README.md`).
- **No container at all after an update.** The app was stopped; updating a stopped app only
  changes its config. Current agents start it automatically; otherwise start it in the UI.
- **Agent logs `skipping ...: previously failed`.** That digest failed health once. Fix the cause,
  then `deploy-agent.sh --force <conf>`, or let the next build move the pointer to a new digest.
- **Pause automatic deploys.** Set `AUTO_APPLY=0` in the app's agent conf; set it back to `1` to resume.
- **A PR with auto-merge queued does not merge.** `master` requires branches to be up to date;
  press **Update branch** on the PR (or `gh api -X PUT repos/turbotas/Jigsaurium/pulls/<n>/update-branch`).
- **Image pull denied.** Check the GHCR credential: in TrueNAS for the app, and
  `/mnt/NAS1Pool1/apps/deploy-agent/state/docker` for the agent (`docker login ghcr.io` again with a
  new `read:packages` PAT if it expired).
