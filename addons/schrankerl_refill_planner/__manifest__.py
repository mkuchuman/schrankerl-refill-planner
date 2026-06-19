{
    "name": "Schrankerl Refill Planner",
    "summary": "Explainable fridge demand forecast and refill planning demo",
    "version": "16.0.1.0.0",
    "category": "Inventory",
    "author": "Demo project",
    "license": "LGPL-3",
    "depends": ["base", "product", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/fridge_views.xml",
        "views/sale_event_views.xml",
        "views/inventory_snapshot_views.xml",
        "views/integration_run_views.xml",
        "views/refill_plan_views.xml",
        "views/menu.xml",
        "data/cron.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
    "installable": True,
    "application": True,
}
