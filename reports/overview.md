# Supply Signal Overview (one-screen roll-up)

> SYNTHETIC / SIMULATED DATA - invented providers, sites, clusters and dates. Not a record of any real project.

Fleet: 3 providers / 5 sites / 8 clusters / 2048 GPUs (synthetic).

| Provider | Site | Cluster | GPUs | Model | State | Forecast delivery (latest) | Actual delivery | Accepted | RFS (planned) | In-service (planned) |
|---|---|---|---|---|---|---|---|---|---|---|
| Atlas Cloud | IAD-1 | CL-06 | 256 | H200 | delivered | 2026-12-01 (256 GPUs) | 2026-12-03 | - | 2027-01-15 | 2027-01-29 |
| Atlas Cloud | IAD-1 | CL-07 | 64 | H100 | shipped | 2027-03-17 (64 GPUs) | - | - | 2027-05-01 | 2027-05-15 |
| Atlas Cloud | IAD-1 | CL-08 | 64 | H100 | ordered | 2027-04-17 (64 GPUs) | - | - | 2027-06-01 | 2027-06-15 |
| Helix Compute | ORD-1 | CL-04 | 512 | H200 | provisioned | 2026-12-29 (512 GPUs) | 2026-12-29 | - | 2027-02-15 | 2027-03-01 |
| Helix Compute | SEA-1 | CL-05 | 256 | B200 | racked | 2027-02-21 (256 GPUs) | 2027-02-21 | - | 2027-04-01 | 2027-04-15 |
| NovaCloud Compute | DAL-1 | CL-03 | 128 | B200 | accepted | 2026-10-17 (128 GPUs) | 2026-10-18 | 2026-11-25 | 2026-12-01 | 2026-12-15 |
| NovaCloud Compute | PHX-1 | CL-01 | 512 | H200 | in_service | 2026-07-23 (512 GPUs) | 2026-07-20 | 2026-08-21 | 2026-09-01 | 2026-09-15 |
| NovaCloud Compute | PHX-1 | CL-02 | 256 | H200 | in_service | 2026-08-20 (248 GPUs) | 2026-08-17 | 2026-09-21 | 2026-10-01 | 2026-10-15 |

Allocations (reserved):

| Cluster | Team | GPUs | Priority | Need by |
|---|---|---|---|---|
| CL-01 | Training-A | 300 | 1 | 2026-09-20 |
| CL-01 | Inference-A | 212 | 2 | 2026-09-25 |
| CL-02 | Training-B | 256 | 1 | 2026-10-20 |
| CL-03 | Inference-B | 128 | 1 | 2026-12-20 |
| CL-04 | Training-C | 300 | 1 | 2027-03-10 |
| CL-04 | Inference-C | 212 | 2 | 2027-03-20 |
| CL-05 | Training-D | 256 | 1 | 2027-04-20 |
| CL-06 | Inference-D | 200 | 1 | 2027-02-05 |
| CL-06 | Training-E | 56 | 2 | 2027-02-10 |
| CL-07 | Inference-E | 64 | 1 | 2027-05-20 |
| CL-08 | Training-F | 64 | 1 | 2027-06-20 |
