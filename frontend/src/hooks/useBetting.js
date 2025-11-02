import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../utils/api';
import useAuthStore from '../stores/authStore';
import useBettingStore from '../stores/bettingStore';
import toast from 'react-hot-toast';

/**
 * Hook for fetching odds with real-time refresh
 * 
 * Features:
 * - Client-side fallback filtering for expired events
 * - Filters out events where event_date <= NOW()
 * - Performance optimized with React Query select
 * - Auto-refresh every 15 seconds for live odds
 * 
 * Backend already filters expired events, but this provides
 * an additional safety layer in case of clock skew or caching
 */
export const useOdds = () => {
  return useQuery({
    queryKey: ['odds'],
    queryFn: async () => {
      return await api.getOdds();
    },
    // Client-side filtering: Remove expired events as fallback
    // This runs on every render but is memoized by React Query
    select: (data) => {
      if (!data || !Array.isArray(data)) return [];
      
      const now = new Date();
      
      // Filter out events that have already started or passed
      return data.filter((event) => {
        // Parse event date (handle various formats)
        const eventDate = new Date(event.event_date);
        
        // Only show events in the future
        // Add 5-minute buffer to account for clock skew
        const bufferMs = 5 * 60 * 1000; // 5 minutes
        return eventDate.getTime() > (now.getTime() - bufferMs);
      });
    },
    staleTime: 10000, // 10 seconds - data considered fresh
    refetchInterval: 15000, // Refetch every 15 seconds for real-time odds
    retry: 3,
    onError: (error) => {
      toast.error(`Failed to fetch odds: ${error.message}`);
    },
  });
};

// Hook for placing a bet
export const usePlaceBet = () => {
  const queryClient = useQueryClient();
  const { updateBalance, addBet } = useAuthStore();
  const { placeBet, setPlacingBet, getRemainingBudget, isAtLimit } = useBettingStore();

  return useMutation({
    mutationFn: async ({ eventId, amount, odds, type }) => {
      // Check session limit before placing bet
      if (isAtLimit()) {
        throw new Error('Session betting limit reached ($100). Please take a break.');
      }

      const remaining = getRemainingBudget();
      if (amount > remaining) {
        throw new Error(`Bet amount exceeds session limit. Remaining: $${remaining.toFixed(2)}`);
      }

      setPlacingBet(true);
      return await api.placeBet(eventId, amount, odds, type);
    },
    onSuccess: (data, variables) => {
      // Update local state
      const betResult = placeBet({
        id: data.bet_id || Date.now(),
        eventId: variables.eventId,
        amount: variables.amount,
        odds: variables.odds,
        type: variables.type,
        status: 'pending',
        timestamp: new Date().toISOString(),
      });

      if (!betResult.success) {
        toast.error(betResult.error);
        return;
      }

      // Update user balance
      if (data.new_balance !== undefined) {
        updateBalance(data.new_balance);
      }

      // Add bet to user's history
      if (data.bet) {
        addBet(data.bet);
      }

      // Invalidate relevant queries
      queryClient.invalidateQueries(['user']);
      queryClient.invalidateQueries(['betsHistory']);

      // Show success message with potential payout
      const potentialPayout = (variables.amount * variables.odds).toFixed(2);
      toast.success(
        `Bet placed! $${variables.amount} on ${variables.type}. Potential payout: $${potentialPayout}`,
        { duration: 4000 }
      );

      setPlacingBet(false);
    },
    onError: (error) => {
      setPlacingBet(false);
      toast.error(error.message || 'Failed to place bet');
    },
  });
};

// Hook for fetching bets history
export const useBetsHistory = () => {
  const { isAuthenticated } = useAuthStore();
  const { setBetsHistory } = useBettingStore();

  return useQuery({
    queryKey: ['betsHistory'],
    queryFn: async () => {
      const bets = await api.getBetsHistory();
      setBetsHistory(bets);
      return bets;
    },
    enabled: isAuthenticated,
    staleTime: 20000, // 20 seconds
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 2,
    onError: (error) => {
      toast.error(`Failed to fetch bet history: ${error.message}`);
    },
  });
};

// Hook for deposit
export const useDeposit = () => {
  const queryClient = useQueryClient();
  const { updateBalance } = useAuthStore();

  return useMutation({
    mutationFn: async (amount) => {
      return await api.deposit(amount);
    },
    onSuccess: (data) => {
      if (data.new_balance !== undefined) {
        updateBalance(data.new_balance);
      }
      queryClient.invalidateQueries(['user']);
      toast.success(`Deposited $${data.amount || 0} successfully!`);
    },
    onError: (error) => {
      toast.error(error.message || 'Deposit failed');
    },
  });
};

// Hook for withdrawal
export const useWithdraw = () => {
  const queryClient = useQueryClient();
  const { updateBalance } = useAuthStore();

  return useMutation({
    mutationFn: async (amount) => {
      return await api.withdraw(amount);
    },
    onSuccess: (data) => {
      if (data.new_balance !== undefined) {
        updateBalance(data.new_balance);
      }
      queryClient.invalidateQueries(['user']);
      toast.success(`Withdrew $${data.amount || 0} successfully!`);
    },
    onError: (error) => {
      toast.error(error.message || 'Withdrawal failed');
    },
  });
};

export default {
  useOdds,
  usePlaceBet,
  useBetsHistory,
  useDeposit,
  useWithdraw,
};
