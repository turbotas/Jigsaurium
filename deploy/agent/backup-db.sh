#!/usr/bin/env bash
# backup-db.sh - generic pre-deploy dump of the app database, using DATABASE_URL from the app's env file.
# Usage: backup-db.sh <env_file> <backup_dir> [keep=14]
# Supports MariaDB/MySQL URLs like mysql+pymysql://user:pass@host:3306/dbname
# Dumps via a throwaway container so the NAS host needs no DB client. Password is never put on argv.
set -euo pipefail
ENV_FILE="${1:?env file}"; DEST="${2:?backup dir}"; KEEP="${3:-14}"
DUMP_IMAGE="${DUMP_IMAGE:-mariadb:11}"

eval "$(python3 - "$ENV_FILE" <<'PY'
import sys, shlex
from urllib.parse import urlsplit, unquote
url = ""
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if line.startswith("DATABASE_URL="):
        url = line.split("=", 1)[1].strip().strip('"').strip("'")
if not url:
    sys.exit("DATABASE_URL not found in env file")
u = urlsplit(url)
if not u.scheme.startswith(("mysql", "mariadb")):
    sys.exit("unsupported DATABASE_URL scheme: " + u.scheme)
for k, v in (("DB_HOST", u.hostname), ("DB_PORT", u.port or 3306), ("DB_USER", unquote(u.username or "")),
             ("DB_PASS", unquote(u.password or "")), ("DB_NAME", u.path.lstrip("/"))):
    print(f"{k}={shlex.quote(str(v))}")
PY
)"

umask 077; mkdir -p "$DEST"
OUT="$DEST/${DB_NAME}-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
export MYSQL_PWD="$DB_PASS"
echo "Dumping $DB_NAME from $DB_HOST:$DB_PORT -> $OUT"
docker run --rm -e MYSQL_PWD "$DUMP_IMAGE" mariadb-dump --single-transaction --routines --triggers \
  -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" | gzip > "$OUT"
gzip -t "$OUT"
[ "$(stat -c %s "$OUT")" -gt 200 ] || { echo "backup suspiciously small"; rm -f "$OUT"; exit 1; }
ls -1t "$DEST/${DB_NAME}-"*.sql.gz 2>/dev/null | tail -n +"$((KEEP+1))" | xargs -r rm -f --
echo "Backup OK: $OUT"
