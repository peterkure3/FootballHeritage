import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBetsHistory } from '../hooks/useBetting';
import useAuthStore from '../stores/authStore';
import Navbar from '../components/Navbar';
import BetCard from '../components/BetCard';
import LoadingSkeleton from '../components/LoadingSkeleton';
import EmptyState from '../components/EmptyState';

const BetHistory = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const { data: bets, isLoading, isError } = useBetsHistory();

  const [filter, setFilter] = useState('all'); // all, pending, won, lost
  const [searchTerm, setSearchTerm] = useState('');
  const [displayCount, setDisplayCount] = useState(10);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) {
    return null;
  }

  // Filter bets based on status and search
  const filteredBets = bets?.filter((bet) => {
    // Filter by status
    let statusMatch = true;
    if (filter === 'pending') {
      statusMatch = bet.status === 'pending' || bet.status === 'active';
    } else if (filter === 'won') {
      statusMatch = bet.status === 'won' || bet.status === 'settled_won';
    } else if (filter === 'lost') {
      statusMatch = bet.status === 'lost' || bet.status === 'settled_lost';
    }

    // Filter by search term
    let searchMatch = true;
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      const eventName = bet.event_name || bet.eventName || '';
      const betType = bet.type || bet.bet_type || '';
      searchMatch =
        eventName.toLowerCase().includes(search) ||
        betType.toLowerCase().includes(search);
    }

    return statusMatch && searchMatch;
  }) || [];

  // Paginated bets
  const displayedBets = filteredBets.slice(0, displayCount);
  const hasMore = displayCount < filteredBets.length;

  // Load more bets
  const loadMore = () => {
    setDisplayCount((prev) => prev + 10);
  };

  // Calculate statistics
  const totalBets = bets?.length || 0;
  const wonBets = bets?.filter(bet =>
    bet.status === 'won' || bet.status === 'settled_won'
  ).length || 0;
  const lostBets = bets?.filter(bet =>
    bet.status === 'lost' || bet.status === 'settled_lost'
  ).length || 0;
  const pendingBets = bets?.filter(bet =>
    bet.status === 'pending' || bet.status === 'active'
  ).length || 0;

  const totalWagered = bets?.reduce((sum, bet) => sum + (parseFloat(bet.amount) || 0), 0) || 0;
  const totalWon = bets?.filter(bet =>
    bet.status === 'won' || bet.status === 'settled_won'
  ).reduce((sum, bet) => sum + (parseFloat(bet.payout || bet.amount * bet.odds) || 0), 0) || 0;
  const netProfit = totalWon - totalWagered;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Section */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            📊 Betting History
          </h1>
          <p className="text-gray-400">
            View and track all your betting activity
          </p>
        </div>

        {/* Statistics Cards */}
        {isLoading ? (
          <LoadingSkeleton type="stats" count={1} />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {/* Total Bets */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors">
              <h3 className="text-gray-400 text-xs font-semibold uppercase mb-1">Total Bets</h3>
              <p className="text-white text-2xl font-bold">{totalBets}</p>
            </div>

            {/* Won Bets */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors">
              <h3 className="text-gray-400 text-xs font-semibold uppercase mb-1">Won</h3>
              <p className="text-green-400 text-2xl font-bold">{wonBets}</p>
              <p className="text-gray-500 text-xs mt-1">
                {totalBets > 0 ? `${Math.round((wonBets / totalBets) * 100)}%` : '0%'}
              </p>
            </div>

            {/* Lost Bets */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors">
              <h3 className="text-gray-400 text-xs font-semibold uppercase mb-1">Lost</h3>
              <p className="text-red-400 text-2xl font-bold">{lostBets}</p>
              <p className="text-gray-500 text-xs mt-1">
                {totalBets > 0 ? `${Math.round((lostBets / totalBets) * 100)}%` : '0%'}
              </p>
            </div>

            {/* Pending Bets */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors">
              <h3 className="text-gray-400 text-xs font-semibold uppercase mb-1">Pending</h3>
              <p className="text-yellow-400 text-2xl font-bold">{pendingBets}</p>
            </div>
          </div>
        )}

        {/* Financial Summary */}
        {!isLoading && totalBets > 0 && (
          <div className="bg-gradient-to-r from-gray-800 to-gray-900 border border-gray-700 rounded-xl p-6 mb-8">
            <h3 className="text-white text-lg font-bold mb-4">Financial Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-gray-400 text-sm mb-1">Total Wagered</p>
                <p className="text-white text-2xl font-bold">${totalWagered.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm mb-1">Total Won</p>
                <p className="text-green-400 text-2xl font-bold">${totalWon.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm mb-1">Net Profit/Loss</p>
                <p className={`text-2xl font-bold ${netProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {netProfit >= 0 ? '+' : ''}{netProfit.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Filters and Search */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 mb-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* Filter Tabs */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => {
                  setFilter('all');
                  setDisplayCount(10);
                }}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
                  filter === 'all'
                    ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                All ({totalBets})
              </button>
              <button
                onClick={() => {
                  setFilter('pending');
                  setDisplayCount(10);
                }}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
                  filter === 'pending'
                    ? 'bg-yellow-500 text-white shadow-lg shadow-yellow-500/30'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                Pending ({pendingBets})
              </button>
              <button
                onClick={() => {
                  setFilter('won');
                  setDisplayCount(10);
                }}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
                  filter === 'won'
                    ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                Won ({wonBets})
              </button>
              <button
                onClick={() => {
                  setFilter('lost');
                  setDisplayCount(10);
                }}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
                  filter === 'lost'
                    ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                Lost ({lostBets})
              </button>
            </div>

            {/* Search Bar */}
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg
                  className="w-5 h-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Search bets..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setDisplayCount(10);
                }}
                className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all"
              />
            </div>
          </div>
        </div>

        {/* Bets List */}
        {isLoading ? (
          <LoadingSkeleton type="card" count={5} />
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
            <h3 className="text-red-400 text-xl font-bold mb-2">Failed to Load History</h3>
            <p className="text-red-300">Unable to fetch your betting history. Please try again.</p>
          </div>
        ) : filteredBets.length === 0 ? (
          <div className="bg-gray-800 border border-gray-700 rounded-xl">
            <EmptyState
              type={searchTerm || filter !== 'all' ? 'search' : 'bets'}
              title={searchTerm || filter !== 'all' ? 'No Matching Bets' : undefined}
              description={
                searchTerm
                  ? 'Try adjusting your search or filters to find what you\'re looking for.'
                  : filter !== 'all'
                  ? `No ${filter} bets found. Try selecting a different filter.`
                  : undefined
              }
              action={
                (searchTerm || filter !== 'all')
                  ? {
                      label: 'Clear Filters',
                      onClick: () => {
                        setSearchTerm('');
                        setFilter('all');
                        setDisplayCount(10);
                      },
                    }
                  : {
                      label: 'Browse Odds',
                      onClick: () => navigate('/odds'),
                    }
              }
            />
          </div>
        ) : (
          <>
            {/* Results Count */}
            <div className="mb-4 text-gray-400 text-sm">
              Showing {displayedBets.length} of {filteredBets.length} bet{filteredBets.length !== 1 ? 's' : ''}
            </div>

            {/* Bets Grid */}
            <div className="space-y-4 mb-8">
              {displayedBets.map((bet, index) => (
                <BetCard key={bet.id || index} bet={bet} />
              ))}
            </div>

            {/* Load More Button */}
            {hasMore && (
              <div className="text-center">
                <button
                  onClick={loadMore}
                  className="bg-gray-800 hover:bg-gray-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors border border-gray-700"
                >
                  Load More ({filteredBets.length - displayCount} remaining)
                </button>
              </div>
            )}
          </>
        )}

        {/* Export/Download Options */}
        {!isLoading && filteredBets.length > 0 && (
          <div className="mt-8 bg-gray-800 border border-gray-700 rounded-xl p-6 text-center">
            <h3 className="text-white font-bold mb-2">Need your betting records?</h3>
            <p className="text-gray-400 text-sm mb-4">
              Contact support to request a detailed betting history export
            </p>
            <button
              onClick={() => window.location.href = 'mailto:support@sportsbet.com'}
              className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold transition-colors text-sm"
            >
              Contact Support
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default BetHistory;
