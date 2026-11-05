# Bare-Metal GPU Hardware State Machine

SYNTHETIC / SIMULATED method demonstration. One state per cluster batch
(the unit a delivery commitment ships in). Transitions are forward-only,
one step at a time, and each requires the listed acceptance evidence.
Enforcement: the `hardware_state` CHECK constraint in `schema.sql` limits
values to the seven states; `capacity_signal/state_machine.py` enforces
ordering and the evidence requirement, and logs every transition in
`state_transition`.

| # | State | Meaning | Acceptance evidence required to ENTER the state |
|---|---|---|---|
| 1 | ordered | Purchase order placed against a delivery commitment | (initial state) signed commitment / PO reference |
| 2 | shipped | Hardware has left the factory / integrator | Carrier ASN or bill of lading with serial manifest |
| 3 | delivered | Hardware received at site, count and condition verified | Signed receiving report + serial manifest diff (ordered vs received) |
| 4 | racked | Nodes installed in racks, power and cooling connected | Rack elevation record + power/cooling connection checklist |
| 5 | provisioned | Firmware baseline applied, fabric registration complete, nodes visible to inventory | Provisioning log (firmware versions per node) + inventory registration dump |
| 6 | accepted | Acceptance test suite passed at cluster level | Acceptance test report (burn-in, fabric bandwidth, collective operations) with pass/fail per test |
| 7 | in_service | Capacity released to production allocation | Production release record + operations handover sign-off |

Rules:

1. No skipping: `delivered -> provisioned` is illegal; `racked` must
   come first. A cluster that fails acceptance stays in `provisioned`
   until the acceptance report passes.
2. No backward moves in the log. A failed unit is handled by an RMA /
   replacement sub-flow against the same commitment, not by moving the
   cluster backward.
3. No evidence, no transition: the state machine rejects an empty
   evidence string, mirroring the rule that a gate passes on evidence,
   not on a status meeting.
4. The readiness_milestone rows mirror these states (plus the
   ready_for_service program milestone) so the scorecard can measure
   planned vs actual per step.
