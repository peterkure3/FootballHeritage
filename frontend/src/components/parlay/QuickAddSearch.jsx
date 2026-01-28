import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Plus, Check, X, TrendingUp, Calendar } from 'lucide-react';
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

const QuickAddSearch = ({ onClose }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [showValueOnly, setShowValueOnly] = useState(true);
  const { addBet, isBetSelected } = useParlayStore();

  // Fetch value bets for quick add
  const { data, isLoading } = useQuery({
    queryKey: ['quick-add-bets'],
    queryFn: async () => {
      const response = await fetch(`${PIPELINE_API_URL}/best-value-bets?limit=50&min_edge=0.02`);
      if (!response.ok) throw new Error('Failed to fetch bets');
      return response.json();
    },
    staleTime: 60000,
  });

  const bets = useMemo(() => {
    const allBets = Array.isArray(data) ? data : [];
    
    // Filter by search term
    let filtered = allBets;
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = allBets.filter(bet => 
        bet.home_team?.toLowerCase().includes(term) ||
        bet.away_team?.toLowerCase().includes(term) ||
        bet.competition?.toLowerCase().includes(term) ||
        bet.selection?.toLowerCase().includes(term)
      );
    }
    
    // Filter by value only
    if (showValueOnly) {
      filtered = filtered.filter(bet => bet.edge_pct > 5);
    }
    
    return filtered.slice(0, 20);
  }, [data, searchTerm, showValueOnly]);

  const handleAddBet = (bet) => {
    // Extract selection type
    const selectionMatch = bet.selection.match(/\((Home|Away|Draw)\s*Win\)/i);
    const selection = selectionMatch 
      ? selectionMatch[1].toUpperCase() === 'HOME' ? 'HOME' 
        : selectionMatch[1].toUpperCase() === 'AWAY' ? 'AWAY' 
        : 'DRAW'
      : bet.selection.includes('Home') ? 'HOME' 
        : bet.selection.includes('Away') ? 'AWAY' 
        : 'DRAW';
    
    const event = {
      id: bet.match_id,
      home_team: bet.home_team,
      away_team: bet.away_team,
      event_date: bet.match_date,
      league: bet.competition,
    };
    
    // Convert decimal odds to American
    const americanOdds = bet.decimal_odds >= 2 
      ? Math.round((bet.decimal_odds - 1) * 100)
      : Math.round(-100 / (bet.decimal_odds - 1));
    
    const success = addBet(event, 'MONEYLINE', selection, americanOdds);
    if (success) {
      toast.success(`Added ${bet.selection}!`, { icon: '🎯', duration: 2000 });
    } else {
      toast.error('Already in parlay or limit reached');
    }
  };

  const isSelected = (bet) => {
    const selectionMatch = bet.selection.match(/\((Home|Away|Draw)\s*Win\)/i);
    const selection = selectionMatch 
      ? selectionMatch[1].toUpperCase() === 'HOME' ? 'HOME' 
        : selectionMatch[1].toUpperCase() === 'AWAY' ? 'AWAY' 
        : 'DRAW'
      : bet.selection.includes('Home') ? 'HOME' 
        : bet.selection.includes('Away') ? 'AWAY' 
        : 'DRAW';
    return isBetSelected(bet.match_id, 'MONEYLINE', selection);
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <h3 className="font-bold text-white flex items-center gap-2">
          <Search className="w-5 h-5 text-blue-400" />
          Quick Add Bets
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Search & Filters */}
      <div className="p-4 border-b border-gray-700 space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search teams, leagues..."
            className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showValueOnly}
            onChange={(e) => setShowValueOnly(e.target.checked)}
            className="w-4 h-4 rounded bg-gray-900 border-gray-700 text-green-500 focus:ring-green-500"
          />
          <span className="text-sm text-gray-400">Show high-value bets only (+5% edge)</span>
        </label>
      </div>

      {/* Results */}
      <div className="max-h-80 overflow-y-auto">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        ) : bets.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No bets found</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-700">
            {bets.map((bet, idx) => {
              const selected = isSelected(bet);
              return (
                <div
                  key={`${bet.match_id}-${bet.selection}-${idx}`}
                  className={`p-3 hover:bg-gray-700/50 transition ${selected ? 'bg-green-900/20' : ''}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white truncate">
                        {bet.home_team} vs {bet.away_team}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                        <Calendar className="w-3 h-3" />
                        <span>{formatDate(bet.match_date)}</span>
                        <span className="text-gray-600">•</span>
                        <span>{bet.competition || 'Football'}</span>
                      </div>
                    </div>
                    
                    <div className="text-right flex-shrink-0">
                      <p className="text-sm font-bold text-green-400">{bet.selection}</p>
                      <div className="flex items-center gap-1 text-xs">
                        <TrendingUp className="w-3 h-3 text-green-400" />
                        <span className="text-green-400">+{bet.edge_pct?.toFixed(1)}%</span>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleAddBet(bet)}
                      disabled={selected}
                      className={`p-2 rounded-lg transition ${
                        selected
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-blue-600 hover:bg-blue-700 text-white'
                      }`}
                    >
                      {selected ? <Check className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-700 bg-gray-900/50">
        <p className="text-xs text-gray-500 text-center">
          Showing {bets.length} bets • Click + to add to parlay
        </p>
      </div>
    </div>
  );
};

export default QuickAddSearch;
