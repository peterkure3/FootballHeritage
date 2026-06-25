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

  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [displayCount, setDisplayCount] = useState(10);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) {
    return null;
  }

  const filteredBets = bets?.filter((bet) => {
    let statusMatch = true;
    if (filter === 'pending') {
      statusMatch = bet.status === 'pending' || bet.status === 'active';
    } else if (filter === 'won') {
      statusMatch = bet.status === 'won' || bet.status === 'settled_won';
    } else if (filter === 'lost') {
      statusMatch = bet.status === 'lost' || bet.status === 'settled_lost';
    }

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

  const displayedBets = filteredBets.slice(0, displayCount);
  const hasMore = displayCount < filteredBets.length;

  const loadMore = () => {
    setDisplayCount((prev) => prev + 10);
  };

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
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight">
              Betting History
            </h1>
            <span className="text-2xl">📊</span>
          </div>
          <p className="text-sm" style={{ color: '#64748b' }}>
            View and track all your betting activity
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton type="stats" count={1} />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 mb-8 stagger-children">
            <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <h3 className="text-xs font-semibold uppercase mb-1" style={{ color: '#64748b' }}>Total Bets</h3>
              <p className="text-white text-2xl font-bold font-[Oswald] tracking-tight">{totalBets}</p>
            </div>
            <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <h3 className="text-xs font-semibold uppercase mb-1" style={{ color: '#10b981' }}>Won</h3>
              <p className="text-green-400 text-2xl font-bold font-[Oswald] tracking-tight">{wonBets}</p>
              <p className="text-xs mt-1" style={{ color: '#64748b' }}>
                {totalBets > 0 ? `${Math.round((wonBets / totalBets) * 100)}%` : '0%'}
              </p>
            </div>
            <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <h3 className="text-xs font-semibold uppercase mb-1" style={{ color: '#ef4444' }}>Lost</h3>
              <p className="text-red-400 text-2xl font-bold font-[Oswald] tracking-tight">{lostBets}</p>
              <p className="text-xs mt-1" style={{ color: '#64748b' }}>
                {totalBets > 0 ? `${Math.round((lostBets / totalBets) * 100)}%` : '0%'}
              </p>
            </div>
            <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
              <h3 className="text-xs font-semibold uppercase mb-1" style={{ color: '#f59e0b' }}>Pending</h3>
              <p className="text-yellow-400 text-2xl font-bold font-[Oswald] tracking-tight">{pendingBets}</p>
            </div>
          </div>
        )}

        {!isLoading && totalBets > 0 && (
          <div className="card-glow rounded-xl p-6 mb-8 border" style={{ background: 'linear-gradient(135deg, var(--color-card), #16162a)', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.5s ease-out 0.1s both' }}>
            <h3 className="text-white font-bold mb-4 font-[Oswald] tracking-tight text-lg">Financial Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-xs mb-1" style={{ color: '#64748b' }}>Total Wagered</p>
                <p className="text-white text-2xl font-bold font-[Oswald] tracking-tight">${totalWagered.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-xs mb-1" style={{ color: '#64748b' }}>Total Won</p>
                <p className="text-green-400 text-2xl font-bold font-[Oswald] tracking-tight">${totalWon.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-xs mb-1" style={{ color: '#64748b' }}>Net Profit/Loss</p>
                <p className={`text-2xl font-bold font-[Oswald] tracking-tight ${netProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {netProfit >= 0 ? '+' : ''}{netProfit.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="card-glow rounded-xl p-4 mb-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.5s ease-out 0.15s both' }}>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => { setFilter('all'); setDisplayCount(10); }}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                  filter === 'all'
                    ? 'text-white shadow-lg'
                    : 'text-gray-400 hover:text-white'
                }`}
                style={filter === 'all' ? { background: 'linear-gradient(135deg, #10b981, #059669)' } : { background: 'var(--color-card)' }}
              >
                All ({totalBets})
              </button>
              <button
                onClick={() => { setFilter('pending'); setDisplayCount(10); }}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                  filter === 'pending'
                    ? 'text-white shadow-lg'
                    : 'text-gray-400 hover:text-white'
                }`}
                style={filter === 'pending' ? { background: 'linear-gradient(135deg, #f59e0b, #d97706)' } : { background: 'var(--color-card)' }}
              >
                Pending ({pendingBets})
              </button>
              <button
                onClick={() => { setFilter('won'); setDisplayCount(10); }}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                  filter === 'won'
                    ? 'text-white shadow-lg'
                    : 'text-gray-400 hover:text-white'
                }`}
                style={filter === 'won' ? { background: 'linear-gradient(135deg, #10b981, #059669)' } : { background: 'var(--color-card)' }}
              >
                Won ({wonBets})
              </button>
              <button
                onClick={() => { setFilter('lost'); setDisplayCount(10); }}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                  filter === 'lost'
                    ? 'text-white shadow-lg'
                    : 'text-gray-400 hover:text-white'
                }`}
                style={filter === 'lost' ? { background: 'linear-gradient(135deg, #ef4444, #dc2626)' } : { background: 'var(--color-card)' }}
              >
                Lost ({lostBets})
              </button>
            </div>

            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="w-5 h-5" style={{ color: '#64748b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Search bets..."
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setDisplayCount(10); }}
                className="w-full pl-10 pr-4 py-2 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
              />
            </div>
          </div>
        </div>

        {isLoading ? (
          <LoadingSkeleton type="card" count={5} />
        ) : isError ? (
          <div className="rounded-xl p-12 text-center border card-glow" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'rgba(239, 68, 68, 0.3)', animation: 'fade-in 0.3s ease-out' }}>
            <svg className="w-16 h-16 mx-auto mb-4" style={{ color: '#ef4444' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-xl font-bold mb-2 font-[Oswald] tracking-tight" style={{ color: '#ef4444' }}>Failed to Load History</h3>
            <p style={{ color: '#fca5a5' }}>Unable to fetch your betting history. Please try again.</p>
          </div>
        ) : filteredBets.length === 0 ? (
          <div className="rounded-xl border card-glow" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
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
            <div className="mb-4" style={{ color: '#64748b', animation: 'fade-in 0.3s ease-out' }}>
              <span className="text-sm">Showing {displayedBets.length} of {filteredBets.length} bet{filteredBets.length !== 1 ? 's' : ''}</span>
            </div>

            <div className="space-y-4 mb-8 stagger-children">
              {displayedBets.map((bet, index) => (
                <BetCard key={bet.id || index} bet={bet} />
              ))}
            </div>

            {hasMore && (
              <div className="text-center">
                <button
                  onClick={loadMore}
                  className="px-8 py-3 rounded-lg font-semibold text-sm transition-all card-glow hover:opacity-90"
                  style={{
                    background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))',
                    border: '1px solid var(--color-card-border)',
                    color: 'white',
                  }}
                >
                  Load More ({filteredBets.length - displayCount} remaining)
                </button>
              </div>
            )}
          </>
        )}

        {!isLoading && filteredBets.length > 0 && (
          <div className="card-glow rounded-xl p-6 text-center border mt-8" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.5s ease-out 0.2s both' }}>
            <h3 className="text-white font-bold mb-2 font-[Oswald] tracking-tight">Need your betting records?</h3>
            <p className="text-sm mb-4" style={{ color: '#64748b' }}>
              Contact support to request a detailed betting history export
            </p>
            <button
              onClick={() => window.location.href = 'mailto:support@sportsbet.com'}
              className="text-white px-6 py-2.5 rounded-lg font-semibold text-sm transition-all hover:opacity-90"
              style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}
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
