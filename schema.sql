-- capacity-supply-signal schema (SQLite). SYNTHETIC / SIMULATED DATA only.
-- Six core entities: provider, site, cluster, delivery_commitment,
-- readiness_milestone, allocation. Plus forecast_revision (version history
-- for commitments) and state_transition (bare-metal state machine log).

CREATE TABLE IF NOT EXISTS provider (
    provider_id INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS site (
    site_id     INTEGER PRIMARY KEY,
    provider_id INTEGER NOT NULL REFERENCES provider(provider_id),
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    region      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cluster (
    cluster_id              INTEGER PRIMARY KEY,
    site_id                 INTEGER NOT NULL REFERENCES site(site_id),
    code                    TEXT NOT NULL UNIQUE,
    name                    TEXT NOT NULL,
    gpu_model               TEXT NOT NULL,
    gpu_count               INTEGER NOT NULL CHECK (gpu_count > 0),
    hardware_state          TEXT NOT NULL DEFAULT 'ordered' CHECK (hardware_state IN
        ('ordered','shipped','delivered','racked','provisioned','accepted','in_service')),
    planned_rfs_date        TEXT NOT NULL,
    planned_inservice_date  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS delivery_commitment (
    commitment_id          INTEGER PRIMARY KEY,
    provider_id            INTEGER NOT NULL REFERENCES provider(provider_id),
    cluster_id             INTEGER NOT NULL UNIQUE REFERENCES cluster(cluster_id),
    committed_qty          INTEGER NOT NULL CHECK (committed_qty > 0),
    committed_delivery_date TEXT NOT NULL,
    actual_qty             INTEGER,
    actual_delivery_date   TEXT
);

CREATE TABLE IF NOT EXISTS forecast_revision (
    revision_id            INTEGER PRIMARY KEY,
    commitment_id          INTEGER NOT NULL REFERENCES delivery_commitment(commitment_id),
    revision_no            INTEGER NOT NULL CHECK (revision_no >= 1),
    forecast_delivery_date TEXT NOT NULL,
    forecast_qty           INTEGER NOT NULL,
    recorded_at            TEXT NOT NULL,
    changed_fields         TEXT NOT NULL DEFAULT '',
    note                   TEXT NOT NULL DEFAULT '',
    UNIQUE (commitment_id, revision_no)
);

CREATE TABLE IF NOT EXISTS readiness_milestone (
    milestone_id   INTEGER PRIMARY KEY,
    cluster_id     INTEGER NOT NULL REFERENCES cluster(cluster_id),
    milestone_type TEXT NOT NULL CHECK (milestone_type IN
        ('delivered','racked','provisioned','accepted','ready_for_service','in_service')),
    planned_date   TEXT NOT NULL,
    actual_date    TEXT,
    status         TEXT NOT NULL DEFAULT 'planned' CHECK (status IN
        ('planned','in_progress','done','missed')),
    evidence       TEXT NOT NULL DEFAULT '',
    UNIQUE (cluster_id, milestone_type)
);

CREATE TABLE IF NOT EXISTS allocation (
    allocation_id INTEGER PRIMARY KEY,
    cluster_id    INTEGER NOT NULL REFERENCES cluster(cluster_id),
    team          TEXT NOT NULL,
    allocated_qty INTEGER NOT NULL CHECK (allocated_qty > 0),
    priority      INTEGER NOT NULL DEFAULT 1,
    need_by_date  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'reserved' CHECK (status IN
        ('reserved','active','at_risk','released'))
);

CREATE TABLE IF NOT EXISTS state_transition (
    transition_id   INTEGER PRIMARY KEY,
    cluster_id      INTEGER NOT NULL REFERENCES cluster(cluster_id),
    from_state      TEXT NOT NULL,
    to_state        TEXT NOT NULL,
    transitioned_at TEXT NOT NULL,
    evidence        TEXT NOT NULL
);
