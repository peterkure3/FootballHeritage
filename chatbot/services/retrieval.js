/**
 * Hybrid Retrieval Service for RAG System
 * Combines vector similarity search with keyword matching
 */

import pg from 'pg';
import { generateEmbedding } from './embeddings.js';
import dotenv from 'dotenv';

dotenv.config();

// Database connection pool
const pool = new pg.Pool({
    connectionString: process.env.DATABASE_URL,
    max: 20, // Higher for parallel queries
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

pool.on('connect', () => {
    console.log('✅ Retrieval service: Database connected');
});

pool.on('error', (err) => {
    console.error('❌ Retrieval service: Database error:', err);
});

/**
 * Vector similarity search using pgvector
 * @param {Array<number>} queryEmbedding - Query embedding vector
 * @param {number} limit - Maximum results to return
 * @param {number} threshold - Minimum similarity threshold (0-1)
 * @returns {Promise<Array>} Similar events
 */
async function vectorSearch(queryEmbedding, limit = 10, threshold = 0.3) {
    try {
        const embeddingStr = `[${queryEmbedding.join(',')}]`;

        const query = `
            SELECT 
                e.id, e.sport, e.league, e.home_team, e.away_team, e.event_date,
                e.moneyline_home, e.moneyline_away, e.point_spread,
                e.spread_home_odds, e.spread_away_odds, e.total_points,
                e.over_odds, e.under_odds, e.status,
                ee.content_text,
                1 - (ee.embedding <=> $1::vector) as similarity
            FROM event_embeddings ee
            JOIN events e ON ee.event_id = e.id
            WHERE e.status = 'UPCOMING' 
                AND e.event_date > NOW()
                AND (1 - (ee.embedding <=> $1::vector)) > $2
            ORDER BY ee.embedding <=> $1::vector
            LIMIT $3
        `;

        const result = await pool.query(query, [embeddingStr, threshold, limit]);
        return result.rows;
    } catch (error) {
        console.error('Vector search error:', error.message);
        return [];
    }
}

/**
 * Keyword search using PostgreSQL full-text search
 * @param {string} query - Search query
 * @param {number} limit - Maximum results to return
 * @returns {Promise<Array>} Matching events
 */
async function keywordSearch(query, limit = 10) {
    try {
        const searchQuery = `
            SELECT 
                id, sport, league, home_team, away_team, event_date,
                moneyline_home, moneyline_away, point_spread,
                spread_home_odds, spread_away_odds, total_points,
                over_odds, under_odds, status,
                ts_rank(search_vector, plainto_tsquery('english', $1)) as rank
            FROM events
            WHERE status = 'UPCOMING' 
                AND event_date > NOW()
                AND search_vector @@ plainto_tsquery('english', $1)
            ORDER BY rank DESC, event_date ASC
            LIMIT $2
        `;

        const result = await pool.query(searchQuery, [query, limit]);
        return result.rows;
    } catch (error) {
        console.error('Keyword search error:', error.message);
        return [];
    }
}

/**
 * Hybrid search: combines vector and keyword results using RRF
 * Reciprocal Rank Fusion (RRF) algorithm for result merging
 * @param {string} query - User query
 * @param {number} limit - Maximum results to return
 * @param {number} k - RRF constant (default: 60)
 * @returns {Promise<Array>} Merged and reranked results
 */
async function hybridSearch(query, limit = 5, k = 60) {
    const startTime = Date.now();

    try {
        // Generate query embedding
        const queryEmbedding = await generateEmbedding(query);

        // Run both searches in parallel
        const [vectorResults, keywordResults] = await Promise.all([
            vectorSearch(queryEmbedding, 20, 0.3), // Get top 20 from vector search
            keywordSearch(query, 20), // Get top 20 from keyword search
        ]);

        console.log(`🔍 Vector: ${vectorResults.length} results, Keyword: ${keywordResults.length} results`);

        // Merge results using RRF
        const merged = new Map();

        // Add vector results with semantic score
        vectorResults.forEach((row, idx) => {
            merged.set(row.id, {
                ...row,
                vector_score: row.similarity || 0,
                vector_rank: idx + 1,
                keyword_score: 0,
                keyword_rank: 999,
            });
        });

        // Add/update with keyword results
        keywordResults.forEach((row, idx) => {
            if (merged.has(row.id)) {
                const existing = merged.get(row.id);
                existing.keyword_score = row.rank || 0;
                existing.keyword_rank = idx + 1;
            } else {
                merged.set(row.id, {
                    ...row,
                    vector_score: 0,
                    vector_rank: 999,
                    keyword_score: row.rank || 0,
                    keyword_rank: idx + 1,
                });
            }
        });

        // Calculate RRF score and rerank
        const reranked = Array.from(merged.values())
            .map(item => ({
                ...item,
                rrf_score: (1 / (k + item.vector_rank)) + (1 / (k + item.keyword_rank)),
            }))
            .sort((a, b) => b.rrf_score - a.rrf_score)
            .slice(0, limit);

        const elapsed = Date.now() - startTime;
        console.log(`✅ Hybrid search: ${reranked.length} results in ${elapsed}ms`);

        return reranked;
    } catch (error) {
        console.error('Hybrid search error:', error.message);
        
        // Fallback to keyword-only search
        console.log('⚠️  Falling back to keyword-only search');
        const fallbackResults = await keywordSearch(query, limit);
        return fallbackResults.map((item, idx) => ({
            ...item,
            rrf_score: 1 / (k + idx + 1),
            vector_score: 0,
            keyword_score: item.rank || 0,
        }));
    }
}

/**
 * Search for events by specific teams
 * @param {Array<string>} teams - Team names
 * @param {number} limit - Maximum results
 * @returns {Promise<Array>} Matching events
 */
async function searchByTeams(teams, limit = 10) {
    try {
        if (teams.length === 0) {
            return [];
        }

        const teamConditions = teams.map((_, idx) => 
            `(LOWER(home_team) LIKE $${idx + 1} OR LOWER(away_team) LIKE $${idx + 1})`
        ).join(' OR ');

        const query = `
            SELECT 
                id, sport, league, home_team, away_team, event_date,
                moneyline_home, moneyline_away, point_spread,
                spread_home_odds, spread_away_odds, total_points,
                over_odds, under_odds, status
            FROM events
            WHERE status = 'UPCOMING' 
                AND event_date > NOW()
                AND (${teamConditions})
            ORDER BY event_date ASC
            LIMIT $${teams.length + 1}
        `;

        const values = [...teams.map(team => `%${team.toLowerCase()}%`), limit];
        const result = await pool.query(query, values);

        return result.rows;
    } catch (error) {
        console.error('Team search error:', error.message);
        return [];
    }
}

/**
 * Get upcoming events (no search, just list)
 * @param {number} limit - Maximum results
 * @param {string} sport - Filter by sport (optional)
 * @returns {Promise<Array>} Upcoming events
 */
async function getUpcomingEvents(limit = 10, sport = null) {
    try {
        const query = `
            SELECT 
                id, sport, league, home_team, away_team, event_date,
                moneyline_home, moneyline_away, point_spread,
                spread_home_odds, spread_away_odds, total_points,
                over_odds, under_odds, status
            FROM events
            WHERE status = 'UPCOMING' 
                AND event_date > NOW()
                ${sport ? 'AND LOWER(sport) = LOWER($2)' : ''}
            ORDER BY event_date ASC
            LIMIT $1
        `;

        const params = sport ? [limit, sport] : [limit];
        const result = await pool.query(query, params);

        return result.rows;
    } catch (error) {
        console.error('Get upcoming events error:', error.message);
        return [];
    }
}

/**
 * Search events by date range
 * @param {Date} startDate - Start date
 * @param {Date} endDate - End date
 * @param {number} limit - Maximum results
 * @returns {Promise<Array>} Events in date range
 */
async function searchByDateRange(startDate, endDate, limit = 50) {
    try {
        const query = `
            SELECT 
                id, sport, league, home_team, away_team, event_date,
                moneyline_home, moneyline_away, point_spread,
                spread_home_odds, spread_away_odds, total_points,
                over_odds, under_odds, status
            FROM events
            WHERE status = 'UPCOMING' 
                AND event_date BETWEEN $1 AND $2
            ORDER BY event_date ASC
            LIMIT $3
        `;

        const result = await pool.query(query, [startDate, endDate, limit]);
        return result.rows;
    } catch (error) {
        console.error('Date range search error:', error.message);
        return [];
    }
}

/**
 * Get retrieval statistics
 * @returns {Promise<object>} Retrieval stats
 */
async function getRetrievalStats() {
    try {
        const query = `
            SELECT 
                COUNT(*) as total_events,
                COUNT(CASE WHEN status = 'UPCOMING' THEN 1 END) as upcoming_events,
                COUNT(DISTINCT sport) as sports_count,
                COUNT(DISTINCT league) as leagues_count,
                MIN(event_date) as earliest_event,
                MAX(event_date) as latest_event
            FROM events
            WHERE event_date > NOW()
        `;

        const result = await pool.query(query);
        return result.rows[0];
    } catch (error) {
        console.error('Retrieval stats error:', error.message);
        return null;
    }
}

/**
 * Close database connection
 */
async function close() {
    await pool.end();
    console.log('✅ Retrieval service: Database connection closed');
}

// Export functions
export {
    vectorSearch,
    keywordSearch,
    hybridSearch,
    searchByTeams,
    getUpcomingEvents,
    searchByDateRange,
    getRetrievalStats,
    close,
};

// Handle process termination
process.on('SIGTERM', close);
process.on('SIGINT', close);
