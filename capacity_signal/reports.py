"""Supply-signal overview and delivery scorecard generation.

Both reports are generated from the SQLite DB by a single command and
every number is recomputable from the DB. Metric definitions live in
docs/definitions.md; the short version:

- committed_qty / actual_qty: from delivery_commitment.
- latest forecast: highest forecast_revision per commitment.
- forecast_changes: revisions beyond the baseline (count - 1 per
  commitment).
- milestone attainment: completed milestones with actual_date <=
  planned_date, divided by all completed milestones.
- time to usable capacity (TTUC): actual in_service milestone date
  minus actual delivered milestone date, in days, per cluster that has
  reached in_service. Distribution reported as n / median / p90 / max.
"""
import math
import statistics
from datetime import date

HEADER = ("> SYNTHETIC / SIMULATED DATA - invented providers, sites, "
          "clusters and dates. Not a record of any real project.\n")


def _milestone(conn, cluster_id, mtype):
    return conn.execute(
        "SELECT planned_date, actual_date FROM readiness_milestone"
        " WHERE cluster_id = ? AND milestone_type = ?",
        (cluster_id, mtype)).fetchone()


def _latest_forecast(conn, commitment_id):
    return conn.execute(
        "SELECT forecast_delivery_date, forecast_qty FROM forecast_revision"
        " WHERE commitment_id = ? ORDER BY revision_no DESC LIMIT 1",
        (commitment_id,)).fetchone()


def ttuc_values(conn, provider_code=None):
    """TTUC in days for every in-service cluster (optionally per provider)."""
    q = ("SELECT c.cluster_id FROM cluster c JOIN site s ON s.site_id = c.site_id"
         " JOIN provider p ON p.provider_id = s.provider_id"
         " WHERE c.hardware_state = 'in_service'")
    params = []
    if provider_code:
        q += " AND p.code = ?"
        params.append(provider_code)
    values = []
    for row in conn.execute(q, params):
        d = _milestone(conn, row["cluster_id"], "delivered")
        s = _milestone(conn, row["cluster_id"], "in_service")
        if d and s and d["actual_date"] and s["actual_date"]:
            values.append((date.fromisoformat(s["actual_date"])
                           - date.fromisoformat(d["actual_date"])).days)
    return sorted(values)


def ttuc_stats(values):
    if not values:
        return {"n": 0, "median": None, "p90": None, "max": None}
    p90 = values[max(0, math.ceil(0.9 * len(values)) - 1)]
    return {"n": len(values), "median": statistics.median(values),
            "p90": p90, "max": max(values)}


def milestone_attainment(conn, provider_code=None):
    """(on_time, completed) milestone counts, optionally per provider."""
    q = ("SELECT rm.actual_date, rm.planned_date FROM readiness_milestone rm"
         " JOIN cluster c ON c.cluster_id = rm.cluster_id"
         " JOIN site s ON s.site_id = c.site_id"
         " JOIN provider p ON p.provider_id = s.provider_id"
         " WHERE rm.actual_date IS NOT NULL")
    params = []
    if provider_code:
        q += " AND p.code = ?"
        params.append(provider_code)
    rows = conn.execute(q, params).fetchall()
    on_time = sum(1 for r in rows if r["actual_date"] <= r["planned_date"])
    return on_time, len(rows)


def overview_markdown(conn):
    lines = ["# Supply Signal Overview (one-screen roll-up)", "", HEADER]
    total = conn.execute("SELECT SUM(gpu_count) FROM cluster").fetchone()[0]
    lines.append(f"Fleet: 3 providers / 5 sites / 8 clusters / {total} GPUs "
                 f"(synthetic).")
    lines.append("")
    lines.append("| Provider | Site | Cluster | GPUs | Model | State | "
                 "Forecast delivery (latest) | Actual delivery | Accepted | "
                 "RFS (planned) | In-service (planned) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    rows = conn.execute(
        "SELECT p.name AS provider, s.code AS site, c.code AS cluster,"
        " c.cluster_id, c.gpu_count, c.gpu_model, c.hardware_state,"
        " c.planned_rfs_date, c.planned_inservice_date, dc.commitment_id,"
        " dc.actual_delivery_date FROM cluster c"
        " JOIN site s ON s.site_id = c.site_id"
        " JOIN provider p ON p.provider_id = s.provider_id"
        " JOIN delivery_commitment dc ON dc.cluster_id = c.cluster_id"
        " ORDER BY p.code, s.code, c.code").fetchall()
    for r in rows:
        fc = _latest_forecast(conn, r["commitment_id"])
        acc = _milestone(conn, r["cluster_id"], "accepted")
        lines.append(
            f"| {r['provider']} | {r['site']} | {r['cluster']} | "
            f"{r['gpu_count']} | {r['gpu_model']} | {r['hardware_state']} | "
            f"{fc['forecast_delivery_date']} ({fc['forecast_qty']} GPUs) | "
            f"{r['actual_delivery_date'] or '-'} | "
            f"{(acc['actual_date'] if acc else None) or '-'} | "
            f"{r['planned_rfs_date']} | {r['planned_inservice_date']} |")
    lines.append("")
    lines.append("Allocations (reserved):")
    lines.append("")
    lines.append("| Cluster | Team | GPUs | Priority | Need by |")
    lines.append("|---|---|---|---|---|")
    for r in conn.execute(
            "SELECT c.code AS cluster, a.team, a.allocated_qty, a.priority,"
            " a.need_by_date FROM allocation a"
            " JOIN cluster c ON c.cluster_id = a.cluster_id"
            " ORDER BY c.code, a.priority"):
        lines.append(f"| {r['cluster']} | {r['team']} | {r['allocated_qty']} "
                     f"| {r['priority']} | {r['need_by_date']} |")
    lines.append("")
    return "\n".join(lines)


def scorecard_rows(conn):
    """One dict per provider with all scorecard metrics (testable)."""
    out = []
    for p in conn.execute("SELECT * FROM provider ORDER BY code"):
        code = p["code"]
        agg = conn.execute(
            "SELECT SUM(committed_qty) AS committed,"
            " COALESCE(SUM(actual_qty),0) AS actual FROM delivery_commitment"
            " WHERE provider_id = ?", (p["provider_id"],)).fetchone()
        changes = conn.execute(
            "SELECT COUNT(*) - COUNT(DISTINCT fr.commitment_id) FROM"
            " forecast_revision fr JOIN delivery_commitment dc"
            " ON dc.commitment_id = fr.commitment_id"
            " WHERE dc.provider_id = ?", (p["provider_id"],)).fetchone()[0]
        on_time, completed = milestone_attainment(conn, code)
        out.append({
            "provider": p["name"], "code": code,
            "committed_qty": agg["committed"], "actual_qty": agg["actual"],
            "qty_attainment_pct": round(100.0 * agg["actual"] / agg["committed"], 1),
            "forecast_changes": changes,
            "milestones_on_time": on_time, "milestones_completed": completed,
            "milestone_attainment_pct": (
                round(100.0 * on_time / completed, 1) if completed else None),
            "ttuc": ttuc_stats(ttuc_values(conn, code)),
        })
    return out


def scorecard_markdown(conn):
    lines = ["# Delivery Scorecard by Provider", "", HEADER,
             "Definitions: docs/definitions.md. All figures recomputed "
             "from the DB at generation time.", "",
             "| Provider | Committed GPUs | Actual GPUs | Qty attainment | "
             "Forecast changes | Milestones on-time / completed | "
             "Milestone attainment | TTUC n | TTUC median (d) | TTUC p90 (d) "
             "| TTUC max (d) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in scorecard_rows(conn):
        t = r["ttuc"]
        lines.append(
            f"| {r['provider']} | {r['committed_qty']} | {r['actual_qty']} | "
            f"{r['qty_attainment_pct']}% | {r['forecast_changes']} | "
            f"{r['milestones_on_time']} / {r['milestones_completed']} | "
            f"{r['milestone_attainment_pct']}% | {t['n']} | "
            f"{t['median'] if t['median'] is not None else '-'} | "
            f"{t['p90'] if t['p90'] is not None else '-'} | "
            f"{t['max'] if t['max'] is not None else '-'} |")
    on_time, completed = milestone_attainment(conn)
    g = ttuc_stats(ttuc_values(conn))
    lines.append("")
    lines.append(f"Fleet totals: milestones on-time {on_time} / {completed} "
                 f"({round(100.0 * on_time / completed, 1)}%); TTUC across "
                 f"in-service clusters: n={g['n']}, median={g['median']}d, "
                 f"p90={g['p90']}d, max={g['max']}d.")
    lines.append("")
    return "\n".join(lines)


def main():
    import argparse
    from pathlib import Path
    from .db import connect
    ap = argparse.ArgumentParser(description="Generate reports")
    ap.add_argument("report", choices=["overview", "scorecard"])
    ap.add_argument("--db", default="data/supply.db")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    conn = connect(args.db)
    text = (overview_markdown(conn) if args.report == "overview"
            else scorecard_markdown(conn))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    conn.close()


if __name__ == "__main__":
    main()
