import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../hooks/useAuth';
import { useBetsHistory } from '../hooks/useBetting';
import useAuthStore from '../stores/authStore';
import useBettingStore from '../stores/bettingStore';
import Navbar from '../components/Navbar';
import BetCard from '../components/BetCard';
import LoadingSkeleton from '../components/LoadingSkeleton';

const Dashboard = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const { data: user, isLoading: userLoading } = useUser();
  const { data: bets, isLoading: betsLoading } = useBetsHistory();
  const { getSessionStats } = useBettingStore();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) {
    return null;
  }

  const sessionStats = getSessionStats();
  const activeBets = bets?.filter(bet =>
    bet.status === 'pending' || bet.status === 'active'
  ) || [];
  const recentBets = bets?.slice(0, 5) || [];

  // Calculate statistics
  const totalBets = bets?.length || 0;
  const wonBets = bets?.filter(bet =>
    bet.status === 'won' || bet.status === 'settled_won'
  ).length || 0;
  const pendingBets = activeBets.length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}! 🏈
          </h1>
          <p className="text-gray-400">
            Check your balance, active bets, and betting statistics
          </p>
        </div>

        {/* Stats Grid */}
        {userLoading ? (
          <LoadingSkeleton type="stats" count={1} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            {/* Balance Card */}
            <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl p-6 shadow-xl border border-green-500/50">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-green-100 text-sm font-semibold uppercase">Balance</h3>
                <svg className="w-8 h-8 text-green-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-white text-3xl font-bold mb-1">
                ${user?.balance?.toFixed(2) || '0.00'}
              </p>
              <p className="text-green-100 text-xs">Available to bet</p>
            </div>

            {/* Total Bets Card */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-xl hover:border-gray-600 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-gray-400 text-sm font-semibold uppercase">Total Bets</h3>
                <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
              </div>
              <p className="text-white text-3xl font-bold mb-1">{totalBets}</p>
              <p className="text-gray-400 text-xs">All time</p>
            </div>

            {/* Won Bets Card */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-xl hover:border-gray-600 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-gray-400 text-sm font-semibold uppercase">Won Bets</h3>
                <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-white text-3xl font-bold mb-1">{wonBets}</p>
              <p className="text-gray-400 text-xs">
                {totalBets > 0 ? `${Math.round((wonBets / totalBets) * 100)}%` : '0%'} win rate
              </p>
            </div>

            {/* Pending Bets Card */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-xl hover:border-gray-600 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-gray-400 text-sm font-semibold uppercase">Pending</h3>
                <svg className="w-8 h-8 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-white text-3xl font-bold mb-1">{pendingBets}</p>
              <p className="text-gray-400 text-xs">Active bets</p>
            </div>
          </div>
        )}

        {/* Session Limit Progress */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-8 shadow-xl">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white text-lg font-bold">Session Betting Limit</h3>
            <span className={`text-sm font-semibold ${
              sessionStats.percentUsed >= 80 ? 'text-red-400' :
              sessionStats.percentUsed >= 50 ? 'text-yellow-400' :
              'text-green-400'
            }`}>
              {sessionStats.percentUsed}% Used
            </span>
          </div>
          <div className="bg-gray-900 rounded-full h-4 overflow-hidden mb-2">
            <div
              className={`h-full transition-all duration-500 ${
                sessionStats.percentUsed >= 80 ? 'bg-red-500' :
                sessionStats.percentUsed >= 50 ? 'bg-yellow-500' :
                'bg-green-500'
              }`}
              style={{ width: `${Math.min(sessionStats.percentUsed, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">
              Used: <span className="text-white font-semibold">${sessionStats.total.toFixed(2)}</span>
            </span>
            <span className="text-gray-400">
              Remaining: <span className="text-white font-semibold">${sessionStats.remaining.toFixed(2)}</span>
            </span>
            <span className="text-gray-400">
              Limit: <span className="text-white font-semibold">${sessionStats.limit}</span>
            </span>
          </div>
          {sessionStats.percentUsed >= 80 && (
            <div className="mt-3 bg-yellow-500/10 border border-yellow-500 rounded-lg p-3">
              <p className="text-yellow-400 text-sm flex items-center">
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                You're approaching your session limit. Remember to gamble responsibly!
              </p>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <button
            onClick={() => navigate('/odds')}
            className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white rounded-xl p-6 shadow-xl transition-all active:scale-95 border border-green-500/50"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xl font-bold">Place Bet</h3>
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <p className="text-green-100 text-sm">Browse NFL odds and place your bets</p>
          </button>

          <button
            onClick={() => navigate('/bets')}
            className="bg-gray-800 hover:bg-gray-700 text-white rounded-xl p-6 shadow-xl transition-all active:scale-95 border border-gray-700 hover:border-gray-600"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xl font-bold">My Bets</h3>
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <p className="text-gray-300 text-sm">View your complete betting history</p>
          </button>

          <a
            href="https://www.ncpgambling.org"
            target="_blank"
            rel="noopener noreferrer"
            className="bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded-xl p-6 shadow-xl transition-all active:scale-95 border border-blue-500/50"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xl font-bold">Get Help</h3>
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-blue-200 text-sm">Resources for responsible gambling</p>
          </a>
        </div>

        {/* Active Bets Section */}
        {activeBets.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-white flex items-center">
                <span className="w-3 h-3 bg-green-500 rounded-full mr-3 animate-pulse"></span>
                Active Bets
              </h2>
              <span className="text-gray-400 text-sm">{activeBets.length} pending</span>
            </div>
            {betsLoading ? (
              <LoadingSkeleton type="card" count={2} />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {activeBets.slice(0, 4).map((bet, index) => (
                  <BetCard key={bet.id || index} bet={bet} />
                ))}
              </div>
            )}
            {activeBets.length > 4 && (
              <div className="mt-4 text-center">
                <button
                  onClick={() => navigate('/bets')}
                  className="text-green-400 hover:text-green-300 font-semibold text-sm transition-colors"
                >
                  View all {activeBets.length} active bets →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Recent Bets Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-white">Recent Bets</h2>
            <button
              onClick={() => navigate('/bets')}
              className="text-green-400 hover:text-green-300 font-semibold text-sm transition-colors"
            >
              View All →
            </button>
          </div>
          {betsLoading ? (
            <LoadingSkeleton type="card" count={3} />
          ) : recentBets.length > 0 ? (
            <div className="space-y-4">
              {recentBets.map((bet, index) => (
                <BetCard key={bet.id || index} bet={bet} />
              ))}
            </div>
          ) : (
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center">
              <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <h3 className="text-white text-xl font-bold mb-2">No Bets Yet</h3>
              <p className="text-gray-400 mb-6">Start betting on NFL games to see your history here</p>
              <button
                onClick={() => navigate('/odds')}
                className="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors shadow-lg shadow-green-500/30"
              >
                Browse Odds
              </button>
            </div>
          )}
        </div>

        {/* Responsible Gambling Notice */}
        <div className="bg-blue-500/10 border border-blue-500/50 rounded-xl p-6 text-center">
          <h3 className="text-blue-300 font-bold mb-2">🎰 Gamble Responsibly</h3>
          <p className="text-blue-200 text-sm mb-3">
            Set limits, know when to stop, and never bet more than you can afford to lose.
          </p>
          <p className="text-blue-300 text-xs">
            Need help? Call the National Problem Gambling Helpline:{' '}
            <a href="tel:1-800-522-4700" className="font-bold hover:text-blue-200">
              1-800-522-4700
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
