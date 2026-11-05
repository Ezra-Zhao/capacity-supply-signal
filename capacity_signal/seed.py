"""Synthetic seed data + DB builder.

SYNTHETIC / SIMULATED DATA: provider names, sites, clusters, dates and
quantities below are invented for method demonstration. They do not
describe any real provider, site, cluster, or project.

Fleet shape (exact): 3 providers, 5 sites, 8 clusters, 2048 GPUs total.
  NOVA  (NovaCloud Compute): CL-01 512 + CL-02 256 + CL-03 128 = 896
  HELIX (Helix Compute):     CL-04 512 + CL-05 256             = 768
  ATLAS (Atlas Cloud):       CL-06 256 + CL-07 64 + CL-08 64   = 384
  Total                                                        = 2048

Dates are a synthetic calendar (2026-2027), chosen for arithmetic
convenience, not copied from any real schedule.
"""
import csv
import json
from datetime import date, timedelta
from pathlib import Path

from .db import init_db

PROVIDERS = [
    {"code": "NOVA", "name": "NovaCloud Compute"},
    {"code": "HELIX", "name": "Helix Compute"},
    {"code": "ATLAS", "name": "Atlas Cloud"},
]

SITES = [
    {"code": "PHX-1", "provider": "NOVA", "name": "Phoenix 1", "region": "us-phoenix"},
    {"code": "DAL-1", "provider": "NOVA", "name": "Dallas 1", "region": "us-dallas"},
    {"code": "ORD-1", "provider": "HELIX", "name": "Chicago 1", "region": "us-chicago"},
    {"code": "SEA-1", "provider": "HELIX", "name": "Seattle 1", "region": "us-seattle"},
    {"code": "IAD-1", "provider": "ATLAS", "name": "Ashburn 1", "region": "us-ashburn"},
]

# deltas: actual minus planned, in days, for each completed milestone in
# milestone order (delivered, racked, provisioned, accepted,
# ready_for_service, in_service). Length = number of completed milestones,
# which is fixed by hardware_state (see MILESTONE_ORDER / STATE_DEPTH).
CLUSTERS = [
    {"code": "CL-01", "site": "PHX-1", "name": "Nova Phoenix A", "gpu_model": "H200",
     "gpu_count": 512, "state": "in_service", "rfs": "2026-09-01",
     "deltas": [2, 1, 0, -1, 0, 3],
     "actual_qty": 512},
    {"code": "CL-02", "site": "PHX-1", "name": "Nova Phoenix B", "gpu_model": "H200",
     "gpu_count": 256, "state": "in_service", "rfs": "2026-10-01",
     "deltas": [0, 2, 1, 0, 2, 2],
     "actual_qty": 248},
    {"code": "CL-03", "site": "DAL-1", "name": "Nova Dallas A", "gpu_model": "B200",
     "gpu_count": 128, "state": "accepted", "rfs": "2026-12-01",
     "deltas": [1, 0, -2, 4],
     "actual_qty": 128},
    {"code": "CL-04", "site": "ORD-1", "name": "Helix Chicago A", "gpu_model": "H200",
     "gpu_count": 512, "state": "provisioned", "rfs": "2027-02-15",
     "deltas": [-3, 0, 5],
     "actual_qty": 512},
    {"code": "CL-05", "site": "SEA-1", "name": "Helix Seattle A", "gpu_model": "B200",
     "gpu_count": 256, "state": "racked", "rfs": "2027-04-01",
     "deltas": [6, 1],
     "actual_qty": 256},
    {"code": "CL-06", "site": "IAD-1", "name": "Atlas Ashburn A", "gpu_model": "H200",
     "gpu_count": 256, "state": "delivered", "rfs": "2027-01-15",
     "deltas": [2],
     "actual_qty": 256},
    {"code": "CL-07", "site": "IAD-1", "name": "Atlas Ashburn B", "gpu_model": "H100",
     "gpu_count": 64, "state": "shipped", "rfs": "2027-05-01",
     "deltas": [],
     "actual_qty": None},
    {"code": "CL-08", "site": "IAD-1", "name": "Atlas Ashburn C", "gpu_model": "H100",
     "gpu_count": 64, "state": "ordered", "rfs": "2027-06-01",
     "deltas": [],
     "actual_qty": None},
]

MILESTONE_ORDER = ["delivered", "racked", "provisioned", "accepted",
                   "ready_for_service", "in_service"]
# Planned milestone offsets in days relative to planned RFS date.
MILESTONE_OFFSETS = {"delivered": -45, "racked": -30, "provisioned": -20,
                     "accepted": -10, "ready_for_service": 0, "in_service": 14}
# How many leading milestones are complete for each hardware state.
STATE_DEPTH = {"ordered": 0, "shipped": 0, "delivered": 1, "racked": 2,
               "provisioned": 3, "accepted": 4, "in_service": 6}

# Forecast revisions per cluster beyond the baseline (revision 1 = the
# commitment itself). Each entry: (forecast_delivery_date, forecast_qty,
# recorded_at, note). changed_fields is computed against the previous
# revision at insert time.
EXTRA_REVISIONS = {
    "CL-01": [("2026-07-23", 512, "2026-06-20", "carrier slot moved +5d")],
    "CL-02": [("2026-08-17", 248, "2026-07-02", "partial yield: qty 256 -> 248"),
              ("2026-08-20", 248, "2026-07-28", "freight consolidation +3d")],
    "CL-04": [("2027-01-06", 512, "2026-11-15", "factory output slipped +5d"),
              ("2026-12-29", 512, "2026-12-10", "expedite approved: pulled back in")],
    "CL-05": [("2027-02-21", 256, "2027-01-19", "rack integration queue +6d")],
}

ALLOCATIONS = [
    ("CL-01", "Training-A", 300, 1, "2026-09-20"),
    ("CL-01", "Inference-A", 212, 2, "2026-09-25"),
    ("CL-02", "Training-B", 256, 1, "2026-10-20"),
    ("CL-03", "Inference-B", 128, 1, "2026-12-20"),
    ("CL-04", "Training-C", 300, 1, "2027-03-10"),
    ("CL-04", "Inference-C", 212, 2, "2027-03-20"),
    ("CL-05", "Training-D", 256, 1, "2027-04-20"),
    ("CL-06", "Inference-D", 200, 1, "2027-02-05"),
    ("CL-06", "Training-E", 56, 2, "2027-02-10"),
    ("CL-07", "Inference-E", 64, 1, "2027-05-20"),
    ("CL-08", "Training-F", 64, 1, "2027-06-20"),
]

TOTAL_GPUS = sum(c["gpu_count"] for c in CLUSTERS)  # 2048


def _d(iso):
    return date.fromisoformat(iso)


def planned_milestones(cluster):
    rfs = _d(cluster["rfs"])
    return {m: (rfs + timedelta(days=MILESTONE_OFFSETS[m])).isoformat()
            for m in MILESTONE_ORDER}


def build_db(db_path):
    """Create a fresh DB at db_path and load the synthetic seed. Returns conn."""
    p = Path(db_path)
    if p.exists():
        p.unlink()
    conn = init_db(db_path)
    prov_id, site_id, clus_id = {}, {}, {}
    for i, pr in enumerate(PROVIDERS, 1):
        conn.execute("INSERT INTO provider VALUES (?,?,?)", (i, pr["code"], pr["name"]))
        prov_id[pr["code"]] = i
    for i, s in enumerate(SITES, 1):
        conn.execute("INSERT INTO site VALUES (?,?,?,?,?)",
                     (i, prov_id[s["provider"]], s["code"], s["name"], s["region"]))
        site_id[s["code"]] = i
    site_provider = {s["code"]: s["provider"] for s in SITES}
    for i, c in enumerate(CLUSTERS, 1):
        planned = planned_milestones(c)
        conn.execute(
            "INSERT INTO cluster VALUES (?,?,?,?,?,?,?,?,?)",
            (i, site_id[c["site"]], c["code"], c["name"], c["gpu_model"],
             c["gpu_count"], c["state"], c["rfs"], planned["in_service"]))
        clus_id[c["code"]] = i
        delivered_actual = None
        if c["deltas"]:
            delivered_actual = (_d(planned["delivered"])
                                + timedelta(days=c["deltas"][0])).isoformat()
        conn.execute(
            "INSERT INTO delivery_commitment (commitment_id, provider_id,"
            " cluster_id, committed_qty, committed_delivery_date, actual_qty,"
            " actual_delivery_date) VALUES (?,?,?,?,?,?,?)",
            (i, prov_id[site_provider[c["site"]]], i, c["gpu_count"],
             planned["delivered"], c["actual_qty"], delivered_actual))
        # Revision 1 = baseline forecast (equals the commitment).
        conn.execute(
            "INSERT INTO forecast_revision (commitment_id, revision_no,"
            " forecast_delivery_date, forecast_qty, recorded_at, changed_fields,"
            " note) VALUES (?,?,?,?,'2026-06-01','baseline','initial commitment')",
            (i, 1, planned["delivered"], c["gpu_count"]))
        prev_date, prev_qty = planned["delivered"], c["gpu_count"]
        for j, (fdate, fqty, rec, note) in enumerate(
                EXTRA_REVISIONS.get(c["code"], []), start=2):
            changed = []
            if fdate != prev_date:
                changed.append("forecast_delivery_date")
            if fqty != prev_qty:
                changed.append("forecast_qty")
            conn.execute(
                "INSERT INTO forecast_revision (commitment_id, revision_no,"
                " forecast_delivery_date, forecast_qty, recorded_at,"
                " changed_fields, note) VALUES (?,?,?,?,?,?,?)",
                (i, j, fdate, fqty, rec, ",".join(changed), note))
            prev_date, prev_qty = fdate, fqty
        depth = STATE_DEPTH[c["state"]]
        for k, m in enumerate(MILESTONE_ORDER):
            actual = None
            status = "planned"
            evidence = ""
            if k < depth:
                actual = (_d(planned[m]) + timedelta(days=c["deltas"][k])).isoformat()
                status = "done"
                evidence = f"synthetic evidence pack for {c['code']} {m}"
            conn.execute(
                "INSERT INTO readiness_milestone (cluster_id, milestone_type,"
                " planned_date, actual_date, status, evidence)"
                " VALUES (?,?,?,?,?,?)",
                (i, m, planned[m], actual, status, evidence))
    for j, (ccode, team, qty, prio, need) in enumerate(ALLOCATIONS, 1):
        conn.execute(
            "INSERT INTO allocation VALUES (?,?,?,?,?,?, 'reserved')",
            (j, clus_id[ccode], team, qty, prio, need))
    conn.commit()
    return conn


def write_seed_files(out_dir):
    """Export the seed as CSV/JSON files (the import layer's input format)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "commitments.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["provider_code", "cluster_code", "committed_qty",
                    "committed_delivery_date", "forecast_delivery_date",
                    "forecast_qty"])
        site_provider = {s["code"]: s["provider"] for s in SITES}
        for c in CLUSTERS:
            planned = planned_milestones(c)
            w.writerow([site_provider[c["site"]], c["code"], c["gpu_count"],
                        planned["delivered"], planned["delivered"], c["gpu_count"]])
    revisions = []
    for c in CLUSTERS:
        for j, (fdate, fqty, rec, note) in enumerate(
                EXTRA_REVISIONS.get(c["code"], []), start=2):
            revisions.append({"cluster_code": c["code"], "revision_no": j,
                              "forecast_delivery_date": fdate,
                              "forecast_qty": fqty, "recorded_at": rec,
                              "note": note})
    (out / "forecast_revisions.json").write_text(
        json.dumps(revisions, indent=2), encoding="utf-8")
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Build synthetic seed DB")
    ap.add_argument("--db", default="data/supply.db")
    ap.add_argument("--seed-out", default="data/seed")
    args = ap.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    conn = build_db(args.db)
    write_seed_files(args.seed_out)
    n = conn.execute("SELECT SUM(gpu_count) FROM cluster").fetchone()[0]
    print(f"seeded {args.db}: 3 providers, 5 sites, 8 clusters, {n} GPUs "
          f"(SYNTHETIC DATA)")
    conn.close()


if __name__ == "__main__":
    main()
