import { useState, useEffect, lazy, Suspense } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useOdds } from '../hooks/useBetting';
import useAuthStore from '../stores/authStore';
import Navbar from '../components/Navbar';
import OddsRow from '../components/OddsRow';
import BetConfirmationModal from '../components/BetConfirmationModal';
import LoadingSkeleton from '../components/LoadingSkeleton';
import EmptyState from '../components/EmptyState';
import { SPORTS, getAllSports, getSportByApiParam } from '../utils/constants';

/**
 * Lazy load ParlayBuilderSidebar for better performance
 * Only loads when user adds bets to parlay
 * Reduces initial bundle size by ~50KB
 */
const ParlayBuilderSidebar = lazy(() => import('../components/parlay/ParlayBuilderSidebar'));

const Odds = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuthStore();
  const { data: odds, isLoading, isError, refetch } = useOdds();

  const [selectedBet, setSelectedBet] = useState(null);
  const [isBetModalOpen, setIsBetModalOpen] = useState(false);
  const [filter, setFilter] = useState('all'); // all, live, upcoming
  
  // Get sport filter from URL params (e.g., ?sport=soccer)
  const sportParam = searchParams.get('sport');
  const [selectedSport, setSelectedSport] = useState(sportParam || 'all');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // Update selected sport when URL params change
  useEffect(() => {
    if (sportParam) {
      setSelectedSport(sportParam);
    }
  }, [sportParam]);

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

  // Filter odds based on status AND sport/league
  const filteredOdds = odds?.filter((event) => {
    // Filter by status
    let statusMatch = true;
    if (filter === 'live') {
      statusMatch = event.status === 'live' || event.status === 'in_progress';
    } else if (filter === 'upcoming') {
      statusMatch = event.status === 'upcoming' || event.status === 'scheduled';
    }
    
    // Filter by sport or league (if a specific sport is selected)
    let sportMatch = true;
    if (selectedSport !== 'all') {
      const sportConfig = getSportByApiParam(selectedSport);
      
      // For NBA Cup, filter by league instead of sport
      if (sportConfig?.league) {
        sportMatch = event.league?.toLowerCase() === sportConfig.league.toLowerCase();
      } else {
        // For other sports, filter by sport field
        sportMatch = event.sport?.toLowerCase() === selectedSport.toLowerCase();
      }
    }
    
    return statusMatch && sportMatch;
  }) || [];

  // Count events by status
  const liveCount = odds?.filter(e => e.status === 'live' || e.status === 'in_progress').length || 0;
  const upcomingCount = odds?.filter(e => e.status === 'upcoming' || e.status === 'scheduled').length || 0;

  return (
    <>
      <div className="min-h-screen" style={{ background: 'var(--color-surface)' }}>
        <Navbar />

        {/* Main content with right padding for parlay sidebar */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pr-4 lg:pr-8">
          {/* Header Section */}
          <div className="mb-8">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
              <div>
                <h1 className="text-3xl md:text-4xl font-bold text-white mb-2 flex items-center font-[Oswald] tracking-tight">
                  <span className="text-4xl mr-3">
                    {selectedSport === 'all' ? '🏆' : getSportByApiParam(selectedSport)?.icon || '🏆'}
                  </span>
                  {selectedSport === 'all' 
                    ? 'All Sports Betting Odds' 
                    : `${getSportByApiParam(selectedSport)?.displayName || 'Sports'} Betting Odds`
                  }
                </h1>
                {/* <p className="text-gray-400">
                  Live odds update every 15 seconds • Place your bets now
                </p> */}
              </div>

              {/* Refresh Button */}
              <button
                onClick={() => refetch()}
                disabled={isLoading}
                className="mt-4 md:mt-0 flex items-center text-white px-4 py-2 rounded-lg font-semibold text-sm transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed card-glow"
                style={{
                  background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))',
                  border: '1px solid var(--color-card-border)',
                }}
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

            {/* Sport Filter Dropdown */}
            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2" style={{ color: '#64748b' }}>
                Filter by Sport:
              </label>
              <select
                value={selectedSport}
                onChange={(e) => {
                  const newSport = e.target.value;
                  setSelectedSport(newSport);
                  if (newSport === 'all') {
                    searchParams.delete('sport');
                  } else {
                    searchParams.set('sport', newSport);
                  }
                  setSearchParams(searchParams);
                }}
                className="w-full md:w-64 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 transition-all"
                style={{
                  background: 'var(--color-card)',
                  border: '1px solid var(--color-card-border)',
                  '--tw-ring-color': '#10b981',
                }}
              >
                <option value="all">🏆 All Sports</option>
                {getAllSports().map((sport) => (
                  <option key={sport.key} value={sport.apiParam}>
                    {sport.icon} {sport.displayName}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter Tabs */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setFilter('all')}
                className="px-4 py-2 rounded-lg font-semibold text-sm transition-all"
                style={{
                  background: filter === 'all' ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--color-card)',
                  color: filter === 'all' ? 'white' : '#94a3b8',
                  border: filter === 'all' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--color-card-border)',
                }}
              >
                All Games ({odds?.length || 0})
              </button>
              <button
                onClick={() => setFilter('live')}
                className="px-4 py-2 rounded-lg font-semibold text-sm transition-all"
                style={{
                  background: filter === 'live' ? 'linear-gradient(135deg, #ef4444, #dc2626)' : 'var(--color-card)',
                  color: filter === 'live' ? 'white' : '#94a3b8',
                  border: filter === 'live' ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid var(--color-card-border)',
                }}
              >
                <span className="flex items-center">
                  {filter === 'live' && <span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></span>}
                  Live ({liveCount})
                </span>
              </button>
              <button
                onClick={() => setFilter('upcoming')}
                className="px-4 py-2 rounded-lg font-semibold text-sm transition-all"
                style={{
                  background: filter === 'upcoming' ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : 'var(--color-card)',
                  color: filter === 'upcoming' ? 'white' : '#94a3b8',
                  border: filter === 'upcoming' ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid var(--color-card-border)',
                }}
              >
                Upcoming ({upcomingCount})
              </button>
            </div>
          </div>

          {/* Odds List */}
          {isLoading ? (
            <LoadingSkeleton type="odds" count={3} />
          ) : isError ? (
            <div className="rounded-xl p-12 text-center border card-glow" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
              <svg
                className="w-16 h-16 mx-auto mb-4"
                style={{ color: '#ef4444' }}
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
              <h3 className="text-xl font-bold mb-2 font-[Oswald] tracking-tight" style={{ color: '#ef4444' }}>Failed to Load Odds</h3>
              <p className="mb-6" style={{ color: '#fca5a5' }}>
                Unable to fetch betting odds. Please check your connection.
              </p>
              <button
                onClick={() => refetch()}
                className="text-white px-6 py-3 rounded-lg font-semibold transition-all hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, #ef4444, #dc2626)' }}
              >
                Try Again
              </button>
            </div>
          ) : filteredOdds.length === 0 ? (
            <div className="rounded-xl border card-glow" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
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
              {/* <div className="inline-flex items-center bg-gray-800 border border-gray-700 rounded-lg px-4 py-2">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-3 animate-pulse"></span>
                <span className="text-gray-400 text-sm">
                  Odds refresh automatically every 15 seconds
                </span>
              </div> */}
            </div>
          )}

          {/* Betting Info */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4 stagger-children">
            <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <h4 className="text-white font-bold mb-2 flex items-center font-[Oswald] tracking-tight">
                <svg className="w-5 h-5 mr-2" style={{ color: '#10b981' }} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                Bet Limits
              </h4>
              <p className="text-sm" style={{ color: '#94a3b8' }}>
                • Min bet: $1<br />
                • Max bet per event: $100<br />
                • Session limit: $100
              </p>
            </div>

            <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <h4 className="text-white font-bold mb-2 flex items-center font-[Oswald] tracking-tight">
                <svg className="w-5 h-5 mr-2" style={{ color: '#6366f1' }} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                </svg>
                Bet Types
              </h4>
              <p className="text-sm" style={{ color: '#94a3b8' }}>
                • Moneyline: Pick the winner<br />
                • Spread: Point differential<br />
                • Over/Under: Total points
              </p>
            </div>

            <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <h4 className="text-white font-bold mb-2 flex items-center font-[Oswald] tracking-tight">
                <svg className="w-5 h-5 mr-2" style={{ color: '#f59e0b' }} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Important
              </h4>
              <p className="text-sm" style={{ color: '#94a3b8' }}>
                • Odds change in real-time<br />
                • Bets lock at game start<br />
                • Responsible gambling
              </p>
            </div>
          </div>

          {/* Responsible Gambling Notice */}
          <div className="mt-8 rounded-xl p-6 text-center border card-glow" style={{ background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.03))', borderColor: 'rgba(245, 158, 11, 0.2)' }}>
            <h3 className="font-bold mb-2 flex items-center justify-center font-[Oswald] tracking-tight text-lg" style={{ color: '#fbb84d' }}>
              <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              Gamble Responsibly
            </h3>
            <p className="text-sm mb-3" style={{ color: '#fcd34d' }}>
              Remember: Betting should be fun, not a way to make money. Set limits and stick to them.
            </p>
            <p className="text-xs" style={{ color: '#fbb84d' }}>
              If you need help, call the National Problem Gambling Helpline:{' '}
              <a href="tel:1-800-522-4700" className="font-bold hover:underline" style={{ color: '#fcd34d' }}>
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

      {/* Parlay Builder Sidebar - Lazy loaded for performance */}
      <Suspense fallback={null}>
        <ParlayBuilderSidebar />
      </Suspense>
    </>
  );
};

export default Odds;
