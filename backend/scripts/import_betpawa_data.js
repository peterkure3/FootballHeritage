/**
 * BetPawa Data Importer
 * 
 * Fetches live sports data from BetPawa API and imports it into the database
 * Run with: node scripts/import_betpawa_data.js
 */

const https = require('https');
const { Pool } = require('pg');

// Database configuration
const pool = new Pool({
  host: process.env.DATABASE_HOST || 'localhost',
  port: process.env.DATABASE_PORT || 5432,
  database: process.env.DATABASE_NAME || 'football_heritage',
  user: process.env.DATABASE_USER || 'postgres',
  password: process.env.DATABASE_PASSWORD || 'jumpman13',
});

// BetPawa API configuration
const BETPAWA_API_URL = 'www.betpawa.ug';
const BETPAWA_PATH = '/api/sportsbook/v3/events/lists/by-queries?q=%7B%22queries%22%3A%5B%7B%22query%22%3A%7B%22eventType%22%3A%22UPCOMING%22%2C%22categories%22%3A%5B%222%22%5D%2C%22zones%22%3A%7B%7D%2C%22boosted%22%3Atrue%7D%2C%22skip%22%3A0%2C%22take%22%3A%224%22%7D%2C%7B%22query%22%3A%7B%22eventType%22%3A%22UPCOMING%22%2C%22categories%22%3A%5B%222%22%5D%2C%22zones%22%3A%7B%7D%7D%2C%22skip%22%3A0%2C%22sort%22%3A%7B%22popularity%22%3A%22DESC%22%7D%2C%22take%22%3A%2210%22%7D%2C%7B%22query%22%3A%7B%22eventType%22%3A%22LIVE%22%2C%22categories%22%3A%5B%222%22%2C%223%22%2C%22452%22%5D%2C%22zones%22%3A%7B%7D%7D%2C%22skip%22%3A0%2C%22sort%22%3A%7B%22popularity%22%3A%22DESC%22%7D%2C%22take%22%3A%224%22%7D%2C%7B%22query%22%3A%7B%22eventType%22%3A%22UPCOMING%22%2C%22categories%22%3A%5B%22101%22%5D%2C%22zones%22%3A%7B%7D%7D%2C%22skip%22%3A0%2C%22take%22%3A%223%22%7D%2C%7B%22query%22%3A%7B%22eventType%22%3A%22UPCOMING%22%2C%22categories%22%3A%5B%223%22%5D%2C%22zones%22%3A%7B%7D%7D%2C%22skip%22%3A0%2C%22take%22%3A%223%22%7D%2C%7B%22query%22%3A%7B%22eventType%22%3A%22UPCOMING%22%2C%22categories%22%3A%5B%22452%22%5D%2C%22zones%22%3A%7B%7D%7D%2C%22skip%22%3A0%2C%22take%22%3A%223%22%7D%5D%7D';

// Sport category mapping
const SPORT_CATEGORIES = {
  '2': 'SOCCER',
  '3': 'BASKETBALL',
  '101': 'TENNIS',
  '452': 'ESPORTS',
};

/**
 * Fetch data from BetPawa API
 */
function fetchBetPawaData() {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: BETPAWA_API_URL,
      path: BETPAWA_PATH,
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'x-pawa-language': 'en',
        'x-pawa-brand': 'betpawa-uganda',
        'deviceType': 'web',
        'VueJs': 'true',
        'Referer': 'https://www.betpawa.ug/',
      },
    };

    const req = https.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          const jsonData = JSON.parse(data);
          resolve(jsonData);
        } catch (error) {
          reject(new Error('Failed to parse JSON response'));
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    req.end();
  });
}

/**
 * Map BetPawa event to our database schema
 */
function mapEvent(event, sport) {
  const homeTeam = event.competitors?.[0]?.name || 'Unknown';
  const awayTeam = event.competitors?.[1]?.name || 'Unknown';
  const eventDate = new Date(event.startTime);
  const league = event.competition?.name || 'Unknown League';
  
  // Extract odds
  const moneylineMarket = event.markets?.find(m => m.name === '1X2' || m.name === 'Match Winner');
  const moneylineHome = moneylineMarket?.selections?.[0]?.odds || null;
  const moneylineAway = moneylineMarket?.selections?.[1]?.odds || null;

  const spreadMarket = event.markets?.find(m => m.name === 'Handicap');
  const pointSpread = spreadMarket?.selections?.[0]?.handicap || null;
  const spreadHomeOdds = spreadMarket?.selections?.[0]?.odds || null;
  const spreadAwayOdds = spreadMarket?.selections?.[1]?.odds || null;

  const totalMarket = event.markets?.find(m => m.name === 'Over/Under');
  const totalPoints = totalMarket?.selections?.[0]?.handicap || null;
  const overOdds = totalMarket?.selections?.[0]?.odds || null;
  const underOdds = totalMarket?.selections?.[1]?.odds || null;

  return {
    sport,
    league,
    homeTeam,
    awayTeam,
    eventDate,
    status: event.status === 'LIVE' ? 'LIVE' : 'UPCOMING',
    moneylineHome,
    moneylineAway,
    pointSpread,
    spreadHomeOdds,
    spreadAwayOdds,
    totalPoints,
    overOdds,
    underOdds,
    externalId: event.id,
  };
}

/**
 * Insert or update event in database
 */
async function upsertEvent(client, event) {
  const query = `
    INSERT INTO events (
      sport, league, home_team, away_team, event_date, status,
      moneyline_home, moneyline_away,
      point_spread, spread_home_odds, spread_away_odds,
      total_points, over_odds, under_odds,
      external_id, external_source
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, 'betpawa')
    ON CONFLICT (external_id, external_source) 
    DO UPDATE SET
      status = EXCLUDED.status,
      moneyline_home = EXCLUDED.moneyline_home,
      moneyline_away = EXCLUDED.moneyline_away,
      point_spread = EXCLUDED.point_spread,
      spread_home_odds = EXCLUDED.spread_home_odds,
      spread_away_odds = EXCLUDED.spread_away_odds,
      total_points = EXCLUDED.total_points,
      over_odds = EXCLUDED.over_odds,
      under_odds = EXCLUDED.under_odds,
      updated_at = NOW()
    RETURNING id
  `;

  const values = [
    event.sport,
    event.league,
    event.homeTeam,
    event.awayTeam,
    event.eventDate,
    event.status,
    event.moneylineHome,
    event.moneylineAway,
    event.pointSpread,
    event.spreadHomeOdds,
    event.spreadAwayOdds,
    event.totalPoints,
    event.overOdds,
    event.underOdds,
    event.externalId,
  ];

  try {
    const result = await client.query(query, values);
    return result.rows[0].id;
  } catch (error) {
    console.error('Error upserting event:', error.message);
    console.error('Event data:', event);
    throw error;
  }
}

/**
 * Main import function
 */
async function importData() {
  console.log('🚀 Starting BetPawa data import...');
  
  const client = await pool.connect();
  
  try {
    console.log('📡 Fetching data from BetPawa API...');
    const data = await fetchBetPawaData();
    
    if (!data || !data.results) {
      throw new Error('Invalid API response structure');
    }

    let totalImported = 0;
    let totalUpdated = 0;
    let totalErrors = 0;

    // Process each query result
    for (let i = 0; i < data.results.length; i++) {
      const result = data.results[i];
      const categoryId = data.queries?.[i]?.query?.categories?.[0];
      const sport = SPORT_CATEGORIES[categoryId] || 'UNKNOWN';

      console.log(`\n📊 Processing ${sport} events...`);

      if (!result.events || result.events.length === 0) {
        console.log(`   No events found for ${sport}`);
        continue;
      }

      for (const betpawaEvent of result.events) {
        try {
          const mappedEvent = mapEvent(betpawaEvent, sport);
          const eventId = await upsertEvent(client, mappedEvent);
          
          if (eventId) {
            totalImported++;
            console.log(`   ✅ ${mappedEvent.homeTeam} vs ${mappedEvent.awayTeam}`);
          } else {
            totalUpdated++;
          }
        } catch (error) {
          totalErrors++;
          console.error(`   ❌ Error processing event: ${error.message}`);
        }
      }
    }

    console.log('\n' + '='.repeat(60));
    console.log('📈 Import Summary:');
    console.log(`   ✅ Imported: ${totalImported}`);
    console.log(`   🔄 Updated: ${totalUpdated}`);
    console.log(`   ❌ Errors: ${totalErrors}`);
    console.log('='.repeat(60));
    console.log('✨ Import completed successfully!\n');

  } catch (error) {
    console.error('❌ Import failed:', error.message);
    console.error(error.stack);
    process.exit(1);
  } finally {
    client.release();
    await pool.end();
  }
}

// Run the import
if (require.main === module) {
  importData();
}

module.exports = { importData, fetchBetPawaData };
