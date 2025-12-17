import pg from 'pg';
import dotenv from 'dotenv';
import { generateEmbedding } from './embeddings.js';

dotenv.config();

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

function chunkText(text, { maxChars = 1800, overlapChars = 200 } = {}) {
  const normalized = String(text || '').replace(/\r\n/g, '\n').trim();
  if (!normalized) return [];

  const paragraphs = normalized.split(/\n{2,}/).map(p => p.trim()).filter(Boolean);
  const chunks = [];
  let current = '';

  for (const p of paragraphs) {
    if (!current) {
      current = p;
      continue;
    }

    if ((current.length + 2 + p.length) <= maxChars) {
      current = `${current}\n\n${p}`;
      continue;
    }

    chunks.push(current);
    const overlap = current.slice(Math.max(0, current.length - overlapChars));
    current = overlap ? `${overlap}\n\n${p}` : p;
  }

  if (current) chunks.push(current);
  return chunks;
}

async function upsertDocument({ source, title, docType, sourceId, metadata }) {
  const query = `
    INSERT INTO knowledge_documents (source, title, doc_type, source_id, metadata)
    VALUES ($1, $2, $3, $4, $5)
    ON CONFLICT (source, doc_type, source_id)
    DO UPDATE SET
      title = EXCLUDED.title,
      metadata = EXCLUDED.metadata,
      updated_at = CURRENT_TIMESTAMP
    RETURNING id
  `;

  const { rows } = await pool.query(query, [
    source,
    title,
    docType,
    sourceId,
    metadata ? JSON.stringify(metadata) : null,
  ]);

  return rows[0].id;
}

async function replaceChunks(documentId, chunks, { baseMetadata = {} } = {}) {
  await pool.query('DELETE FROM knowledge_chunks WHERE document_id = $1', [documentId]);

  const inserted = [];
  for (let i = 0; i < chunks.length; i++) {
    const contentText = chunks[i];
    const metadata = { ...baseMetadata, chunk_index: i, title: baseMetadata.title };

    const { rows } = await pool.query(
      `
        INSERT INTO knowledge_chunks (document_id, chunk_index, content_text, metadata)
        VALUES ($1, $2, $3, $4)
        RETURNING id
      `,
      [documentId, i, contentText, JSON.stringify(metadata)]
    );

    inserted.push({ id: rows[0].id, contentText, metadata });
  }

  return inserted;
}

async function embedChunk(chunk) {
  const embedding = await generateEmbedding(chunk.contentText);
  const embeddingStr = `[${embedding.join(',')}]`;

  await pool.query(
    `
      INSERT INTO knowledge_embeddings (chunk_id, embedding, content_text, metadata)
      VALUES ($1, $2, $3, $4)
      ON CONFLICT (chunk_id)
      DO UPDATE SET
        embedding = EXCLUDED.embedding,
        content_text = EXCLUDED.content_text,
        metadata = EXCLUDED.metadata,
        updated_at = CURRENT_TIMESTAMP
    `,
    [chunk.id, embeddingStr, chunk.contentText, JSON.stringify(chunk.metadata || {})]
  );
}

async function buildLeagueDocuments({ source = 'derived', limitLeagues = null } = {}) {
  const leaguesQuery = `
    SELECT sport, league, COUNT(*)::int AS total_events,
           COUNT(*) FILTER (WHERE status = 'UPCOMING')::int AS upcoming_events,
           MIN(event_date) AS first_event_date,
           MAX(event_date) AS last_event_date
    FROM events
    GROUP BY sport, league
    ORDER BY sport, league
    ${limitLeagues ? `LIMIT ${Number(limitLeagues)}` : ''}
  `;

  const { rows: leagues } = await pool.query(leaguesQuery);

  const results = [];
  for (const l of leagues) {
    const upcomingQuery = `
      SELECT home_team, away_team, event_date, status,
             moneyline_home, moneyline_away, point_spread, total_points
      FROM events
      WHERE sport = $1 AND league = $2 AND status = 'UPCOMING' AND event_date > NOW()
      ORDER BY event_date ASC
      LIMIT 10
    `;

    const { rows: upcoming } = await pool.query(upcomingQuery, [l.sport, l.league]);

    const upcomingLines = upcoming.map((e) => {
      const date = new Date(e.event_date).toISOString();
      return `- ${date}: ${e.home_team} vs ${e.away_team} | ML ${e.moneyline_home}/${e.moneyline_away} | Spread ${e.point_spread} | Total ${e.total_points}`;
    });

    const title = `${l.sport} / ${l.league} overview`;
    const content = [
      `${title}`,
      `Total events: ${l.total_events}`,
      `Upcoming events: ${l.upcoming_events}`,
      `Date range in DB: ${l.first_event_date?.toISOString?.() || l.first_event_date} → ${l.last_event_date?.toISOString?.() || l.last_event_date}`,
      `Upcoming schedule (first 10):`,
      upcomingLines.length ? upcomingLines.join('\n') : '- none',
    ].join('\n');

    const docId = await upsertDocument({
      source,
      title,
      docType: 'league_overview',
      sourceId: `${l.sport}::${l.league}`,
      metadata: { sport: l.sport, league: l.league, title },
    });

    const chunks = chunkText(content);
    const insertedChunks = await replaceChunks(docId, chunks, {
      baseMetadata: { sport: l.sport, league: l.league, title },
    });

    results.push({ docId, insertedChunksCount: insertedChunks.length });
  }

  return results;
}

async function buildTeamDocuments({ source = 'derived', limitTeams = null } = {}) {
  const teamsQuery = `
    WITH t AS (
      SELECT sport, league, home_team AS team FROM events
      UNION ALL
      SELECT sport, league, away_team AS team FROM events
    )
    SELECT sport, league, team,
           COUNT(*)::int AS appearances,
           COUNT(*) FILTER (WHERE team IS NOT NULL)::int AS non_null
    FROM t
    WHERE team IS NOT NULL AND team <> ''
    GROUP BY sport, league, team
    ORDER BY sport, league, appearances DESC, team
    ${limitTeams ? `LIMIT ${Number(limitTeams)}` : ''}
  `;

  const { rows: teams } = await pool.query(teamsQuery);

  const results = [];
  for (const t of teams) {
    const nextGamesQuery = `
      SELECT home_team, away_team, event_date, league, sport, status,
             moneyline_home, moneyline_away, point_spread, total_points
      FROM events
      WHERE sport = $1 AND league = $2
        AND status = 'UPCOMING' AND event_date > NOW()
        AND (home_team = $3 OR away_team = $3)
      ORDER BY event_date ASC
      LIMIT 10
    `;

    const { rows: nextGames } = await pool.query(nextGamesQuery, [t.sport, t.league, t.team]);

    const lines = nextGames.map((e) => {
      const opp = e.home_team === t.team ? e.away_team : e.home_team;
      const side = e.home_team === t.team ? 'home' : 'away';
      const date = new Date(e.event_date).toISOString();
      return `- ${date}: vs ${opp} (${side}) | ML ${e.moneyline_home}/${e.moneyline_away} | Spread ${e.point_spread} | Total ${e.total_points}`;
    });

    const title = `${t.team} (${t.sport} / ${t.league}) overview`;
    const content = [
      `${title}`,
      `Appearances in DB: ${t.appearances}`,
      `Upcoming games (next 10):`,
      lines.length ? lines.join('\n') : '- none',
    ].join('\n');

    const docId = await upsertDocument({
      source,
      title,
      docType: 'team_overview',
      sourceId: `${t.sport}::${t.league}::${t.team}`,
      metadata: { sport: t.sport, league: t.league, team: t.team, title },
    });

    const chunks = chunkText(content);
    const insertedChunks = await replaceChunks(docId, chunks, {
      baseMetadata: { sport: t.sport, league: t.league, team: t.team, title },
    });

    results.push({ docId, insertedChunksCount: insertedChunks.length });
  }

  return results;
}

export async function ingestKnowledge({
  limitLeagues = null,
  limitTeams = 200,
  embed = true,
} = {}) {
  const start = Date.now();

  const leagueDocs = await buildLeagueDocuments({ limitLeagues });
  const teamDocs = await buildTeamDocuments({ limitTeams });

  let embeddedChunks = 0;

  if (embed) {
    const { rows: chunks } = await pool.query(
      `
        SELECT kc.id, kc.content_text, kc.metadata
        FROM knowledge_chunks kc
        LEFT JOIN knowledge_embeddings ke ON ke.chunk_id = kc.id
        WHERE ke.id IS NULL
        ORDER BY kc.created_at ASC
      `
    );

    for (const c of chunks) {
      await embedChunk({ id: c.id, contentText: c.content_text, metadata: c.metadata || {} });
      embeddedChunks++;
      await new Promise(r => setTimeout(r, 80));
    }
  }

  return {
    leagueDocuments: leagueDocs.length,
    teamDocuments: teamDocs.length,
    embeddedChunks,
    elapsedMs: Date.now() - start,
  };
}

async function close() {
  await pool.end();
}

process.on('SIGTERM', close);
process.on('SIGINT', close);

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = new Set(process.argv.slice(2));
  const embed = !args.has('--no-embed');
  const limitTeams = (() => {
    const idx = process.argv.indexOf('--limit-teams');
    if (idx >= 0 && process.argv[idx + 1]) return Number(process.argv[idx + 1]);
    return 200;
  })();

  ingestKnowledge({ limitTeams, embed })
    .then((result) => {
      console.log(JSON.stringify(result, null, 2));
      process.exit(0);
    })
    .catch((e) => {
      console.error(e);
      process.exit(1);
    });
}
