# VERIFICATION - capacity-supply-signal

Verification date: 2026-11-05. Environment: Python 3.12.3, pytest in
the repo-local .venv, SQLite via the Python standard library. All
outputs below are from runs executed in this repository.

## 1. Test run (real output)

Command: .venv/bin/python -m pytest tests/ -q

```
........                                                                 [100%]
8 passed in 0.52s
```

(Re-run during final verification: 8 passed in 1.00s.)

Coverage: seed shape (3 providers / 5 sites / 8 clusters / 2,048
GPUs); state-machine legal and illegal transitions including the
evidence requirement and no-write-on-failure; import revision
counting (baseline + 2 changes = 3 history rows for the exercised
cluster, duplicate re-import is a no-op); fleet forecast-change
total = 6; scorecard arithmetic per provider; TTUC distribution;
the fixed slip scenario; zero-day slip produces no gap.

## 2. Pipeline reproducibility (real output)

A fresh database was seeded to a scratch path and all three reports
regenerated; each regenerated report is byte-identical (diff) to the
committed copy in reports/.

```
seeded /tmp/css-check.db: 3 providers, 5 sites, 8 clusters, 2048 GPUs (SYNTHETIC DATA)
wrote /tmp/css-overview.md
wrote /tmp/css-scorecard.md
REPORTS-REPRODUCIBLE
```

## 3. Scorecard key figures (from reports/scorecard.md, generated)

| Provider | Committed | Actual | Qty attainment | Forecast changes | Milestones on-time / completed | TTUC |
|---|---|---|---|---|---|---|
| Atlas Cloud | 384 | 256 | 66.7% | 0 | 0 / 1 | n=0 |
| Helix Compute | 768 | 768 | 100.0% | 3 | 2 / 5 | n=0 |
| NovaCloud Compute | 896 | 888 | 99.1% | 3 | 7 / 16 | n=2, median 60.5d, p90 61d |

Fleet: milestones on-time 9 / 22 (40.9%). TTUC hand-check asserted in
tests: CL-01 delivered 2026-07-20 to in-service 2026-09-18 = 60 days;
CL-02 delivered 2026-08-17 to in-service 2026-10-17 = 61 days.

## 4. Fixed slip scenario: expected vs system output

Scenario: provider Helix Compute slips 14 days. Hand expectation
(documented in capacity_signal/simulate.py and asserted in
tests/test_core.py): CL-04 in-service 2027-03-01 -> 2027-03-15,
missing allocation Training-C (300 GPUs, need by 2027-03-10);
CL-05 in-service 2027-04-15 -> 2027-04-29, missing Training-D
(256 GPUs, need by 2027-04-20); affected clusters 2; total gap
556 GPUs; database unmodified by the simulation.

System output (reports/slip-helix-14d.md) matches on every figure.

## 5. Spec checklist

| Spec item | Status |
|---|---|
| Six-entity data model + bare-metal state machine with per-state acceptance evidence | Done: schema.sql, docs/state-machine.md, state_machine.py |
| Import layer for commitments and forecast changes, versioned, revision history queryable | Done: importer.py (CSV/JSON, history subcommand), examples/ |
| Supply-signal one-screen overview by provider / site / cluster | Done: reports/overview.md |
| Delivery scorecard (committed vs actual, milestone attainment, TTUC distribution), one-command generation, definitions documented | Done: reports/scorecard.md, docs/definitions.md |
| Slip-propagation simulation with a hand-checked fixed scenario | Done: simulate.py, test_slip_scenario_fixed |
| Synthetic seed: 3 providers / 5 sites / about 2,000 GPUs | Done: exactly 2,048 GPUs across 8 clusters |
| Synthetic-data disclaimer on the first screen of README and on every generated report | Done |
| pytest suite over core calculations, all passing | Done: 8 passed |
| README with JD mapping table and honest boundaries | Done |
| Stack note | Spec suggested Python + FastAPI + SQLite; implemented as Python standard library + SQLite (zero-dependency core, CLI report generators). Recorded as a deliberate substitution in README, not an omission. |
| Kubernetes hands-on lab (study item S1 in the gap analysis) | Not in this repo by design: it belongs to the learning-plan item, not to either work sample. The Q1 interview answer describes it as lab work in progress; do not present this repo as covering it. |

Local build only. Not pushed; no remote configured.
