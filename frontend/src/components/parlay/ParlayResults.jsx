import { Save, TrendingUp, AlertTriangle } from "lucide-react";

/**
 * Single Responsibility: Display parlay calculation results
 */
const ParlayResults = ({ result, onSave }) => {
  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case "LOW": return "text-green-400 bg-green-900/50 border-green-700";
      case "MEDIUM": return "text-yellow-400 bg-yellow-900/50 border-yellow-700";
      case "HIGH": return "text-orange-400 bg-orange-900/50 border-orange-700";
      case "VERY_HIGH": return "text-red-400 bg-red-900/50 border-red-700";
      default: return "text-gray-400 bg-gray-800 border-gray-700";
    }
  };

  const getRecommendationStyle = () => {
    if (result.expected_value >= 0.05) {
      return "bg-green-900/30 border-green-700";
    } else if (result.expected_value >= 0) {
      return "bg-yellow-900/30 border-yellow-700";
    }
    return "bg-red-900/30 border-red-700";
  };

  return (
    <div className="space-y-4">
      {/* Results Card */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">Results</h2>
          <button
            onClick={onSave}
            className="flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition text-sm font-semibold"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
        </div>

        <div className="space-y-3">
          <ResultRow label="Combined Odds" value={`${result.combined_odds > 0 ? '+' : ''}${result.combined_odds.toFixed(0)}`} />
          <ResultRow label="Win Probability" value={`${(result.combined_probability * 100).toFixed(2)}%`} />
          <ResultRow 
            label="Projected Payout" 
            value={`$${parseFloat(result.projected_payout).toFixed(2)}`}
            valueClass="text-green-400"
          />
          <ResultRow 
            label="Expected Profit" 
            value={`$${parseFloat(result.expected_profit).toFixed(2)}`}
            valueClass={parseFloat(result.expected_profit) >= 0 ? 'text-green-400' : 'text-red-400'}
          />
          <ResultRow 
            label="Expected Value" 
            value={`${(result.expected_value * 100).toFixed(2)}%`}
            valueClass={result.expected_value >= 0 ? 'text-green-400' : 'text-red-400'}
          />
          <ResultRow label="Break-even Prob" value={`${(result.break_even_probability * 100).toFixed(2)}%`} />
          <ResultRow label="Kelly Criterion" value={`${(result.kelly_criterion * 100).toFixed(2)}%`} />
          
          <div className="flex justify-between items-center py-2 border-t border-gray-700">
            <span className="text-gray-400">Risk Level</span>
            <span className={`px-3 py-1 rounded-full text-sm font-bold border ${getRiskColor(result.risk_level)}`}>
              {result.risk_level}
            </span>
          </div>
        </div>
      </div>

      {/* Recommendation Card */}
      <div className={`rounded-xl shadow-xl p-6 border ${getRecommendationStyle()}`}>
        <div className="flex items-start gap-3">
          {result.expected_value >= 0 ? (
            <TrendingUp className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0 mt-1" />
          )}
          <div>
            <h3 className="font-bold text-white mb-2">Recommendation</h3>
            <p className="text-gray-300 text-sm leading-relaxed">{result.recommendation}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const ResultRow = ({ label, value, valueClass = "text-white" }) => (
  <div className="flex justify-between items-center py-2 border-b border-gray-700">
    <span className="text-gray-400">{label}</span>
    <span className={`font-bold text-lg ${valueClass}`}>{value}</span>
  </div>
);

export default ParlayResults;
