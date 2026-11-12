# deploy-agent (TrueNAS 25.10+ Custom Apps)

Pull-based deployer. Every run, per app config: pull the watched pointer tag, resolve its digest,
and if it differs from what the Custom App runs, back up the DB, pin the app's `image:` to
`repo@sha256:<digest>` via `midclt`, wait for health, and roll back automatically on failure.
Design and rationale: `Documentation/ci-cd-pipeline-playbook.md`.

Files: `deploy-agent.sh` (generic), `backup-db.sh` (generic MariaDB/MySQL dump from the app's env
file), `agent.conf.example` (per app + environment).

## One-time install (per NAS)
1. Copy this folder to `/mnt/<pool>/apps/deploy-agent/` (agent, backup script, `conf/`, `state/`).
2. `chmod 700` the folder; `chmod +x *.sh`. Everything runs as root; secrets are read from the app env files.
3. Registry login for the agent (separate from the TrueNAS UI credential):
   `DOCKER_CONFIG=<STATE_DIR>/docker docker login ghcr.io -u <github-user>` using a PAT with `read:packages`.
4. Copy `agent.conf.example` to `conf/<app>-<env>.conf` and edit.
5. Prove it first: `./deploy-agent.sh --dry-run conf/jigsaurium-test.conf`
   It does not touch the app, but it does `docker pull` the watched tag (moving the local `:test`).
   Check: the payload equals `midclt call app.config <app>` with only `image` changed, and the
   `running container` line shows an image ID and `healthy` (not `<none found>`).
6. Run once for real: `./deploy-agent.sh conf/jigsaurium-test.conf`
7. Schedule: TrueNAS UI > System > Advanced > Cron Jobs, user `root`, every 5 minutes:
   `/mnt/<pool>/apps/deploy-agent/deploy-agent.sh /mnt/<pool>/apps/deploy-agent/conf/*.conf >> /mnt/<pool>/apps/deploy-agent/agent.log 2>&1`

## Behaviour notes
- `--force` re-applies/retries (including a digest that previously failed); `--dry-run` never changes anything.
- A digest that failed health is remembered and not retried until the pointer moves to a new digest.
- Rollback always targets the digest of the image the container was running before the deploy
  (read from the container itself), never the mutable tag, including on the very first run.
- `app.update` is called with `midclt call -j`, so the agent waits for the TrueNAS job and sees failures.
- Healthy means: the service container (compose labels `ix-<APP_NAME>` / `SERVICE`) runs the new
  image ID, its Docker healthcheck is `healthy` (or none is defined), and `HEALTH_URL` returns 2xx.
  If `HEALTH_SHA_FIELD` is set, that field in the health JSON must also match the image's
  `org.opencontainers.image.revision` label. Jigsaurium leaves it empty: its public health
  endpoint intentionally returns only `status`.
- If `BACKUP_CMD` fails, the deploy is aborted and the running version is left untouched.
- Restore a dump: `gunzip -c <file>.sql.gz | docker run -i --rm -e MYSQL_PWD mariadb:11 mariadb -h HOST -u USER DB`.

## Status
Logic exercised against stand-ins for `midclt`/`docker`/`curl` (success, up-to-date, unhealthy+rollback,
skip-failed). **Not yet run on a real TrueNAS** - do step 5 and 6 on `jigsaurium-test` first.
