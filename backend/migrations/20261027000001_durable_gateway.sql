-- Separate protocol from immutable fixture publications. No changes to applied DDL.
CREATE TABLE published.gateway_jobs (
    stream_id UUID NOT NULL REFERENCES published.sources(stream_id),
    request_key TEXT NOT NULL CHECK (length(request_key)=64),
    id UUID NOT NULL UNIQUE,
    owner_id UUID,
    request_nonce UUID,
    request JSONB NOT NULL CHECK (octet_length(request::text)<=524288),
    side_effect BOOLEAN NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued','running','completed','failed','indeterminate')),
    attempts INTEGER NOT NULL DEFAULT 0,
    lease_token UUID,
    lease_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_at TIMESTAMPTZ,
    fresh_until TIMESTAMPTZ,
    response_status INTEGER CHECK (response_status BETWEEN 200 AND 599),
    response JSONB CHECK (octet_length(response::text)<=8388608),
    PRIMARY KEY(stream_id,request_key),
    UNIQUE(stream_id,owner_id,request_nonce),
    CHECK ((state='completed') = (response_status IS NOT NULL AND generated_at IS NOT NULL AND fresh_until IS NOT NULL))
);
CREATE INDEX gateway_jobs_pending ON published.gateway_jobs(stream_id,created_at) WHERE state IN ('queued','running');
CREATE INDEX gateway_jobs_owner ON published.gateway_jobs(stream_id,owner_id) WHERE state IN ('queued','running');
REVOKE ALL ON published.gateway_jobs FROM PUBLIC;
