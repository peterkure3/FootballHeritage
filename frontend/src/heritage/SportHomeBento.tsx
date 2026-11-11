import { ArrowUpRight, CalendarDays, ChartNoAxesCombined, Clock3, Sparkles, Trophy, ArrowRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { FeatureLink as Link, FeatureVisible } from '../features/FeatureAccess';
import { useFeatures } from '../features/useFeatures';
import { hasFeature } from '../features/policy';
import { predictionService } from '../services/predictionService';
import { slug, sportPath, type Sport } from './data';
import { array, record, text, number, formatDate, type Fixture, type RecordData } from './services';
import { isFinal, useSportSchedule } from './sportScheduleData';
import { TeamMark } from './SportSchedule';
import { ModelLabel } from './BettingIntelTable';
import './betting-intel.css';
import './sport-centre.css';

function FeaturedGame({ game }: { game: Fixture }) {
  const final = isFinal(game);
  const when = new Date(game.date);
  return <Link className="sc-featured-game" to={`${sportPath(game.sport, 'schedule')}?date=${when.toISOString().slice(0, 10)}&match=${encodeURIComponent(game.id)}`}>
    <span className="sc-game-meta"><span>{game.league || game.sport}</span><span>{final ? 'FINAL' : when.toLocaleDateString('en', { month: 'short', day: 'numeric', timeZone: 'UTC' })}</span></span>
    <span className={`sc-team-line ${final && game.awayScore! > game.homeScore! ? 'sc-winner' : ''}`}><TeamMark name={game.away} /><span>{game.away}</span>{final && <b>{game.awayScore}</b>}</span>
    <span className={`sc-team-line ${final && game.homeScore! > game.awayScore! ? 'sc-winner' : ''}`}><TeamMark name={game.home} /><span>{game.home}</span>{final && <b>{game.homeScore}</b>}</span>
    {!final && <span className="sc-game-time"><Clock3 size={12} />{when.toLocaleTimeString('en', { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })} UTC <ArrowUpRight size={14} /></span>}
  </Link>;
}

function GamePanel({ sport, games, final, loading, error, retry }: {
  sport: Sport; games: Fixture[]; final?: boolean; loading: boolean; error: Error | null; retry: () => void;
}) {
  return <section className={`fh-card sc-bento-card ${final ? 'sc-results-panel' : 'sc-games-panel'}`} aria-label={final ? 'Featured results' : 'Featured games'}>
    <header className="sc-panel-head"><h3>{final ? <Trophy size={17} /> : <CalendarDays size={17} />}{final ? 'Featured results' : 'Featured games'}</h3>
      <Link to={`${sportPath(sport, 'schedule')}${final ? `?date=${games[0]?.date.slice(0, 10) || ''}` : ''}`} aria-label={final ? 'View all results' : 'View full schedule'}><ArrowUpRight size={18} /></Link></header>
    {loading ? <div className="sc-panel-empty" role="status">Loading {final ? 'results' : 'games'}…</div> : error ? <div className="sc-panel-empty" role="alert"><p>Could not load {final ? 'results' : 'games'}.</p><button className="sc-text-button" onClick={retry}>Try again</button></div> : games.length ?
      <div className="sc-featured-list">{games.map(game => <FeaturedGame game={game} key={game.id} />)}</div> : <div className="sc-panel-empty"><span>{final ? 'No verified finals available.' : 'No upcoming games available.'}</span><Link to={sportPath(sport, 'schedule')}>Check the schedule <ArrowRight size={14} /></Link></div>}
  </section>;
}

function Spotlight({ item, sport, stale }: { item: RecordData | undefined; sport: Sport; stale: boolean }) {
  const pick = record(item?.top_pick);
  const summary = record(item?.summary);
  const probability = number(pick.probability);
  const hasPick = !stale && !!pick.selection && probability !== null && probability >= 0 && probability <= 1;
  const selection = pick.selection === 'home_win' ? text(pick.home_team) : pick.selection === 'away_win' ? text(pick.away_team) : pick.selection === 'draw' ? 'Draw' : '';
  return <>
    <div className="sc-spotlight-label"><span><Sparkles size={15} /> MODEL SPOTLIGHT</span><span className="sc-experimental">{pick.model_status === 'active' ? 'Active model' : 'Model estimate'}</span></div>
    {hasPick ? <>
      <p className="sc-spotlight-match">{text(pick.competition) || sport} <span>·</span> {formatDate(text(pick.kickoff))}</p>
      <div className="sc-spotlight-main"><div><h3>{selection || 'Model selection'}</h3><p>{pick.selection === 'draw' ? 'Predicted draw' : 'Predicted winner'}</p></div>
        <div className="sc-probability-ring" style={{ background: `conic-gradient(var(--fh-accent-soft) ${probability * 360}deg, var(--fh-muted) 0deg)` }} role="img" aria-label={`${(probability * 100).toFixed(1)} percent model probability`}><div><strong>{(probability * 100).toFixed(0)}<small>%</small></strong><span>PROBABILITY</span></div></div></div>
      <div className="sc-spotlight-teams"><span>{text(pick.away_team)}</span><i>at</i><span>{text(pick.home_team)}</span></div>
      <div className="sc-model-note"><ModelLabel row={pick} /></div>
    </> : <div className="sc-no-pick"><ChartNoAxesCombined size={38} strokeWidth={1} /><h3>{stale ? 'Forecast needs a refresh.' : 'The next forecast starts here.'}</h3><p>{stale ? 'The saved snapshot is out of date. Open predictions for the latest available evidence.' : `No eligible ${sport} model pick is available in this snapshot.`}</p></div>}
    <div className="sc-spotlight-metrics">{[['predictions', 'Model forecasts'], ['ev_bets', 'EV estimates'], ['arbitrage', 'Arbitrage signals']].map(([key, label]) => <div key={key}><strong>{number(summary[key])?.toLocaleString() ?? '—'}</strong><span>{label}</span></div>)}</div>
    <Link className="fh-button sc-spotlight-action" to={sportPath(sport, 'predictions')}>View {sport} predictions <ArrowUpRight size={18} /></Link>
    <p className="sc-spotlight-disclaimer">Model estimates, not guaranteed outcomes. Candidate models are experimental.</p>
  </>;
}

export default function SportHomeBento({ sport }: { sport: Sport }) {
  const features = useFeatures();
  const intelligence = hasFeature(features.data, 'intelligence');
  const query = useQuery({ queryKey: ['betting-intel', 'overview'], queryFn: ({ signal }) => predictionService.getBettingIntel(undefined, signal), staleTime: 30000, enabled: intelligence, retry: 1 });
  const payload = record(query.data);
  const item = array(payload.sports).map(record).find(row => row.sport === slug(sport));
  const schedule = useSportSchedule(sport);
  const games = schedule.data?.items ?? [];
  const now = Date.now();
  const upcoming = games.filter(game => !isFinal(game) && Date.parse(game.date) > now && !['CANCELLED', 'CANCELED', 'POSTPONED'].includes(game.status.toUpperCase())).slice(0, 2);
  const results = games.filter(isFinal).slice().reverse().slice(0, 2);
  return <section className={`sc-home bi-inline-summary ${intelligence ? '' : 'sc-no-intel'}`} aria-label={`${sport} match centre`}>
    <header className="sc-home-heading"><div><span className="sc-kicker">YOUR MATCHDAY, AT A GLANCE</span><h2>{sport} AI picks & predictions</h2></div><Link to={`/ai-picks/intelligence/${slug(sport)}`}>View intelligence <ArrowUpRight size={16} /></Link></header>
    <div className="sc-bento">
      <FeatureVisible feature="intelligence"><section className="fh-card sc-bento-card sc-spotlight" aria-label="Prediction spotlight">
        {query.isPending ? <div className="sc-no-pick" role="status"><Sparkles size={30} /><h3>Loading model insights…</h3></div> : query.error ? <div className="sc-no-pick" role="alert"><h3>Predictions are unavailable.</h3><p>The saved intelligence could not be loaded.</p><button className="sc-spotlight-action" onClick={() => void query.refetch()}>Retry predictions <ArrowRight size={16} /></button></div> : <Spotlight item={item} sport={sport} stale={payload.snapshot_status === 'stale'} />}
      </section></FeatureVisible>
      <GamePanel sport={sport} games={upcoming} loading={schedule.isPending} error={schedule.error} retry={() => void schedule.refetch()} />
      <GamePanel sport={sport} games={results} final loading={schedule.isPending} error={schedule.error} retry={() => void schedule.refetch()} />
    </div>
    <div className="sc-home-foot"><span><span className="sc-dot" />{text(payload.snapshot_at) ? `Snapshot collected ${formatDate(text(payload.snapshot_at))}` : 'Saved schedules and verified final scores'} · Not a live score feed</span><Link to={sportPath(sport, 'schedule')}>Open {sport} schedule <ArrowRight size={15} /></Link></div>
    {schedule.data?.issues.map(issue => <p className="sc-source-note" key={issue}>{issue}</p>)}
  </section>;
}
