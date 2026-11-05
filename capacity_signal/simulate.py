"""Slip-propagation simulation.

Given a provider and a slip of N days, shift that provider's forecast
delivery, planned RFS and planned in-service dates by N days (in the
report only - the DB is never mutated) and compute:

- per affected cluster: old vs new RFS / in-service dates;
- allocation gap: an allocation is 'missed' when its need_by_date is
  earlier than the cluster's NEW in-service date. Gap GPUs = sum of
  allocated_qty over missed allocations. (Allocations whose need_by was
  already before the OLD in-service date are pre-existing misses and are
  reported separately, not counted as slip-caused gap.)

Fixed hand-checkable scenario (also asserted in tests/test_core.py):
provider HELIX, slip 14 days.
  CL-04 in-service 2027-03-01 -> 2027-03-15.
    Training-C 300 GPUs need 2027-03-10 (< 03-15) -> missed.
    Inference-C 212 GPUs need 2027-03-20 (>= 03-15) -> still covered.
  CL-05 in-service 2027-04-15 -> 2027-04-29.
    Training-D 256 GPUs need 2027-04-20 (< 04-29) -> missed.
  Expected: affected clusters 2, slip-caused gap 300 + 256 = 556 GPUs.
"""
from datetime import date, timedelta


def _shift(iso, days):
    return (date.fromisoformat(iso) + timedelta(days=days)).isoformat()


def simulate_slip(conn, provider_code, slip_days):
    prov = conn.execute("SELECT * FROM provider WHERE code = ?",
                        (provider_code,)).fetchone()
    if prov is None:
        raise ValueError(f"unknown provider: {provider_code}")
    clusters = []
    total_gap = 0
    for c in conn.execute(
            "SELECT cl.* FROM cluster cl JOIN site s ON s.site_id = cl.site_id"
            " WHERE s.provider_id = ? ORDER BY cl.code", (prov["provider_id"],)):
        new_rfs = _shift(c["planned_rfs_date"], slip_days)
        new_in = _shift(c["planned_inservice_date"], slip_days)
        missed, preexisting = [], []
        for a in conn.execute(
                "SELECT * FROM allocation WHERE cluster_id = ?"
                " ORDER BY priority", (c["cluster_id"],)):
            if a["need_by_date"] < c["planned_inservice_date"]:
                preexisting.append(dict(a))
            elif a["need_by_date"] < new_in:
                missed.append(dict(a))
        gap = sum(a["allocated_qty"] for a in missed)
        total_gap += gap
        clusters.append({
            "cluster": c["code"], "gpu_count": c["gpu_count"],
            "old_rfs": c["planned_rfs_date"], "new_rfs": new_rfs,
            "old_inservice": c["planned_inservice_date"],
            "new_inservice": new_in,
            "missed_allocations": missed,
            "preexisting_missed": preexisting,
            "gap_gpus": gap,
        })
    return {"provider": prov["name"], "provider_code": provider_code,
            "slip_days": slip_days, "clusters": clusters,
            "affected_clusters": sum(1 for c in clusters if c["gap_gpus"] > 0),
            "total_gap_gpus": total_gap}


def slip_markdown(result):
    lines = [f"# Slip Simulation: {result['provider']} +{result['slip_days']} days",
             "",
             "> SYNTHETIC / SIMULATED DATA. Simulation only; the database "
             "is not modified.", ""]
    for c in result["clusters"]:
        lines.append(
            f"- {c['cluster']} ({c['gpu_count']} GPUs): RFS "
            f"{c['old_rfs']} -> {c['new_rfs']}; in-service "
            f"{c['old_inservice']} -> {c['new_inservice']}; "
            f"slip-caused allocation gap {c['gap_gpus']} GPUs")
        for a in c["missed_allocations"]:
            lines.append(
                f"  - missed: {a['team']} {a['allocated_qty']} GPUs, "
                f"need by {a['need_by_date']} < new in-service "
                f"{c['new_inservice']}")
    lines.append("")
    lines.append(f"Affected clusters: {result['affected_clusters']}; "
                 f"total slip-caused allocation gap: "
                 f"{result['total_gap_gpus']} GPUs.")
    lines.append("")
    return "\n".join(lines)


def main():
    import argparse
    from pathlib import Path
    from .db import connect
    ap = argparse.ArgumentParser(description="Simulate a provider slip")
    ap.add_argument("--db", default="data/supply.db")
    ap.add_argument("--provider", required=True)
    ap.add_argument("--days", type=int, required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    conn = connect(args.db)
    text = slip_markdown(simulate_slip(conn, args.provider, args.days))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    print(text)
    conn.close()


if __name__ == "__main__":
    main()
