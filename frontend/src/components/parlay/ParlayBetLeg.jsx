import { Trash2 } from "lucide-react";

/**
 * Single Responsibility: Renders a single parlay bet leg with event data
 */
const ParlayBetLeg = ({ bet, index, onUpdate, onRemove, canRemove }) => {
  const handleChange = (field, value) => {
    onUpdate(index, field, value);
  };

  return (
    <div className="mb-4 p-4 bg-gray-800 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex-1">
          <span className="font-semibold text-white">Leg {index + 1}</span>
          <p className="text-sm text-gray-400 mt-1">{bet.event_name}</p>
        </div>
        <button
          onClick={() => onRemove(index)}
          className="text-red-400 hover:text-red-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={!canRemove}
          title={!canRemove ? "Minimum 2 legs required" : "Remove leg"}
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Team (read-only) */}
        <div className="col-span-2">
          <label className="block text-xs text-gray-500 mb-1">Team</label>
          <div className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white">
            {bet.team}
          </div>
        </div>

        {/* Bet Type & Selection (read-only) */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Type</label>
          <div className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white">
            {bet.bet_type}
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Selection</label>
          <div className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white">
            {bet.selection}
          </div>
        </div>

        {/* Odds (editable for manual override) */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Odds (editable)</label>
          <input
            type="number"
            value={bet.odds}
            onChange={(e) => handleChange("odds", e.target.value)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Win Probability Override */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Win Prob % (optional)</label>
          <input
            type="number"
            step="0.01"
            placeholder="Override"
            value={bet.win_prob || ''}
            onChange={(e) => handleChange("win_prob", e.target.value)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>
    </div>
  );
};

export default ParlayBetLeg;
