CREATE TABLE records (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('projects','skills','education','certificates','milestones')),
    data TEXT NOT NULL CHECK(json_valid(data)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version > 0),
    deleted_at TEXT,
    sync_status TEXT NOT NULL CHECK(sync_status IN ('pending','synced','conflict')),
    last_server_version INTEGER NOT NULL DEFAULT 0 CHECK(last_server_version >= 0)
);
CREATE INDEX records_owner_kind ON records(owner_id, kind, id);
CREATE UNIQUE INDEX project_slug ON records(owner_id, json_extract(data, '$.slug'))
    WHERE kind = 'projects' AND deleted_at IS NULL;
CREATE UNIQUE INDEX skill_name ON records(owner_id, lower(json_extract(data, '$.name')))
    WHERE kind = 'skills' AND deleted_at IS NULL;
CREATE TABLE local_sync_state (
    owner_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    last_cursor INTEGER NOT NULL DEFAULT 0,
    last_success_at TEXT
);
CREATE TABLE local_outbox (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL UNIQUE,
    owner_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL REFERENCES records(id),
    action TEXT NOT NULL CHECK(action IN ('create','update','delete')),
    base_version INTEGER NOT NULL,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    state TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry_at TEXT,
    last_error TEXT
);
CREATE INDEX outbox_owner_sequence ON local_outbox(owner_id, sequence);
