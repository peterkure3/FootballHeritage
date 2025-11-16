/**
 * PredictionBadge Component
 * 
 * Displays a compact prediction badge showing the predicted outcome
 * and confidence level for a match
 */

import { usePrediction } from '../hooks/usePredictions';
import { Brain, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const PredictionBadge = ({ matchId, variant = 'default' }) => {
  const { data: prediction, isLoading, isError } = usePrediction(matchId);

  if (isLoading) {
    return (
      <div className="animate-pulse bg-gray-700 h-6 w-24 rounded-full"></div>
    );
  }

  if (isError || !prediction) {
    return null;
  }

  // Calculate confidence level
  const maxProb = Math.max(
    prediction.home_prob,
    prediction.draw_prob,
    prediction.away_prob
  );

  const confidence = maxProb > 0.6 ? 'High' : maxProb > 0.45 ? 'Medium' : 'Low';
  
  // Color based on confidence
  const colorClasses = {
    High: 'bg-green-500/20 text-green-400 border-green-500/50',
    Medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
    Low: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
  };

  // Format winner text
  const formatWinner = (winner) => {
    const map = {
      'home_win': 'Home',
      'draw': 'Draw',
      'away_win': 'Away',
    };
    return map[winner] || winner;
  };

  // Get icon based on prediction
  const getIcon = () => {
    if (prediction.winner === 'home_win') return <TrendingUp className="w-3 h-3" />;
    if (prediction.winner === 'away_win') return <TrendingDown className="w-3 h-3" />;
    return <Minus className="w-3 h-3" />;
  };

  // Compact variant
  if (variant === 'compact') {
    return (
      <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold border ${colorClasses[confidence]}`}>
        <Brain className="w-3 h-3" />
        <span>{formatWinner(prediction.winner)}</span>
      </div>
    );
  }

  // Default variant with confidence
  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border ${colorClasses[confidence]}`}>
      <Brain className="w-3.5 h-3.5" />
      <span>{formatWinner(prediction.winner)}</span>
      {getIcon()}
      <span className="text-xs opacity-75">({confidence})</span>
    </div>
  );
};

export default PredictionBadge;
