"""Bare-metal GPU hardware state machine.

States (strictly ordered, forward-only, one step at a time):
    ordered -> shipped -> delivered -> racked -> provisioned -> accepted
    -> in_service

Every transition requires an evidence string (what proves the new state:
ASN, receiving report, rack elevation photo set, provisioning log,
acceptance test report, production release record). A transition without
evidence, a skipped state, or a backward move raises ValueError and
writes nothing.
"""
from .db import connect

STATES = ["ordered", "shipped", "delivered", "racked",
          "provisioned", "accepted", "in_service"]

# Evidence expected per target state (also documented in docs/state-machine.md).
EVIDENCE_HINT = {
    "shipped": "carrier ASN / bill of lading",
    "delivered": "signed receiving report + serial manifest diff",
    "racked": "rack elevation record + power/cooling connection checklist",
    "provisioned": "provisioning log (firmware baseline + fabric registration)",
    "accepted": "acceptance test report (burn-in + fabric + collective tests)",
    "in_service": "production release record + operations handover sign-off",
}


def next_state(state):
    idx = STATES.index(state)
    return STATES[idx + 1] if idx + 1 < len(STATES) else None


def can_transition(from_state, to_state):
    return next_state(from_state) == to_state


def transition(conn, cluster_code, to_state, evidence, transitioned_at):
    if not evidence or not evidence.strip():
        raise ValueError("transition requires non-empty evidence")
    row = conn.execute(
        "SELECT cluster_id, hardware_state FROM cluster WHERE code = ?",
        (cluster_code,)).fetchone()
    if row is None:
        raise ValueError(f"unknown cluster: {cluster_code}")
    from_state = row["hardware_state"]
    if not can_transition(from_state, to_state):
        raise ValueError(
            f"illegal transition {from_state} -> {to_state}; "
            f"only {from_state} -> {next_state(from_state)} is allowed")
    conn.execute(
        "INSERT INTO state_transition (cluster_id, from_state, to_state,"
        " transitioned_at, evidence) VALUES (?,?,?,?,?)",
        (row["cluster_id"], from_state, to_state, transitioned_at, evidence))
    conn.execute(
        "UPDATE cluster SET hardware_state = ? WHERE cluster_id = ?",
        (to_state, row["cluster_id"]))
    conn.commit()
    return {"cluster": cluster_code, "from": from_state, "to": to_state}
