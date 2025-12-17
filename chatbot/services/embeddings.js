/**
 * Embeddings Service for RAG System
 * Generates and manages vector embeddings for events and bets
 */

import { GoogleGenerativeAI } from '@google/generative-ai';
import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

// Initialize Gemini AI
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// Database connection pool
const pool = new pg.Pool({
    connectionString: process.env.DATABASE_URL,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 10000,
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

pool.on('connect', () => {
    console.log('✅ Embeddings service: Database connected');
});

pool.on('error', (err) => {
    console.error('❌ Embeddings service: Database error:', err);
});

/**
 * Format event data into text for embedding
 * @param {object} event - Event object from database
 * @returns {string} Formatted text
 */
function formatEventForEmbedding(event) {
    const date = new Date(event.event_date).toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });

    return `
${event.sport} ${event.league} Game
${event.home_team} vs ${event.away_team}
Date: ${date}
Moneyline: ${event.home_team} ${event.moneyline_home}, ${event.away_team} ${event.moneyline_away}
Point Spread: ${event.point_spread} (Home ${event.spread_home_odds}, Away ${event.spread_away_odds})
Total Points: ${event.total_points} (Over ${event.over_odds}, Under ${event.under_odds})
Status: ${event.status}
    `.trim();
}

/**
 * Generate embedding for text using Gemini
 * @param {string} text - Text to embed
 * @returns {Promise<Array<number>>} Embedding vector (768 dimensions)
 */
async function generateEmbedding(text) {
    try {
        const model = genAI.getGenerativeModel({ model: 'text-embedding-004' });
        const result = await model.embedContent(text);
        return result.embedding.values;
    } catch (error) {
        console.error('Embedding generation error:', error.message);
        throw error;
    }
}

/**
 * Embed a single event and store in database
 * @param {object} event - Event object
 * @returns {Promise<object>} Created embedding record
 */
async function embedEvent(event) {
    try {
        // Format event text
        const contentText = formatEventForEmbedding(event);

        // Generate embedding
        const embedding = await generateEmbedding(contentText);

        // Convert embedding array to PostgreSQL vector format
        const embeddingStr = `[${embedding.join(',')}]`;

        // Store in database (upsert)
        const query = `
            INSERT INTO event_embeddings (event_id, embedding, content_text, metadata)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (event_id) 
            DO UPDATE SET
                embedding = $2,
                content_text = $3,
                metadata = $4,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, event_id, created_at, updated_at
        `;

        const metadata = {
            sport: event.sport,
            league: event.league,
            teams: [event.home_team, event.away_team],
            event_date: event.event_date,
            status: event.status,
        };

        const result = await pool.query(query, [
            event.id,
            embeddingStr,
            contentText,
            JSON.stringify(metadata),
        ]);

        return result.rows[0];
    } catch (error) {
        console.error(`Failed to embed event ${event.id}:`, error.message);
        throw error;
    }
}

/**
 * Embed all upcoming events
 * @param {number} limit - Maximum number of events to embed (default: all)
 * @returns {Promise<object>} Summary of embedding operation
 */
async function embedAllEvents(limit = null) {
    const startTime = Date.now();
    let embedded = 0;
    let failed = 0;
    let skipped = 0;

    try {
        // Fetch upcoming events
        const query = `
            SELECT 
                e.id, e.sport, e.league, e.home_team, e.away_team, e.event_date,
                e.moneyline_home, e.moneyline_away, e.point_spread,
                e.spread_home_odds, e.spread_away_odds, e.total_points,
                e.over_odds, e.under_odds, e.status
            FROM events e
            WHERE e.status = 'UPCOMING' AND e.event_date > NOW()
            ORDER BY e.event_date ASC
            ${limit ? `LIMIT ${limit}` : ''}
        `;

        const { rows: events } = await pool.query(query);
        console.log(`📊 Found ${events.length} upcoming events to embed`);

        // Process events with rate limiting
        for (const event of events) {
            try {
                await embedEvent(event);
                embedded++;
                console.log(`✅ [${embedded}/${events.length}] Embedded: ${event.home_team} vs ${event.away_team}`);

                // Rate limiting: wait 100ms between requests (10 req/sec)
                await new Promise(resolve => setTimeout(resolve, 100));
            } catch (error) {
                failed++;
                console.error(`❌ [${embedded + failed}/${events.length}] Failed: ${event.home_team} vs ${event.away_team}`);
            }
        }

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
        const summary = {
            total: events.length,
            embedded,
            failed,
            skipped,
            elapsed: `${elapsed}s`,
        };

        console.log('\n📈 Embedding Summary:');
        console.log(`   Total Events: ${summary.total}`);
        console.log(`   ✅ Embedded: ${summary.embedded}`);
        console.log(`   ❌ Failed: ${summary.failed}`);
        console.log(`   ⏱️  Time: ${summary.elapsed}`);

        return summary;
    } catch (error) {
        console.error('Batch embedding error:', error.message);
        throw error;
    }
}

/**
 * Embed events that don't have embeddings yet
 * @returns {Promise<object>} Summary of embedding operation
 */
async function embedMissingEvents() {
    try {
        // Find events without embeddings
        const query = `
            SELECT 
                e.id, e.sport, e.league, e.home_team, e.away_team, e.event_date,
                e.moneyline_home, e.moneyline_away, e.point_spread,
                e.spread_home_odds, e.spread_away_odds, e.total_points,
                e.over_odds, e.under_odds, e.status
            FROM events e
            LEFT JOIN event_embeddings ee ON e.id = ee.event_id
            WHERE e.status = 'UPCOMING' 
                AND e.event_date > NOW()
                AND ee.id IS NULL
            ORDER BY e.event_date ASC
        `;

        const { rows: events } = await pool.query(query);
        
        if (events.length === 0) {
            console.log('✅ All events already have embeddings');
            return { total: 0, embedded: 0, failed: 0, skipped: 0 };
        }

        console.log(`📊 Found ${events.length} events without embeddings`);

        let embedded = 0;
        let failed = 0;

        for (const event of events) {
            try {
                await embedEvent(event);
                embedded++;
                console.log(`✅ [${embedded}/${events.length}] Embedded: ${event.home_team} vs ${event.away_team}`);
                await new Promise(resolve => setTimeout(resolve, 100));
            } catch (error) {
                failed++;
                console.error(`❌ Failed: ${event.home_team} vs ${event.away_team}`);
            }
        }

        return {
            total: events.length,
            embedded,
            failed,
            skipped: 0,
        };
    } catch (error) {
        console.error('Missing events embedding error:', error.message);
        throw error;
    }
}

/**
 * Delete embeddings for finished or cancelled events
 * @returns {Promise<number>} Number of embeddings deleted
 */
async function cleanupOldEmbeddings() {
    try {
        const query = `
            DELETE FROM event_embeddings
            WHERE event_id IN (
                SELECT id FROM events
                WHERE status IN ('FINISHED', 'CANCELLED')
                    OR event_date < NOW() - INTERVAL '7 days'
            )
            RETURNING id
        `;

        const result = await pool.query(query);
        const deleted = result.rowCount;

        console.log(`🗑️  Cleaned up ${deleted} old embeddings`);
        return deleted;
    } catch (error) {
        console.error('Cleanup error:', error.message);
        throw error;
    }
}

/**
 * Get embedding statistics
 * @returns {Promise<object>} Embedding stats
 */
async function getEmbeddingStats() {
    try {
        const query = `
            SELECT 
                COUNT(DISTINCT ee.event_id) as events_with_embeddings,
                COUNT(e.id) as total_upcoming_events,
                COUNT(DISTINCT ee.event_id)::float / NULLIF(COUNT(e.id), 0) * 100 as coverage_percent
            FROM events e
            LEFT JOIN event_embeddings ee ON e.id = ee.event_id
            WHERE e.status = 'UPCOMING' AND e.event_date > NOW()
        `;

        const result = await pool.query(query);
        return result.rows[0];
    } catch (error) {
        console.error('Stats error:', error.message);
        return {
            events_with_embeddings: 0,
            total_upcoming_events: 0,
            coverage_percent: 0,
        };
    }
}

/**
 * Close database connection
 */
async function close() {
    await pool.end();
    console.log('✅ Embeddings service: Database connection closed');
}

// Export functions
export {
    embedEvent,
    embedAllEvents,
    embedMissingEvents,
    cleanupOldEmbeddings,
    getEmbeddingStats,
    generateEmbedding,
    close,
};

// Handle process termination
process.on('SIGTERM', close);
process.on('SIGINT', close);

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    console.log('🚀 Starting embedding generation...\n');
    
    embedAllEvents()
        .then(summary => {
            console.log('\n✅ Embedding generation complete!');
            process.exit(0);
        })
        .catch(err => {
            console.error('\n❌ Embedding generation failed:', err);
            process.exit(1);
        });
}
