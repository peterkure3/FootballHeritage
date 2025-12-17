/**
 * React hooks for ML predictions
 * 
 * Provides hooks for fetching and managing predictions from the pipeline API
 * Uses React Query for caching and automatic refetching
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { predictionService } from '../services/predictionService';
import toast from 'react-hot-toast';

/**
 * Hook to fetch prediction for a specific match
 * 
 * @param {number|string} matchId - The match ID from pipeline database (external_id)
 * @returns {Object} React Query result with prediction data
 * 
 * @example
 * const { data: prediction, isLoading } = usePrediction(event.external_id);
 * if (prediction) {
 *   console.log(`Predicted winner: ${prediction.winner}`);
 *   console.log(`Home win probability: ${prediction.home_prob * 100}%`);
 * }
 */
export const usePrediction = (matchId, refreshKey = 0) => {
  return useQuery({
    queryKey: ['prediction', matchId, refreshKey],
    queryFn: () => predictionService.getPrediction(matchId),
    enabled: !!matchId, // Only fetch if matchId exists
    staleTime: 60000, // 1 minute - predictions don't change frequently
    cacheTime: 300000, // 5 minutes - keep in cache
    retry: 1, // Only retry once on failure
    onError: (error) => {
      console.error('Failed to fetch prediction:', error);
    },
  });
};

/**
 * Hook to fetch predictions for multiple matches
 * 
 * @param {Array<number|string>} matchIds - Array of match IDs
 * @returns {Object} React Query result with map of predictions
 */
export const useBatchPredictions = (matchIds) => {
  return useQuery({
    queryKey: ['predictions', 'batch', matchIds],
    queryFn: () => predictionService.getBatchPredictions(matchIds),
    enabled: matchIds && matchIds.length > 0,
    staleTime: 60000,
    cacheTime: 300000,
  });
};

/**
 * Hook to fetch matches from pipeline API
 * 
 * @param {Object} filters - Optional filters (competition, date, limit)
 * @returns {Object} React Query result with matches array
 */
export const usePipelineMatches = (filters = {}) => {
  return useQuery({
    queryKey: ['pipeline-matches', filters],
    queryFn: () => predictionService.getMatches(filters),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
    onError: (error) => {
      toast.error('Failed to fetch matches from pipeline');
      console.error(error);
    },
  });
};

/**
 * Hook to predict matchup between any two teams (What-If scenario)
 * 
 * @param {string} homeTeam - Home team name
 * @param {string} awayTeam - Away team name
 * @param {Object} options - Additional options
 * @param {boolean} options.enabled - Whether to enable the query
 * @returns {Object} React Query result with prediction and recommendation
 * 
 * @example
 * const { data, isLoading, refetch } = useMatchupPrediction('Arsenal', 'Chelsea');
 * if (data) {
 *   console.log(data.recommendation); // AI-generated betting advice
 *   console.log(data.confidence); // 'High', 'Medium', or 'Low'
 * }
 */
export const useMatchupPrediction = (homeTeam, awayTeam, options = {}) => {
  return useQuery({
    queryKey: ['matchup-prediction', homeTeam, awayTeam],
    queryFn: () => predictionService.predictMatchup(homeTeam, awayTeam),
    enabled: options.enabled !== false && !!homeTeam && !!awayTeam,
    staleTime: 300000, // 5 minutes - team form doesn't change that quickly
    cacheTime: 600000, // 10 minutes
    retry: 1,
    onError: (error) => {
      toast.error(error.message || 'Failed to predict matchup');
    },
  });
};

/**
 * Hook to check pipeline API health
 * 
 * @returns {Object} React Query result with health status
 */
export const usePipelineHealth = () => {
  return useQuery({
    queryKey: ['pipeline-health'],
    queryFn: () => predictionService.healthCheck(),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Check every minute
    retry: 2,
  });
};

/**
 * Hook to calculate betting edge for a prediction
 * 
 * @param {Object} prediction - Prediction object
 * @param {Object} odds - Odds object
 * @returns {Object|null} Edge calculations or null
 */
export const useBettingEdge = (prediction, odds) => {
  if (!prediction || !odds) return null;
  
  return predictionService.calculateBettingEdge(prediction, odds);
};

/**
 * Mutation hook for requesting a new prediction
 * Useful for triggering prediction generation on-demand
 */
export const useRequestPrediction = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ homeTeam, awayTeam }) => {
      return await predictionService.predictMatchup(homeTeam, awayTeam);
    },
    onSuccess: (data, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries(['matchup-prediction', variables.homeTeam, variables.awayTeam]);
      toast.success('Prediction generated successfully!');
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to generate prediction');
    },
  });
};

export default {
  usePrediction,
  useBatchPredictions,
  usePipelineMatches,
  useMatchupPrediction,
  usePipelineHealth,
  useBettingEdge,
  useRequestPrediction,
};
