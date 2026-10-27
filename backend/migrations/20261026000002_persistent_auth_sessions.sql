-- Application-owned state. The sports publication role receives no access.
CREATE TABLE auth_sessions (
    session_id TEXT PRIMARY KEY CHECK (length(session_id) BETWEEN 1 AND 256),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    ip_address TEXT NOT NULL,
    user_agent TEXT NOT NULL,
    CHECK (expires_at >= created_at)
);
CREATE INDEX auth_sessions_active_user ON auth_sessions(user_id,expires_at)
    WHERE revoked_at IS NULL;
REVOKE ALL ON auth_sessions FROM PUBLIC;
