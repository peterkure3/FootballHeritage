import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const PIPELINE_API_URL = import.meta.env?.VITE_PIPELINE_API_URL || "http://localhost:5555/api/v1";

/**
 * Parlay Builder Store
 * Manages selected bets for parlay construction with real-time calculations
 * 
 * Features:
 * - Add/remove bet legs
 * - Real-time total odds calculation
 * - Persistent storage across sessions
 * - Optimistic UI updates
 * - ML prediction enrichment
 * - Correlation detection
 */
const useParlayStore = create(
  persist(
    (set, get) => ({
      // State
      selectedBets: [], // Array of bet legs
      totalOdds: 1.0,   // Combined odds (American format)
      isCalculating: false, // Loading state for calculations
      
      // ML Enrichment state
      enrichedData: null, // Enriched parlay data from ML API
      isEnriching: false, // Loading state for enrichment
      correlationWarnings: [], // Warnings about correlated legs
      combinedModelProb: null, // Combined ML probability
      combinedEdge: null, // Combined edge percentage
      parlayEV: null, // Expected value percentage
      
      /**
       * Add a bet to the parlay
       * Performs validation and calculates new total odds
       * 
       * @param {object} event - Event data from odds page
       * @param {string} betType - Type of bet (MONEYLINE, SPREAD, etc.)
       * @param {string} selection - HOME or AWAY
       * @param {number} odds - American odds (e.g., -110, +150)
       * @returns {boolean} - Success status
       */
      addBet: (event, betType, selection, odds) => {
        const { selectedBets } = get();
        
        // Validation: Check if this exact bet already exists
        const exists = selectedBets.some(
          bet => bet.event_id === event.id && 
                 bet.bet_type === betType && 
                 bet.selection === selection
        );
        
        if (exists) {
          return false; // Already added - prevent duplicates
        }
        
        // Validation: Limit to 15 legs (parlay maximum)
        if (selectedBets.length >= 15) {
          return false;
        }
        
        // Create new bet leg with all required data
        const newBet = {
          event_id: event.id,
          team: selection === 'HOME' ? event.home_team : event.away_team,
          event_name: `${event.home_team} vs ${event.away_team}`,
          odds: parseFloat(odds), // Ensure numeric
          win_prob: null, // Can be manually overridden later
          bet_type: betType,
          selection: selection,
          event_date: event.event_date,
          league: event.league,
          sport: event.sport || 'Unknown', // Track sport type
        };
        
        const updatedBets = [...selectedBets, newBet];
        
        // Calculate new total odds
        const newTotalOdds = get().calculateTotalOdds(updatedBets);
        
        // Optimistic update: immediately update UI
        set({ 
          selectedBets: updatedBets,
          totalOdds: newTotalOdds
        });
        
        return true;
      },
      
      /**
       * Remove a bet from the parlay by index
       * Recalculates total odds after removal
       * 
       * @param {number} index - Index of bet to remove
       */
      removeBet: (index) => {
        const { selectedBets } = get();
        const updatedBets = selectedBets.filter((_, i) => i !== index);
        
        // Recalculate total odds
        const newTotalOdds = updatedBets.length > 0 
          ? get().calculateTotalOdds(updatedBets)
          : 1.0;
        
        // Optimistic update
        set({ 
          selectedBets: updatedBets,
          totalOdds: newTotalOdds
        });
      },
      
      /**
       * Update a specific bet field (e.g., manual odds override)
       * Recalculates total odds if odds field is changed
       * 
       * @param {number} index - Index of bet to update
       * @param {string} field - Field name to update
       * @param {any} value - New value
       */
      updateBet: (index, field, value) => {
        const { selectedBets } = get();
        const updated = [...selectedBets];
        updated[index] = { ...updated[index], [field]: value };
        
        // If odds changed, recalculate total
        const newTotalOdds = field === 'odds' 
          ? get().calculateTotalOdds(updated)
          : get().totalOdds;
        
        set({ 
          selectedBets: updated,
          totalOdds: newTotalOdds
        });
      },
      
      /**
       * Clear all bets from parlay
       * Resets total odds to default
       */
      clearAll: () => {
        set({ 
          selectedBets: [],
          totalOdds: 1.0,
          enrichedData: null,
          correlationWarnings: [],
          combinedModelProb: null,
          combinedEdge: null,
          parlayEV: null,
        });
      },
      
      /**
       * Enrich parlay legs with ML predictions
       * Calls pipeline API to get model probabilities and edge calculations
       */
      enrichParlay: async () => {
        const { selectedBets } = get();
        if (selectedBets.length === 0) return;
        
        set({ isEnriching: true });
        
        try {
          // Prepare legs for API
          const legs = selectedBets.map(bet => ({
            home_team: bet.event_name?.split(' vs ')[0] || bet.team,
            away_team: bet.event_name?.split(' vs ')[1] || 'Unknown',
            selection: bet.selection,
            odds: bet.odds,
            bet_type: bet.bet_type,
          }));
          
          const response = await fetch(`${PIPELINE_API_URL}/parlay/enrich`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ legs }),
          });
          
          if (!response.ok) {
            throw new Error('Failed to enrich parlay');
          }
          
          const data = await response.json();
          
          // Update bets with enriched data
          const enrichedBets = selectedBets.map((bet, index) => ({
            ...bet,
            model_prob: data.legs[index]?.model_prob,
            edge_pct: data.legs[index]?.edge_pct,
            confidence: data.legs[index]?.confidence,
            has_value: data.legs[index]?.has_value,
            implied_prob: data.legs[index]?.implied_prob,
          }));
          
          set({
            selectedBets: enrichedBets,
            enrichedData: data,
            correlationWarnings: data.correlation_warnings || [],
            combinedModelProb: data.combined_model_prob,
            combinedEdge: data.combined_edge_pct,
            parlayEV: data.parlay_ev,
            isEnriching: false,
          });
          
          return data;
        } catch (error) {
          console.error('Parlay enrichment error:', error);
          set({ isEnriching: false });
          return null;
        }
      },
      
      // Get bet count
      getBetCount: () => {
        return get().selectedBets.length;
      },
      
      /**
       * Check if a specific bet is already selected
       * Used to highlight selected bets in odds list
       * 
       * @param {string} eventId - Event UUID
       * @param {string} betType - Bet type
       * @param {string} selection - HOME or AWAY
       * @returns {boolean}
       */
      isBetSelected: (eventId, betType, selection) => {
        const { selectedBets } = get();
        return selectedBets.some(
          bet => bet.event_id === eventId && 
                 bet.bet_type === betType && 
                 bet.selection === selection
        );
      },
      
      /**
       * Calculate total parlay odds from individual legs
       * Converts American odds to decimal, multiplies, converts back
       * 
       * Formula:
       * 1. Convert each American odd to decimal
       * 2. Multiply all decimals together
       * 3. Convert result back to American odds
       * 
       * @param {array} bets - Array of bet legs
       * @returns {number} - Total odds in American format
       */
      calculateTotalOdds: (bets) => {
        if (!bets || bets.length === 0) return 1.0;
        
        // Convert American odds to decimal and multiply
        const totalDecimal = bets.reduce((acc, bet) => {
          const odds = parseFloat(bet.odds);
          
          // Convert American to Decimal
          // Positive odds: (odds / 100) + 1
          // Negative odds: (100 / |odds|) + 1
          const decimal = odds > 0 
            ? (odds / 100) + 1 
            : (100 / Math.abs(odds)) + 1;
          
          return acc * decimal;
        }, 1);
        
        // Convert back to American odds
        // If decimal >= 2.0: (decimal - 1) * 100
        // If decimal < 2.0: -100 / (decimal - 1)
        const americanOdds = totalDecimal >= 2.0
          ? (totalDecimal - 1) * 100
          : -100 / (totalDecimal - 1);
        
        return Math.round(americanOdds); // Round to nearest integer
      },
      
      /**
       * Calculate potential payout for a given stake
       * 
       * @param {number} stake - Bet amount in dollars
       * @returns {object} - { payout, profit, totalOdds }
       */
      calculatePayout: (stake) => {
        const { totalOdds } = get();
        const stakeAmount = parseFloat(stake) || 0;
        
        if (stakeAmount <= 0 || totalOdds === 1.0) {
          return { payout: 0, profit: 0, totalOdds: 1.0 };
        }
        
        // Convert American odds to decimal for payout calculation
        const decimal = totalOdds > 0 
          ? (totalOdds / 100) + 1 
          : (100 / Math.abs(totalOdds)) + 1;
        
        const payout = stakeAmount * decimal;
        const profit = payout - stakeAmount;
        
        return {
          payout: Math.round(payout * 100) / 100,
          profit: Math.round(profit * 100) / 100,
          totalOdds
        };
      },
      
      /**
       * Set calculating state (for loading indicators)
       */
      setCalculating: (isCalculating) => {
        set({ isCalculating });
      },
    }),
    {
      name: 'parlay-builder-storage',
      partialPersist: true,
    }
  )
);

export default useParlayStore;
