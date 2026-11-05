"""Import layer: supplier commitments and forecast changes (CSV / JSON).

Versioning rule: a delivery_commitment is created once. Every later
forecast that differs from the latest forecast_revision appends a new
revision (revision_no = max + 1) recording exactly which fields changed
(forecast_delivery_date and/or forecast_qty). Re-importing an identical
forecast is a no-op reported as 'unchanged', so imports are idempotent
and the full change history of any commitment stays queryable.
"""
import csv
import json
from pathlib import Path


def _commitment_id(conn, cluster_code):
    row = conn.execute(
        "SELECT dc.commitment_id FROM delivery_commitment dc"
        " JOIN cluster c ON c.cluster_id = dc.cluster_id WHERE c.code = ?",
        (cluster_code,)).fetchone()
    return row["commitment_id"] if row else None


def _latest_revision(conn, commitment_id):
    return conn.execute(
        "SELECT * FROM forecast_revision WHERE commitment_id = ?"
        " ORDER BY revision_no DESC LIMIT 1", (commitment_id,)).fetchone()


def apply_forecast(conn, cluster_code, forecast_delivery_date, forecast_qty,
                   recorded_at, note=""):
    """Apply one forecast observation. Returns 'revised' or 'unchanged'."""
    cid = _commitment_id(conn, cluster_code)
    if cid is None:
        raise ValueError(f"no commitment for cluster: {cluster_code}")
    latest = _latest_revision(conn, cid)
    if (latest["forecast_delivery_date"] == forecast_delivery_date
            and latest["forecast_qty"] == int(forecast_qty)):
        return "unchanged"
    changed = []
    if latest["forecast_delivery_date"] != forecast_delivery_date:
        changed.append("forecast_delivery_date")
    if latest["forecast_qty"] != int(forecast_qty):
        changed.append("forecast_qty")
    conn.execute(
        "INSERT INTO forecast_revision (commitment_id, revision_no,"
        " forecast_delivery_date, forecast_qty, recorded_at, changed_fields,"
        " note) VALUES (?,?,?,?,?,?,?)",
        (cid, latest["revision_no"] + 1, forecast_delivery_date,
         int(forecast_qty), recorded_at, ",".join(changed), note))
    conn.commit()
    return "revised"


def import_commitments_csv(conn, path):
    """Create commitments from CSV (baseline revision 1 each).

    Columns: provider_code, cluster_code, committed_qty,
    committed_delivery_date, forecast_delivery_date, forecast_qty.
    Clusters and providers must already exist (seed creates them).
    Returns {'created': n, 'skipped_existing': n}.
    """
    stats = {"created": 0, "skipped_existing": 0}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if _commitment_id(conn, row["cluster_code"]) is not None:
                stats["skipped_existing"] += 1
                continue
            prov = conn.execute("SELECT provider_id FROM provider WHERE code = ?",
                                (row["provider_code"],)).fetchone()
            clus = conn.execute("SELECT cluster_id FROM cluster WHERE code = ?",
                                (row["cluster_code"],)).fetchone()
            if prov is None or clus is None:
                raise ValueError(f"unknown provider/cluster in row: {row}")
            cur = conn.execute(
                "INSERT INTO delivery_commitment (provider_id, cluster_id,"
                " committed_qty, committed_delivery_date) VALUES (?,?,?,?)",
                (prov["provider_id"], clus["cluster_id"],
                 int(row["committed_qty"]), row["committed_delivery_date"]))
            conn.execute(
                "INSERT INTO forecast_revision (commitment_id, revision_no,"
                " forecast_delivery_date, forecast_qty, recorded_at,"
                " changed_fields, note) VALUES (?,1,?,?,'import','baseline',"
                " 'initial commitment import')",
                (cur.lastrowid, row["forecast_delivery_date"],
                 int(row["forecast_qty"])))
            stats["created"] += 1
    conn.commit()
    return stats


def import_forecast_csv(conn, path):
    """Apply forecast updates from CSV.

    Columns: cluster_code, forecast_delivery_date, forecast_qty,
    recorded_at, note. Returns {'revised': n, 'unchanged': n}.
    """
    stats = {"revised": 0, "unchanged": 0}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            r = apply_forecast(conn, row["cluster_code"],
                               row["forecast_delivery_date"],
                               int(row["forecast_qty"]), row["recorded_at"],
                               row.get("note", ""))
            stats[r] += 1
    return stats


def import_forecast_json(conn, path):
    """Apply forecast updates from a JSON list of objects with keys:
    cluster_code, forecast_delivery_date, forecast_qty, recorded_at, note.
    Returns {'revised': n, 'unchanged': n}."""
    stats = {"revised": 0, "unchanged": 0}
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    for row in rows:
        r = apply_forecast(conn, row["cluster_code"],
                           row["forecast_delivery_date"],
                           int(row["forecast_qty"]), row["recorded_at"],
                           row.get("note", ""))
        stats[r] += 1
    return stats


def forecast_history(conn, cluster_code):
    """Full revision history of one commitment, oldest first."""
    rows = conn.execute(
        "SELECT fr.revision_no, fr.forecast_delivery_date, fr.forecast_qty,"
        " fr.recorded_at, fr.changed_fields, fr.note FROM forecast_revision fr"
        " JOIN delivery_commitment dc ON dc.commitment_id = fr.commitment_id"
        " JOIN cluster c ON c.cluster_id = dc.cluster_id WHERE c.code = ?"
        " ORDER BY fr.revision_no", (cluster_code,)).fetchall()
    return [dict(r) for r in rows]


def forecast_change_count(conn, cluster_code=None):
    """Number of forecast changes (revisions beyond the baseline).

    With cluster_code: changes for that commitment. Without: fleet total.
    """
    if cluster_code:
        hist = forecast_history(conn, cluster_code)
        return max(0, len(hist) - 1)
    row = conn.execute(
        "SELECT COUNT(*) - COUNT(DISTINCT commitment_id) FROM forecast_revision"
    ).fetchone()
    return row[0]


def main():
    import argparse
    from .db import connect
    ap = argparse.ArgumentParser(description="Import commitments / forecasts")
    ap.add_argument("--db", default="data/supply.db")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("commitments")
    p1.add_argument("--file", required=True)
    p2 = sub.add_parser("forecast-csv")
    p2.add_argument("--file", required=True)
    p3 = sub.add_parser("forecast-json")
    p3.add_argument("--file", required=True)
    p4 = sub.add_parser("history")
    p4.add_argument("--cluster", required=True)
    args = ap.parse_args()
    conn = connect(args.db)
    if args.cmd == "commitments":
        print(import_commitments_csv(conn, args.file))
    elif args.cmd == "forecast-csv":
        print(import_forecast_csv(conn, args.file))
    elif args.cmd == "forecast-json":
        print(import_forecast_json(conn, args.file))
    else:
        for h in forecast_history(conn, args.cluster):
            print(h)
    conn.close()


if __name__ == "__main__":
    main()
