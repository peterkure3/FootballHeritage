import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Parlay Builder Store
 * Manages selected bets for parlay construction
 */
const useParlayStore = create(
  persist(
    (set, get) => ({
      // State
      selectedBets: [],
      
      // Add a bet to the parlay
      addBet: (event, betType, selection, odds) => {
        const { selectedBets } = get();
        
        // Check if this exact bet already exists
        const exists = selectedBets.some(
          bet => bet.event_id === event.id && 
                 bet.bet_type === betType && 
                 bet.selection === selection
        );
        
        if (exists) {
          return false; // Already added
        }
        
        // Limit to 15 legs
        if (selectedBets.length >= 15) {
          return false;
        }
        
        const newBet = {
          event_id: event.id,
          team: selection === 'HOME' ? event.home_team : event.away_team,
          event_name: `${event.home_team} vs ${event.away_team}`,
          odds: odds,
          win_prob: null, // Can be overridden later
          bet_type: betType,
          selection: selection,
          event_date: event.event_date,
          league: event.league,
        };
        
        set({ selectedBets: [...selectedBets, newBet] });
        return true;
      },
      
      // Remove a bet from the parlay
      removeBet: (index) => {
        const { selectedBets } = get();
        set({ selectedBets: selectedBets.filter((_, i) => i !== index) });
      },
      
      // Update a specific bet (for manual overrides)
      updateBet: (index, field, value) => {
        const { selectedBets } = get();
        const updated = [...selectedBets];
        updated[index] = { ...updated[index], [field]: value };
        set({ selectedBets: updated });
      },
      
      // Clear all bets
      clearAll: () => {
        set({ selectedBets: [] });
      },
      
      // Get bet count
      getBetCount: () => {
        return get().selectedBets.length;
      },
      
      // Check if a specific bet is selected
      isBetSelected: (eventId, betType, selection) => {
        const { selectedBets } = get();
        return selectedBets.some(
          bet => bet.event_id === eventId && 
                 bet.bet_type === betType && 
                 bet.selection === selection
        );
      },
    }),
    {
      name: 'parlay-builder-storage',
      partialPersist: true,
    }
  )
);

export default useParlayStore;
