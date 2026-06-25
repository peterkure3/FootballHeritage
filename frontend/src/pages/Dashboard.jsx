import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../hooks/useAuth';
import { useBetsHistory } from '../hooks/useBetting';
import useAuthStore from '../stores/authStore';
import useBettingStore from '../stores/bettingStore';
import Navbar from '../components/Navbar';
import BetCard from '../components/BetCard';
import LoadingSkeleton from '../components/LoadingSkeleton';

const StatCard = ({ title, value, subtitle, icon, accent, delay = 0 }) => (
  <div
    className="card-glow rounded-xl p-6 border"
    style={{
      background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))',
      borderColor: 'var(--color-card-border)',
      animation: `slide-up 0.5s ease-out ${delay}s both`,
    }}
  >
    <div className="flex items-center justify-between mb-3">
      <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: accent }}>{title}</span>
      <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${accent}15` }}>
        <svg className="w-5 h-5" fill="none" stroke={accent} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={icon} />
        </svg>
      </div>
    </div>
    <p className="text-3xl font-bold text-white mb-0.5 font-[Oswald] tracking-tight">{value}</p>
    <p className="text-xs" style={{ color: 'var(--color-muted, #64748b)' }}>{subtitle}</p>
  </div>
);

const Dashboard = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const { data: user, isLoading: userLoading } = useUser();
  const { data: bets, isLoading: betsLoading } = useBetsHistory();
  const { getSessionStats } = useBettingStore();

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

  const totalBets = bets?.length || 0;
  const wonBets = bets?.filter(bet =>
    bet.status === 'won' || bet.status === 'settled_won'
  ).length || 0;
  const pendingBets = activeBets.length;
  const winRate = totalBets > 0 ? Math.round((wonBets / totalBets) * 100) : 0;

  const quickActions = [
    {
      label: 'Place Bet',
      desc: 'Browse odds and place wagers',
      icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
      path: '/odds',
      gradient: 'linear-gradient(135deg, #10b981, #059669)',
      accent: '#10b981',
    },
    {
      label: 'My Bets',
      desc: 'Track your active wagers',
      icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
      path: '/bets',
      gradient: 'linear-gradient(135deg, #6366f1, #4f46e5)',
      accent: '#6366f1',
    },
    {
      label: 'AI Picks',
      desc: 'Smart predictions & insights',
      icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
      path: '/best-bets',
      gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
      accent: '#f59e0b',
    },
  ];

  return (
    <div className="min-h-screen" style={{ background: 'var(--color-surface)' }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight">
              Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}
            </h1>
            <span className="text-2xl">🏈</span>
          </div>
          <p className="text-sm" style={{ color: '#64748b' }}>
            Check your balance, active bets, and betting statistics
          </p>
        </div>

        {/* Stats Grid */}
        {userLoading ? (
          <LoadingSkeleton type="stats" count={1} />
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-8 mb-8 stagger-children">
            <StatCard
              title="Balance"
              value={`$${user?.balance?.toFixed(2) || '0.00'}`}
              subtitle="Available to bet"
              accent="#10b981"
              icon="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              delay={0}
            />
            <StatCard
              title="Total Bets"
              value={totalBets}
              subtitle="All time"
              accent="#6366f1"
              icon="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
              delay={0.06}
            />
            <StatCard
              title="Win Rate"
              value={`${winRate}%`}
              subtitle={`${wonBets} won / ${totalBets - wonBets} lost`}
              accent="#f59e0b"
              icon="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              delay={0.1}
            />
            <StatCard
              title="Pending"
              value={pendingBets}
              subtitle="Active bets"
              accent="#f97316"
              icon="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              delay={0.14}
            />
          </div>
        )}

        {/* Session Limit Progress */}
        <div
          className="rounded-xl p-6 mb-8 border card-glow stagger-children"
          style={{
            background: 'linear-gradient(135deg, var(--card, #14141f), #16162a)',
            borderColor: 'var(--color-card-border)',
            animation: 'slide-up 0.5s ease-out 0.18s both',
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold font-[Oswald] tracking-tight text-lg">
              Session Limit
            </h3>
            <span
              className="text-xs font-bold px-3 py-1 rounded-full"
              style={{
                background: sessionStats.percentUsed >= 80
                  ? 'rgba(239, 68, 68, 0.15)'
                  : sessionStats.percentUsed >= 50
                  ? 'rgba(245, 158, 11, 0.15)'
                  : 'rgba(16, 185, 129, 0.15)',
                color: sessionStats.percentUsed >= 80
                  ? '#ef4444'
                  : sessionStats.percentUsed >= 50
                  ? '#f59e0b'
                  : '#10b981',
              }}
            >
              {sessionStats.percentUsed}% Used
            </span>
          </div>
          <div className="rounded-full h-2 mb-3 overflow-hidden" style={{ background: '#1a1a2e' }}>
            <div
              className="h-full transition-all duration-700 ease-out rounded-full"
              style={{
                width: `${Math.min(sessionStats.percentUsed, 100)}%`,
                background: sessionStats.percentUsed >= 80
                  ? 'linear-gradient(90deg, #ef4444, #dc2626)'
                  : sessionStats.percentUsed >= 50
                  ? 'linear-gradient(90deg, #f59e0b, #d97706)'
                  : 'linear-gradient(90deg, #10b981, #059669)',
              }}
            />
          </div>
          <div className="flex justify-between text-xs" style={{ color: '#64748b' }}>
            <span>Used: <span className="text-white font-semibold">${sessionStats.total.toFixed(2)}</span></span>
            <span>Remaining: <span className="text-white font-semibold">${sessionStats.remaining.toFixed(2)}</span></span>
            <span>Limit: <span className="text-white font-semibold">${sessionStats.limit}</span></span>
          </div>
          {sessionStats.percentUsed >= 80 && (
            <div className="mt-4 rounded-lg p-3 flex items-center gap-2 text-sm" style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.2)', color: '#fbb84d' }}>
              <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              You're approaching your session limit. Remember to gamble responsibly!
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8 stagger-children">
          {quickActions.map((action) => (
            <button
              key={action.path}
              onClick={() => navigate(action.path)}
              className="rounded-xl p-6 border text-left transition-all active:scale-[0.98] card-glow"
              style={{
                background: action.gradient,
                borderColor: `${action.accent}40`,
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-bold text-white font-[Oswald] tracking-tight">{action.label}</h3>
                <svg className="w-7 h-7 opacity-60" fill="none" stroke="white" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.7)' }}>{action.desc}</p>
            </button>
          ))}
        </div>

        {/* Active Bets Section */}
        {activeBets.length > 0 && (
          <div className="mb-8" style={{ animation: 'slide-up 0.5s ease-out 0.3s both' }}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white font-[Oswald] tracking-tight flex items-center gap-3">
                <span className="w-2 h-2 rounded-full animate-pulse-glow" style={{ background: '#10b981' }}></span>
                Active Bets
              </h2>
              <span className="text-xs" style={{ color: '#64748b' }}>{activeBets.length} pending</span>
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
                  className="font-semibold text-sm transition-colors hover:underline"
                  style={{ color: '#10b981' }}
                >
                  View all {activeBets.length} active bets →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Recent Bets Section */}
        <div className="mb-8" style={{ animation: 'slide-up 0.5s ease-out 0.35s both' }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white font-[Oswald] tracking-tight">Recent Bets</h2>
            <button
              onClick={() => navigate('/bets')}
              className="font-semibold text-sm transition-colors hover:underline"
              style={{ color: '#10b981' }}
            >
              View All →
            </button>
          </div>
          {betsLoading ? (
            <LoadingSkeleton type="card" count={3} />
          ) : recentBets.length > 0 ? (
            <div className="space-y-3">
              {recentBets.map((bet, index) => (
                <BetCard key={bet.id || index} bet={bet} />
              ))}
            </div>
          ) : (
            <div
              className="rounded-xl p-12 text-center border card-glow"
              style={{
                background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))',
                borderColor: 'var(--color-card-border)',
              }}
            >
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
                <svg className="w-8 h-8" fill="none" stroke="#10b981" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h3 className="text-white text-lg font-bold mb-2 font-[Oswald]">No Bets Yet</h3>
              <p className="text-sm mb-6" style={{ color: '#64748b' }}>Start betting to see your history here</p>
              <button
                onClick={() => navigate('/odds')}
                className="font-semibold px-6 py-2.5 rounded-lg text-sm transition-all hover:opacity-90"
                style={{
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  color: 'white',
                }}
              >
                Browse Odds
              </button>
            </div>
          )}
        </div>

        {/* Responsible Gambling Notice */}
        <div
          className="rounded-xl p-6 text-center border mb-8"
          style={{
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(99, 102, 241, 0.03))',
            borderColor: 'rgba(99, 102, 241, 0.2)',
            animation: 'slide-up 0.5s ease-out 0.4s both',
          }}
        >
          <h3 className="font-bold mb-2 font-[Oswald] text-lg" style={{ color: '#818cf8' }}>Play Responsibly</h3>
          <p className="text-sm mb-3" style={{ color: '#a5b4fc' }}>
            Set limits, know when to stop, and never bet more than you can afford to lose.
          </p>
          <p className="text-xs" style={{ color: '#818cf8' }}>
            Need help? Call{' '}
            <a href="tel:1-800-522-4700" className="font-bold hover:underline" style={{ color: '#a5b4fc' }}>
              1-800-522-4700
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
