import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOdds } from '../hooks/useBetting';
import useAuthStore from '../stores/authStore';
import Navbar from '../components/Navbar';
import OddsRow from '../components/OddsRow';
import BetConfirmationModal from '../components/BetConfirmationModal';
import LoadingSkeleton from '../components/LoadingSkeleton';
import EmptyState from '../components/EmptyState';

const Odds = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const { data: odds, isLoading, isError, refetch } = useOdds();

  const [selectedBet, setSelectedBet] = useState(null);
  const [isBetModalOpen, setIsBetModalOpen] = useState(false);
  const [filter, setFilter] = useState('all'); // all, live, upcoming

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) {
    return null;
  }

  // Handle bet selection
  const handleBetSelection = (betDetails) => {
    setSelectedBet(betDetails);
    setIsBetModalOpen(true);
  };

  // Close bet modal
  const closeBetModal = () => {
    setIsBetModalOpen(false);
    setSelectedBet(null);
  };

  // Filter odds based on status
  const filteredOdds = odds?.filter((event) => {
    if (filter === 'all') return true;
    if (filter === 'live') return event.status === 'live' || event.status === 'in_progress';
    if (filter === 'upcoming') return event.status === 'upcoming' || event.status === 'scheduled';
    return true;
  }) || [];

  // Count events by status
  const liveCount = odds?.filter(e => e.status === 'live' || e.status === 'in_progress').length || 0;
  const upcomingCount = odds?.filter(e => e.status === 'upcoming' || e.status === 'scheduled').length || 0;

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
        <Navbar />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header Section */}
          <div className="mb-8">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
              <div>
                <h1 className="text-3xl md:text-4xl font-bold text-white mb-2 flex items-center">
                  <span className="text-4xl mr-3">🏈</span>
                  NFL Betting Odds
                </h1>
                <p className="text-gray-400">
                  Live odds update every 15 seconds • Place your bets now
                </p>
              </div>

              {/* Refresh Button */}
              <button
                onClick={() => refetch()}
                disabled={isLoading}
                className="mt-4 md:mt-0 flex items-center bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors border border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg
                  className={`w-5 h-5 mr-2 ${isLoading ? 'animate-spin' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Refresh Odds
              </button>
            </div>

            {/* Filter Tabs */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setFilter('all')}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
                  filter === 'all'
                    ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700'
                }`}
              >
                All Games ({odds?.length || 0})
              </button>
              <button
                onClick={() => setFilter('live')}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
                  filter === 'live'
                    ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700'
                }`}
              >
                <span className="flex items-center">
                  {filter === 'live' && <span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></span>}
                  Live ({liveCount})
                </span>
              </button>
              <button
                onClick={() => setFilter('upcoming')}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
                  filter === 'upcoming'
                    ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700'
                }`}
              >
                Upcoming ({upcomingCount})
              </button>
            </div>
          </div>

          {/* Odds List */}
          {isLoading ? (
            <LoadingSkeleton type="odds" count={3} />
          ) : isError ? (
            <div className="bg-red-500/10 border border-red-500 rounded-xl p-12 text-center">
              <svg
                className="w-16 h-16 text-red-400 mx-auto mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <h3 className="text-red-400 text-xl font-bold mb-2">Failed to Load Odds</h3>
              <p className="text-red-300 mb-6">
                Unable to fetch betting odds. Please check your connection.
              </p>
              <button
                onClick={() => refetch()}
                className="bg-red-500 hover:bg-red-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
              >
                Try Again
              </button>
            </div>
          ) : filteredOdds.length === 0 ? (
            <div className="bg-gray-800 border border-gray-700 rounded-xl">
              <EmptyState
                type="odds"
                description={
                  filter === 'all'
                    ? undefined
                    : `No ${filter} games available. Try selecting a different filter.`
                }
                action={
                  filter !== 'all'
                    ? {
                        label: 'View All Games',
                        onClick: () => setFilter('all'),
                      }
                    : undefined
                }
              />
            </div>
          ) : (
            <div className="space-y-4">
              {filteredOdds.map((event, index) => (
                <OddsRow key={event.id || index} event={event} onBetClick={handleBetSelection} />
              ))}
            </div>
          )}

          {/* Auto-refresh indicator */}
          {!isLoading && odds && odds.length > 0 && (
            <div className="mt-8 text-center">
              <div className="inline-flex items-center bg-gray-800 border border-gray-700 rounded-lg px-4 py-2">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-3 animate-pulse"></span>
                <span className="text-gray-400 text-sm">
                  Odds refresh automatically every 15 seconds
                </span>
              </div>
            </div>
          )}

          {/* Betting Info */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <h4 className="text-white font-bold mb-2 flex items-center">
                <svg className="w-5 h-5 mr-2 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
                Bet Limits
              </h4>
              <p className="text-gray-400 text-sm">
                • Min bet: $1<br />
                • Max bet per event: $100<br />
                • Session limit: $100
              </p>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <h4 className="text-white font-bold mb-2 flex items-center">
                <svg className="w-5 h-5 mr-2 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z"
                    clipRule="evenodd"
                  />
                </svg>
                Bet Types
              </h4>
              <p className="text-gray-400 text-sm">
                • Moneyline: Pick the winner<br />
                • Spread: Point differential<br />
                • Over/Under: Total points
              </p>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <h4 className="text-white font-bold mb-2 flex items-center">
                <svg className="w-5 h-5 mr-2 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                Important
              </h4>
              <p className="text-gray-400 text-sm">
                • Odds change in real-time<br />
                • Bets lock at game start<br />
                • Responsible gambling
              </p>
            </div>
          </div>

          {/* Responsible Gambling Notice */}
          <div className="mt-8 bg-yellow-500/10 border border-yellow-500 rounded-xl p-6 text-center">
            <h3 className="text-yellow-400 font-bold mb-2 flex items-center justify-center">
              <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              Gamble Responsibly
            </h3>
            <p className="text-yellow-300 text-sm mb-3">
              Remember: Betting should be fun, not a way to make money. Set limits and stick to them.
            </p>
            <p className="text-yellow-300 text-xs">
              If you need help, call the National Problem Gambling Helpline:{' '}
              <a href="tel:1-800-522-4700" className="font-bold hover:text-yellow-200">
                1-800-522-4700
              </a>
            </p>
          </div>
        </div>
      </div>

      {/* Bet Confirmation Modal */}
      <BetConfirmationModal
        isOpen={isBetModalOpen}
        onClose={closeBetModal}
        betDetails={selectedBet}
      />
    </>
  );
};

export default Odds;
