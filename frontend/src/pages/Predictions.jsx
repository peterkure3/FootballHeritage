import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';
import PredictionResults from '../components/predictions/PredictionResults';
import {
  usePipelineMatches,
  usePrediction,
  useMatchupPrediction,
  useBettingEdge,
} from '../hooks/usePredictions';

const toNumber = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
};

const formatAmericanOdds = (value) => {
  const n = toNumber(value);
  if (n === null || n === 0) return '--';
  return n > 0 ? `+${Math.round(n)}` : `${Math.round(n)}`;
};

const impliedProbabilityFromAmerican = (value) => {
  const odds = toNumber(value);
  if (odds === null || odds === 0) return null;

  if (odds > 0) {
    return 100 / (odds + 100);
  }

  const absOdds = Math.abs(odds);
  return absOdds / (absOdds + 100);
};

const formatDateTime = (value) => {
  if (!value) return 'TBD';
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value;
  }
};

const Predictions = () => {
  const [activeTab, setActiveTab] = useState('upcoming');
  const [homeTeam, setHomeTeam] = useState('');
  const [awayTeam, setAwayTeam] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [matchesPage, setMatchesPage] = useState(1);
  const matchesPerPage = 6;

  const {
    data: matches = [],
    isLoading: matchesLoading,
    isError: matchesError,
    refetch: refetchMatches,
  } = usePipelineMatches({ limit: 30, _t: refreshKey });

  const upcomingMatches = useMemo(() => {
    const now = Date.now();
    const graceMs = 2 * 60 * 60 * 1000;
    const allowedStatuses = new Set(['UPCOMING', 'SCHEDULED', 'NOT_STARTED', 'PRE', 'PREGAME']);

    return (matches || [])
      .filter((match) => {
        const rawStatus = match?.status ? String(match.status).toUpperCase() : null;
        if (rawStatus && (rawStatus === 'FINISHED' || rawStatus === 'CANCELLED')) {
          return false;
        }

        const dateValue = match?.date ?? match?.event_date ?? match?.start_time;
        const time = dateValue ? new Date(dateValue).getTime() : null;
        const isFutureOrRecent = typeof time === 'number' && Number.isFinite(time) ? time > (now - graceMs) : null;

        if (rawStatus && (allowedStatuses.has(rawStatus) || rawStatus === 'LIVE')) {
          return isFutureOrRecent === null ? true : isFutureOrRecent;
        }

        return isFutureOrRecent === null ? false : isFutureOrRecent;
      })
      .sort((a, b) => {
        const ta = new Date(a?.date ?? a?.event_date ?? a?.start_time ?? 0).getTime();
        const tb = new Date(b?.date ?? b?.event_date ?? b?.start_time ?? 0).getTime();
        return ta - tb;
      });
  }, [matches]);

  useEffect(() => {
    setMatchesPage(1);
  }, [refreshKey, upcomingMatches.length]);

  const totalPages = Math.max(1, Math.ceil(upcomingMatches.length / matchesPerPage));
  const clampedPage = Math.min(matchesPage, totalPages);
  const startIndex = (clampedPage - 1) * matchesPerPage;
  const pagedUpcomingMatches = useMemo(
    () => upcomingMatches.slice(startIndex, startIndex + matchesPerPage),
    [upcomingMatches, startIndex, matchesPerPage]
  );

  const pageNumbers = useMemo(() => {
    const maxButtons = 5;
    if (totalPages <= maxButtons) {
      return Array.from({ length: totalPages }, (_, idx) => idx + 1);
    }

    const half = Math.floor(maxButtons / 2);
    const start = Math.max(1, Math.min(clampedPage - half, totalPages - maxButtons + 1));
    return Array.from({ length: maxButtons }, (_, idx) => start + idx);
  }, [clampedPage, totalPages]);

  const {
    data: matchupPrediction,
    isFetching: matchupLoading,
    refetch: refetchMatchup,
  } = useMatchupPrediction(homeTeam, awayTeam, { enabled: false });

  const handleMatchupSubmit = (event) => {
    event.preventDefault();
    if (!homeTeam.trim() || !awayTeam.trim()) {
      toast.error('Enter both team names before requesting a prediction');
      return;
    }
    refetchMatchup();
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 py-8 space-y-10">
        <header style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <p className="text-sm uppercase tracking-wide font-semibold mb-2" style={{ color: '#10b981' }}>AI Insights</p>
          <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight mb-2">Predictions & Betting Edge</h1>
          <p className="text-sm max-w-3xl" style={{ color: '#64748b' }}>
            Explore upcoming fixtures powered by our ML pipeline, visualize probabilities, and run custom
            what-if matchups before placing a bet.
          </p>
        </header>

        {/* Tab Navigation */}
        <div className="flex border-b" style={{ borderColor: 'var(--color-card-border)' }}>
          <button
            onClick={() => setActiveTab('upcoming')}
            className={`px-6 py-3 font-semibold text-sm transition`}
            style={{
              color: activeTab === 'upcoming' ? '#10b981' : '#64748b',
              borderBottom: activeTab === 'upcoming' ? '2px solid #10b981' : '2px solid transparent',
            }}
          >
            Upcoming Predictions
          </button>
          <button
            onClick={() => setActiveTab('results')}
            className={`px-6 py-3 font-semibold text-sm transition`}
            style={{
              color: activeTab === 'results' ? '#10b981' : '#64748b',
              borderBottom: activeTab === 'results' ? '2px solid #10b981' : '2px solid transparent',
            }}
          >
            Results & Accuracy
          </button>
        </div>

        {/* Results Tab Content */}
        {activeTab === 'results' ? (
          <PredictionResults />
        ) : (
        <>
        <section className="card-glow rounded-xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.4s ease-out 0.06s both' }}>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-white font-[Oswald] tracking-tight">Upcoming Matches</h2>
              <p className="text-sm" style={{ color: '#64748b' }}>Pulled directly from the pipeline API (auto-refreshes every minute)</p>
            </div>
            <button
              onClick={() => {
                setRefreshKey((value) => value + 1);
                refetchMatches();
              }}
              className="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white font-semibold text-sm transition-all card-glow"
              style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}
            >
              <svg className={`w-4 h-4 ${matchesLoading ? 'animate-spin' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2a8.001 8.001 0 00-15.356-2m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>

          {matchesLoading ? (
            <div className="grid gap-4 md:grid-cols-2">
              {[...Array(4)].map((_, index) => (
                <div key={index} className="h-48 rounded-xl animate-pulse" style={{ background: 'var(--color-card)' }} />
              ))}
            </div>
          ) : matchesError ? (
            <div className="rounded-xl p-6 text-center border" style={{ background: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
              <p style={{ color: '#fca5a5' }} className="font-semibold">Failed to load matches. Please try again.</p>
            </div>
          ) : matches.length === 0 ? (
            <div className="card-glow rounded-xl p-10 text-center border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <p style={{ color: '#64748b' }}>No pipeline matches available right now. Check back shortly.</p>
            </div>
          ) : upcomingMatches.length === 0 ? (
            <div className="card-glow rounded-xl p-10 text-center border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <p style={{ color: '#64748b' }}>No upcoming matches found. Try refreshing after the next pipeline sync.</p>
            </div>
          ) : (
            <div>
              <div className="grid gap-6 md:grid-cols-2">
                {pagedUpcomingMatches.map((match) => (
                  <PredictionCard key={match.match_id || match.external_id} match={match} refreshKey={refreshKey} />
                ))}
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm" style={{ color: '#64748b' }}>
                  Showing <span className="text-gray-200">{Math.min(upcomingMatches.length, startIndex + 1)}</span>-
                  <span className="text-gray-200">{Math.min(upcomingMatches.length, startIndex + pagedUpcomingMatches.length)}</span>{' '}
                  of <span className="text-gray-200">{upcomingMatches.length}</span>
                </p>

                <div className="flex flex-wrap items-center gap-2 justify-start sm:justify-end">
                  <button
                    type="button"
                    onClick={() => setMatchesPage((page) => Math.max(1, page - 1))}
                    disabled={clampedPage <= 1}
                    className="px-3 py-2 rounded-lg text-white text-sm font-semibold transition-all card-glow disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}
                  >
                    Prev
                  </button>

                  {pageNumbers[0] !== 1 && (
                    <>
                      <button
                        type="button"
                        onClick={() => setMatchesPage(1)}
                        className="px-3 py-2 rounded-lg text-sm font-semibold transition-all"
                        style={{
                          background: clampedPage === 1 ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--color-card)',
                          color: 'white',
                          border: clampedPage === 1 ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--color-card-border)',
                        }}
                      >
                        1
                      </button>
                      <span className="px-1" style={{ color: '#64748b' }}>…</span>
                    </>
                  )}

                  {pageNumbers.map((page) => (
                    <button
                      key={page}
                      type="button"
                      onClick={() => setMatchesPage(page)}
                      className="px-3 py-2 rounded-lg text-sm font-semibold transition-all"
                      style={{
                        background: clampedPage === page ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--color-card)',
                        color: 'white',
                        border: clampedPage === page ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--color-card-border)',
                      }}
                    >
                      {page}
                    </button>
                  ))}

                  {pageNumbers[pageNumbers.length - 1] !== totalPages && (
                    <>
                      <span className="px-1" style={{ color: '#64748b' }}>…</span>
                      <button
                        type="button"
                        onClick={() => setMatchesPage(totalPages)}
                        className="px-3 py-2 rounded-lg text-sm font-semibold transition-all"
                        style={{
                          background: clampedPage === totalPages ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--color-card)',
                          color: 'white',
                          border: clampedPage === totalPages ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--color-card-border)',
                        }}
                      >
                        {totalPages}
                      </button>
                    </>
                  )}

                  <button
                    type="button"
                    onClick={() => setMatchesPage((page) => Math.min(totalPages, page + 1))}
                    disabled={clampedPage >= totalPages}
                    className="px-3 py-2 rounded-lg text-white text-sm font-semibold transition-all card-glow disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="grid gap-6 md:grid-cols-2 stagger-children">
          <div className="card-glow rounded-xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
            <h2 className="text-2xl font-bold text-white font-[Oswald] tracking-tight mb-2">What-If Matchup</h2>
            <p className="text-sm mb-6" style={{ color: '#64748b' }}>Compare any two teams and get instant probabilities plus an AI recommendation.</p>

            <form onSubmit={handleMatchupSubmit} className="space-y-4">
              <div>
                <label className="text-sm font-semibold mb-2 block" style={{ color: '#94a3b8' }}>Home Team</label>
                <input
                  type="text"
                  value={homeTeam}
                  onChange={(event) => setHomeTeam(event.target.value)}
                  placeholder="e.g., Arsenal"
                  className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                  style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                />
              </div>
              <div>
                <label className="text-sm font-semibold mb-2 block" style={{ color: '#94a3b8' }}>Away Team</label>
                <input
                  type="text"
                  value={awayTeam}
                  onChange={(event) => setAwayTeam(event.target.value)}
                  placeholder="e.g., Chelsea"
                  className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                  style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                />
              </div>
              <button
                type="submit"
                disabled={matchupLoading}
                className="w-full flex items-center justify-center gap-2 text-white font-semibold rounded-lg py-3 transition-all hover:opacity-90 disabled:opacity-70 disabled:cursor-not-allowed"
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
              >
                {matchupLoading && (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2a8.001 8.001 0 00-15.356-2m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                )}
                Generate Prediction
              </button>
            </form>
          </div>

          <div className="card-glow rounded-xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
            <h3 className="text-xl font-bold text-white font-[Oswald] tracking-tight mb-4">Matchup Insights</h3>
            {!matchupPrediction ? (
              <div className="h-full flex items-center justify-center text-sm text-center" style={{ color: '#64748b' }}>
                Enter two teams and tap "Generate Prediction" to view AI analysis.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm" style={{ color: '#64748b' }}>Predicted Winner</p>
                    <p className="text-2xl font-bold text-white capitalize font-[Oswald] tracking-tight">{matchupPrediction.winner?.replace('_', ' ') || 'N/A'}</p>
                  </div>
                  <span className="px-3 py-1 rounded-full border text-xs font-semibold" style={{ borderColor: 'rgba(16, 185, 129, 0.5)', color: '#6ee7b7' }}>
                    {matchupPrediction.confidence || 'Medium'} confidence
                  </span>
                </div>

                <div className="grid gap-3">
                  {['home', 'draw', 'away'].map((key) => (
                    <ProbabilityBar
                      key={key}
                      label={key === 'home' ? 'Home Win' : key === 'away' ? 'Away Win' : 'Draw'}
                      value={matchupPrediction[`${key}_prob`]}
                    />
                  ))}
                </div>

                {matchupPrediction.recommendation && (
                  <div className="card-glow rounded-xl p-4 border" style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}>
                    <p className="text-xs uppercase tracking-wide mb-2" style={{ color: '#64748b' }}>Recommendation</p>
                    <p className="leading-relaxed" style={{ color: '#cbd5e1' }}>{matchupPrediction.recommendation}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
        </>
        )}
      </div>
    </div>
  );
};

const ProbabilityBar = ({ label, value }) => {
  const percentage = Math.round((value || 0) * 100);
  return (
    <div>
      <div className="flex justify-between text-sm mb-1" style={{ color: '#94a3b8' }}>
        <span>{label}</span>
        <span>{percentage}%</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: '#1a1a2e' }}>
        <div className="h-full" style={{ width: `${percentage}%`, background: 'linear-gradient(90deg, #10b981, #059669)' }} />
      </div>
    </div>
  );
};

const PredictionCard = ({ match, refreshKey }) => {
  const matchId = match?.match_id || match?.external_id;
  const { data: prediction, isLoading } = usePrediction(matchId, refreshKey);

  const odds = useMemo(
    () => ({
      home: toNumber(match?.moneyline_home ?? match?.home_moneyline ?? match?.home_ml ?? match?.home_win_odds),
      away: toNumber(match?.moneyline_away ?? match?.away_moneyline ?? match?.away_ml ?? match?.away_win_odds),
    }),
    [match]
  );

  const edge = useBettingEdge(prediction, {
    home_win: odds.home,
    draw: null,
    away_win: odds.away,
  });
  const bestBet = edge?.bestBet;

  return (
    <div className="card-glow rounded-xl p-5 border flex flex-col gap-4" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide" style={{ color: '#64748b' }}>{match.competition || 'Competition'}</p>
          <h3 className="text-xl font-bold text-white font-[Oswald] tracking-tight">
            {match.home_team} vs {match.away_team}
          </h3>
          <p className="text-sm" style={{ color: '#64748b' }}>{formatDateTime(match.date)}</p>
        </div>
        {match.status && (
          <span className="px-3 py-1 rounded-full border text-xs font-semibold" style={{ borderColor: 'var(--color-card-border)', color: '#94a3b8' }}>
            {match.status}
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="card-glow rounded-xl p-3 text-center border" style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}>
          <p className="text-xs uppercase mb-1" style={{ color: '#64748b' }}>Home ML</p>
          <p className="text-white font-semibold text-lg font-[Oswald] tracking-tight">{formatAmericanOdds(odds.home)}</p>
          <p className="text-xs" style={{ color: '#64748b' }}>moneyline</p>
        </div>
        <div className="card-glow rounded-xl p-3 text-center border" style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}>
          <p className="text-xs uppercase mb-1" style={{ color: '#64748b' }}>Away ML</p>
          <p className="text-white font-semibold text-lg font-[Oswald] tracking-tight">{formatAmericanOdds(odds.away)}</p>
          <p className="text-xs" style={{ color: '#64748b' }}>moneyline</p>
        </div>
        <div className="card-glow rounded-xl p-3 text-center border" style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}>
          <p className="text-xs uppercase mb-1" style={{ color: '#64748b' }}>Best Edge</p>
          {(() => {
            const homeImplied = impliedProbabilityFromAmerican(odds.home);
            const awayImplied = impliedProbabilityFromAmerican(odds.away);
            const homeEdge = prediction?.home_prob != null && homeImplied != null ? prediction.home_prob - homeImplied : null;
            const awayEdge = prediction?.away_prob != null && awayImplied != null ? prediction.away_prob - awayImplied : null;
            const best = [
              { side: 'home', value: homeEdge },
              { side: 'away', value: awayEdge },
            ].filter((item) => typeof item.value === 'number' && Number.isFinite(item.value))
              .sort((a, b) => b.value - a.value)[0];

            if (!best) {
              return <p className="text-white font-semibold text-lg font-[Oswald] tracking-tight">--</p>;
            }

            const pct = Math.round(best.value * 1000) / 10;
            const color = best.value > 0 ? 'text-green-300' : 'text-gray-300';
            return (
              <p className={`font-semibold text-lg font-[Oswald] tracking-tight ${color}`}>
                {best.side === 'home' ? 'Home' : 'Away'} {pct > 0 ? '+' : ''}{pct}%
              </p>
            );
          })()}
          <p className="text-xs" style={{ color: '#64748b' }}>model - implied</p>
        </div>
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="h-4 rounded animate-pulse" style={{ background: '#1a1a2e' }} />
        ) : prediction ? (
          <>
            <ProbabilityBar label={`Home win (${match.home_team})`} value={prediction.home_prob} />
            <ProbabilityBar label={`Away win (${match.away_team})`} value={prediction.away_prob} />
          </>
        ) : (
          <p className="text-sm" style={{ color: '#64748b' }}>Prediction unavailable for this match.</p>
        )}
      </div>

      {bestBet ? (
        <div className="rounded-xl p-4 border" style={{ background: 'rgba(16, 185, 129, 0.08)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
          <p className="text-xs uppercase tracking-wide mb-1" style={{ color: '#6ee7b7' }}>Top Value Bet</p>
          <p className="text-white font-semibold">
            {bestBet.outcome === 'home' && match.home_team}
            {bestBet.outcome === 'away' && match.away_team}
            <span className="text-sm font-normal" style={{ color: '#34d399' }}> · {Math.round(bestBet.edge * 100)}% edge</span>
          </p>
        </div>
      ) : (
        <div className="rounded-xl p-4 text-sm border" style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)', color: '#64748b' }}>
          No positive value edge detected for current odds.
        </div>
      )}
    </div>
  );
};

export default Predictions;
