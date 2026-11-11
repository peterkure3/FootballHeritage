import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { predictionService } from '../../services/predictionService';
import { slug, type Sport } from '../../heritage/data';
import { array, record, text, number, type RecordData } from '../../heritage/services';
import ForecastCard from './ForecastCard';
import BookmakerGrid from './BookmakerGrid';
import Pagination from './Pagination';
import QueryState from './QueryState';

function fixtureFromSnapshot(row: RecordData, markets: RecordData[]) {
  const prediction = Object.hasOwn(row, 'prediction') ? row.prediction === null ? null : record(row.prediction) : row;
  const quotes = markets.filter(market => market.fixture_id === row.fixture_id && market.market === 'h2h').map(market => {
    const legs = record(market.legs);
    const prices = Object.fromEntries(Object.entries(legs).map(([key, leg]) => [key, number(record(leg).decimal_odds)]));
    const times = Object.values(legs).map(leg => Date.parse(text(record(leg).observed_at)));
    const oldest = Math.min(...times);
    const complete = ['home_win', 'away_win'].every(outcome => Object.hasOwn(legs, outcome));
    const fresh = complete && times.every(time => Number.isFinite(time) && time < Date.parse(text(row.kickoff)) && Date.now() - time >= 0 && Date.now() - time <= 30 * 60 * 1000);
    return {bookmaker: text(market.bookmaker), observed_at: Number.isFinite(oldest) ? new Date(oldest).toISOString() : '', prices,
      fair_probabilities: record(market.fair_probabilities),
      fresh: fresh && Object.values(prices).every(price => price !== null && price > 1)};
  });
  return {match_id: text(row.fixture_id), competition: text(row.competition), home_team: text(row.home_team), away_team: text(row.away_team), kickoff: text(row.kickoff),
    prediction_unavailable: prediction === null,
    prediction: prediction ? {status: text(prediction.status), winner: text(prediction.winner), model_version: text(prediction.model_version),
      probabilities: record(prediction.probabilities), generated_at: text(prediction.generated_at), feature_cutoff: text(prediction.feature_cutoff)} : null,
    market: {state: quotes.some(quote => quote.fresh) ? 'current' : quotes.length ? 'unverified_or_stale' : 'missing', quotes, comparisons: []},
    settlement_rule: text(row.settlement_rule).replaceAll('_', ' ') || 'Not supplied by the source',
    market_note: "Each bookmaker retains the source's margin-removed probabilities. The grid uses its captured prices; no missing quote is filled from another fixture.",
    freshness_policy: 'Existing intelligence snapshot; bookmaker quotes expire after 30 minutes'};
}

export default function SportPredictionFeed({sport, comparison = false}: {sport: Sport; comparison?: boolean}) {
  const [competition, setCompetition] = useState('');
  const [date, setDate] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = comparison ? 20 : 6;
  const query = useQuery({queryKey: ['betting-intel', slug(sport)], queryFn: async ({signal}) => {
    const data = record(await predictionService.getBettingIntel(slug(sport), signal));
    if (data.sport !== slug(sport)) throw new Error(`The source did not return ${sport} predictions.`);
    return data;
  }, staleTime: 30000, refetchInterval: 60000, retry: 1});
  const scoped = query.data?.sport === slug(sport) ? query.data : undefined;
  const scheduled = array(Array.isArray(scoped?.fixtures) ? scoped.fixtures : scoped?.predictions).map(record)
    .filter(row => row.sport === slug(sport));
  const competitions = [...new Set(scheduled.map(row => text(row.competition)).filter(Boolean))];
  const markets = array(scoped?.devigged_odds).map(record);
  const fixtures = scheduled.filter(row => (!competition || row.competition === competition) && (!date || text(row.kickoff).slice(0,10) === date))
    .map(row => fixtureFromSnapshot(row, markets));
  const currentPage = Math.min(page, Math.max(1, Math.ceil(fixtures.length / pageSize)));
  const visible = fixtures.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const twoWay = !fixtures.some(fixture => Object.hasOwn(fixture.prediction?.probabilities ?? {}, 'draw'));
  return <section aria-label="Upcoming predictions">
    <div className="pd-toolbar"><div className="pd-filters">
      <label>Competition<select value={competition} onChange={event => {setCompetition(event.target.value); setPage(1);}}>
        <option value="">All competitions</option>{competitions.map(item => <option key={item}>{item}</option>)}</select></label>
      <label>Kickoff date (UTC)<input type="date" value={date} onChange={event => {setDate(event.target.value); setPage(1);}} /></label>
    </div><button className="pd-button pd-button-outline" disabled={query.isFetching} onClick={() => void query.refetch()}><RefreshCw size={15} />{query.isFetching ? 'Refreshing…' : 'Refresh'}</button></div>
    <QueryState query={query} loading={`Loading ${sport} fixture predictions…`} failure="Could not refresh predictions">{() => fixtures.length ? <>
      <div className="pd-feed-summary"><span><strong>{fixtures.length}</strong> upcoming fixtures</span><span>{sport} · source model versions shown per fixture</span></div>
      {comparison ? <BookmakerGrid fixtures={visible} twoWay={twoWay} freshnessPolicy="30-minute intelligence snapshot policy" /> : <div className="pd-forecast-grid">{visible.map(fixture => <ForecastCard key={fixture.match_id} fixture={fixture} />)}</div>}
      <Pagination page={currentPage} total={fixtures.length} pageSize={pageSize} busy={query.isFetching} onPage={setPage} />
    </> : <div className="pd-empty"><h2>No upcoming {sport} fixtures match these filters.</h2><p>No forecasts from another sport are substituted.</p></div>}</QueryState>
  </section>;
}
