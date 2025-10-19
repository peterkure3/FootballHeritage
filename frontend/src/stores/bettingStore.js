import { create } from 'zustand';

// Session betting limit: $100 per session
const SESSION_LIMIT = 100;

const useBettingStore = create((set, get) => ({
  // State
  sessionTotal: 0,
  activeBets: [],
  betsHistory: [],
  selectedEvent: null,
  isPlacingBet: false,

  // Responsible gambling features
  sessionLimit: SESSION_LIMIT,
  warningThreshold: SESSION_LIMIT * 0.8, // 80% of limit

  // Actions

  // Add a bet to session total
  placeBet: (bet) => {
    const { sessionTotal, sessionLimit } = get();
    const newTotal = sessionTotal + bet.amount;

    if (newTotal > sessionLimit) {
      return {
        success: false,
        error: `Session limit of $${sessionLimit} would be exceeded`,
      };
    }

    set((state) => ({
      sessionTotal: newTotal,
      activeBets: [...state.activeBets, bet],
      isPlacingBet: false,
    }));

    return { success: true };
  },

  // Update bet status (won, lost, pending)
  updateBet: (betId, status, payout = 0) => {
    set((state) => ({
      activeBets: state.activeBets.map((bet) =>
        bet.id === betId ? { ...bet, status, payout } : bet
      ),
    }));
  },

  // Move bet from active to history
  settleBet: (betId) => {
    const { activeBets } = get();
    const bet = activeBets.find((b) => b.id === betId);

    if (bet) {
      set((state) => ({
        activeBets: state.activeBets.filter((b) => b.id !== betId),
        betsHistory: [bet, ...state.betsHistory],
      }));
    }
  },

  // Set all bets history
  setBetsHistory: (bets) => {
    set({ betsHistory: bets });
  },

  // Select an event for betting
  selectEvent: (event) => {
    set({ selectedEvent: event });
  },

  // Clear selected event
  clearSelectedEvent: () => {
    set({ selectedEvent: null });
  },

  // Set placing bet flag
  setPlacingBet: (isPlacing) => {
    set({ isPlacingBet: isPlacing });
  },

  // Reset session (call when user logs in or after cooldown)
  resetSession: () => {
    set({
      sessionTotal: 0,
      activeBets: [],
    });
  },

  // Get remaining session budget
  getRemainingBudget: () => {
    const { sessionTotal, sessionLimit } = get();
    return sessionLimit - sessionTotal;
  },

  // Check if near limit
  isNearLimit: () => {
    const { sessionTotal, warningThreshold } = get();
    return sessionTotal >= warningThreshold;
  },

  // Check if at limit
  isAtLimit: () => {
    const { sessionTotal, sessionLimit } = get();
    return sessionTotal >= sessionLimit;
  },

  // Calculate session statistics
  getSessionStats: () => {
    const { sessionTotal, sessionLimit, activeBets } = get();
    const remaining = sessionLimit - sessionTotal;
    const percentUsed = (sessionTotal / sessionLimit) * 100;

    return {
      total: sessionTotal,
      remaining,
      percentUsed: Math.round(percentUsed),
      betCount: activeBets.length,
      limit: sessionLimit,
    };
  },

  // Update session limit (for testing or admin)
  setSessionLimit: (newLimit) => {
    if (newLimit > 0 && newLimit <= 10000) {
      set({
        sessionLimit: newLimit,
        warningThreshold: newLimit * 0.8,
      });
    }
  },
}));

export default useBettingStore;
