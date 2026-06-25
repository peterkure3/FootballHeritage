import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import Navbar from "../components/Navbar";
import LoadingSkeleton from "../components/LoadingSkeleton";
import EmptyState from "../components/EmptyState";
import { TrendingUp, DollarSign, Target, Zap, AlertTriangle, Plus, Check } from "lucide-react";
import useParlayStore from "../stores/parlayStore";

const PIPELINE_API_URL = import.meta.env.VITE_PIPELINE_API_URL || "http://localhost:5555/api/v1";

const formatPct = (v) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "--";
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
};

const formatMoney = (v) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
};

const formatDecimalOdds = (v) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "--";
  return n.toFixed(2);
};

const formatDate = (v) => {
  if (!v) return "TBD";
  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(v));
  } catch {
    return v;
  }
};

const confidenceColors = {
  High: "bg-green-500/20 text-green-400 border-green-500/40",
  Medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  Low: "bg-gray-500/20 text-gray-400 border-gray-500/40",
};

const BestBets = () => {
  const [bankroll, setBankroll] = useState(1000);
  const [minEdge, setMinEdge] = useState(0.05);
  const [kellyFraction, setKellyFraction] = useState(0.25);
  const [limit, setLimit] = useState(20);
  
  const { addBet, isBetSelected } = useParlayStore();

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["best-value-bets", bankroll, minEdge, kellyFraction, limit],
    queryFn: async () => {
      const params = new URLSearchParams({
        bankroll: bankroll.toString(),
        min_edge: minEdge.toString(),
        kelly_fraction: kellyFraction.toString(),
        limit: limit.toString(),
        upcoming_only: "true",
      });
      const response = await fetch(`${PIPELINE_API_URL}/best-value-bets?${params}`);
      if (!response.ok) throw new Error("Failed to fetch value bets");
      return response.json();
    },
    staleTime: 60000,
    refetchInterval: 120000,
  });

  const bets = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  const totalEV = useMemo(
    () => bets.reduce((sum, b) => sum + (b.expected_value || 0), 0),
    [bets]
  );

  const totalStake = useMemo(
    () => bets.reduce((sum, b) => sum + (b.recommended_stake || 0), 0),
    [bets]
  );

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <header style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <p className="text-sm uppercase tracking-wide font-semibold mb-2" style={{ color: '#10b981' }}>Value Bets</p>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Zap className="w-6 h-6 text-green-400" />
            </div>
            <h1 className="text-3xl font-[Oswald] tracking-tight text-white">Best Value Bets</h1>
          </div>
          <p style={{ color: '#64748b' }} className="text-sm">
            AI-powered betting recommendations with Kelly criterion stake sizing.
            Only showing bets where our model finds positive edge.
          </p>
        </header>

        {/* Settings Panel */}
        <div className="card-glow rounded-xl p-6 border mb-6" style={{ animation: 'slide-up 0.4s ease-out 0.06s both', background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
          <h2 className="text-lg font-semibold text-white mb-4">Settings</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm mb-2" style={{ color: '#64748b' }}>Bankroll ($)</label>
              <input
                type="number"
                value={bankroll}
                onChange={(e) => setBankroll(Number(e.target.value) || 1000)}
                className="rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all w-full"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                min={100}
                step={100}
              />
            </div>
            <div>
              <label className="block text-sm mb-2" style={{ color: '#64748b' }}>Min Edge</label>
              <select
                value={minEdge}
                onChange={(e) => setMinEdge(Number(e.target.value))}
                className="rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all w-full"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
              >
                <option value={0.02}>2% (Aggressive)</option>
                <option value={0.05}>5% (Balanced)</option>
                <option value={0.08}>8% (Conservative)</option>
                <option value={0.10}>10% (Very Conservative)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm mb-2" style={{ color: '#64748b' }}>Kelly Fraction</label>
              <select
                value={kellyFraction}
                onChange={(e) => setKellyFraction(Number(e.target.value))}
                className="rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all w-full"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
              >
                <option value={0.1}>10% Kelly (Very Safe)</option>
                <option value={0.25}>25% Kelly (Recommended)</option>
                <option value={0.5}>50% Kelly (Moderate)</option>
                <option value={1.0}>Full Kelly (Risky)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm mb-2" style={{ color: '#64748b' }}>Max Bets</label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all w-full"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
              >
                <option value={10}>10 bets</option>
                <option value={20}>20 bets</option>
                <option value={50}>50 bets</option>
              </select>
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={() => refetch()}
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
              className="text-white font-semibold rounded-lg py-3 px-4 transition-all hover:opacity-90"
            >
              Refresh Bets
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        {bets.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="card-glow rounded-xl p-4 border" style={{ animation: 'slide-up 0.4s ease-out 0.06s both', background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <div className="flex items-center gap-2 text-sm mb-1" style={{ color: '#64748b' }}>
                <Target className="w-4 h-4" />
                <span>Value Bets Found</span>
              </div>
              <p className="text-2xl font-[Oswald] tracking-tight text-white">{bets.length}</p>
            </div>
            <div className="card-glow rounded-xl p-4 border" style={{ animation: 'slide-up 0.4s ease-out 0.12s both', background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <div className="flex items-center gap-2 text-sm mb-1" style={{ color: '#64748b' }}>
                <DollarSign className="w-4 h-4" />
                <span>Total Stake</span>
              </div>
              <p className="text-2xl font-[Oswald] tracking-tight text-white">{formatMoney(totalStake)}</p>
            </div>
            <div className="card-glow rounded-xl p-4 border" style={{ animation: 'slide-up 0.4s ease-out 0.18s both', background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <div className="flex items-center gap-2 text-sm mb-1" style={{ color: '#64748b' }}>
                <TrendingUp className="w-4 h-4" />
                <span>Expected Value</span>
              </div>
              <p className={`text-2xl font-[Oswald] tracking-tight ${totalEV >= 0 ? "text-green-400" : "text-red-400"}`}>
                {formatMoney(totalEV)}
              </p>
            </div>
            <div className="card-glow rounded-xl p-4 border" style={{ animation: 'slide-up 0.4s ease-out 0.24s both', background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <div className="flex items-center gap-2 text-sm mb-1" style={{ color: '#64748b' }}>
                <Zap className="w-4 h-4" />
                <span>Avg Edge</span>
              </div>
              <p className="text-2xl font-[Oswald] tracking-tight text-green-400">
                {bets.length > 0
                  ? formatPct(bets.reduce((s, b) => s + b.edge_pct, 0) / bets.length)
                  : "--"}
              </p>
            </div>
          </div>
        )}

        {/* Bets List */}
        {isLoading ? (
          <LoadingSkeleton type="list" count={3} />
        ) : isError ? (
          <div className="rounded-xl p-6 flex items-center gap-3" style={{ color: '#fca5a5', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
            <AlertTriangle className="w-5 h-5" />
            <span>{error?.message || "Failed to load value bets"}</span>
          </div>
        ) : bets.length === 0 ? (
          <div className="card-glow rounded-xl border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
            <EmptyState
              type="data"
              title="No Value Bets Found"
              description={`No bets with ${(minEdge * 100).toFixed(0)}%+ edge found. Try lowering the minimum edge or check back later.`}
            />
          </div>
        ) : (
          <div className="space-y-4">
            {bets.map((bet, idx) => (
              <div
                key={`${bet.match_id}-${bet.selection}-${idx}`}
                className="card-glow rounded-xl p-5 border transition"
                style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  {/* Match Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs uppercase tracking-wide" style={{ color: '#64748b' }}>
                        {bet.competition || "Football"}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${
                          confidenceColors[bet.confidence] || confidenceColors.Low
                        }`}
                      >
                        {bet.confidence}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-white">
                      {bet.home_team} vs {bet.away_team}
                    </h3>
                    <p className="text-sm" style={{ color: '#64748b' }}>{formatDate(bet.match_date)}</p>
                  </div>

                  {/* Selection */}
                  <div className="lg:text-center">
                    <p className="text-xs uppercase mb-1" style={{ color: '#64748b' }}>Bet On</p>
                    <p className="text-lg font-bold text-green-400">{bet.selection}</p>
                    <p className="text-sm" style={{ color: '#94a3b8' }}>@ {formatDecimalOdds(bet.decimal_odds)}</p>
                  </div>

                  {/* Edge */}
                  <div className="lg:text-center">
                    <p className="text-xs uppercase mb-1" style={{ color: '#64748b' }}>Edge</p>
                    <p className="text-2xl font-bold text-green-400">{formatPct(bet.edge_pct)}</p>
                    <p className="text-xs" style={{ color: '#64748b' }}>
                      Model: {(bet.model_prob * 100).toFixed(0)}% vs Implied:{" "}
                      {(bet.implied_prob * 100).toFixed(0)}%
                    </p>
                  </div>

                  {/* Stake */}
                  <div className="lg:text-center">
                    <p className="text-xs uppercase mb-1" style={{ color: '#64748b' }}>Recommended Stake</p>
                    <p className="text-2xl font-bold text-white">
                      {formatMoney(bet.recommended_stake)}
                    </p>
                    <p className="text-xs" style={{ color: '#64748b' }}>
                      {bet.kelly_stake_pct.toFixed(1)}% of bankroll
                    </p>
                  </div>

                  {/* EV */}
                  <div className="lg:text-right">
                    <p className="text-xs uppercase mb-1" style={{ color: '#64748b' }}>Expected Value</p>
                    <p
                      className={`text-xl font-bold ${
                        bet.expected_value >= 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {formatMoney(bet.expected_value)}
                    </p>
                    <p className="text-xs" style={{ color: '#64748b' }}>v{bet.model_version}</p>
                  </div>

                  {/* Add to Parlay Button */}
                  <div className="lg:ml-4">
                    {(() => {
                      const selectionMatch = bet.selection.match(/\((Home|Away|Draw)\s*Win\)/i);
                      const selection = selectionMatch 
                        ? selectionMatch[1].toUpperCase() === 'HOME' ? 'HOME' 
                          : selectionMatch[1].toUpperCase() === 'AWAY' ? 'AWAY' 
                          : 'DRAW'
                        : bet.selection.includes('Home') ? 'HOME' 
                          : bet.selection.includes('Away') ? 'AWAY' 
                          : 'DRAW';
                      
                      const isSelected = isBetSelected(bet.match_id, 'MONEYLINE', selection);
                      
                      const handleAddToParlay = () => {
                        const event = {
                          id: bet.match_id,
                          home_team: bet.home_team,
                          away_team: bet.away_team,
                          event_date: bet.match_date,
                          league: bet.competition,
                        };
                        
                        const americanOdds = bet.decimal_odds >= 2 
                          ? Math.round((bet.decimal_odds - 1) * 100)
                          : Math.round(-100 / (bet.decimal_odds - 1));
                        
                        const success = addBet(event, 'MONEYLINE', selection, americanOdds);
                        if (success) {
                          toast.success(`Added ${bet.selection} to parlay!`, { icon: '🎯' });
                        } else {
                          toast.error('Already in parlay or limit reached');
                        }
                      };
                      
                      return (
                        <button
                          onClick={handleAddToParlay}
                          disabled={isSelected}
                          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition ${
                            isSelected
                              ? 'bg-green-500/20 text-green-400 border border-green-500/40 cursor-default'
                              : 'text-white'
                          }`}
                          style={isSelected ? {} : { background: 'linear-gradient(135deg, #10b981, #059669)' }}
                          title={isSelected ? 'Already in parlay' : 'Add to parlay'}
                        >
                          {isSelected ? (
                            <>
                              <Check className="w-4 h-4" />
                              <span className="hidden sm:inline">In Parlay</span>
                            </>
                          ) : (
                            <>
                              <Plus className="w-4 h-4" />
                              <span className="hidden sm:inline">Add to Parlay</span>
                            </>
                          )}
                        </button>
                      );
                    })()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Disclaimer */}
        <div className="mt-8 card-glow rounded-xl p-4 border" style={{ background: 'rgba(234, 179, 8, 0.08)', borderColor: 'rgba(234, 179, 8, 0.2)' }}>
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm" style={{ color: '#fef08a' }}>
              <p className="font-semibold mb-1">Betting Disclaimer</p>
              <p style={{ color: '#fef08a', opacity: 0.8 }}>
                These recommendations are based on our ML model predictions and should not be
                considered financial advice. Past performance does not guarantee future results.
                Always bet responsibly and only with money you can afford to lose.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BestBets;
