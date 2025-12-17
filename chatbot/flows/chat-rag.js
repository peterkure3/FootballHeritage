/**
 * RAG-Enhanced Chat Flow
 * Integrates hybrid search, caching, and query routing
 */

import { GoogleGenerativeAI } from '@google/generative-ai';
import pg from 'pg';
import dotenv from 'dotenv';
import { getCached, setCached } from '../services/cache.js';
import { hybridSearch, getUpcomingEvents } from '../services/retrieval.js';
import { hybridKnowledgeSearch } from '../services/knowledge-retrieval.js';
import { routeQuery, getCacheTTL } from '../services/router.js';

dotenv.config();

// Initialize Google Generative AI
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

const pool = new pg.Pool({
    connectionString: process.env.DATABASE_URL,
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
});

/**
 * Get user betting context
 */
async function getUserContext(userId) {
    try {
        const { rows } = await pool.query(
            `SELECT 
                COUNT(*) as total_bets,
                COUNT(CASE WHEN status = 'WON' THEN 1 END) as wins,
                AVG(amount) as avg_bet,
                SUM(CASE WHEN status = 'WON' THEN potential_win - amount ELSE 0 END) as profit
            FROM bets
            WHERE user_id = $1`,
            [userId]
        );
        return rows[0];
    } catch (error) {
        console.error('Error fetching user context:', error);
        return null;
    }
}

/**
 * Format events for LLM context
 */
function formatContext(events, userStats) {
    const eventsText = events
        .map((e, i) => {
            const relevance = e.rrf_score ? `${(e.rrf_score * 100).toFixed(0)}%` : 'N/A';
            const date = new Date(e.event_date).toLocaleString();
            
            return `
Event ${i + 1} (Relevance: ${relevance}):
- ${e.home_team} vs ${e.away_team}
- ${e.league} (${e.sport})
- Date: ${date}
- Moneyline: ${e.home_team} ${e.moneyline_home}, ${e.away_team} ${e.moneyline_away}
- Spread: ${e.point_spread} (Home ${e.spread_home_odds}, Away ${e.spread_away_odds})
- Total: ${e.total_points} (Over ${e.over_odds}, Under ${e.under_odds})
            `.trim();
        })
        .join('\n\n');

    const userText = userStats && userStats.total_bets > 0 ? `
User Stats:
- Total Bets: ${userStats.total_bets}
- Win Rate: ${((userStats.wins / userStats.total_bets) * 100).toFixed(1)}%
- Avg Bet: $${parseFloat(userStats.avg_bet || 0).toFixed(2)}
- Profit: $${parseFloat(userStats.profit || 0).toFixed(2)}
    `.trim() : 'No betting history available.';

    return { eventsText, userText };
}

function formatKnowledgeContext(chunks) {
    if (!chunks || chunks.length === 0) {
        return 'No additional knowledge context available.';
    }

    return chunks
        .map((c, i) => {
            const relevance = c.rrf_score ? `${(c.rrf_score * 100).toFixed(0)}%` : 'N/A';
            const title = c.document_title || c.metadata?.title || 'Untitled';
            const docType = c.doc_type || 'unknown';
            return `
Knowledge ${i + 1} (Relevance: ${relevance}):
- Title: ${title}
- Type: ${docType}
- Snippet: ${String(c.content_text || '').slice(0, 600)}
            `.trim();
        })
        .join('\n\n');
}

/**
 * RAG-enhanced chat flow
 */
export async function ragChatFlow({ prompt, userId }) {
    const startTime = Date.now();

    try {
        // Step 1: Route query
        const routing = routeQuery(prompt);
        console.log(`🎯 Intent: ${routing.intent} (${(routing.confidence * 100).toFixed(0)}%)`);

        // Step 2: Check cache
        const cached = await getCached(prompt, userId, { intent: routing.intent });
        if (cached) {
            console.log(`⚡ Cache HIT - returning in ${Date.now() - startTime}ms`);
            return {
                ...cached,
                latency: Date.now() - startTime,
                cached: true,
            };
        }

        // Step 3: Retrieve relevant events
        let events = [];
        try {
            if (routing.context.hasTeams || routing.context.hasSports) {
                events = await hybridSearch(prompt, 5);
            } else {
                events = await getUpcomingEvents(5);
            }
        } catch (error) {
            console.error('Retrieval error:', error.message);
            // Fallback to simple query
            events = await getUpcomingEvents(5);
        }

        // Step 3b: Retrieve relevant knowledge
        let knowledge = [];
        try {
            knowledge = await hybridKnowledgeSearch(prompt, 4);
        } catch (error) {
            console.error('Knowledge retrieval error:', error.message);
            knowledge = [];
        }

        // Step 4: Get user context
        const userStats = await getUserContext(userId);

        // Step 5: Build context
        const { eventsText, userText } = formatContext(events, userStats);
        const knowledgeText = formatKnowledgeContext(knowledge);

        async function callGeminiWithRetry(payload, { maxAttempts = 3 } = {}) {
            let lastError;
            for (let attempt = 1; attempt <= maxAttempts; attempt++) {
                try {
                    const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${process.env.GEMINI_API_KEY}`;

                    const apiResponse = await fetch(apiUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });

                    if (apiResponse.ok) {
                        return apiResponse.json();
                    }

                    const retryAfterHeader = apiResponse.headers.get('retry-after');
                    const retryAfterMs = retryAfterHeader
                        ? Math.max(0, parseFloat(retryAfterHeader) * 1000)
                        : null;

                    let errorBody;
                    try {
                        errorBody = await apiResponse.json();
                    } catch {
                        errorBody = await apiResponse.text();
                    }

                    const err = new Error(`Gemini API error: ${apiResponse.status} ${apiResponse.statusText}`);
                    err.status = apiResponse.status;
                    err.body = errorBody;

                    // Retry only on rate limiting / transient errors
                    if (apiResponse.status === 429 || apiResponse.status >= 500) {
                        lastError = err;

                        if (attempt < maxAttempts) {
                            const base = retryAfterMs ?? (250 * Math.pow(2, attempt - 1));
                            const jitter = Math.floor(Math.random() * 150);
                            const delayMs = Math.min(5000, base + jitter);
                            console.warn(`⚠️  Gemini ${apiResponse.status} on attempt ${attempt}/${maxAttempts}. Retrying in ${delayMs}ms`);
                            await new Promise(r => setTimeout(r, delayMs));
                            continue;
                        }
                    }

                    throw err;
                } catch (e) {
                    lastError = e;
                    // Network errors: retry
                    if (attempt < maxAttempts) {
                        const delayMs = Math.min(5000, 250 * Math.pow(2, attempt - 1) + Math.floor(Math.random() * 150));
                        console.warn(`⚠️  Gemini call failed on attempt ${attempt}/${maxAttempts}. Retrying in ${delayMs}ms: ${e.message}`);
                        await new Promise(r => setTimeout(r, delayMs));
                        continue;
                    }
                }
            }
            throw lastError;
        }

        // Step 6: Generate response
        const systemPrompt = `You are an expert sports betting advisor for Football Heritage.

Your role:
1. Analyze odds and provide betting recommendations
2. Calculate implied probabilities from American odds
3. Identify value bets where probability exceeds implied odds
4. Promote responsible gambling

Context:
${eventsText}

Additional Knowledge Context:
${knowledgeText}

${userText}

User Question: ${prompt}

Provide a concise, actionable response (max 200 words).`;

        const apiData = await callGeminiWithRetry({
            contents: [{ parts: [{ text: systemPrompt }] }],
            generationConfig: {
                temperature: 0.7,
                maxOutputTokens: 300,
                topK: 40,
                topP: 0.95,
            },
        });
        const text = apiData.candidates[0].content.parts[0].text;

        const response = {
            response: text,
            confidence: routing.confidence + (events.length > 0 ? 0.2 : 0),
            latency: Date.now() - startTime,
            cached: false,
            data: {
                intent: routing.intent,
                eventsFound: events.length,
                knowledgeFound: knowledge.length,
                userStats: userStats && userStats.total_bets > 0 ? {
                    totalBets: parseInt(userStats.total_bets),
                    winRate: parseFloat(((userStats.wins / userStats.total_bets) * 100).toFixed(1)),
                } : null,
            },
        };

        // Step 7: Cache response
        const ttl = getCacheTTL(routing);
        await setCached(prompt, userId, response, { intent: routing.intent }, ttl);

        console.log(`✅ Response generated in ${response.latency}ms`);
        return response;

    } catch (error) {
        console.error('RAG chat error:', error);

        if (error?.status === 429) {
            return {
                response: "I'm getting rate-limited by the AI provider right now. Please wait ~30–60 seconds and try again.",
                confidence: 0,
                latency: Date.now() - startTime,
                cached: false,
                data: { error: error.message, status: error.status, body: error.body },
            };
        }
        return {
            response: "I'm having trouble processing your request. Please try again.",
            confidence: 0,
            latency: Date.now() - startTime,
            cached: false,
            data: { error: error.message, status: error?.status, body: error?.body },
        };
    }
}
