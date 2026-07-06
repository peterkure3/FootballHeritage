-- RAG System Migration: Add pgvector support and embeddings tables
-- Run this migration to enable super-fast RAG queries

-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Event embeddings table for semantic search
CREATE TABLE IF NOT EXISTS event_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    content_text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id)
);

-- HNSW index for fast approximate nearest neighbor search
-- m=16: number of connections per layer (higher = more accurate but slower)
-- ef_construction=64: size of dynamic candidate list (higher = better quality index)
CREATE INDEX IF NOT EXISTS event_embeddings_embedding_idx 
ON event_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index on event_id for fast lookups
CREATE INDEX IF NOT EXISTS event_embeddings_event_id_idx 
ON event_embeddings(event_id);

-- Bet embeddings table for user history semantic search
CREATE TABLE IF NOT EXISTS bet_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bet_id UUID NOT NULL REFERENCES bets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    content_text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bet_id)
);

-- HNSW index for bet embeddings
CREATE INDEX IF NOT EXISTS bet_embeddings_embedding_idx 
ON bet_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index on user_id for filtering user-specific bets
CREATE INDEX IF NOT EXISTS bet_embeddings_user_id_idx 
ON bet_embeddings(user_id);

-- Add full-text search column to events table
ALTER TABLE events ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- GIN index for full-text search (keyword matching)
CREATE INDEX IF NOT EXISTS events_search_idx 
ON events USING GIN(search_vector);

-- Trigger function to auto-update search vector on insert/update
CREATE OR REPLACE FUNCTION events_search_trigger() 
RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.home_team, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.away_team, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.league, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.sport, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS events_search_update ON events;
CREATE TRIGGER events_search_update
    BEFORE INSERT OR UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION events_search_trigger();

-- Update existing events with search vectors
UPDATE events 
SET search_vector = 
    setweight(to_tsvector('english', COALESCE(home_team, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(away_team, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(league, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(sport, '')), 'B')
WHERE search_vector IS NULL;

-- Create updated_at trigger for event_embeddings
CREATE OR REPLACE FUNCTION update_event_embeddings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_event_embeddings_updated_at_trigger ON event_embeddings;
CREATE TRIGGER update_event_embeddings_updated_at_trigger
    BEFORE UPDATE ON event_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_event_embeddings_updated_at();

-- Create helper function for vector similarity search
CREATE OR REPLACE FUNCTION search_similar_events(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    event_id UUID,
    similarity float,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    event_date TIMESTAMP WITH TIME ZONE,
    sport VARCHAR(50),
    league VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        1 - (ee.embedding <=> query_embedding) as similarity,
        e.home_team,
        e.away_team,
        e.event_date,
        e.sport,
        e.league
    FROM event_embeddings ee
    JOIN events e ON ee.event_id = e.id
    WHERE e.status = 'UPCOMING' 
        AND e.event_date > NOW()
        AND (1 - (ee.embedding <=> query_embedding)) > match_threshold
    ORDER BY ee.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Create helper function for keyword search
CREATE OR REPLACE FUNCTION search_events_by_keyword(
    search_query text,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    event_id UUID,
    rank float,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    event_date TIMESTAMP WITH TIME ZONE,
    sport VARCHAR(50),
    league VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        ts_rank(e.search_vector, plainto_tsquery('english', search_query)) as rank,
        e.home_team,
        e.away_team,
        e.event_date,
        e.sport,
        e.league
    FROM events e
    WHERE e.status = 'UPCOMING' 
        AND e.event_date > NOW()
        AND e.search_vector @@ plainto_tsquery('english', search_query)
    ORDER BY rank DESC, e.event_date ASC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE event_embeddings IS 'Stores vector embeddings of events for semantic search in RAG system';
COMMENT ON TABLE bet_embeddings IS 'Stores vector embeddings of user bets for personalized recommendations';
COMMENT ON COLUMN events.search_vector IS 'Full-text search vector for keyword-based event search';
COMMENT ON FUNCTION search_similar_events IS 'Performs vector similarity search on events using cosine distance';
COMMENT ON FUNCTION search_events_by_keyword IS 'Performs full-text keyword search on events';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON event_embeddings TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON bet_embeddings TO your_app_user;
-- GRANT EXECUTE ON FUNCTION search_similar_events TO your_app_user;
-- GRANT EXECUTE ON FUNCTION search_events_by_keyword TO your_app_user;
