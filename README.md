# Schrankerl Refill Planner

Minimal Odoo add-on for an explainable fridge refill planner.

The project is based on public Schrankerl/FrescoFrigo context: purchase history exists, refill operations exist, but no public developer API contract is visible. So the demo uses a seeded mock source adapter and keeps the integration boundary explicit.

## What It Shows

- Odoo-native domain model for fridges, sales events, inventory snapshots, and refill plans.
- A mock source sync that generates sales and stock snapshots from seeded synthetic data.
- A scheduled Odoo cron that can run the sync and refill planning flow.
- A small forecasting core: rolling demand, weekday effect, safety stock.
- Refill recommendations with capacity and near-expiry stock handling.
- A small pure-Python planning core covered by unit tests.

## Run Tests

Install dev tooling once:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

```bash
.venv/bin/python -m unittest discover -s tests
```

Run pre-commit checks:

```bash
.venv/bin/pre-commit run --all-files
```

Use that command from a standalone project checkout, not from a parent git repo.

## Odoo Add-on

Install `addons/schrankerl_refill_planner` in an Odoo 16+ environment with `base`, `product`, and `stock`.

The menu appears as `Schrankerl > Refill Planning`.

## Docker Demo

```bash
docker compose up
```

Open `http://localhost:8069/web?db=schrankerl_demo`.

Default Odoo demo login is usually `admin` / `admin`.

First run installs the module, loads master data, runs mock sync, and generates 70 sales events, 10 inventory snapshots, and 10 refill lines.

Each manual mock sync uses a new seed, so the demo recommendations visibly change without accumulating fake source rows.

Useful menus:

- `Schrankerl > Refill Planning`
- `Schrankerl > Run Mock Sync Now`
- `Schrankerl > Sync Runs`
- `Schrankerl > Reports > Refill Lines`

To reset the demo:

```bash
docker compose down -v
```

## Render Demo

Render runs Docker services from a `Dockerfile`, not from `docker-compose.yml`. This repo includes `render.yaml` for a free web service plus a free Render Postgres database.

Deploy from the Render dashboard:

1. Create a new Blueprint from the GitHub repo.
2. When Render asks for `ODOO_DEMO_PASSWORD`, enter the password you want for the public demo.
3. Open the deployed service URL and go to `/web/login`.

Login:

- user: `admin`
- password: the `ODOO_DEMO_PASSWORD` value you entered in Render

The startup script installs the add-on, sets the demo password, runs mock sync, and starts Odoo.

Render free limits are enough for a short interview demo, but expect slow cold starts. The free Postgres database has a 30-day limit. If the demo feels too slow, upgrade only the web service from `free` to `starter`.

## Intentional Limits

- No real FrescoFrigo API integration is claimed.
- No ML model; the baseline is explainable and easier to validate with operations.
- No route optimization or stock picking generation in the MVP.

Those are add-ons after Schrankerl confirms the current source of truth for sales, inventory, expiry, and refiller workflow data.
