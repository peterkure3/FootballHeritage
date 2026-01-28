import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { 
  CheckCircle, 
  XCircle, 
  TrendingUp, 
  Filter,
  ChevronLeft,
  ChevronRight,
  Target,
  Award,
  BarChart3,
  RefreshCw,
  Calendar
} from 'lucide-react';

const PIPELINE_API_URL = import.meta.env.VITE_PIPELINE_API_URL || "http://localhost:5555/api/v1";

const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A';
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
};

const formatResult = (result) => {
  if (!result) return 'N/A';
  switch (result) {
    case 'home_win': return 'Home Win';
    case 'away_win': return 'Away Win';
    case 'draw': return 'Draw';
    default: return result;
  }
};

const confidenceColors = {
  High: 'bg-green-500/20 text-green-400 border-green-500/40',
  Medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  Low: 'bg-gray-500/20 text-gray-400 border-gray-500/40',
};

const PredictionResults = () => {
  const [page, setPage] = useState(1);
  const [resultFilter, setResultFilter] = useState('all');
  const [leagueFilter, setLeagueFilter] = useState('');
  const [dateRange, setDateRange] = useState('all'); // all, 7, 30, 90
  const [isUpdating, setIsUpdating] = useState(false);
  const pageSize = 10;
  const queryClient = useQueryClient();

  // Update results mutation
  const handleUpdateResults = async () => {
    setIsUpdating(true);
    try {
      const response = await fetch(`${PIPELINE_API_URL}/predictions/update-results?days=7`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to update results');
      const data = await response.json();
      toast.success(data.message || `Updated ${data.updated_count} matches`);
      // Refetch data
      queryClient.invalidateQueries({ queryKey: ['prediction-history'] });
      queryClient.invalidateQueries({ queryKey: ['prediction-accuracy'] });
    } catch (error) {
      toast.error('Failed to update results: ' + error.message);
    } finally {
      setIsUpdating(false);
    }
  };

  // Fetch prediction history
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['prediction-history', page, resultFilter, leagueFilter, dateRange],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (resultFilter !== 'all') params.append('result_filter', resultFilter);
      if (leagueFilter) params.append('league', leagueFilter);
      if (dateRange !== 'all') params.append('days', dateRange);
      
      const response = await fetch(`${PIPELINE_API_URL}/predictions/history-data?${params}`);
      if (!response.ok) throw new Error('Failed to fetch history');
      return response.json();
    },
    staleTime: 60000,
  });

  // Fetch accuracy metrics
  const { data: accuracyData, isLoading: accuracyLoading } = useQuery({
    queryKey: ['prediction-accuracy', dateRange],
    queryFn: async () => {
      const days = dateRange === 'all' ? 365 : dateRange;
      const response = await fetch(`${PIPELINE_API_URL}/predictions/accuracy-data?days=${days}`);
      if (!response.ok) throw new Error('Failed to fetch accuracy');
      return response.json();
    },
    staleTime: 300000, // 5 minutes
  });

  const predictions = historyData?.predictions || [];
  const totalCount = historyData?.total_count || 0;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="space-y-6">
      {/* Update Results Button */}
      <div className="flex justify-end">
        <button
          onClick={handleUpdateResults}
          disabled={isUpdating}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-wait text-white font-semibold rounded-lg transition"
        >
          <RefreshCw className={`w-4 h-4 ${isUpdating ? 'animate-spin' : ''}`} />
          {isUpdating ? 'Fetching Results...' : 'Fetch Latest Results'}
        </button>
      </div>

      {/* Accuracy Summary Cards */}
      {!accuracyLoading && accuracyData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
              <Target className="w-4 h-4" />
              <span>Overall Accuracy</span>
            </div>
            <p className={`text-3xl font-bold ${accuracyData.overall_accuracy >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
              {accuracyData.overall_accuracy}%
            </p>
            <p className="text-xs text-gray-500 mt-1">Last 90 days</p>
          </div>
          
          <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
              <BarChart3 className="w-4 h-4" />
              <span>Total Predictions</span>
            </div>
            <p className="text-3xl font-bold text-white">{accuracyData.total_predictions}</p>
            <p className="text-xs text-gray-500 mt-1">
              {accuracyData.correct_predictions} correct
            </p>
          </div>
          
          <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
              <Award className="w-4 h-4" />
              <span>High Confidence</span>
            </div>
            {accuracyData.by_confidence?.find(c => c.confidence === 'High') ? (
              <>
                <p className="text-3xl font-bold text-green-400">
                  {accuracyData.by_confidence.find(c => c.confidence === 'High').accuracy_pct}%
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {accuracyData.by_confidence.find(c => c.confidence === 'High').total} predictions
                </p>
              </>
            ) : (
              <p className="text-xl text-gray-500">N/A</p>
            )}
          </div>
          
          <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
              <TrendingUp className="w-4 h-4" />
              <span>Recent Form</span>
            </div>
            <div className="flex gap-1 mt-2">
              {accuracyData.recent_form?.slice(0, 10).map((r, i) => (
                <div
                  key={i}
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                    r.correct ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
                  }`}
                  title={`${r.teams}: ${r.correct ? 'Correct' : 'Wrong'}`}
                >
                  {r.correct ? '✓' : '✗'}
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">Last 10 predictions</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 bg-gray-800/40 border border-gray-700 rounded-xl p-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-400">Filter:</span>
        </div>
        
        <select
          value={resultFilter}
          onChange={(e) => { setResultFilter(e.target.value); setPage(1); }}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm focus:ring-2 focus:ring-green-500"
        >
          <option value="all">All Results</option>
          <option value="correct">Correct Only</option>
          <option value="incorrect">Incorrect Only</option>
        </select>
        
        <input
          type="text"
          value={leagueFilter}
          onChange={(e) => { setLeagueFilter(e.target.value); setPage(1); }}
          placeholder="Filter by league..."
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-green-500 w-48"
        />

        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-gray-400" />
          <select
            value={dateRange}
            onChange={(e) => { setDateRange(e.target.value); setPage(1); }}
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm focus:ring-2 focus:ring-green-500"
          >
            <option value="all">All Time</option>
            <option value="7">Last 7 Days</option>
            <option value="30">Last 30 Days</option>
            <option value="90">Last 90 Days</option>
          </select>
        </div>
        
        {(resultFilter !== 'all' || leagueFilter || dateRange !== 'all') && (
          <button
            onClick={() => { setResultFilter('all'); setLeagueFilter(''); setDateRange('all'); setPage(1); }}
            className="text-sm text-gray-400 hover:text-white underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Results Table */}
      <div className="bg-gray-800/40 border border-gray-700 rounded-xl overflow-hidden">
        {historyLoading ? (
          <div className="p-8 text-center">
            <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-gray-400 mt-4">Loading prediction history...</p>
          </div>
        ) : predictions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No prediction results found</p>
            <p className="text-sm mt-1">Results will appear here once matches are completed</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-900/50 border-b border-gray-700">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Match</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Date</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Prediction</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actual</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Score</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Confidence</th>
                    <th className="text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Result</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {predictions.map((pred) => (
                    <tr key={pred.match_id} className="hover:bg-gray-700/30 transition">
                      <td className="px-4 py-3">
                        <p className="font-semibold text-white">{pred.home_team} vs {pred.away_team}</p>
                        <p className="text-xs text-gray-500">{pred.competition || 'Football'}</p>
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-400">
                        {formatDate(pred.match_date)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-sm font-medium text-blue-400">
                          {formatResult(pred.predicted_winner)}
                        </span>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {(Math.max(pred.home_prob, pred.draw_prob, pred.away_prob) * 100).toFixed(0)}% conf
                        </p>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-sm font-medium text-white">
                          {formatResult(pred.actual_result)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-300">
                        {pred.home_score !== null && pred.away_score !== null 
                          ? `${pred.home_score} - ${pred.away_score}`
                          : 'N/A'
                        }
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${confidenceColors[pred.confidence] || confidenceColors.Low}`}>
                          {pred.confidence}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {pred.is_correct ? (
                          <div className="flex items-center justify-center gap-1 text-green-400">
                            <CheckCircle className="w-5 h-5" />
                            <span className="text-sm font-semibold">Correct</span>
                          </div>
                        ) : (
                          <div className="flex items-center justify-center gap-1 text-red-400">
                            <XCircle className="w-5 h-5" />
                            <span className="text-sm font-semibold">Wrong</span>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700 bg-gray-900/30">
                <p className="text-sm text-gray-400">
                  Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, totalCount)} of {totalCount}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-2 rounded-lg bg-gray-800 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700 transition"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-sm text-gray-400">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-2 rounded-lg bg-gray-800 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700 transition"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Accuracy by League */}
      {!accuracyLoading && accuracyData?.by_league?.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Accuracy by League</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {accuracyData.by_league.map((league) => (
              <div 
                key={league.league}
                className="flex items-center justify-between bg-gray-900/50 rounded-lg p-3 border border-gray-700"
              >
                <div>
                  <p className="font-medium text-white text-sm">{league.league}</p>
                  <p className="text-xs text-gray-500">{league.total} predictions</p>
                </div>
                <div className="text-right">
                  <p className={`text-lg font-bold ${league.accuracy_pct >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {league.accuracy_pct}%
                  </p>
                  <p className="text-xs text-gray-500">{league.correct}/{league.total}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PredictionResults;
