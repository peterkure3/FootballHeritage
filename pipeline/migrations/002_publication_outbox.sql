-- Local database only. Additive: no changes to provider/training/user tables.
CREATE SCHEMA IF NOT EXISTS fh_sync;

CREATE TABLE fh_sync.identity (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    stream_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid()
);
INSERT INTO fh_sync.identity(singleton) VALUES (TRUE);

-- Each bundle is self-contained: fixture + predictions + quotes + provider IDs.
-- No cross-bundle FK needs to be resolved at the destination.
CREATE TABLE fh_sync.records (
    dataset TEXT NOT NULL CHECK (dataset IN ('fixture_bundle','model_metadata','simulation_bundle')),
    record_key TEXT NOT NULL CHECK (length(record_key) BETWEEN 1 AND 512),
    version BIGINT NOT NULL DEFAULT 1 CHECK (version > 0),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object' AND octet_length(payload::text) <= 1048576),
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(dataset, record_key)
);

CREATE TABLE fh_sync.outbox (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL REFERENCES fh_sync.identity(stream_id),
    dataset TEXT NOT NULL,
    record_key TEXT NOT NULL,
    version BIGINT NOT NULL,
    payload JSONB NOT NULL,
    payload_bytes INTEGER GENERATED ALWAYS AS (octet_length(payload::text)) STORED,
    deleted BOOLEAN NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    dead_at TIMESTAMPTZ,
    error_code TEXT,
    UNIQUE(dataset, record_key, version)
);
CREATE INDEX fh_sync_pending ON fh_sync.outbox(available_at, id)
    WHERE completed_at IS NULL AND dead_at IS NULL;

CREATE TABLE fh_sync.status (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    error_code TEXT
);
INSERT INTO fh_sync.status(singleton) VALUES (TRUE);

CREATE FUNCTION fh_sync.version_record() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Use an explicit publication tombstone, not DELETE';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF (NEW.dataset,NEW.record_key) IS DISTINCT FROM (OLD.dataset,OLD.record_key) THEN
            RAISE EXCEPTION 'Publication record identity is immutable';
        END IF;
        NEW.version := OLD.version + 1;
    ELSE
        NEW.version := 1;
    END IF;
    NEW.changed_at := clock_timestamp();
    RETURN NEW;
END;
$$;
CREATE TRIGGER fh_sync_version BEFORE INSERT OR UPDATE OR DELETE ON fh_sync.records
    FOR EACH ROW EXECUTE FUNCTION fh_sync.version_record();

CREATE FUNCTION fh_sync.capture_record() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO fh_sync.outbox(stream_id,dataset,record_key,version,payload,deleted,changed_at)
    SELECT stream_id,NEW.dataset,NEW.record_key,NEW.version,NEW.payload,NEW.deleted,NEW.changed_at
    FROM fh_sync.identity;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Publication stream identity is missing';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER fh_sync_capture AFTER INSERT OR UPDATE ON fh_sync.records
    FOR EACH ROW EXECUTE FUNCTION fh_sync.capture_record();

REVOKE ALL ON SCHEMA fh_sync FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA fh_sync FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA fh_sync FROM PUBLIC;
