import React, { useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';
import {
  usePipelineMatches,
  usePrediction,
  useMatchupPrediction,
  useBettingEdge,
} from '../hooks/usePredictions';

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
  const [homeTeam, setHomeTeam] = useState('');
  const [awayTeam, setAwayTeam] = useState('');

  const {
    data: matches = [],
    isLoading: matchesLoading,
    isError: matchesError,
    refetch: refetchMatches,
  } = usePipelineMatches({ limit: 6 });

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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 py-8 space-y-10">
        <header>
          <p className="text-sm uppercase tracking-wide text-green-400 mb-2">AI Insights</p>
          <h1 className="text-4xl font-bold text-white mb-3">Predictions & Betting Edge</h1>
          <p className="text-gray-400 max-w-3xl">
            Explore upcoming fixtures powered by our ML pipeline, visualize probabilities, and run custom
            what-if matchups before placing a bet.
          </p>
        </header>

        <section className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 shadow-2xl shadow-black/30">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
            <div>
              <h2 className="text-2xl font-semibold text-white">Upcoming Matches</h2>
              <p className="text-gray-500 text-sm">Pulled directly from the pipeline API (auto-refreshes every minute)</p>
            </div>
            <button
              onClick={() => refetchMatches()}
              className="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 text-white font-semibold border border-gray-700 hover:bg-gray-700"
            >
              <svg className={`w-4 h-4 ${matchesLoading ? 'animate-spin' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 4v5h.582m15.356 2a8.001 8.001 0 00-15.356-2m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Refresh
            </button>
          </div>

          {matchesLoading ? (
            <div className="grid gap-4 md:grid-cols-2">
              {[...Array(4)].map((_, index) => (
                <div key={index} className="h-48 rounded-xl bg-gray-800 animate-pulse" />
              ))}
            </div>
          ) : matchesError ? (
            <div className="border border-red-500/60 bg-red-500/10 rounded-xl p-6 text-center">
              <p className="text-red-300 font-semibold">Failed to load matches. Please try again.</p>
            </div>
          ) : matches.length === 0 ? (
            <div className="rounded-xl border border-gray-800 bg-gray-850 p-10 text-center text-gray-400">
              No pipeline matches available right now. Check back shortly.
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2">
              {matches.map((match) => (
                <PredictionCard key={match.match_id || match.external_id} match={match} />
              ))}
            </div>
          )}
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="p-6 rounded-2xl border border-gray-800 bg-gray-900/60 shadow-xl shadow-black/20">
            <h2 className="text-2xl font-semibold text-white mb-2">What-If Matchup</h2>
            <p className="text-gray-400 text-sm mb-6">Compare any two teams and get instant probabilities plus an AI recommendation.</p>

            <form onSubmit={handleMatchupSubmit} className="space-y-4">
              <div>
                <label className="text-gray-300 text-sm font-semibold mb-2 block">Home Team</label>
                <input
                  type="text"
                  value={homeTeam}
                  onChange={(event) => setHomeTeam(event.target.value)}
                  placeholder="e.g., Arsenal"
                  className="w-full bg-gray-850 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
              <div>
                <label className="text-gray-300 text-sm font-semibold mb-2 block">Away Team</label>
                <input
                  type="text"
                  value={awayTeam}
                  onChange={(event) => setAwayTeam(event.target.value)}
                  placeholder="e.g., Chelsea"
                  className="w-full bg-gray-850 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
              <button
                type="submit"
                disabled={matchupLoading}
                className="w-full flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-lg py-3 transition disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {matchupLoading && (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M4 4v5h.582m15.356 2a8.001 8.001 0 00-15.356-2m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                )}
                Generate Prediction
              </button>
            </form>
          </div>

          <div className="p-6 rounded-2xl border border-gray-800 bg-gray-900/60 shadow-xl shadow-black/20">
            <h3 className="text-xl font-semibold text-white mb-4">Matchup Insights</h3>
            {!matchupPrediction ? (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm text-center">
                Enter two teams and tap “Generate Prediction” to view AI analysis.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Predicted Winner</p>
                    <p className="text-2xl font-bold text-white capitalize">{matchupPrediction.winner?.replace('_', ' ') || 'N/A'}</p>
                  </div>
                  <span className="px-3 py-1 rounded-full border border-green-500/50 text-green-300 text-xs font-semibold">
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
                  <div className="bg-gray-850 border border-gray-700 rounded-xl p-4">
                    <p className="text-sm text-gray-400 uppercase tracking-wide mb-2">Recommendation</p>
                    <p className="text-gray-200 leading-relaxed">{matchupPrediction.recommendation}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

const ProbabilityBar = ({ label, value }) => {
  const percentage = Math.round((value || 0) * 100);
  return (
    <div>
      <div className="flex justify-between text-sm text-gray-400 mb-1">
        <span>{label}</span>
        <span>{percentage}%</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div className="h-full bg-green-500" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
};

const PredictionCard = ({ match }) => {
  const matchId = match?.match_id || match?.external_id;
  const { data: prediction, isLoading } = usePrediction(matchId);

  const odds = useMemo(
    () => ({
      home_win: match?.home_win_odds ? Number(match.home_win_odds) : null,
      draw: match?.draw_odds ? Number(match.draw_odds) : null,
      away_win: match?.away_win_odds ? Number(match.away_win_odds) : null,
    }),
    [match]
  );

  const edge = useBettingEdge(prediction, odds);
  const bestBet = edge?.bestBet;

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-850 p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">{match.competition || 'Competition'}</p>
          <h3 className="text-xl font-semibold text-white">
            {match.home_team} vs {match.away_team}
          </h3>
          <p className="text-gray-500 text-sm">{formatDateTime(match.date)}</p>
        </div>
        {match.status && (
          <span className="px-3 py-1 rounded-full border border-gray-700 text-gray-300 text-xs font-semibold">
            {match.status}
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {['home_team', 'draw', 'away_team'].map((key) => (
          <div key={key} className="bg-gray-900/60 rounded-xl border border-gray-800 p-3 text-center">
            <p className="text-xs uppercase text-gray-500 mb-1">
              {key === 'home_team' ? 'Home' : key === 'away_team' ? 'Away' : 'Draw'}
            </p>
            <p className="text-white font-semibold text-lg">
              {key === 'draw'
                ? odds.draw?.toFixed(2) || '--'
                : odds[key === 'home_team' ? 'home_win' : 'away_win']?.toFixed(2) || '--'}
            </p>
            <p className="text-gray-500 text-xs">decimal odds</p>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="h-4 bg-gray-800 rounded animate-pulse" />
        ) : prediction ? (
          <>
            <ProbabilityBar label={`Home win (${match.home_team})`} value={prediction.home_prob} />
            <ProbabilityBar label="Draw" value={prediction.draw_prob} />
            <ProbabilityBar label={`Away win (${match.away_team})`} value={prediction.away_prob} />
          </>
        ) : (
          <p className="text-gray-500 text-sm">Prediction unavailable for this match.</p>
        )}
      </div>

      {bestBet ? (
        <div className="border border-green-600/40 bg-green-500/10 rounded-xl p-4">
          <p className="text-xs uppercase text-green-300 tracking-wide mb-1">Top Value Bet</p>
          <p className="text-white font-semibold">
            {bestBet.outcome === 'home' && match.home_team}
            {bestBet.outcome === 'away' && match.away_team}
            {bestBet.outcome === 'draw' && 'Draw'}
            <span className="text-green-300 text-sm font-normal"> · {Math.round(bestBet.edge * 100)}% edge</span>
          </p>
        </div>
      ) : (
        <div className="border border-gray-800 rounded-xl p-4 text-sm text-gray-500">
          No positive value edge detected for current odds.
        </div>
      )}
    </div>
  );
};

export default Predictions;
