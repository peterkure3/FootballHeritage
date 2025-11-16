/**
 * PredictionCard Component
 * 
 * Displays detailed ML prediction information including:
 * - Win/Draw/Loss probabilities
 * - Confidence level
 * - Model version
 * - Visual probability bars
 */

import { usePrediction } from '../hooks/usePredictions';
import { Brain, TrendingUp, AlertCircle } from 'lucide-react';

const PredictionCard = ({ matchId, homeTeam, awayTeam, showEdge = false, odds = null }) => {
  const { data: prediction, isLoading, isError } = usePrediction(matchId);

  if (isLoading) {
    return (
      <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-lg p-4 border border-purple-500/30 animate-pulse">
        <div className="h-4 bg-gray-700 rounded w-1/3 mb-3"></div>
        <div className="space-y-2">
          <div className="h-8 bg-gray-700 rounded"></div>
          <div className="h-8 bg-gray-700 rounded"></div>
          <div className="h-8 bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (isError || !prediction) {
    return (
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 text-gray-400">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">No prediction available</span>
        </div>
      </div>
    );
  }

  // Calculate confidence
  const maxProb = Math.max(
    prediction.home_prob,
    prediction.draw_prob,
    prediction.away_prob
  );
  const confidence = maxProb > 0.6 ? 'High' : maxProb > 0.45 ? 'Medium' : 'Low';
  const confidenceColor = maxProb > 0.6 ? 'text-green-400' : maxProb > 0.45 ? 'text-yellow-400' : 'text-gray-400';

  // Calculate betting edge if odds provided
  let edge = null;
  if (showEdge && odds) {
    const homeEdge = (prediction.home_prob * odds.home) - 1;
    const drawEdge = (prediction.draw_prob * odds.draw) - 1;
    const awayEdge = (prediction.away_prob * odds.away) - 1;
    
    edge = {
      home: homeEdge,
      draw: drawEdge,
      away: awayEdge,
      best: Math.max(homeEdge, drawEdge, awayEdge)
    };
  }

  // Probability bar component
  const ProbabilityBar = ({ label, probability, isWinner, edge: edgeValue }) => {
    const percentage = (probability * 100).toFixed(1);
    const barWidth = `${probability * 100}%`;
    
    return (
      <div className="space-y-1">
        <div className="flex justify-between items-center text-sm">
          <span className={`${isWinner ? 'font-bold text-white' : 'text-gray-400'}`}>
            {label}
          </span>
          <div className="flex items-center gap-2">
            <span className={`${isWinner ? 'font-bold text-white' : 'text-gray-400'}`}>
              {percentage}%
            </span>
            {edgeValue !== null && edgeValue !== undefined && (
              <span className={`text-xs ${edgeValue > 0 ? 'text-green-400' : 'text-red-400'}`}>
                ({edgeValue > 0 ? '+' : ''}{(edgeValue * 100).toFixed(1)}%)
              </span>
            )}
          </div>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isWinner 
                ? 'bg-gradient-to-r from-green-500 to-green-400' 
                : 'bg-gradient-to-r from-blue-500 to-blue-400'
            }`}
            style={{ width: barWidth }}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-lg p-4 border border-purple-500/30">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <span className="text-purple-400 font-semibold">AI Prediction</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${confidenceColor}`}>
            {confidence} Confidence
          </span>
          <span className="text-xs text-gray-500">v{prediction.model_version}</span>
        </div>
      </div>

      {/* Probabilities */}
      <div className="space-y-3">
        <ProbabilityBar
          label={homeTeam || 'Home Win'}
          probability={prediction.home_prob}
          isWinner={prediction.winner === 'home_win'}
          edge={edge?.home}
        />
        <ProbabilityBar
          label="Draw"
          probability={prediction.draw_prob}
          isWinner={prediction.winner === 'draw'}
          edge={edge?.draw}
        />
        <ProbabilityBar
          label={awayTeam || 'Away Win'}
          probability={prediction.away_prob}
          isWinner={prediction.winner === 'away_win'}
          edge={edge?.away}
        />
      </div>

      {/* Best Value Bet */}
      {edge && edge.best > 0 && (
        <div className="mt-4 pt-4 border-t border-purple-500/30">
          <div className="flex items-center gap-2 text-green-400">
            <TrendingUp className="w-4 h-4" />
            <span className="text-sm font-semibold">
              Best Value: {edge.home === edge.best ? 'Home' : edge.draw === edge.best ? 'Draw' : 'Away'}
              {' '}(+{(edge.best * 100).toFixed(1)}% edge)
            </span>
          </div>
        </div>
      )}

      {/* Prediction Summary */}
      <div className="mt-4 pt-4 border-t border-purple-500/30">
        <p className="text-sm text-gray-300 text-center">
          Model predicts: <strong className="text-white">
            {prediction.winner === 'home_win' ? homeTeam || 'Home Win' : 
             prediction.winner === 'draw' ? 'Draw' : 
             awayTeam || 'Away Win'}
          </strong>
        </p>
      </div>
    </div>
  );
};

export default PredictionCard;
