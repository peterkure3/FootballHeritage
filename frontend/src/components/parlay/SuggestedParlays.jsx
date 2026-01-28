import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Sparkles, 
  TrendingUp, 
  ChevronDown, 
  ChevronUp, 
  Plus,
  AlertTriangle,
  Target,
  Zap,
  Shield,
  Flame
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import useParlayStore from '../../stores/parlayStore';

const PIPELINE_API_URL = import.meta.env.VITE_PIPELINE_API_URL || "http://localhost:5555/api/v1";

const formatDate = (dateStr) => {
  if (!dateStr) return 'TBD';
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
};

const getRiskIcon = (riskLevel) => {
  switch (riskLevel) {
    case 'Low': return <Shield className="w-4 h-4" />;
    case 'Medium': return <Target className="w-4 h-4" />;
    case 'High': return <Flame className="w-4 h-4" />;
    default: return <Zap className="w-4 h-4" />;
  }
};

const getRiskStyle = (riskLevel) => {
  switch (riskLevel) {
    case 'Low': return 'bg-green-500/20 text-green-400 border-green-500/40';
    case 'Medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40';
    case 'High': return 'bg-red-500/20 text-red-400 border-red-500/40';
    default: return 'bg-gray-500/20 text-gray-400 border-gray-500/40';
  }
};

const SuggestedParlayCard = ({ parlay, onAddToBuilder }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-xl overflow-hidden hover:border-green-500/30 transition">
      {/* Header */}
      <div 
        className="p-4 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-400" />
            <h3 className="font-bold text-white">{parlay.name}</h3>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs font-semibold border flex items-center gap-1 ${getRiskStyle(parlay.risk_level)}`}>
              {getRiskIcon(parlay.risk_level)}
              {parlay.risk_level} Risk
            </span>
            {isExpanded ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </div>
        </div>
        
        <p className="text-sm text-gray-400 mb-3">{parlay.description}</p>
        
        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-xs text-gray-500">Odds</p>
            <p className="text-sm font-bold text-white">
              {parlay.combined_odds_american > 0 ? '+' : ''}{parlay.combined_odds_american}
            </p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-xs text-gray-500">Win Prob</p>
            <p className="text-sm font-bold text-white">
              {(parlay.combined_model_prob * 100).toFixed(1)}%
            </p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-xs text-gray-500">Edge</p>
            <p className={`text-sm font-bold ${parlay.combined_edge_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {parlay.combined_edge_pct > 0 ? '+' : ''}{parlay.combined_edge_pct}%
            </p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-xs text-gray-500">EV</p>
            <p className={`text-sm font-bold ${parlay.expected_value_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {parlay.expected_value_pct > 0 ? '+' : ''}{parlay.expected_value_pct}%
            </p>
          </div>
        </div>
      </div>

      {/* Expanded Legs */}
      {isExpanded && (
        <div className="border-t border-gray-700 p-4 space-y-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-400">
              {parlay.legs.length} Legs
            </span>
            <span className="text-xs text-gray-500">
              Recommended Stake: {parlay.recommended_stake_pct}% of bankroll
            </span>
          </div>
          
          {parlay.legs.map((leg, idx) => (
            <div 
              key={idx}
              className="bg-gray-900/50 rounded-lg p-3 border border-gray-700"
            >
              <div className="flex items-center justify-between mb-1">
                <div>
                  <p className="text-sm font-semibold text-white">{leg.selection}</p>
                  <p className="text-xs text-gray-400">{leg.home_team} vs {leg.away_team}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-green-400">
                    {leg.american_odds > 0 ? '+' : ''}{leg.american_odds}
                  </p>
                  <p className="text-xs text-gray-500">{formatDate(leg.match_date)}</p>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs mt-2 pt-2 border-t border-gray-700">
                <span className="text-gray-500">{leg.competition || 'Football'}</span>
                <div className="flex items-center gap-3">
                  <span className="text-gray-400">
                    Prob: <span className="text-white">{(leg.model_prob * 100).toFixed(0)}%</span>
                  </span>
                  <span className={`font-semibold ${leg.edge_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Edge: {leg.edge_pct > 0 ? '+' : ''}{leg.edge_pct}%
                  </span>
                </div>
              </div>
            </div>
          ))}

          {/* Add to Builder Button */}
          <button
            onClick={() => onAddToBuilder(parlay)}
            className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold transition"
          >
            <Plus className="w-5 h-5" />
            Add to Parlay Builder
          </button>
        </div>
      )}
    </div>
  );
};

const SuggestedParlays = () => {
  const { addBet, clearAll, selectedBets } = useParlayStore();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['suggested-parlays'],
    queryFn: async () => {
      const response = await fetch(`${PIPELINE_API_URL}/suggested-parlays`);
      if (!response.ok) throw new Error('Failed to fetch suggested parlays');
      return response.json();
    },
    staleTime: 60000, // 1 minute
  });

  const handleAddToBuilder = (parlay) => {
    // Clear existing bets if any
    if (selectedBets.length > 0) {
      const confirm = window.confirm(
        'This will replace your current parlay. Continue?'
      );
      if (!confirm) return;
      clearAll();
    }

    // Add each leg to the parlay builder
    let addedCount = 0;
    for (const leg of parlay.legs) {
      const event = {
        id: leg.match_id,
        home_team: leg.home_team,
        away_team: leg.away_team,
        event_date: leg.match_date,
        league: leg.competition,
      };
      
      // Extract selection type from the selection string
      let selection = 'HOME';
      if (leg.selection.includes('AWAY')) selection = 'AWAY';
      else if (leg.selection.includes('DRAW')) selection = 'DRAW';
      
      const success = addBet(event, 'MONEYLINE', selection, leg.american_odds);
      if (success) addedCount++;
    }

    if (addedCount > 0) {
      toast.success(`Added ${addedCount} legs to parlay builder!`, {
        icon: '🎯',
      });
    }
  };

  if (isLoading) {
    return (
      <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Sparkles className="w-6 h-6 text-yellow-400 animate-pulse" />
          <h2 className="text-xl font-bold text-white">AI Suggested Parlays</h2>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-red-400" />
          <h2 className="text-xl font-bold text-white">AI Suggested Parlays</h2>
        </div>
        <p className="text-gray-400 text-center py-4">
          Failed to load suggestions. Make sure the pipeline API is running.
        </p>
        <button
          onClick={() => refetch()}
          className="w-full mt-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
        >
          Retry
        </button>
      </div>
    );
  }

  const parlays = data?.parlays || [];

  return (
    <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Sparkles className="w-6 h-6 text-yellow-400" />
          <div>
            <h2 className="text-xl font-bold text-white">AI Suggested Parlays</h2>
            <p className="text-sm text-gray-400">Auto-generated from best value bets</p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition"
        >
          Refresh
        </button>
      </div>

      {parlays.length === 0 ? (
        <div className="text-center py-8">
          <TrendingUp className="w-12 h-12 mx-auto mb-3 text-gray-600" />
          <p className="text-gray-400">No suggested parlays available</p>
          <p className="text-sm text-gray-500 mt-1">
            Check back when more value bets are detected
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {parlays.map((parlay, idx) => (
            <SuggestedParlayCard
              key={idx}
              parlay={parlay}
              onAddToBuilder={handleAddToBuilder}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuggestedParlays;
