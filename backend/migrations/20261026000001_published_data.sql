-- Destination only. No ownership or DML grants on application/user tables.
CREATE SCHEMA published;

-- Register each authorized local installation explicitly using migration credentials.
-- Never reuse a stream identity with a divergent/restored source history.
CREATE TABLE published.sources (
    stream_id UUID PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT NOT NULL,
    last_success_at TIMESTAMPTZ
);

CREATE TABLE published.records (
    stream_id UUID NOT NULL REFERENCES published.sources(stream_id),
    dataset TEXT NOT NULL CHECK (dataset IN ('fixture_bundle','model_metadata','simulation_bundle')),
    record_key TEXT NOT NULL CHECK (length(record_key) BETWEEN 1 AND 512),
    version BIGINT NOT NULL CHECK (version > 0),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object' AND octet_length(payload::text) <= 1048576),
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    changed_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
    PRIMARY KEY(stream_id,dataset,record_key)
);

-- A receipt commits in the SAME transaction as the corresponding record write.
CREATE TABLE published.receipts (
    event_id UUID PRIMARY KEY,
    stream_id UUID NOT NULL REFERENCES published.sources(stream_id),
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX published_receipts_stream ON published.receipts(stream_id,committed_at);
REVOKE ALL ON SCHEMA published FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA published FROM PUBLIC;
