/**
 * Genkit Chat Flow
 * 
 * This module implements the core AI chatbot logic using Google's Genkit framework.
 * It queries the PostgreSQL database for sports data and odds, then uses Gemini 1.5 Flash
 * to generate intelligent betting advice.
 */

import { genkit } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';
import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

// ============================================================================
// GENKIT INITIALIZATION
// ============================================================================

const ai = genkit({
  plugins: [
    googleAI({
      apiKey: process.env.GEMINI_API_KEY,
    }),
  ],
  model: 'googleai/gemini-1.5-flash',
});

// ============================================================================
// DATABASE CONNECTION POOL
// ============================================================================

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

pool.on('connect', () => {
  console.log('✅ Database connection established');
});

pool.on('error', (err) => {
  console.error('❌ Unexpected database error:', err);
});

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function extractTeams(prompt) {
  const lowerPrompt = prompt.toLowerCase();
  const teams = [];
  
  const teamPatterns = [
    'chiefs', 'bills', '49ers', 'niners', 'cowboys', 'eagles', 'dolphins',
    'lions', 'buccaneers', 'bucs', 'ravens', 'bengals', 'packers', 'vikings',
    'jets', 'patriots', 'rams', 'seahawks', 'cardinals', 'browns', 'steelers',
    'lakers', 'celtics', 'warriors', 'heat', 'bucks', 'nets', 'suns',
    'barcelona', 'real madrid', 'manchester united', 'liverpool', 'chelsea',
  ];
  
  teamPatterns.forEach(team => {
    if (lowerPrompt.includes(team)) {
      teams.push(team);
    }
  });
  
  return teams;
}

async function queryEvents(teams) {
  if (teams.length === 0) {
    const query = `
      SELECT 
        id, sport, league, home_team, away_team, event_date,
        moneyline_home, moneyline_away, point_spread,
        spread_home_odds, spread_away_odds, total_points,
        over_odds, under_odds, status
      FROM events
      WHERE status = 'UPCOMING' AND event_date > NOW()
      ORDER BY event_date ASC
      LIMIT 5
    `;
    
    const result = await pool.query(query);
    return result.rows;
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
    LIMIT 10
  `;
  
  const values = teams.map(team => `%${team}%`);
  const result = await pool.query(query, values);
  return result.rows;
}

async function getUserBettingStats(userId) {
  try {
    const query = `
      SELECT 
        COUNT(*) as total_bets,
        COUNT(CASE WHEN status = 'WON' THEN 1 END) as wins,
        COUNT(CASE WHEN status = 'LOST' THEN 1 END) as losses,
        AVG(amount) as avg_bet_amount,
        SUM(CASE WHEN status = 'WON' THEN potential_win - amount ELSE 0 END) as total_profit
      FROM bets
      WHERE user_id = $1
    `;
    
    const result = await pool.query(query, [userId]);
    return result.rows[0];
  } catch (error) {
    console.error('Error fetching user stats:', error);
    return null;
  }
}

function formatEventsForPrompt(events) {
  if (events.length === 0) {
    return 'No upcoming events found.';
  }
  
  return events.map((event, idx) => {
    const date = new Date(event.event_date).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
    
    return `
Event ${idx + 1}:
- Match: ${event.home_team} vs ${event.away_team}
- League: ${event.league} (${event.sport})
- Date: ${date}
- Moneyline: ${event.home_team} ${event.moneyline_home}, ${event.away_team} ${event.moneyline_away}
- Spread: ${event.point_spread} (Home ${event.spread_home_odds}, Away ${event.spread_away_odds})
- Total: ${event.total_points} (Over ${event.over_odds}, Under ${event.under_odds})
    `.trim();
  }).join('\n\n');
}

// ============================================================================
// GENKIT CHAT FLOW
// ============================================================================

export const chatFlow = ai.defineFlow(
  {
    name: 'chatFlow',
    inputSchema: {
      type: 'object',
      properties: {
        prompt: { type: 'string' },
        userId: { type: 'string' },
      },
      required: ['prompt', 'userId'],
    },
    outputSchema: {
      type: 'object',
      properties: {
        response: { type: 'string' },
        confidence: { type: 'number' },
        data: { type: 'object' },
      },
    },
  },
  async ({ prompt, userId }) => {
    try {
      // Step 1: Extract teams from prompt
      const teams = extractTeams(prompt);
      console.log(`Extracted teams: ${teams.join(', ') || 'none'}`);

      // Step 2: Query database for events
      const events = await queryEvents(teams);
      console.log(`Found ${events.length} matching events`);

      // Step 3: Get user betting history
      const userStats = await getUserBettingStats(userId);

      // Step 4: Format data for AI prompt
      const eventsData = formatEventsForPrompt(events);
      
      const userContext = userStats ? `
User Betting History:
- Total Bets: ${userStats.total_bets}
- Win Rate: ${userStats.total_bets > 0 ? ((userStats.wins / userStats.total_bets) * 100).toFixed(1) : 0}%
- Average Bet: $${parseFloat(userStats.avg_bet_amount || 0).toFixed(2)}
- Total Profit/Loss: $${parseFloat(userStats.total_profit || 0).toFixed(2)}
      `.trim() : 'No betting history available.';

      // Step 5: Create AI prompt
      const systemPrompt = `You are an expert sports betting advisor for Football Heritage, a responsible gambling platform. 

Your role:
1. Analyze odds and provide betting recommendations
2. Calculate implied probabilities from American odds
3. Identify value bets where your probability estimate exceeds implied odds
4. Promote responsible gambling (suggest reasonable bet sizes, warn about risks)
5. Be concise, friendly, and data-driven

Important:
- American odds format: Negative = favorite (e.g., -150 means bet $150 to win $100), Positive = underdog (e.g., +130 means bet $100 to win $130)
- Implied probability from American odds: Negative = |odds| / (|odds| + 100), Positive = 100 / (odds + 100)
- Only recommend bets with positive expected value
- Always remind users to bet responsibly and within their limits
- If no relevant data is available, suggest checking back later or exploring other games

Current Sports Data:
${eventsData}

${userContext}

User Question: ${prompt}

Provide a helpful, actionable response with specific betting recommendations if applicable.`;

      // Step 6: Call Gemini AI
      const { text } = await ai.generate({
        model: 'googleai/gemini-1.5-flash',
        prompt: systemPrompt,
        config: {
          temperature: 0.7,
          maxOutputTokens: 500,
          topK: 40,
          topP: 0.95,
        },
      });

      // Step 7: Calculate confidence score (simple heuristic)
      let confidence = 0.5; // Default medium confidence
      if (events.length > 0) confidence += 0.2;
      if (teams.length > 0) confidence += 0.2;
      if (userStats && userStats.total_bets > 5) confidence += 0.1;
      confidence = Math.min(confidence, 1.0);

      return {
        response: text,
        confidence: parseFloat(confidence.toFixed(2)),
        data: {
          eventsFound: events.length,
          teamsMatched: teams,
          userStats: userStats ? {
            totalBets: parseInt(userStats.total_bets),
            winRate: userStats.total_bets > 0 
              ? parseFloat(((userStats.wins / userStats.total_bets) * 100).toFixed(1))
              : 0,
          } : null,
        },
      };

    } catch (error) {
      console.error('Chat flow error:', error);
      
      // Return user-friendly error
      return {
        response: "I'm having trouble accessing the betting data right now. Please try again in a moment, or contact support if the issue persists.",
        confidence: 0,
        data: { error: error.message },
      };
    }
  }
);

// Export for use in index.js
export default chatFlow;
