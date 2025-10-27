import { useState } from "react";
import { Calculator, AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import ParlayBetLeg from "../components/parlay/ParlayBetLeg";
import ParlayResults from "../components/parlay/ParlayResults";
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

  const { selectedBets, updateBet, removeBet } = useParlayStore();
  const { loading, result, calculateParlay, saveParlay } = useParlayCalculator();
  const { refreshSavedParlays, refreshHistory } = useParlayData();

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

  // Show message if no bets selected
  if (selectedBets.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center">
            <AlertCircle className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <h2 className="text-2xl font-bold text-white mb-2">No Bets Selected</h2>
            <p className="text-gray-400 mb-6">
              Go to the Odds page and select at least 2 bets to build your parlay
            </p>
            <button
              onClick={() => navigate('/odds')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition"
            >
              Browse Odds
            </button>
          </div>
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Bet Input */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-xl">
              <h2 className="text-xl font-bold text-white mb-4">
                Parlay Legs ({selectedBets.length})
              </h2>
              
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

          {/* Right Column - Results */}
          <div className="space-y-4">
            {result ? (
              <ParlayResults result={result} onSave={handleSave} />
            ) : (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 text-center text-gray-500">
                <Calculator className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <p>Enter your bets and calculate to see results</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParlayCalculator;
