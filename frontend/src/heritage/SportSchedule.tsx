import { ChevronLeft, ChevronRight, RefreshCw, CalendarDays, ArrowUpRight } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import AppShell from './AppShell';
import { sportPath, type Sport } from './data';
import type { Fixture } from './services';
import { DataState, Dialog } from './ui';
import { isFinal, shiftDay, utcDay, useSportSchedule, validDay } from './sportScheduleData';
import './sport-centre.css';

export function TeamMark({ name }: { name: string }) {
  const words = name.trim().split(/\s+/);
  return <span className="sc-team-mark" aria-hidden="true">{words.length > 1 ? `${words[0][0]}${words[words.length - 1][0]}` : name.slice(0, 2)}</span>;
}

function GameTeams({ game }: { game: Fixture }) {
  return <span className="sc-matchup"><span><TeamMark name={game.away} />{game.away}</span><i>@</i><span><TeamMark name={game.home} />{game.home}</span></span>;
}

function GameResult({ game }: { game: Fixture }) {
  if (isFinal(game)) return <span className="sc-result"><b>{game.awayScore}</b><span>–</span><b>{game.homeScore}</b></span>;
  if (['CANCELLED', 'CANCELED', 'POSTPONED'].includes(game.status.toUpperCase())) return <span>—</span>;
  return <time dateTime={game.date}>{new Date(game.date).toLocaleTimeString('en', { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })}</time>;
}

function ScheduleRows({ games, sport, selectedDay }: { games: Fixture[]; sport: Sport; selectedDay: string }) {
  const [params] = useSearchParams();
  const days = [selectedDay, shiftDay(selectedDay, 1)];
  return <>{days.map(day => {
    const rows = games.filter(game => utcDay(new Date(game.date)) === day);
    return <section className="sc-day-group" key={day} aria-label={day}>
      <div className="sc-day-title"><h3>{new Date(`${day}T12:00:00Z`).toLocaleDateString('en', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' })}</h3><span>{rows.length} {rows.length === 1 ? 'game' : 'games'}</span></div>
      {rows.length ? <div className="sc-table-wrap" role="region" aria-label={`${sport} games on ${day}`} tabIndex={0}>
        <table className="sc-table"><caption className="sc-sr-only">{sport} matchups, times and results for {day}. Away team listed first. Times in UTC.</caption>
          <thead><tr><th scope="col">Matchup</th><th scope="col">Time / result</th><th scope="col">Status</th><th scope="col">Competition</th></tr></thead>
          <tbody>{rows.map(game => {
            const next = new URLSearchParams(params); next.set('match', game.id); next.set('date', day);
            return <tr key={game.id}><td><Link className="sc-match-link" to={`${sportPath(sport, 'schedule')}?${next}`}><GameTeams game={game} /></Link></td>
              <td><GameResult game={game} /></td><td><span className={`sc-status ${isFinal(game) ? 'sc-final' : ''}`}>{isFinal(game) ? 'Final' : game.status.replaceAll('_', ' ').toLowerCase() || 'Scheduled'}</span></td><td>{game.league || sport}</td></tr>;
          })}</tbody></table>
      </div> : <div className="sc-no-games">No {sport} games available for this date.</div>}
    </section>;
  })}</>;
}

export default function SportSchedule({ sport }: { sport: Sport }) {
  const [params, setParams] = useSearchParams();
  const dateParam = params.get('date') || '';
  const date = validDay(dateParam) ? dateParam : utcDay();
  const team = params.get('team') || '';
  const competition = params.get('competition') || '';
  const query = useSportSchedule(sport, date, shiftDay(date, 1));
  const games = query.data?.items ?? [];
  const teams = [...new Set([...games.flatMap(game => [game.home, game.away]), team].filter(Boolean))].sort();
  const competitions = [...new Set([...games.map(game => game.league), competition].filter(Boolean))].sort();
  const visible = games.filter(game => (!team || game.home === team || game.away === team) && (!competition || game.league === competition));
  const selected = games.find(game => game.id === params.get('match'));
  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== 'match') next.delete('match');
    setParams(next);
  }
  return <AppShell sport={sport} title={`${sport} schedule.`} eyebrow="MATCH CENTRE / SCHEDULE">
    <section className="fh-card sc-schedule" aria-labelledby="sc-schedule-title">
      <header className="sc-schedule-head"><div><span className="sc-kicker">THE GAME PLAN</span><h2 id="sc-schedule-title">{sport} Schedule</h2><p>Upcoming matchups. Verified finals. All in one place.</p></div>
        <div className="sc-controls"><label>Team schedules<select aria-label="Team schedules" value={team} onChange={event => update('team', event.target.value)}><option value="">All teams</option>{teams.map(name => <option key={name}>{name}</option>)}</select></label>
          <button className="sc-icon-button" aria-label="Refresh schedule" disabled={query.isFetching} onClick={() => void query.refetch()}><RefreshCw size={18} /></button></div>
      </header>
      <div className="sc-date-strip"><button className="sc-icon-button" aria-label="Previous week" onClick={() => update('date', shiftDay(date, -7))}><ChevronLeft size={20} /></button>
        <nav aria-label="Schedule dates">{Array.from({ length: 7 }, (_, index) => shiftDay(date, index - 3)).map(day => <button key={day} aria-pressed={day === date} className={day === date ? 'is-selected' : ''} onClick={() => update('date', day)}>
          <span>{new Date(`${day}T12:00:00Z`).toLocaleDateString('en', { weekday: 'short', timeZone: 'UTC' })}</span><b>{new Date(`${day}T12:00:00Z`).toLocaleDateString('en', { month: 'short', day: 'numeric', timeZone: 'UTC' })}</b>{day === utcDay() && <i aria-label="Today" />}</button>)}</nav>
        <button className="sc-icon-button" aria-label="Next week" onClick={() => update('date', shiftDay(date, 7))}><ChevronRight size={20} /></button></div>
      <div className="sc-filter-line"><span><CalendarDays size={15} /> Times shown in UTC</span><div><label>Jump to date<input type="date" value={date} onChange={event => { if (validDay(event.target.value)) update('date', event.target.value); }} /></label>
        <label>Competition<select value={competition} onChange={event => update('competition', event.target.value)}><option value="">All competitions</option>{competitions.map(name => <option key={name}>{name}</option>)}</select></label>
        <button className="sc-text-button" onClick={() => update('date', utcDay())}>Today</button></div></div>
      {query.isPending || query.error ? <DataState loading={query.isPending} error={query.error} retry={() => void query.refetch()} /> : <>
        {query.data?.issues.map(issue => <p className="sc-source-note" key={issue}>{issue}</p>)}
        <ScheduleRows games={visible} sport={sport} selectedDay={date} />
      </>}
      <footer className="sc-schedule-foot"><span>Saved schedules and verified results. Not a live score feed.</span><Link to={sportPath(sport, 'predictions')}>View {sport} predictions <ArrowUpRight size={15} /></Link></footer>
    </section>
    {selected && <Dialog className="sc-match-dialog" title={`${selected.away} at ${selected.home}`} onClose={() => update('match', '')}>
      <span className="sc-kicker">{selected.league || sport} · {isFinal(selected) ? 'MATCH RESULT' : 'MATCH DETAILS'}</span>
      <h2>{selected.away} at {selected.home}</h2>
      {isFinal(selected) ? <div className="sc-dialog-scoreboard" aria-label={`Final score: ${selected.away} ${selected.awayScore}, ${selected.home} ${selected.homeScore}`}>
        <div><TeamMark name={selected.away} /><span>{selected.away}</span><strong>{selected.awayScore}</strong><small>Away</small></div>
        <span className="sc-score-divider" aria-hidden="true">–</span>
        <div><TeamMark name={selected.home} /><span>{selected.home}</span><strong>{selected.homeScore}</strong><small>Home</small></div>
      </div> : <p className="sc-dialog-start"><GameResult game={selected} /> UTC</p>}
      <div className="sc-dialog-meta"><span className={`sc-status ${isFinal(selected) ? 'sc-final' : ''}`}>{isFinal(selected) ? 'Final' : selected.status.replaceAll('_', ' ').toLowerCase() || 'Scheduled'}</span>
        <time dateTime={selected.date}>{new Date(selected.date).toLocaleString('en', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })} UTC</time></div>
    </Dialog>}
  </AppShell>;
}
