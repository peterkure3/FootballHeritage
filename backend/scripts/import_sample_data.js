/**
 * Sample Data Importer
 * 
 * Imports sample sports events for testing
 * Run with: node scripts/import_sample_data.js
 */

const { Pool } = require('pg');

// Database configuration
const pool = new Pool({
  host: process.env.DATABASE_HOST || 'localhost',
  port: process.env.DATABASE_PORT || 5432,
  database: process.env.DATABASE_NAME || 'football_heritage',
  user: process.env.DATABASE_USER || 'postgres',
  password: process.env.DATABASE_PASSWORD || 'jumpman13',
});

// Sample events data
const sampleEvents = [
  {
    sport: 'SOCCER',
    league: 'Premier League',
    home_team: 'Manchester United',
    away_team: 'Liverpool',
    event_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000), // 2 days from now
    status: 'UPCOMING',
    moneyline_home: 2.10,
    moneyline_away: 3.40,
    point_spread: -1.5,
    spread_home_odds: 1.90,
    spread_away_odds: 1.90,
    total_points: 2.5,
    over_odds: 1.85,
    under_odds: 1.95,
  },
  {
    sport: 'SOCCER',
    league: 'Premier League',
    home_team: 'Arsenal',
    away_team: 'Chelsea',
    event_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000), // 3 days from now
    status: 'UPCOMING',
    moneyline_home: 1.75,
    moneyline_away: 4.20,
    point_spread: -0.5,
    spread_home_odds: 1.95,
    spread_away_odds: 1.85,
    total_points: 3.5,
    over_odds: 1.90,
    under_odds: 1.90,
  },
  {
    sport: 'BASKETBALL',
    league: 'NBA',
    home_team: 'Los Angeles Lakers',
    away_team: 'Golden State Warriors',
    event_date: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000), // 1 day from now
    status: 'UPCOMING',
    moneyline_home: 1.95,
    moneyline_away: 1.85,
    point_spread: -3.5,
    spread_home_odds: 1.90,
    spread_away_odds: 1.90,
    total_points: 220.5,
    over_odds: 1.90,
    under_odds: 1.90,
  },
  {
    sport: 'BASKETBALL',
    league: 'NBA',
    home_team: 'Boston Celtics',
    away_team: 'Miami Heat',
    event_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000),
    status: 'UPCOMING',
    moneyline_home: 1.70,
    moneyline_away: 2.15,
    point_spread: -5.5,
    spread_home_odds: 1.90,
    spread_away_odds: 1.90,
    total_points: 215.5,
    over_odds: 1.85,
    under_odds: 1.95,
  },
  {
    sport: 'TENNIS',
    league: 'ATP Tour',
    home_team: 'Novak Djokovic',
    away_team: 'Carlos Alcaraz',
    event_date: new Date(Date.now() + 4 * 24 * 60 * 60 * 1000),
    status: 'UPCOMING',
    moneyline_home: 1.85,
    moneyline_away: 1.95,
    point_spread: null,
    spread_home_odds: null,
    spread_away_odds: null,
    total_points: 3.5,
    over_odds: 1.90,
    under_odds: 1.90,
  },
  {
    sport: 'NFL',
    league: 'NFL',
    home_team: 'Kansas City Chiefs',
    away_team: 'Buffalo Bills',
    event_date: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000),
    status: 'UPCOMING',
    moneyline_home: 1.80,
    moneyline_away: 2.00,
    point_spread: -2.5,
    spread_home_odds: 1.90,
    spread_away_odds: 1.90,
    total_points: 47.5,
    over_odds: 1.90,
    under_odds: 1.90,
  },
  {
    sport: 'SOCCER',
    league: 'La Liga',
    home_team: 'Real Madrid',
    away_team: 'Barcelona',
    event_date: new Date(Date.now() + 6 * 24 * 60 * 60 * 1000),
    status: 'UPCOMING',
    moneyline_home: 2.20,
    moneyline_away: 3.10,
    point_spread: -1.0,
    spread_home_odds: 1.90,
    spread_away_odds: 1.90,
    total_points: 3.0,
    over_odds: 1.95,
    under_odds: 1.85,
  },
  {
    sport: 'SOCCER',
    league: 'Champions League',
    home_team: 'Bayern Munich',
    away_team: 'Paris Saint-Germain',
    event_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
    status: 'UPCOMING',
    moneyline_home: 1.90,
    moneyline_away: 3.80,
    point_spread: -0.5,
    spread_home_odds: 1.90,
    spread_away_odds: 1.90,
    total_points: 2.5,
    over_odds: 1.80,
    under_odds: 2.00,
  },
];

/**
 * Import sample events
 */
async function importSampleData() {
  console.log('🚀 Starting sample data import...\n');
  
  let imported = 0;
  let updated = 0;
  let errors = 0;

  for (const event of sampleEvents) {
    try {
      // Check if event already exists
      const existingEvent = await pool.query(
        `SELECT id FROM events 
         WHERE home_team = $1 AND away_team = $2 AND league = $3`,
        [event.home_team, event.away_team, event.league]
      );

      if (existingEvent.rows.length > 0) {
        // Update existing event
        await pool.query(
          `UPDATE events SET
            event_date = $1,
            status = $2,
            moneyline_home = $3,
            moneyline_away = $4,
            point_spread = $5,
            spread_home_odds = $6,
            spread_away_odds = $7,
            total_points = $8,
            over_odds = $9,
            under_odds = $10,
            updated_at = NOW()
          WHERE id = $11`,
          [
            event.event_date,
            event.status,
            event.moneyline_home,
            event.moneyline_away,
            event.point_spread,
            event.spread_home_odds,
            event.spread_away_odds,
            event.total_points,
            event.over_odds,
            event.under_odds,
            existingEvent.rows[0].id,
          ]
        );
        console.log(`🔄 Updated: ${event.home_team} vs ${event.away_team}`);
        updated++;
      } else {
        // Insert new event
        await pool.query(
          `INSERT INTO events (
            sport, league, home_team, away_team, event_date, status,
            moneyline_home, moneyline_away, point_spread,
            spread_home_odds, spread_away_odds, total_points,
            over_odds, under_odds, created_at, updated_at
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), NOW())`,
          [
            event.sport,
            event.league,
            event.home_team,
            event.away_team,
            event.event_date,
            event.status,
            event.moneyline_home,
            event.moneyline_away,
            event.point_spread,
            event.spread_home_odds,
            event.spread_away_odds,
            event.total_points,
            event.over_odds,
            event.under_odds,
          ]
        );
        console.log(`✅ Imported: ${event.home_team} vs ${event.away_team}`);
        imported++;
      }
    } catch (error) {
      console.error(`❌ Error importing ${event.home_team} vs ${event.away_team}:`, error.message);
      errors++;
    }
  }

  console.log('\n====================================================');
  console.log('📈 Import Summary:');
  console.log(`   ✅ Imported: ${imported}`);
  console.log(`   🔄 Updated: ${updated}`);
  console.log(`   ❌ Errors: ${errors}`);
  console.log('====================================================');
  console.log('✨ Import completed successfully!\n');
}

// Run the import
importSampleData()
  .then(() => {
    pool.end();
    process.exit(0);
  })
  .catch((error) => {
    console.error('❌ Import failed:', error.message);
    pool.end();
    process.exit(1);
  });
