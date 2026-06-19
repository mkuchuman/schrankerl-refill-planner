#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${ODOO_DEMO_PASSWORD:?Set ODOO_DEMO_PASSWORD in Render environment variables}"

eval "$(
  python3 - <<'PY'
import os
import shlex
from urllib.parse import unquote, urlparse

url = urlparse(os.environ["DATABASE_URL"])
values = {
    "DB_HOST": url.hostname or "",
    "DB_PORT": str(url.port or 5432),
    "DB_USER": unquote(url.username or ""),
    "DB_PASSWORD": unquote(url.password or ""),
    "DB_NAME": os.environ.get("ODOO_DATABASE") or unquote((url.path or "/").lstrip("/")),
    "ODOO_MASTER_PASSWORD": os.environ.get("ODOO_MASTER_PASSWORD", "odoo"),
}

for key, value in values.items():
    print(f"export {key}={shlex.quote(value)}")
PY
)"

python3 - <<'PY'
import os
import socket
import time

host = os.environ["DB_HOST"]
port = int(os.environ["DB_PORT"])

for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            raise SystemExit(0)
    except OSError:
        time.sleep(2)

raise SystemExit(f"Postgres is not reachable at {host}:{port}")
PY

addons_path="/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons"
odoo_args=(
  --db_host="$DB_HOST"
  --db_port="$DB_PORT"
  --db_user="$DB_USER"
  --db_password="$DB_PASSWORD"
  --admin-passwd="$ODOO_MASTER_PASSWORD"
  --addons-path="$addons_path"
)

odoo -d "$DB_NAME" -i schrankerl_refill_planner -u schrankerl_refill_planner --stop-after-init "${odoo_args[@]}"

cat <<'PY' | odoo shell -d "$DB_NAME" "${odoo_args[@]}"
import os

env.ref("base.user_admin").write(
    {
        "login": os.environ.get("ODOO_DEMO_LOGIN", "admin"),
        "password": os.environ["ODOO_DEMO_PASSWORD"],
    }
)
env["sch.integration.run"].run_mock_sync()
env.cr.commit()
PY

exec odoo \
  -d "$DB_NAME" \
  --db-filter="^${DB_NAME}$" \
  --http-port="${PORT:-8069}" \
  --proxy-mode \
  --no-database-list \
  "${odoo_args[@]}"
