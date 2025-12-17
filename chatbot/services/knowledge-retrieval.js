import pg from 'pg';
import dotenv from 'dotenv';
import { generateEmbedding } from './embeddings.js';

dotenv.config();

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

async function knowledgeVectorSearch(queryEmbedding, limit = 8, threshold = 0.25) {
  try {
    const embeddingStr = `[${queryEmbedding.join(',')}]`;

    const query = `
      SELECT
        kd.id AS document_id,
        kd.title AS document_title,
        kd.doc_type,
        kd.source,
        kc.id AS chunk_id,
        kc.content_text,
        kc.metadata,
        1 - (ke.embedding <=> $1::vector) AS similarity
      FROM knowledge_embeddings ke
      JOIN knowledge_chunks kc ON kc.id = ke.chunk_id
      JOIN knowledge_documents kd ON kd.id = kc.document_id
      WHERE (1 - (ke.embedding <=> $1::vector)) > $2
      ORDER BY ke.embedding <=> $1::vector
      LIMIT $3
    `;

    const { rows } = await pool.query(query, [embeddingStr, threshold, limit]);
    return rows;
  } catch {
    return [];
  }
}

async function knowledgeKeywordSearch(query, limit = 8) {
  try {
    const searchQuery = `
      SELECT
        kd.id AS document_id,
        kd.title AS document_title,
        kd.doc_type,
        kd.source,
        kc.id AS chunk_id,
        kc.content_text,
        kc.metadata,
        ts_rank(kc.search_vector, plainto_tsquery('english', $1)) AS rank
      FROM knowledge_chunks kc
      JOIN knowledge_documents kd ON kd.id = kc.document_id
      WHERE kc.search_vector @@ plainto_tsquery('english', $1)
      ORDER BY rank DESC, kc.updated_at DESC
      LIMIT $2
    `;

    const { rows } = await pool.query(searchQuery, [query, limit]);
    return rows;
  } catch {
    return [];
  }
}

export async function hybridKnowledgeSearch(query, limit = 5, k = 60) {
  const queryEmbedding = await generateEmbedding(query);
  const [vectorResults, keywordResults] = await Promise.all([
    knowledgeVectorSearch(queryEmbedding, 20, 0.25),
    knowledgeKeywordSearch(query, 20),
  ]);

  const merged = new Map();

  vectorResults.forEach((row, idx) => {
    merged.set(row.chunk_id, {
      ...row,
      vector_rank: idx + 1,
      keyword_rank: 999,
      vector_score: row.similarity || 0,
      keyword_score: 0,
    });
  });

  keywordResults.forEach((row, idx) => {
    if (merged.has(row.chunk_id)) {
      const existing = merged.get(row.chunk_id);
      existing.keyword_rank = idx + 1;
      existing.keyword_score = row.rank || 0;
    } else {
      merged.set(row.chunk_id, {
        ...row,
        vector_rank: 999,
        keyword_rank: idx + 1,
        vector_score: 0,
        keyword_score: row.rank || 0,
      });
    }
  });

  return Array.from(merged.values())
    .map(item => ({
      ...item,
      rrf_score: (1 / (k + item.vector_rank)) + (1 / (k + item.keyword_rank)),
    }))
    .sort((a, b) => b.rrf_score - a.rrf_score)
    .slice(0, limit);
}

async function close() {
  await pool.end();
}

process.on('SIGTERM', close);
process.on('SIGINT', close);
