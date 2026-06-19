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
  --addons-path="$addons_path"
)

odoo -d "$DB_NAME" -i schrankerl_refill_planner -u schrankerl_refill_planner --stop-after-init "${odoo_args[@]}"

cat <<'PY' | odoo shell -d "$DB_NAME" "${odoo_args[@]}"
import os

from odoo import fields

config = env["ir.config_parameter"].sudo()
config.set_param("ir_attachment.location", "db")
Attachment = env["ir.attachment"].sudo()
Attachment.regenerate_assets_bundles()

env.cr.execute("SELECT id, store_fname FROM ir_attachment WHERE store_fname IS NOT NULL")
stale_attachment_ids = [
    attachment_id
    for attachment_id, store_fname in env.cr.fetchall()
    if store_fname and not os.path.exists(Attachment._full_path(store_fname))
]
if stale_attachment_ids:
    Attachment.browse(stale_attachment_ids).unlink()
Attachment.clear_caches()
env["ir.qweb"].clear_caches()
print(f"Render startup removed {len(stale_attachment_ids)} stale filestore attachments.")

env.ref("base.user_admin").write(
    {
        "login": os.environ.get("ODOO_DEMO_LOGIN", "admin"),
        "password": os.environ["ODOO_DEMO_PASSWORD"],
    }
)
env["sch.integration.run"].run_mock_sync()
cron = env.ref("schrankerl_refill_planner.ir_cron_sch_mock_sync", raise_if_not_found=False)
if cron:
    cron.nextcall = fields.Datetime.add(fields.Datetime.now(), days=1)
env.cr.commit()
PY

exec odoo \
  -d "$DB_NAME" \
  --db-filter="^${DB_NAME}$" \
  --http-port="${PORT:-8069}" \
  --proxy-mode \
  --no-database-list \
  --max-cron-threads=1 \
  "${odoo_args[@]}"
