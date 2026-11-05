# Scorecard and Signal Definitions

SYNTHETIC / SIMULATED DATA throughout. Every metric below names its
source table and exact definition so any number in a generated report
can be recomputed by hand from the database.

## Supply signal (overview)

| Field | Source | Definition |
|---|---|---|
| GPUs | cluster.gpu_count | Nameplate GPU count of the cluster batch |
| Forecast delivery (latest) | forecast_revision (max revision_no) | The provider's current promised delivery date and quantity for the commitment |
| Actual delivery | delivery_commitment.actual_delivery_date | Date the delivered milestone evidence was signed; blank until delivered |
| Accepted | readiness_milestone type=accepted | Actual acceptance date; blank until the acceptance report passes |
| RFS (planned) | cluster.planned_rfs_date | Ready-for-service date in the current plan baseline |
| In-service (planned) | cluster.planned_inservice_date | Date capacity is planned to be usable by internal teams |

## Delivery scorecard (per provider)

| Metric | Source | Definition |
|---|---|---|
| Committed GPUs | delivery_commitment.committed_qty | Sum over the provider's commitments |
| Actual GPUs | delivery_commitment.actual_qty | Sum of quantities actually delivered (0 until delivered) |
| Qty attainment | derived | Actual GPUs / Committed GPUs x 100, 1 decimal |
| Forecast changes | forecast_revision | Total revisions minus one baseline per commitment; a change is counted when a re-imported forecast differs in date or quantity from the then-latest revision |
| Milestones completed | readiness_milestone | Rows with actual_date set, for clusters at that provider's sites |
| Milestones on-time | readiness_milestone | Completed rows with actual_date <= planned_date |
| Milestone attainment | derived | On-time / completed x 100, 1 decimal |
| Time to usable capacity (TTUC) | readiness_milestone | Per cluster in state in_service: actual in_service date minus actual delivered date, in days. Reported as n, median, p90 (nearest-rank), and max |

## Slip simulation

| Term | Definition |
|---|---|
| Slip | A uniform +N day shift applied to one provider's forecast delivery, RFS, and in-service dates (report-only; DB unchanged) |
| Missed allocation | An allocation whose need_by_date is earlier than the cluster's NEW in-service date but was covered by the OLD in-service date |
| Slip-caused gap | Sum of allocated_qty over missed allocations |
| Pre-existing miss | need_by_date already earlier than the OLD in-service date; reported separately, never counted in the slip-caused gap |

## Capacity-planning link

Allocations are the demand side of the same ledger: each cluster's
allocations sum to at most its gpu_count, carry a priority and a
need-by date, and are the first thing the slip simulation checks.
Unallocated remainder = cluster.gpu_count minus allocated sum is the
free capacity a planner can offer against a new demand signal.
