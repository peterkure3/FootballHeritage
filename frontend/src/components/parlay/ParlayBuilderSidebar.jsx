import { API_BASE_URL } from '../../utils/api';
import { useState, useMemo } from "react";
import { X, Trash2, TrendingUp, DollarSign, Brain, AlertTriangle, RefreshCw } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import useParlayStore from "../../stores/parlayStore";
import useAuthStore from "../../stores/authStore";
import ParlayBetLeg from "./ParlayBetLeg";

/**
 * Persistent Parlay Builder Sidebar
 * 
 * Features:
 * - Fixed right-side panel (w-80)
 * - Real-time odds calculation
 * - Stake input with payout preview
 * - Place parlay bet with React Query mutation
 * - Optimistic UI updates
 * - Input validation and error handling
 * 
 * UX Improvements:
 * - Always visible when bets are selected
 * - Collapsible for more screen space
 * - Live payout calculations
 * - Toast notifications for feedback
 */
const ParlayBuilderSidebar = () => {
  // Zustand store for parlay state
  const { 
    selectedBets, 
    removeBet, 
    updateBet,
    clearAll, 
    getBetCount,
    totalOdds,
    calculatePayout,
    enrichParlay,
    isEnriching,
    correlationWarnings,
    combinedModelProb,
    combinedEdge,
    parlayEV,
  } = useParlayStore();
  
  // Auth store for user token
  const { token, user } = useAuthStore();
  
  // Local state
  const [stake, setStake] = useState(10); // Default $10 stake
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false); // For detailed view
  
  const betCount = getBetCount();

  // Calculate payout in real-time using memoization for performance
  // totalOdds is included in calculatePayout closure, so we only need stake and the function
  const payoutInfo = useMemo(() => {
    return calculatePayout(stake);
  }, [stake, calculatePayout]);

  /**
   * React Query mutation for placing parlay bet
   * Handles API call, loading state, and error handling
   */
  const placeParlayMutation = useMutation({
    mutationFn: async (parlayData) => {
      const response = await fetch(`${API_BASE_URL}/parlay/place`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(parlayData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to place parlay bet');
      }

      return response.json();
    },
    onSuccess: (data) => {
      // Success feedback
      toast.success(`Parlay bet placed! Bet ID: ${data.bet_id || 'N/A'}`, {
        duration: 5000,
        icon: '🎉',
      });
      
      // Clear parlay after successful placement
      clearAll();
      setStake(10); // Reset stake
    },
    onError: (error) => {
      // Error feedback
      toast.error(error.message || 'Failed to place parlay bet', {
        duration: 6000,
      });
    },
  });

  /**
   * Handle place bet button click
   * Validates inputs before submitting
   */
  const handlePlaceBet = () => {
    // Validation: Minimum 2 legs
    if (betCount < 2) {
      toast.error('Add at least 2 bets to place a parlay');
      return;
    }

    // Validation: Stake amount
    if (stake <= 0) {
      toast.error('Stake must be greater than $0');
      return;
    }

    // Validation: Maximum stake (example: $1000)
    if (stake > 1000) {
      toast.error('Maximum stake is $1000');
      return;
    }

    // Validation: Check user balance
    if (user?.balance && stake > user.balance) {
      toast.error('Insufficient balance');
      return;
    }

    // Prepare parlay data for API
    const parlayData = {
      legs: selectedBets.map(bet => ({
        event_id: bet.event_id,
        bet_type: bet.bet_type,
        selection: bet.selection,
        odds: bet.odds,
        team: bet.team,
      })),
      stake: parseFloat(stake),
      total_odds: totalOdds,
    };

    // Submit mutation
    placeParlayMutation.mutate(parlayData);
  };

  /**
   * Handle stake input change with validation
   */
  const handleStakeChange = (e) => {
    const value = e.target.value;
    
    // Allow empty input for user to type
    if (value === '') {
      setStake('');
      return;
    }
    
    // Parse and validate
    const numValue = parseFloat(value);
    if (!isNaN(numValue) && numValue >= 0) {
      setStake(numValue);
    }
  };

  // Don't render if no bets selected
  if (betCount === 0) return null;

  return (
    <>
      {/* Fixed right sidebar - always visible */}
      <div 
        className={`fixed right-0 top-0 h-screen w-80 bg-card border-l-2 border-green-500 shadow-2xl z-40 transition-transform duration-300 ${
          isCollapsed ? 'translate-x-full' : 'translate-x-0'
        } flex flex-col`}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-white" />
            <h3 className="font-bold text-heritage-ink">Parlay Builder</h3>
            <span className="bg-white text-green-700 px-2 py-0.5 rounded-full text-xs font-bold">
              {betCount}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-heritage-ink hover:text-heritage-ink transition"
              title={isExpanded ? "Simple view" : "Detailed view"}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
              </svg>
            </button>
            <button
              onClick={clearAll}
              className="text-heritage-ink hover:text-red-700 transition"
              title="Clear all bets"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Bet List - Scrollable */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {isExpanded ? (
            // Detailed view with editable fields
            selectedBets.map((bet, index) => (
              <ParlayBetLeg
                key={index}
                bet={bet}
                index={index}
                onUpdate={updateBet}
                onRemove={removeBet}
                canRemove={betCount > 2}
              />
            ))
          ) : (
            // Simple compact view
            selectedBets.map((bet, index) => (
              <div
                key={index}
                className="bg-card border border-card-border rounded-lg p-3 hover:border-card-border transition"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <p className="text-heritage-ink font-semibold text-sm">{bet.team}</p>
                    <p className="text-heritage-muted text-xs truncate">{bet.event_name}</p>
                  </div>
                  <button
                    onClick={() => removeBet(index)}
                    className="text-red-700 hover:text-red-700 transition ml-2"
                    title="Remove bet"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-heritage-muted">{bet.bet_type}</span>
                  <span className="text-green-700 font-bold">
                    {bet.odds > 0 ? '+' : ''}{bet.odds}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Correlation Warnings */}
        {correlationWarnings && correlationWarnings.length > 0 && (
          <div className="px-4 py-2 bg-yellow-500/10 border-t border-yellow-500/30">
            {correlationWarnings.map((warning, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs text-yellow-700 py-1">
                <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                <span>{warning}</span>
              </div>
            ))}
          </div>
        )}

        {/* Calculation Section */}
        <div className="border-t border-card-border p-4 space-y-3 bg-gray-850">
          {/* ML Enrich Button */}
          <button
            onClick={() => enrichParlay()}
            disabled={isEnriching || betCount === 0}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-card-hover text-white rounded-lg text-sm font-semibold transition"
          >
            {isEnriching ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Brain className="w-4 h-4" />
                Get ML Predictions
              </>
            )}
          </button>

          {/* ML Insights Display */}
          {combinedModelProb !== null && (
            <div className={`rounded-lg p-3 border ${
              combinedEdge > 0 
                ? 'bg-green-900/20 border-green-500/30' 
                : 'bg-yellow-900/20 border-yellow-500/30'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-4 h-4 text-blue-700" />
                <span className="text-sm font-semibold text-heritage-ink">ML Analysis</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-heritage-muted">Win Prob</span>
                  <p className="text-heritage-ink font-bold">{(combinedModelProb * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <span className="text-heritage-muted">Edge</span>
                  <p className={`font-bold ${combinedEdge > 0 ? 'text-green-700' : 'text-yellow-700'}`}>
                    {combinedEdge > 0 ? '+' : ''}{combinedEdge?.toFixed(1)}%
                  </p>
                </div>
              </div>
              {parlayEV !== null && (
                <div className="mt-2 pt-2 border-t border-card-border">
                  <div className="flex items-center justify-between">
                    <span className="text-heritage-muted text-xs">Expected Value</span>
                    <span className={`font-bold ${parlayEV > 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {parlayEV > 0 ? '+' : ''}{parlayEV}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Total Odds Display */}
          <div className="bg-card border border-card-border rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-heritage-muted text-sm">Total Odds</span>
              <span className="text-green-700 font-bold text-lg">
                {totalOdds > 0 ? '+' : ''}{totalOdds}
              </span>
            </div>
            <div className="text-xs text-heritage-muted">
              {betCount} leg{betCount !== 1 ? 's' : ''} combined
            </div>
          </div>

          {/* Stake Input */}
          <div>
            <label className="block text-heritage-muted text-sm font-semibold mb-2">
              Stake Amount
            </label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-heritage-muted" />
              <input
                type="number"
                value={stake}
                onChange={handleStakeChange}
                min="1"
                max="1000"
                step="1"
                className="w-full pl-10 pr-4 py-3 bg-card border border-card-border rounded-lg text-heritage-ink text-lg font-semibold focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="10.00"
              />
            </div>
            <p className="text-xs text-heritage-muted mt-1">
              Min: $1 • Max: $1000
            </p>
          </div>

          {/* Payout Preview */}
          <div className="bg-gradient-to-r from-green-900/30 to-blue-900/30 border border-green-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-heritage-muted text-sm">Potential Payout</span>
              <span className="text-heritage-ink font-bold text-xl">
                ${payoutInfo.payout.toFixed(2)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-heritage-muted text-xs">Profit</span>
              <span className="text-green-700 font-semibold text-sm">
                +${payoutInfo.profit.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Place Bet Button */}
          <button
            onClick={handlePlaceBet}
            disabled={betCount < 2 || placeParlayMutation.isPending || stake <= 0}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-lg transition font-bold text-lg shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {placeParlayMutation.isPending ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Placing Bet...
              </>
            ) : (
              <>
                <TrendingUp className="w-5 h-5" />
                Place Parlay Bet
              </>
            )}
          </button>
          
          {betCount < 2 && (
            <p className="text-center text-xs text-yellow-700">
              ⚠️ Add at least 2 bets to place parlay
            </p>
          )}
        </div>
      </div>

      {/* Collapse/Expand Toggle Button */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className={`fixed right-0 top-1/2 transform -translate-y-1/2 bg-green-600 hover:bg-green-700 text-white p-3 rounded-l-lg shadow-lg z-50 transition-all ${
          isCollapsed ? 'translate-x-0' : '-translate-x-80'
        }`}
        title={isCollapsed ? "Show parlay builder" : "Hide parlay builder"}
      >
        <svg 
          className={`w-5 h-5 transition-transform ${
            isCollapsed ? 'rotate-180' : ''
          }`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </>
  );
};

export default ParlayBuilderSidebar;
