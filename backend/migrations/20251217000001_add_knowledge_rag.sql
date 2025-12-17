CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    source_id TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source, doc_type, source_id)
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content_text TEXT NOT NULL,
    metadata JSONB,
    search_vector tsvector,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS knowledge_chunks_document_id_idx
ON knowledge_chunks(document_id);

CREATE INDEX IF NOT EXISTS knowledge_chunks_search_idx
ON knowledge_chunks USING GIN(search_vector);

CREATE OR REPLACE FUNCTION knowledge_chunks_search_trigger()
RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.content_text, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.metadata->>'title', '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.metadata->>'sport', '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.metadata->>'league', '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.metadata->>'home_team', '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.metadata->>'away_team', '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS knowledge_chunks_search_update ON knowledge_chunks;
CREATE TRIGGER knowledge_chunks_search_update
    BEFORE INSERT OR UPDATE ON knowledge_chunks
    FOR EACH ROW EXECUTE FUNCTION knowledge_chunks_search_trigger();

UPDATE knowledge_chunks
SET search_vector =
    setweight(to_tsvector('english', COALESCE(content_text, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(metadata->>'title', '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(metadata->>'sport', '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(metadata->>'league', '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(metadata->>'home_team', '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(metadata->>'away_team', '')), 'C')
WHERE search_vector IS NULL;

CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID NOT NULL REFERENCES knowledge_chunks(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    content_text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chunk_id)
);

CREATE INDEX IF NOT EXISTS knowledge_embeddings_embedding_idx
ON knowledge_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS knowledge_embeddings_chunk_id_idx
ON knowledge_embeddings(chunk_id);

CREATE OR REPLACE FUNCTION update_knowledge_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_knowledge_documents_updated_at_trigger ON knowledge_documents;
CREATE TRIGGER update_knowledge_documents_updated_at_trigger
    BEFORE UPDATE ON knowledge_documents
    FOR EACH ROW EXECUTE FUNCTION update_knowledge_updated_at();

DROP TRIGGER IF EXISTS update_knowledge_chunks_updated_at_trigger ON knowledge_chunks;
CREATE TRIGGER update_knowledge_chunks_updated_at_trigger
    BEFORE UPDATE ON knowledge_chunks
    FOR EACH ROW EXECUTE FUNCTION update_knowledge_updated_at();

DROP TRIGGER IF EXISTS update_knowledge_embeddings_updated_at_trigger ON knowledge_embeddings;
CREATE TRIGGER update_knowledge_embeddings_updated_at_trigger
    BEFORE UPDATE ON knowledge_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_knowledge_updated_at();
