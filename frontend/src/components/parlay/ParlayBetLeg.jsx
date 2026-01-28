import { Trash2, TrendingUp, TrendingDown, Brain, AlertTriangle } from "lucide-react";

/**
 * Enhanced Parlay Bet Leg Component
 * Shows ML predictions, edge calculations, and value indicators
 */
const ParlayBetLeg = ({ bet, index, onUpdate, onRemove, canRemove, compact = false }) => {
  const handleChange = (field, value) => {
    onUpdate(index, field, value);
  };

  // Determine edge styling
  const getEdgeStyle = () => {
    if (bet.edge_pct === undefined || bet.edge_pct === null) return null;
    if (bet.edge_pct > 10) return { color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/40' };
    if (bet.edge_pct > 0) return { color: 'text-green-300', bg: 'bg-green-500/10', border: 'border-green-500/30' };
    if (bet.edge_pct > -5) return { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' };
    return { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' };
  };

  const getConfidenceBadge = () => {
    if (!bet.confidence) return null;
    const styles = {
      High: 'bg-green-500/20 text-green-400 border-green-500/40',
      Medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
      Low: 'bg-gray-500/20 text-gray-400 border-gray-500/40',
      Negative: 'bg-red-500/20 text-red-400 border-red-500/40',
    };
    return styles[bet.confidence] || styles.Low;
  };

  const edgeStyle = getEdgeStyle();
  const hasMLData = bet.model_prob !== undefined && bet.model_prob !== null;

  // Compact view for sidebar
  if (compact) {
    return (
      <div className={`p-3 rounded-lg border transition ${
        bet.has_value 
          ? 'bg-green-900/20 border-green-500/30' 
          : 'bg-gray-800 border-gray-700 hover:border-gray-600'
      }`}>
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1 min-w-0">
            <p className="text-white font-semibold text-sm truncate">{bet.team}</p>
            <p className="text-gray-400 text-xs truncate">{bet.event_name}</p>
          </div>
          <button
            onClick={() => onRemove(index)}
            className="text-red-400 hover:text-red-300 transition ml-2 flex-shrink-0"
            title="Remove bet"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
        
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="text-gray-500">{bet.bet_type}</span>
            <span className="text-green-400 font-bold">
              {bet.odds > 0 ? '+' : ''}{bet.odds}
            </span>
          </div>
          
          {hasMLData && (
            <div className="flex items-center gap-2">
              {bet.edge_pct !== null && (
                <span className={`font-semibold ${edgeStyle?.color || 'text-gray-400'}`}>
                  {bet.edge_pct > 0 ? '+' : ''}{bet.edge_pct?.toFixed(1)}%
                </span>
              )}
              {bet.has_value && (
                <TrendingUp className="w-3 h-3 text-green-400" />
              )}
            </div>
          )}
        </div>
        
        {/* ML Probability Bar */}
        {hasMLData && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-500 flex items-center gap-1">
                <Brain className="w-3 h-3" /> ML Prob
              </span>
              <span className="text-white font-semibold">
                {(bet.model_prob * 100).toFixed(0)}%
              </span>
            </div>
            <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full ${bet.has_value ? 'bg-green-500' : 'bg-gray-500'}`}
                style={{ width: `${bet.model_prob * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>
    );
  }

  // Full view for calculator page
  return (
    <div className={`mb-4 p-4 rounded-lg border transition-colors ${
      bet.has_value 
        ? 'bg-green-900/10 border-green-500/30 hover:border-green-500/50' 
        : 'bg-gray-800 border-gray-700 hover:border-gray-600'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-7 h-7 rounded-full bg-gray-700 text-white text-sm font-bold">
            {index + 1}
          </span>
          <div>
            <p className="font-semibold text-white">{bet.team}</p>
            <p className="text-sm text-gray-400">{bet.event_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {bet.confidence && (
            <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${getConfidenceBadge()}`}>
              {bet.confidence}
            </span>
          )}
          <button
            onClick={() => onRemove(index)}
            className="text-red-400 hover:text-red-300 transition disabled:opacity-50 disabled:cursor-not-allowed p-1"
            disabled={!canRemove}
            title={!canRemove ? "Minimum 2 legs required" : "Remove leg"}
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* ML Insights Row */}
      {hasMLData && (
        <div className={`mb-3 p-3 rounded-lg border ${edgeStyle?.bg} ${edgeStyle?.border}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs text-gray-400 flex items-center gap-1">
                  <Brain className="w-3 h-3" /> Model Probability
                </p>
                <p className="text-lg font-bold text-white">
                  {(bet.model_prob * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Implied Prob</p>
                <p className="text-lg font-semibold text-gray-300">
                  {bet.implied_prob ? (bet.implied_prob * 100).toFixed(1) : '--'}%
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">Edge</p>
              <p className={`text-2xl font-bold ${edgeStyle?.color}`}>
                {bet.edge_pct > 0 ? '+' : ''}{bet.edge_pct?.toFixed(1)}%
              </p>
            </div>
          </div>
          
          {/* Value indicator */}
          {bet.has_value ? (
            <div className="mt-2 flex items-center gap-2 text-green-400 text-xs">
              <TrendingUp className="w-4 h-4" />
              <span>Positive expected value detected</span>
            </div>
          ) : bet.edge_pct !== null && bet.edge_pct < 0 && (
            <div className="mt-2 flex items-center gap-2 text-yellow-400 text-xs">
              <AlertTriangle className="w-4 h-4" />
              <span>Negative edge - bookmaker has advantage</span>
            </div>
          )}
        </div>
      )}

      {/* Bet Details Grid */}
      <div className="grid grid-cols-4 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Type</label>
          <div className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm">
            {bet.bet_type}
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Selection</label>
          <div className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm">
            {bet.selection}
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Odds</label>
          <input
            type="number"
            value={bet.odds}
            onChange={(e) => handleChange("odds", e.target.value)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Win Prob %</label>
          <input
            type="number"
            step="0.01"
            placeholder="Override"
            value={bet.win_prob || ''}
            onChange={(e) => handleChange("win_prob", e.target.value)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-600 text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
          />
        </div>
      </div>
    </div>
  );
};

export default ParlayBetLeg;
