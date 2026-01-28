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

/**
 * SOLID Principles Applied:
 * - Single Responsibility: Main component only orchestrates child components
 * - Open/Closed: Extensible through props and composition
 * - Liskov Substitution: Components can be swapped with compatible interfaces
 * - Interface Segregation: Each component has focused, minimal interface
 * - Dependency Inversion: Depends on hooks (abstractions) not implementations
 */
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

  // Auto-enrich when bets change
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

  // Show suggested parlays if no bets selected
  if (selectedBets.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-2 flex items-center">
              <Calculator className="w-10 h-10 mr-3 text-blue-400" />
              Parlay Builder
            </h1>
            <p className="text-gray-400">
              Build your own parlay or use our AI-suggested picks
            </p>
          </div>

          {/* Empty State Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-8 text-center mb-8">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 text-gray-600" />
            <h2 className="text-xl font-bold text-white mb-2">No Bets Selected</h2>
            <p className="text-gray-400 mb-4">
              Go to the Odds page to build your own parlay, or use a suggested parlay below
            </p>
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => navigate('/odds')}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition"
              >
                Browse Odds
              </button>
              <button
                onClick={() => navigate('/best-bets')}
                className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold transition"
              >
                Best Value Bets
              </button>
            </div>
          </div>

          {/* Suggested Parlays */}
          <SuggestedParlays />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2 flex items-center">
            <Calculator className="w-10 h-10 mr-3 text-blue-400" />
            Parlay Expected Value Calculator
          </h1>
          <p className="text-gray-400">
            Calculate combined odds, probabilities, and expected value for your parlays
          </p>
        </div>

        {/* Correlation Warnings */}
        {correlationWarnings && correlationWarnings.length > 0 && (
          <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              <h3 className="font-semibold text-yellow-400">Correlation Warnings</h3>
            </div>
            {correlationWarnings.map((warning, idx) => (
              <p key={idx} className="text-sm text-yellow-300 ml-7">{warning}</p>
            ))}
          </div>
        )}

        {/* ML Insights Summary */}
        {combinedModelProb !== null && (
          <div className={`mb-6 p-4 rounded-xl border ${
            combinedEdge > 0 
              ? 'bg-green-900/20 border-green-500/30' 
              : 'bg-yellow-900/20 border-yellow-500/30'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Brain className="w-6 h-6 text-blue-400" />
                <div>
                  <h3 className="font-semibold text-white">ML Analysis</h3>
                  <p className="text-sm text-gray-400">Combined parlay probability from our model</p>
                </div>
              </div>
              <div className="flex items-center gap-6 text-right">
                <div>
                  <p className="text-xs text-gray-400">Win Probability</p>
                  <p className="text-xl font-bold text-white">{(combinedModelProb * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Edge</p>
                  <p className={`text-xl font-bold ${combinedEdge > 0 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {combinedEdge > 0 ? '+' : ''}{combinedEdge?.toFixed(1)}%
                  </p>
                </div>
                {parlayEV !== null && (
                  <div>
                    <p className="text-xs text-gray-400">Expected Value</p>
                    <p className={`text-xl font-bold ${parlayEV > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {parlayEV > 0 ? '+' : ''}{parlayEV}%
                    </p>
                  </div>
                )}
              </div>
            </div>
            {combinedEdge > 0 && (
              <div className="mt-3 flex items-center gap-2 text-green-400 text-sm">
                <TrendingUp className="w-4 h-4" />
                <span>This parlay has positive expected value based on our ML model</span>
              </div>
            )}
          </div>
        )}

        {/* Refresh ML Button */}
        {isEnriching && (
          <div className="mb-6 flex items-center justify-center gap-2 text-blue-400">
            <RefreshCw className="w-5 h-5 animate-spin" />
            <span>Analyzing parlay with ML model...</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Bet Input */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">
                  Parlay Legs ({selectedBets.length})
                </h2>
                <button
                  onClick={() => enrichParlay()}
                  disabled={isEnriching}
                  className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg text-sm font-semibold transition"
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
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-xl">
              <label className="block text-sm font-semibold text-gray-400 mb-2">
                Stake Amount ($)
              </label>
              <input
                type="number"
                value={stake}
                onChange={(e) => setStake(e.target.value)}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg font-semibold"
                placeholder="100"
              />
            </div>

            {/* Calculate Button */}
            <button
              onClick={handleCalculate}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition font-bold text-lg shadow-lg disabled:opacity-50"
            >
              <Calculator className="w-6 h-6" />
              {loading ? "Calculating..." : "Calculate Expected Value"}
            </button>
          </div>

          {/* Right Column - Results & Quick Add */}
          <div className="space-y-4">
            {result ? (
              <ParlayResults result={result} onSave={handleSave} />
            ) : (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 text-center text-gray-500">
                <Calculator className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <p>Enter your bets and calculate to see results</p>
              </div>
            )}
            
            {/* Quick Add Search */}
            <QuickAddSearch />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParlayCalculator;
