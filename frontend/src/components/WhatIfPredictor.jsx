/**
 * WhatIfPredictor Component
 * 
 * Allows users to predict the outcome of any matchup between two teams
 * Useful for exploring hypothetical scenarios and getting AI recommendations
 */

import { useState } from 'react';
import { useMatchupPrediction } from '../hooks/usePredictions';
import { Brain, Search, TrendingUp, AlertCircle, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

const WhatIfPredictor = () => {
  const [homeTeam, setHomeTeam] = useState('');
  const [awayTeam, setAwayTeam] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const { 
    data: prediction, 
    isLoading, 
    isError, 
    error,
    refetch 
  } = useMatchupPrediction(homeTeam, awayTeam, { enabled: submitted });

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!homeTeam.trim() || !awayTeam.trim()) {
      toast.error('Please enter both team names');
      return;
    }

    if (homeTeam.toLowerCase() === awayTeam.toLowerCase()) {
      toast.error('Teams must be different');
      return;
    }

    setSubmitted(true);
    refetch();
  };

  const handleReset = () => {
    setHomeTeam('');
    setAwayTeam('');
    setSubmitted(false);
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-purple-500/20 rounded-lg">
          <Brain className="w-6 h-6 text-purple-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">What-If Predictor</h2>
          <p className="text-sm text-gray-400">Predict any matchup using AI</p>
        </div>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="space-y-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Home Team
            </label>
            <input
              type="text"
              value={homeTeam}
              onChange={(e) => setHomeTeam(e.target.value)}
              placeholder="e.g., Arsenal"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Away Team
            </label>
            <input
              type="text"
              value={awayTeam}
              onChange={(e) => setAwayTeam(e.target.value)}
              placeholder="e.g., Chelsea"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isLoading}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Predicting...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Predict Outcome
              </>
            )}
          </button>
          {submitted && (
            <button
              type="button"
              onClick={handleReset}
              className="px-6 py-3 bg-gray-700 text-white font-semibold rounded-lg hover:bg-gray-600 transition"
            >
              Reset
            </button>
          )}
        </div>
      </form>

      {/* Error State */}
      {isError && (
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-red-400 font-semibold mb-1">Prediction Failed</h3>
              <p className="text-sm text-red-300">
                {error?.message || 'Unable to generate prediction. Please try again.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Prediction Results */}
      {prediction && !isLoading && (
        <div className="space-y-4">
          {/* Match Header */}
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
            <div className="text-center">
              <h3 className="text-lg font-bold text-white mb-2">
                {prediction.home_team} vs {prediction.away_team}
              </h3>
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full border border-purple-500/50">
                <span className="text-purple-400 font-semibold">
                  Predicted Winner: {prediction.winner.replace('_', ' ').toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          {/* Probabilities */}
          <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-lg p-4 border border-purple-500/30">
            <h4 className="text-sm font-semibold text-purple-400 mb-3">Win Probabilities</h4>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">Home Win</div>
                <div className="text-2xl font-bold text-white">
                  {(prediction.home_prob * 100).toFixed(1)}%
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                  <div
                    className={`h-full rounded-full ${
                      prediction.winner === 'home_win' 
                        ? 'bg-gradient-to-r from-green-500 to-green-400' 
                        : 'bg-gradient-to-r from-blue-500 to-blue-400'
                    }`}
                    style={{ width: `${prediction.home_prob * 100}%` }}
                  />
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">Draw</div>
                <div className="text-2xl font-bold text-white">
                  {(prediction.draw_prob * 100).toFixed(1)}%
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                  <div
                    className={`h-full rounded-full ${
                      prediction.winner === 'draw' 
                        ? 'bg-gradient-to-r from-green-500 to-green-400' 
                        : 'bg-gradient-to-r from-blue-500 to-blue-400'
                    }`}
                    style={{ width: `${prediction.draw_prob * 100}%` }}
                  />
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">Away Win</div>
                <div className="text-2xl font-bold text-white">
                  {(prediction.away_prob * 100).toFixed(1)}%
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                  <div
                    className={`h-full rounded-full ${
                      prediction.winner === 'away_win' 
                        ? 'bg-gradient-to-r from-green-500 to-green-400' 
                        : 'bg-gradient-to-r from-blue-500 to-blue-400'
                    }`}
                    style={{ width: `${prediction.away_prob * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Confidence & Recommendation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                <h4 className="text-sm font-semibold text-gray-300">Confidence Level</h4>
              </div>
              <div className={`text-2xl font-bold ${
                prediction.confidence === 'High' ? 'text-green-400' :
                prediction.confidence === 'Medium' ? 'text-yellow-400' :
                'text-gray-400'
              }`}>
                {prediction.confidence}
              </div>
            </div>

            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-4 h-4 text-purple-400" />
                <h4 className="text-sm font-semibold text-gray-300">Model Version</h4>
              </div>
              <div className="text-2xl font-bold text-white">
                v{prediction.model_version}
              </div>
            </div>
          </div>

          {/* AI Recommendation */}
          <div className="bg-gradient-to-r from-green-900/20 to-blue-900/20 rounded-lg p-4 border border-green-500/30">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-green-500/20 rounded-lg flex-shrink-0">
                <TrendingUp className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-green-400 mb-2">AI Recommendation</h4>
                <p className="text-sm text-gray-300 leading-relaxed">
                  {prediction.recommendation}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WhatIfPredictor;
