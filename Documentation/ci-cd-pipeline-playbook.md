# CI/CD Pipeline Playbook (GitHub → GHCR → TrueNAS)

Status: **DRAFT proposal** – written for Jigsaurium, designed to be copied into any app repo that
ships as a Docker image to TrueNAS. Sections marked **[per-app]** are the only parts that change
between projects.

## 1. Goals

1. Dependency patches/updates arrive as pull requests with no manual effort.
2. Every change is tested automatically; nothing is released unless tests pass.
3. Every release is an **immutable image identified by digest**, built once.
4. `test` deploys automatically; `prod` deploys after one explicit approval.
5. TrueNAS pulls and applies new images itself, health-checks them, and rolls back on failure.
6. The same mechanism works for every app with only a small config file per app.

## 2. Principles

- **Build once, promote by digest.** Environments never rebuild; they point at an existing image.
- **Running containers are pinned by digest** (`image: ghcr.io/owner/app@sha256:...`). Pointer tags
  (`test`, `prod`) are only the *signal* "this is what I want"; they are never what actually runs.
- **No inbound access to the NAS.** TrueNAS polls GitHub/GHCR (pull model). GitHub never connects in.
- **Secrets stay where they are used.** Runtime env files stay on the NAS. The NAS holds a GHCR
  read token and a TrueNAS API key; GitHub holds no NAS credentials.
- **Everything is a file in the repo** (workflows, configs, deploy templates) so it can be copied.

## 3. Tag and image model (unchanged from `release-and-versioning.md`, plus digest)

| Tag | Mutable? | Created by | Purpose |
|---|---|---|---|
| `sha-<12>` | No | merge to default branch | Every tested build |
| `vX.Y.Z` | No | release tag | Named release |
| `test`, `prod` (`dev` optional) | Yes | promote workflow | Desired state per environment |

Every build also records its `sha256:` digest, an SBOM and build provenance attestation.

## 4. Pipeline flow

```
Dependabot / scheduled refresh ──► PR ──► PR checks ──► auto-merge (patch/minor) ──┐
Human PR ──────────────────────────────► PR checks ──► review/merge ───────────────┤
                                                                                   ▼
                                       Build image once (sha-<sha>, digest, SBOM, scan)
                                                                                   ▼
                                       Promote `test` pointer (automatic)
                                                                                   ▼
                          NAS agent sees new digest ► deploys ► health check ► reports to GitHub
                                                                                   ▼
        Tag vX.Y.Z (or auto-patch tag) ► Promote `prod` (GitHub Environment approval,
        requires successful test deployment of the same digest)
                                                                                   ▼
                          NAS agent sees new digest ► backup ► deploys ► health ► reports
```

### 4.1 Dependency updates

- **Dependabot** (`.github/dependabot.yml`) for `github-actions` (grouped weekly PR). Add `docker`
  / `npm` only where the app does not vendor or rebuild them another way. Jigsaurium: npm
  (GOV.UK Frontend) is vendored into `app/static/vendor` by a script, so the refresh workflow
  handles it; the base image tag is re-pulled and `apt-get upgrade`d on every build.
- **Token gotcha:** PRs opened with the built-in `GITHUB_TOKEN` do not trigger CI, and merges it
  performs do not trigger later workflows (e.g. the image build). The refresh workflow therefore
  uses a fine-grained PAT secret (`DEPS_AUTOMATION_TOKEN`: Contents + Pull requests, read/write,
  this repo only). Dependabot PRs trigger CI themselves; their auto-merge uses `GITHUB_TOKEN`,
  which is fine because action-version bumps do not change the image.
- **Python / lock files [per-app]:** if the app uses a custom lock flow (Jigsaurium:
  `requirements/*.txt` ranges + generated `known-good-*.txt`), a scheduled workflow
  (`deps-refresh.yml`) runs the app's own refresh command and opens a PR
  (`peter-evans/create-pull-request`). Contract: the app provides **one command** that
  regenerates locks and vendored assets, e.g. `scripts/refresh-deps.sh`.
- **Auto-merge:** `gh pr merge --auto --squash` enabled by a workflow for Dependabot/refresh PRs of
  patch/minor type only. Branch protection makes the CI checks required, so a failing update
  can never merge. Major updates wait for a human. Required repo settings: "Allow auto-merge" on,
  and a ruleset on the default branch requiring the CI check names (with an admin bypass if you
  still push directly). Without required checks, `--auto` merges immediately.

### 4.2 PR checks (`ci.yml`)

- Trigger on `pull_request` and pushes to the default branch only (not every branch – avoids
  duplicate runs).
- Unit/API tests, UI/e2e tests, app-specific guards (Jigsaurium: no `nvidia-*`/`cuda-*` packages).
- **Build the image without pushing**, start it, wait for the health endpoint, then stop it.
- Vulnerability scan (Trivy) – fail on fixable HIGH/CRITICAL.
- Concurrency group cancels superseded runs.

### 4.3 Build (`build-image.yml`, on push to default branch)

- Runs only after the same commit's CI passed (reusable-workflow `needs`, or `workflow_run`).
- `docker/build-push-action` with GHA cache, `provenance: true`, `sbom: true`.
- Tags `sha-<12>`; outputs the digest; writes it to the job summary.
- Automatically calls the promote workflow for `test`.

### 4.4 Release and prod (`release.yml`, `promote.yml`)

- A `vX.Y.Z` tag **re-tags the existing image for that commit** (no rebuild) and creates a GitHub
  Release from `CHANGELOG.md`. Optional: auto-create a patch tag when only dependency PRs merged.
- `promote.yml` (manual `workflow_dispatch` plus `workflow_call`) takes `source_ref` and
  `target_pointer`. For `prod` it uses a GitHub **Environment** named `production` with a required
  reviewer, and checks that the same digest has a successful `test` deployment record.
- Rollback = promote an earlier `vX.Y.Z` to `prod`. Same path, same approval.

## 5. TrueNAS deployment mechanism

### 5.1 Chosen approach: a pull-based "deploy agent" on the NAS

A small, generic script (`deploy-agent`) runs on TrueNAS as a **Cron Task every 5 minutes** (or
a systemd timer). It is identical for every app; each app has one config file.

For each app config it:

1. Resolves the digest of the watched pointer tag (`ghcr.io/owner/app:test` or `:prod`) using
   `docker buildx imagetools inspect` / `crane digest`.
2. Compares it to the digest currently deployed (recorded in its state file).
3. If different: verifies the image (attestation/signature check – optional but recommended),
   takes a pre-deploy backup if configured, then updates the TrueNAS Custom App's stored compose
   config so only the `image:` line becomes `repo@sha256:<new>`.
4. Waits until the app's container (found by compose labels, project `ix-<app>`) runs the new
   image ID, its Docker healthcheck reports healthy, and the health URL answers 2xx. The health
   body is compared with the image's revision label only if the app exposes one
   (`HEALTH_SHA_FIELD`); Jigsaurium's public `/api/v1/health` deliberately does not.
5. **On failure, automatically restores the previous digest** and marks the deployment failed.
6. Reports the result to the **GitHub Deployments API** (environment `test`/`prod`, digest,
   sha, status) using a fine-grained token. This is what lets GitHub gate `prod` on a successful
   `test` deployment without ever reaching into your network.

Why this over alternatives:

| Option | Verdict |
|---|---|
| **Deploy agent (pull, digest-pinned)** | Chosen. No inbound access, health-checked, rollback, audit trail, reusable. |
| Watchtower | Rejected: follows mutable tags, fights TrueNAS's management of custom apps, no real rollback, no GitHub reporting. |
| Self-hosted Actions runner on NAS | Viable fallback. Needs a long-lived runner with NAS API credentials; larger attack surface. |
| Webhook from GitHub to NAS | Needs inbound exposure; rejected. |

### 5.2 Per-app deployment config **[per-app]** (`deploy/<env>/agent.conf`)

```
APP_NAME=jigsaurium-test
IMAGE=ghcr.io/turbotas/jigsaurium
WATCH_TAG=test                  # pointer tag to follow
GITHUB_ENVIRONMENT=test         # name used when reporting deployments
HEALTH_URL=http://127.0.0.1:15000/api/v1/health
HEALTH_SHA_FIELD=                # [optional] health JSON field compared to the image revision label
TRUENAS_APP_NAME=jigsaurium-test  # name of the Custom App in TrueNAS whose image: line is updated
PRE_DEPLOY_BACKUP_CMD=          # [optional] e.g. DB dump hook
AUTO_APPLY=1                    # 0 for prod if you want "notify only, apply on my command"
```

### 5.3 Repo layout change

- **Current state (confirmed for `jigsaurium-test`):** the app is a TrueNAS *Custom App* whose
  compose config is essentially identical to the repo's `docker-compose.test.yml`
  (`image: ghcr.io/turbotas/jigsaurium:test`, `env_file` at an absolute NAS path, healthcheck on
  `/api/v1/health`, port `15000`). Secrets (DB credentials, API keys) are read from
  `environments/test.env.local` on the NAS, not from GitHub.
- Because of that, **no template rendering is needed.** The agent keeps the app's existing stored
  config and changes only the `image:` line, swapping `:test` for `@sha256:<digest>`. Everything
  else (env_file path, ports, volumes, healthcheck) is left exactly as configured on the NAS.
- The repo's `docker-compose.*.yml` files stay as documentation/reference of the intended config.
  Keep the NAS-specific `env_file` path out of anything shared across apps; it is a per-app value.
- Runtime `*.env.local` files stay on the NAS, never in Git. The agent never reads or copies them;
  it only requires that the file still exists (`required: True` makes the app fail loudly if not).
- `deploy/agent/deploy-agent.sh` (generic) and `deploy/agent/README.md` (install steps) live in the
  shared kit.

### 5.4 One-time NAS setup (per NAS, not per app)

1. Dataset for agent state/logs (e.g. `/mnt/<pool>/apps/deploy-agent`).
2. TrueNAS API key (least privilege available) stored in a root-only file.
3. GHCR pull credential (already created for the current process).
4. GitHub fine-grained token with only `Deployments: write` on the repos involved.
5. Cron Task running the agent every 5 minutes.

## 6. Cross-project reuse

Two reusable pieces, both plain files:

1. **Reusable workflows** in a shared repo (suggest `turbotas/pipeline-kit`):
   `ci-build-test.yml`, `build-image.yml`, `promote.yml`, `deps-refresh.yml`. Each app's
   `.github/workflows/*.yml` is a ~15-line caller that passes inputs.
2. **Deploy agent + docs** in the same repo.

Until the kit repo exists, copy this playbook plus the `deploy/` and `.github/` folders; the
per-app inputs below are all that need editing.

### 6.1 Per-app adoption checklist

- [ ] Set image name and registry owner.
- [ ] Provide test command(s), UI/e2e command(s), health endpoint path.
- [ ] Provide `scripts/refresh-deps.sh` (or accept Dependabot-only).
- [ ] Add `deploy/<env>/compose.yml.tmpl` and `agent.conf` for test and prod.
- [ ] Enable branch protection with required checks; create `production` Environment with reviewer.
- [ ] Enable auto-merge on the repo; add `dependabot.yml`.
- [ ] Pin the base image by digest (Dependabot keeps it current).
- [ ] Add health endpoint that reports build SHA/version.
- [ ] Install/enable the agent for each environment on the NAS.

## 7. Risks and decisions to confirm

1. **Database migrations vs rollback.** Jigsaurium runs `alembic upgrade head` on start
   (`AUTO_MIGRATE=1`). Rolling the image back does **not** roll the schema back. Policy needed:
   backward-compatible (expand/contract) migrations, plus a mandatory DB backup hook before every
   prod deploy.
2. **TrueNAS API for custom (YAML) apps.** The agent relies on updating a custom app's compose
   config through the TrueNAS API (`midclt`/REST). Behaviour differs by TrueNAS version; confirm
   on your version before building. Fallback: agent restarts the app after rewriting the compose
   file the app is defined from.
3. **Auto-merge scope.** Proposed: patch/minor automatic, major manual. Confirm.
4. **Prod apply mode.** Proposed: prod promotion needs GitHub approval, then the agent applies
   automatically. Alternative: agent only notifies and a human triggers apply.
5. **Image size / build time.** The image bakes in torch and the CLIP model; builds need layer
   caching. Consider a separate cached base layer for the model.
6. **Supply chain.** Scan + SBOM + provenance included; signature verification on the NAS is
   optional but recommended.

## 8. Rollout order

1. Fix CI triggers, add image build+smoke test and scan (no behaviour change to releases).
2. Add Dependabot + `deps-refresh` + auto-merge with required checks.
3. Build workflow publishes digests and promotes `test` automatically.
4. Introduce `deploy/` templates and the agent on **test only**; run alongside the manual path.
5. Add GitHub Deployments reporting and the `production` approval gate.
6. Cut prod over to the agent; retire the manual runbook
   (`truenas-first-test-and-prod-deploy.md`).
7. Extract workflows + agent into the shared kit repo and adopt in the next app.
