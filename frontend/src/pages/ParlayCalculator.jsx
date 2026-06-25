import { useState, useEffect } from "react";
import { Calculator, AlertCircle, Brain, AlertTriangle, RefreshCw, TrendingUp } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import ParlayBetLeg from "../components/parlay/ParlayBetLeg";
import ParlayResults from "../components/parlay/ParlayResults";
import SuggestedParlays from "../components/parlay/SuggestedParlays";
import QuickAddSearch from "../components/parlay/QuickAddSearch";
import { useParlayCalculator } from "../hooks/useParlayCalculator";
import { useParlayData } from "../hooks/useParlayData";
import useParlayStore from "../stores/parlayStore";

const ParlayCalculator = () => {
  const navigate = useNavigate();
  const [stake, setStake] = useState(100);

  const {
    selectedBets,
    updateBet,
    removeBet,
    enrichParlay,
    isEnriching,
    correlationWarnings,
    combinedModelProb,
    combinedEdge,
    parlayEV,
  } = useParlayStore();
  const { loading, result, calculateParlay, saveParlay } = useParlayCalculator();
  const { refreshSavedParlays, refreshHistory } = useParlayData();

  useEffect(() => {
    if (selectedBets.length >= 2) {
      enrichParlay();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBets.length]);

  const handleCalculate = async () => {
    await calculateParlay(selectedBets, stake);
    refreshHistory();
  };

  const handleSave = async () => {
    const name = prompt("Enter a name for this parlay:");
    if (!name) return;

    const success = await saveParlay(selectedBets, stake, name);
    if (success) {
      refreshSavedParlays();
    }
  };

  if (selectedBets.length === 0) {
    return (
      <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div style={{ animation: 'slide-up 0.4s ease-out both' }}>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight">
                Parlay Builder
              </h1>
              <Calculator className="w-8 h-8" style={{ color: '#6366f1' }} />
            </div>
            <p className="text-sm" style={{ color: '#64748b' }}>
              Build your own parlay or use our AI-suggested picks
            </p>
          </div>

          <div className="card-glow rounded-xl p-8 text-center mt-8 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.4s ease-out 0.06s both' }}>
            <AlertCircle className="w-12 h-12 mx-auto mb-4" style={{ color: '#64748b' }} />
            <h2 className="text-xl font-bold text-white font-[Oswald] tracking-tight mb-2">No Bets Selected</h2>
            <p className="mb-4" style={{ color: '#94a3b8' }}>
              Go to the Odds page to build your own parlay, or use a suggested parlay below
            </p>
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => navigate('/odds')}
                className="px-6 py-3 text-white rounded-lg font-semibold text-sm transition-all hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}
              >
                Browse Odds
              </button>
              <button
                onClick={() => navigate('/best-bets')}
                className="px-6 py-3 text-white rounded-lg font-semibold text-sm transition-all hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
              >
                Best Value Bets
              </button>
            </div>
          </div>

          <div style={{ animation: 'slide-up 0.4s ease-out 0.1s both' }}>
            <SuggestedParlays />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight">
              Parlay Calculator
            </h1>
            <Calculator className="w-8 h-8" style={{ color: '#6366f1' }} />
          </div>
          <p className="text-sm" style={{ color: '#64748b' }}>
            Calculate combined odds, probabilities, and expected value for your parlays
          </p>
        </div>

        {/* Correlation Warnings */}
        {correlationWarnings && correlationWarnings.length > 0 && (
          <div className="mt-6 mb-6 p-4 rounded-xl border card-glow" style={{ background: 'rgba(245, 158, 11, 0.08)', borderColor: 'rgba(245, 158, 11, 0.2)', animation: 'fade-in 0.3s ease-out' }}>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-5 h-5" style={{ color: '#f59e0b' }} />
              <h3 className="font-semibold" style={{ color: '#f59e0b' }}>Correlation Warnings</h3>
            </div>
            {correlationWarnings.map((warning, idx) => (
              <p key={idx} className="text-sm ml-7" style={{ color: '#fcd34d' }}>{warning}</p>
            ))}
          </div>
        )}

        {/* ML Insights Summary */}
        {combinedModelProb !== null && (
          <div className={`mt-6 mb-6 p-4 rounded-xl border card-glow`}
            style={{
              background: combinedEdge > 0 ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)',
              borderColor: combinedEdge > 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              animation: 'fade-in 0.3s ease-out',
            }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Brain className="w-6 h-6" style={{ color: '#6366f1' }} />
                <div>
                  <h3 className="font-semibold text-white">ML Analysis</h3>
                  <p className="text-sm" style={{ color: '#64748b' }}>Combined parlay probability from our model</p>
                </div>
              </div>
              <div className="flex items-center gap-6 text-right">
                <div>
                  <p className="text-xs" style={{ color: '#64748b' }}>Win Probability</p>
                  <p className="text-xl font-bold text-white font-[Oswald] tracking-tight">{(combinedModelProb * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: '#64748b' }}>Edge</p>
                  <p className={`text-xl font-bold font-[Oswald] tracking-tight ${combinedEdge > 0 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {combinedEdge > 0 ? '+' : ''}{combinedEdge?.toFixed(1)}%
                  </p>
                </div>
                {parlayEV !== null && (
                  <div>
                    <p className="text-xs" style={{ color: '#64748b' }}>Expected Value</p>
                    <p className={`text-xl font-bold font-[Oswald] tracking-tight ${parlayEV > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {parlayEV > 0 ? '+' : ''}{parlayEV}%
                    </p>
                  </div>
                )}
              </div>
            </div>
            {combinedEdge > 0 && (
              <div className="mt-3 flex items-center gap-2 text-sm" style={{ color: '#34d399' }}>
                <TrendingUp className="w-4 h-4" />
                <span>This parlay has positive expected value based on our ML model</span>
              </div>
            )}
          </div>
        )}

        {/* Refresh ML Button */}
        {isEnriching && (
          <div className="mb-6 flex items-center justify-center gap-2" style={{ color: '#818cf8', animation: 'fade-in 0.2s ease-out' }}>
            <RefreshCw className="w-5 h-5 animate-spin" />
            <span>Analyzing parlay with ML model...</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Left Column - Bet Input */}
          <div className="lg:col-span-2 space-y-4 stagger-children">
            <div className="card-glow rounded-xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white font-[Oswald] tracking-tight">
                  Parlay Legs ({selectedBets.length})
                </h2>
                <button
                  onClick={() => enrichParlay()}
                  disabled={isEnriching}
                  className="flex items-center gap-2 px-3 py-1.5 text-white rounded-lg text-sm font-semibold transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}
                >
                  <Brain className="w-4 h-4" />
                  {isEnriching ? 'Analyzing...' : 'Refresh ML'}
                </button>
              </div>

              {selectedBets.map((bet, index) => (
                <ParlayBetLeg
                  key={index}
                  bet={bet}
                  index={index}
                  onUpdate={updateBet}
                  onRemove={removeBet}
                  canRemove={selectedBets.length > 2}
                />
              ))}
            </div>

            {/* Stake Input */}
            <div className="card-glow rounded-xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>
                Stake Amount ($)
              </label>
              <input
                type="number"
                value={stake}
                onChange={(e) => setStake(e.target.value)}
                className="w-full px-4 py-3 rounded-lg text-white text-lg font-semibold focus:outline-none focus:ring-2 transition-all"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#6366f1' }}
                placeholder="100"
              />
            </div>

            {/* Calculate Button */}
            <button
              onClick={handleCalculate}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-6 py-4 text-white rounded-lg font-bold text-lg transition-all hover:opacity-90 shadow-lg disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}
            >
              <Calculator className="w-6 h-6" />
              {loading ? "Calculating..." : "Calculate Expected Value"}
            </button>
          </div>

          {/* Right Column - Results & Quick Add */}
          <div className="space-y-4 stagger-children">
            {result ? (
              <ParlayResults result={result} onSave={handleSave} />
            ) : (
              <div className="card-glow rounded-xl p-6 text-center border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
                <Calculator className="w-16 h-16 mx-auto mb-4" style={{ color: '#64748b' }} />
                <p style={{ color: '#64748b' }}>Enter your bets and calculate to see results</p>
              </div>
            )}

            <QuickAddSearch />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParlayCalculator;
