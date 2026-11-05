# capacity-supply-signal — GPU Supply Signal and Delivery Scorecard System

> SYNTHETIC / SIMULATED DATA — every provider, site, cluster, date and
> quantity in this repository is invented for method demonstration.
> Nothing here is a record of a real supplier, site, project or employer,
> and nothing here claims the author has owned a hyperscale fleet or a
> production supply-signal platform. See "Honest boundaries" below.

## What this is

A working model of the supply-signal layer for GPU capacity delivery:
multiple providers shipping bare-metal GPU cluster batches to multiple
sites, where the program-level job is to keep one trustworthy signal —
quantities, delivery forecasts and their revisions, acceptance and
readiness milestones, ready-for-service and in-service dates — and to
make slippage visible early enough to act on. It produces three
artifacts from one SQLite database: a one-screen supply-signal
overview, a per-provider delivery scorecard, and a slip-propagation
simulation. Every number in every report is recomputed from the
database at generation time and can be re-derived by hand from
`docs/definitions.md`.

Seed fleet (synthetic): 3 providers, 5 sites, 8 clusters, 2,048 GPUs.

## Why it exists (target role)

Built as a work sample against the OpenAI Technical Program Manager,
Compute Infrastructure role, whose core is owning the GPU supply
signal and the tooling/data platform behind it, and building delivery
scorecards for cloud providers and internal infrastructure teams.
The JD mapping table below ties each module to the duty it answers.

## How to run

Python 3.12, standard library only (sqlite3 / csv / json). Tests use
pytest, installed in the repo-local virtualenv.

```bash
cd ~/workspace/capacity-supply-signal
python3 -m venv .venv && .venv/bin/pip install pytest   # once

# 1. Build the seeded database (also writes the seed CSV/JSON files)
.venv/bin/python -m capacity_signal.seed --db data/supply.db

# 2. Import a forecast update (CSV or JSON), then inspect its history
.venv/bin/python -m capacity_signal.importer --db data/supply.db forecast-csv --file examples/forecast_update.csv
.venv/bin/python -m capacity_signal.importer --db data/supply.db history --cluster CL-07

# 3. Generate the overview and the scorecard
.venv/bin/python -m capacity_signal.reports overview  --db data/supply.db --out reports/overview.md
.venv/bin/python -m capacity_signal.reports scorecard --db data/supply.db --out reports/scorecard.md

# 4. Simulate a provider slip (read-only; the database is not modified)
.venv/bin/python -m capacity_signal.simulate --db data/supply.db --provider HELIX --days 14 --out reports/slip-helix-14d.md

# 5. Run the test suite
.venv/bin/python -m pytest tests/ -q
```

Note on the stack: the specification suggested FastAPI; the system is
implemented on the Python standard library instead (SQLite plus CLI
report generators), because every consumer of these artifacts is a
report or a batch simulation, and a zero-dependency core keeps the
numbers reproducible anywhere. The module boundaries (importer /
reports / simulate over one schema) are where an HTTP layer would sit.

## Modules and JD mapping

| Module | What it does | JD duty it answers |
|---|---|---|
| `schema.sql` + `capacity_signal/seed.py` | Six-entity data model: provider, site, cluster, delivery_commitment, readiness_milestone, allocation, plus forecast_revision and state_transition history tables | Define the data model behind the supply signal; bare-metal provisioning / inventory / planning system concepts |
| `docs/state-machine.md` + `capacity_signal/state_machine.py` | Bare-metal lifecycle ordered -> shipped -> delivered -> racked -> provisioned -> accepted -> in_service; forward-only, one step at a time, named acceptance evidence required per transition, every transition logged | Understand how site readiness, equipment delivery, commissioning and ready-for-service milestones gate cluster deployment |
| `capacity_signal/importer.py` | CSV/JSON import of delivery commitments and forecast updates with revision versioning: identical re-imports are no-ops, real changes record which fields changed and why | Own the supply signal: quantities, arrival forecasts, and forecast changes made visible |
| `capacity_signal/reports.py` (overview) | One-screen roll-up by provider / site / cluster: GPUs, latest forecast vs actual delivery, acceptance, RFS, in-service, plus reserved allocations | Give internal teams one current view of expected in-service dates and downstream impact |
| `capacity_signal/reports.py` (scorecard) | Per-provider scorecard: committed vs actual quantity and attainment, forecast-change count, milestone on-time attainment, time-to-usable-capacity distribution (median / p90 / max); definitions in `docs/definitions.md` | Build delivery scorecards: commitments, forecast changes, actual deliveries, readiness milestones, time to usable capacity |
| `capacity_signal/simulate.py` | Slip propagation: delay one provider by N days, recompute cluster RFS / in-service dates, and report allocations whose need-by date is missed (allocation gap). Includes a fixed, hand-checked scenario (Helix +14 days -> 2 clusters, 556 GPU gap) asserted in tests | Work with capacity planning on supply/demand, allocation and constraints; show what a delivery change does downstream |
| `tests/test_core.py` | 8 pytest tests: seed shape, state-machine legality, import version counting, fleet forecast-change total, scorecard arithmetic, TTUC distribution, the fixed slip scenario, zero-slip no-op | Evidence the calculations are correct, not just plausible |

Related but separate: cluster bring-up validation hands-on work
(Kubernetes lab) is tracked as a study item in the candidate's
learning plan, not in this repository; this system models the supply
and readiness layer that feeds a cluster, not the cluster's internal
orchestration.

## Honest boundaries

What this demonstrates:
- The data model, metric definitions and decision workflow of a GPU
  supply signal and provider scorecard, implemented end to end and
  verified by tests with hand-checked numbers.
- Method transferred from the author's real work: delivery-commitment
  discipline and acceptance-evidence habits from factory rack-scale
  builds and bring-up, and the receiving side's view of what
  "usable capacity" means from operating a live data-center facility.

What this does not demonstrate:
- Employment at a hyperscaler or cloud provider, ownership of a real
  GPU fleet, or operation of a production supply-signal platform.
  The fleet here is 2,048 synthetic GPUs; the method is the sample,
  not the scale.
- Any real supplier's performance. Provider names are invented and
  scorecard numbers describe the seed data only.

## File list

| Path | Contents |
|---|---|
| `schema.sql` | Full SQLite schema for the six entities plus history tables |
| `capacity_signal/db.py` | Connection / schema bootstrap |
| `capacity_signal/seed.py` | Synthetic seed generator (3 providers / 5 sites / 8 clusters / 2,048 GPUs) |
| `capacity_signal/state_machine.py` | Bare-metal state transitions with evidence enforcement |
| `capacity_signal/importer.py` | Commitment and forecast import with revision history |
| `capacity_signal/reports.py` | Overview and scorecard generators |
| `capacity_signal/simulate.py` | Slip-propagation simulation (hand-checked scenario in its docstring) |
| `docs/state-machine.md` | State definitions and the acceptance evidence each state requires |
| `docs/definitions.md` | Every report field and metric: source table and exact definition |
| `data/seed/` | Generated seed inputs (commitments.csv, forecast_revisions.json) |
| `examples/` | Sample forecast-update files (CSV and JSON) for the importer |
| `reports/` | Generated overview, scorecard and slip-simulation reports |
| `tests/test_core.py` | Pytest suite (8 tests) |
| `VERIFICATION.md` | Verification record: real test output, reproducibility check, spec checklist |
