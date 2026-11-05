"""Core tests: seed shape, state machine, import versioning, scorecard
arithmetic, TTUC, and the fixed hand-checked slip scenario."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from capacity_signal import importer, reports, seed  # noqa: E402
from capacity_signal.simulate import simulate_slip  # noqa: E402
from capacity_signal.state_machine import transition  # noqa: E402


@pytest.fixture()
def conn(tmp_path):
    c = seed.build_db(tmp_path / "test.db")
    yield c
    c.close()


def test_seed_shape(conn):
    assert conn.execute("SELECT COUNT(*) FROM provider").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM site").fetchone()[0] == 5
    assert conn.execute("SELECT COUNT(*) FROM cluster").fetchone()[0] == 8
    assert conn.execute(
        "SELECT SUM(gpu_count) FROM cluster").fetchone()[0] == 2048


def test_state_machine_legal_and_illegal(conn):
    # CL-08 is 'ordered': only -> shipped is legal, with evidence.
    r = transition(conn, "CL-08", "shipped", "ASN-8841 manifest", "2026-08-01")
    assert r == {"cluster": "CL-08", "from": "ordered", "to": "shipped"}
    with pytest.raises(ValueError):
        transition(conn, "CL-08", "racked", "photo set", "2026-08-02")  # skip
    with pytest.raises(ValueError):
        transition(conn, "CL-08", "ordered", "rewind", "2026-08-02")  # backward
    with pytest.raises(ValueError):
        transition(conn, "CL-08", "delivered", "", "2026-08-02")  # no evidence
    # Failed attempts wrote nothing: still shipped, exactly 1 log row.
    state = conn.execute(
        "SELECT hardware_state FROM cluster WHERE code='CL-08'").fetchone()[0]
    assert state == "shipped"
    assert conn.execute(
        "SELECT COUNT(*) FROM state_transition").fetchone()[0] == 1


def test_import_version_counting(conn):
    base = importer.forecast_change_count(conn, "CL-07")
    assert base == 0
    # New forecast (date slips 10 days: baseline 2027-03-17 -> 2027-03-27).
    assert importer.apply_forecast(conn, "CL-07", "2027-03-27", 64,
                                   "2027-01-05", "port delay") == "revised"
    # Identical re-import -> no-op.
    assert importer.apply_forecast(conn, "CL-07", "2027-03-27", 64,
                                   "2027-01-06", "duplicate send") == "unchanged"
    # Quantity-only change -> another revision.
    assert importer.apply_forecast(conn, "CL-07", "2027-03-27", 56,
                                   "2027-01-12", "8 units diverted") == "revised"
    hist = importer.forecast_history(conn, "CL-07")
    assert len(hist) == 3  # baseline + 2 changes
    assert importer.forecast_change_count(conn, "CL-07") == 2
    assert hist[1]["changed_fields"] == "forecast_delivery_date"
    assert hist[2]["changed_fields"] == "forecast_qty"
    assert hist[2]["forecast_qty"] == 56


def test_fleet_forecast_changes(conn):
    # Seed: CL-01 1, CL-02 2, CL-04 2, CL-05 1, others 0 -> total 6.
    assert importer.forecast_change_count(conn) == 6


def test_scorecard_numbers(conn):
    rows = {r["code"]: r for r in reports.scorecard_rows(conn)}
    nova = rows["NOVA"]
    assert nova["committed_qty"] == 896
    assert nova["actual_qty"] == 888  # 512 + 248 + 128
    assert nova["qty_attainment_pct"] == 99.1
    assert nova["forecast_changes"] == 3
    assert (nova["milestones_on_time"], nova["milestones_completed"]) == (7, 16)
    assert nova["milestone_attainment_pct"] == 43.8
    helix = rows["HELIX"]
    assert helix["committed_qty"] == 768 and helix["actual_qty"] == 768
    assert helix["forecast_changes"] == 3
    assert (helix["milestones_on_time"],
            helix["milestones_completed"]) == (2, 5)
    atlas = rows["ATLAS"]
    assert atlas["committed_qty"] == 384 and atlas["actual_qty"] == 256
    assert atlas["forecast_changes"] == 0
    assert (atlas["milestones_on_time"],
            atlas["milestones_completed"]) == (0, 1)


def test_ttuc_distribution(conn):
    # CL-01: delivered actual 2026-07-20, in-service actual 2026-09-18 = 60d.
    # CL-02: delivered actual 2026-08-17, in-service actual 2026-10-17 = 61d.
    assert reports.ttuc_values(conn) == [60, 61]
    stats = reports.ttuc_stats(reports.ttuc_values(conn))
    assert stats == {"n": 2, "median": 60.5, "p90": 61, "max": 61}


def test_slip_scenario_fixed(conn):
    """Hand-checked scenario documented in simulate.py docstring."""
    r = simulate_slip(conn, "HELIX", 14)
    by = {c["cluster"]: c for c in r["clusters"]}
    assert by["CL-04"]["old_inservice"] == "2027-03-01"
    assert by["CL-04"]["new_inservice"] == "2027-03-15"
    assert by["CL-04"]["new_rfs"] == "2027-03-01"
    assert by["CL-04"]["gap_gpus"] == 300  # Training-C only
    assert by["CL-05"]["old_inservice"] == "2027-04-15"
    assert by["CL-05"]["new_inservice"] == "2027-04-29"
    assert by["CL-05"]["gap_gpus"] == 256  # Training-D
    assert r["affected_clusters"] == 2
    assert r["total_gap_gpus"] == 556
    # Simulation must not mutate the DB.
    assert conn.execute(
        "SELECT planned_inservice_date FROM cluster WHERE code='CL-04'"
    ).fetchone()[0] == "2027-03-01"


def test_slip_zero_days_no_gap(conn):
    r = simulate_slip(conn, "HELIX", 0)
    assert r["total_gap_gpus"] == 0 and r["affected_clusters"] == 0
