import { X, Calculator, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import useParlayStore from "../../stores/parlayStore";

/**
 * Floating sidebar showing selected parlay bets
 */
const ParlayBuilderSidebar = () => {
  const navigate = useNavigate();
  const { selectedBets, removeBet, clearAll, getBetCount } = useParlayStore();
  const betCount = getBetCount();

  if (betCount === 0) return null;

  const handleCalculate = () => {
    navigate('/parlay-calculator');
  };

  return (
    <div className="fixed right-4 bottom-4 w-80 bg-gray-800 border-2 border-blue-500 rounded-xl shadow-2xl z-50 max-h-[600px] flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-4 rounded-t-xl flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-white" />
          <h3 className="font-bold text-white">Parlay Builder</h3>
          <span className="bg-white text-blue-700 px-2 py-0.5 rounded-full text-xs font-bold">
            {betCount}
          </span>
        </div>
        <button
          onClick={clearAll}
          className="text-white hover:text-red-300 transition"
          title="Clear all"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Bet List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {selectedBets.map((bet, index) => (
          <div
            key={index}
            className="bg-gray-900 border border-gray-700 rounded-lg p-3 hover:border-gray-600 transition"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <p className="text-white font-semibold text-sm">{bet.team}</p>
                <p className="text-gray-400 text-xs">{bet.event_name}</p>
              </div>
              <button
                onClick={() => removeBet(index)}
                className="text-red-400 hover:text-red-300 transition ml-2"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">{bet.bet_type}</span>
              <span className="text-blue-400 font-bold">
                {bet.odds > 0 ? '+' : ''}{bet.odds}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={handleCalculate}
          disabled={betCount < 2}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-lg transition font-bold disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Calculator className="w-5 h-5" />
          Calculate Parlay
        </button>
        {betCount < 2 && (
          <p className="text-center text-xs text-gray-400 mt-2">
            Add at least 2 bets to calculate
          </p>
        )}
      </div>
    </div>
  );
};

export default ParlayBuilderSidebar;
