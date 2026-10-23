import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, NavLink, useParams } from 'react-router-dom';
import { ArrowUpRight, RefreshCw, Sparkles } from 'lucide-react';
import AppShell from './AppShell';
import { array, record, text, formatDate, type RecordData } from './services';
import { DataState } from './ui';
import { predictionService } from '../services/predictionService';
import type { Sport } from './data';
import MarketTable, { ModelLabel } from './BettingIntelTable';
import { percent as pct, selectionName as selection, metric } from './bettingIntelFormat';
import './betting-intel.css';

const sportLabels: Record<string, Sport> = {
  football: 'Football', nba: 'NBA', nfl: 'NFL', wnba: 'WNBA', ncaab: 'NCAAB', 'college-football': 'College Football',
};
const views: Record<string, { title: string; key: string; description: string }> = {
  summary: { title: 'Summary', key: 'ai_picks', description: 'Your sport’s model picks, predictions and market signals in one place.' },
  predictions: { title: 'Predictions', key: 'predictions', description: 'Model probabilities for upcoming games. Candidate forecasts are experimental.' },
  'devigged-odds': { title: 'De-vigged odds', key: 'devigged_odds', description: 'Bookmaker implied probabilities with the margin removed proportionally. These are market estimates.' },
  'ev-bets': { title: 'EV bets', key: 'ev_bets', description: 'Positive gross expected value estimates. The probability source is shown for every price.' },
  'player-props': { title: 'Player props', key: 'player_props', description: 'Matched over/under quotes for the same player, statistic and line. No player prediction model is claimed.' },
  arbitrage: { title: 'Arbitrage', key: 'arbitrage', description: 'Complete cross-book price combinations. Returns are theoretical before costs; execution is unverified.' },
};
function Provenance({ data }: { data: RecordData }) {
  const errors = array(data.source_errors);
  const states: Record<string,string> = {current:'Snapshot available',partial:'Partial coverage',stale:'Snapshot needs refresh'};
  return <div className="bi-provenance" role="status">
    <strong>{states[text(data.snapshot_status)]}</strong>
    <span>Collected {formatDate(text(data.snapshot_at))}. Quotes expire after 30 minutes.</span>
    {errors.length > 0 && <details><summary>{errors.length} source or forecast issue{errors.length === 1 ? '' : 's'}</summary>
      <ul>{errors.map((raw, i) => { const error = record(raw); return <li key={i}>{text(error.sport) || text(error.source)}: {text(error.reason)}</li>; })}</ul>
    </details>}
  </div>;
}
function QueryState({ query }: { query: { isLoading: boolean; error: Error | null; refetch: () => unknown } }) {
  if (!query.isLoading && !query.error) return null;
  return <DataState loading={query.isLoading} error={query.error} retry={() => void query.refetch()} />;
}
function PickPreview({ pick }: { pick: RecordData }) {
  if (!pick.selection) return <p className="fh-muted">No eligible model pick in this snapshot.</p>;
  return <p><strong>{selection(pick,pick.selection)}</strong> · {pct(pick.probability)} model probability <ModelLabel row={pick} /></p>;
}
function SummaryContent({ item }: { item: RecordData | undefined }) {
  if (!item) return null;
  const summary=record(item.summary);
  return <><p className="fh-muted">{metric(summary,'predictions')} model forecasts · {metric(summary,'ev_bets')} EV estimates · {metric(summary,'arbitrage')} nominal arbitrage combinations</p><PickPreview pick={record(item.top_pick)} /></>;
}
export function SportIntelSummary({ sport }: { sport: string }) {
  const slug = Object.keys(sportLabels).find(key => sportLabels[key] === sport) || sport.toLowerCase();
  const query = useQuery({ queryKey: ['betting-intel', 'overview'], queryFn: ({ signal }) => predictionService.getBettingIntel(undefined, signal), staleTime: 30000 });
  const item = array(record(query.data).sports).map(record).find(row => row.sport === slug);
  return <section className="fh-card fh-section bi-inline-summary">
    <div className="fh-section-heading"><h2>{sport} AI picks & predictions</h2><Link to={`/ai-picks/intelligence/${slug}`}>View intelligence <ArrowUpRight size={14} /></Link></div>
    <QueryState query={query} /><SummaryContent item={item} />
  </section>;
}
function NextPrediction({ prediction }: { prediction: RecordData }) {
  if (!prediction.home_team) return null;
  return <p className="bi-next-game">Next forecast: {text(prediction.home_team)} vs {text(prediction.away_team)}</p>;
}
function SportCard({ slug, label, row }: { slug: string; label: string; row: RecordData | undefined }) {
  const summary=record(row?.summary);
  const count=(key: string) => row ? metric(summary,key) : '—';
  return <article className="fh-card fh-section bi-sport-card"><span className="fh-eyebrow">{label}</span><h2>{label} intelligence</h2>
    <div className="bi-mini-metrics"><div><b>{count('ai_picks')}</b><small>AI picks</small></div><div><b>{count('predictions')}</b><small>Predictions</small></div><div><b>{count('ev_bets')}</b><small>EV estimates</small></div></div>
    {row ? <PickPreview pick={record(row.top_pick)} /> : <p className="fh-muted">Coverage is unavailable until the pipeline responds.</p>}
    <NextPrediction prediction={record(row?.next_prediction)} />
    <Link to={`/ai-picks/intelligence/${slug}`}>Open {label} summary <ArrowUpRight size={14} /></Link></article>;
}
function Hub() {
  const query = useQuery({ queryKey: ['betting-intel', 'overview'], queryFn: ({ signal }) => predictionService.getBettingIntel(undefined, signal), refetchInterval: 60000 });
  const data = record(query.data);
  return <AppShell title="A clearer view of the market." eyebrow="AI PICKS / INTELLIGENCE">
    <section className="fh-card fh-section bi-intro"><Sparkles size={21} /><h2>Betting intelligence</h2>
      <p>Compare model forecasts, fair market probabilities and bookmaker prices. Choose a sport to explore the evidence.</p>
      <Link className="fh-button" to="/ai-picks/intelligence/nba">Explore NBA <ArrowUpRight size={15} /></Link></section>
    <QueryState query={query} />
    {query.data !== undefined && <Provenance data={data} />}
    <div className="bi-sport-grid">{Object.entries(sportLabels).map(([slug, label]) => {
      const row = array(data.sports).map(record).find(item => item.sport === slug);
      return <SportCard key={slug} slug={slug} label={label} row={row} />;
    })}</div>
  </AppShell>;
}
function matchesSearch(row: RecordData, search: string) {
  return `${row.home_team} ${row.away_team} ${row.competition} ${text(row.player)} ${text(row.bookmaker)}`.toLowerCase().includes(search.toLowerCase());
}
function viewTitle(sport: string, view: string) {
  return view === 'summary' ? `${sportLabels[sport]} AI picks & predictions` : views[view].title;
}
function EmptyResults({ search, view }: { search: string; view: string }) {
  if (search) return <div className="fh-state"><h3>No results match your filter.</h3><p>Try another team, player or bookmaker.</p></div>;
  return <div className="fh-state"><h3>No eligible {views[view].title.toLowerCase()} right now.</h3><p>This snapshot has no complete, fresh evidence for this view. Missing data is not a prediction that no opportunity exists.</p></div>;
}
function RefreshButton({ busy, refresh }: { busy: boolean; refresh: () => unknown }) {
  return <button className="fh-button secondary" onClick={() => void refresh()} disabled={busy}><RefreshCw size={14} /> {busy ? 'Refreshing…' : 'Refresh view'}</button>;
}
function SportWorkspace({ sport, view }: { sport: string; view: string }) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ['betting-intel', sport], queryFn: ({ signal }) => predictionService.getBettingIntel(sport, signal), refetchInterval: 60000 });
  const data = record(query.data), summary = record(data.summary);
  const rows = array(data[views[view].key]).map(record).filter(row => matchesSearch(row,search));
  const pages = Math.max(1,Math.ceil(rows.length/20));
  const currentPage = Math.min(page,pages);
  return <AppShell sport={sportLabels[sport]} title={`${sportLabels[sport]} betting intelligence.`} eyebrow="AI PICKS / INTELLIGENCE">
    <section className="fh-card fh-section bi-workspace">
      <div className="bi-toolbar"><Link to="/ai-picks/intelligence">← All sports</Link><RefreshButton busy={query.isFetching} refresh={query.refetch} /></div>
      <nav className="bi-sport-nav" aria-label="Intelligence sport">{Object.entries(sportLabels).map(([key,label]) => <NavLink key={key} to={`/ai-picks/intelligence/${key}`} aria-current={key === sport ? 'page' : undefined}>{label}</NavLink>)}</nav>
      <nav className="bi-view-nav" aria-label="Intelligence tools">{Object.entries(views).map(([key,item]) => <Link key={key} to={`/ai-picks/intelligence/${sport}${key === 'summary' ? '' : `/${key}`}`} aria-current={view === key ? 'page' : undefined}>{item.title}</Link>)}</nav>
      <h2>{viewTitle(sport,view)}</h2><p className="fh-muted">{views[view].description}</p>
      <QueryState query={query} />
      {query.data !== undefined && <><Provenance data={data} /><div className="bi-mini-metrics">{[['fixtures','Games'],['predictions','Predictions'],['ev_bets','EV estimates'],['player_props','Prop quotes'],['arbitrage','Nominal arbitrage']].map(([key,label]) => <div key={key}><b>{metric(summary,key)}</b><small>{label}</small></div>)}</div>
        <label className="bi-search">Filter games, players or books<input type="search" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Team, player, competition…" /></label>
        {rows.length ? <><MarketTable rows={rows.slice((currentPage-1)*20,currentPage*20)} view={view} title={views[view].title} /><div className="bi-pagination"><button className="fh-button secondary" disabled={currentPage<=1} onClick={() => setPage(currentPage-1)}>Previous</button><span>Page {currentPage} of {pages} · {rows.length} results</span><button className="fh-button secondary" disabled={currentPage>=pages} onClick={() => setPage(currentPage+1)}>Next</button></div></> :
          <EmptyResults search={search} view={view} />}
        {view === 'summary' && <div className="bi-summary-links">{Object.entries(views).filter(([key]) => key !== 'summary').map(([key,item]) => <Link key={key} to={`/ai-picks/intelligence/${sport}/${key}`}>{item.title} <ArrowUpRight size={14} /></Link>)}</div>}
      </>}
      <p className="bi-footnote">Probabilities are estimates. EV and arbitrage returns exclude taxes, commission and execution costs. Bookmaker rules, limits and availability need checking. No bets are placed here.</p>
    </section>
  </AppShell>;
}
export default function BettingIntel() {
  const { sport, view = 'summary' } = useParams();
  if (!sport) return <Hub />;
  if (!Object.hasOwn(sportLabels,sport) || !Object.hasOwn(views,view)) return <AppShell title="Intelligence view unavailable."><Link to="/ai-picks/intelligence">Choose a supported sport and tool →</Link></AppShell>;
  return <SportWorkspace key={`${sport}/${view}`} sport={sport} view={view} />;
}
