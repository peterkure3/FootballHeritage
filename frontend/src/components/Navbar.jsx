import { memo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../stores/authStore';
import { useLogout } from '../hooks/useAuth';
import WalletModal from './WalletModal';
import RoleSwitcher from './RoleSwitcher';
import { SPORTS } from '../utils/constants';

const Navbar = memo(() => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuthStore();
  const logout = useLogout();

  const [isWalletOpen, setIsWalletOpen] = useState(false);
  const [walletTab, setWalletTab] = useState('deposit');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    setIsMobileMenuOpen(false);
  };

  const openWallet = (tab = 'deposit') => {
    setWalletTab(tab);
    setIsWalletOpen(true);
    setIsMobileMenuOpen(false);
  };

  const handleNavigation = (path) => {
    navigate(path);
    setIsMobileMenuOpen(false);
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      <nav className="bg-gray-900 border-b border-gray-800 sticky top-0 z-40 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center">
              <Link
                to="/dashboard"
                className="flex items-center space-x-2 hover:opacity-80 transition-opacity"
              >
                <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center shadow-lg">
                  <span className="text-white text-xl font-bold">🏈</span>
                </div>
                <span className="text-white text-xl font-bold hidden sm:block">
                  Sports<span className="text-green-400">Bet</span>
                </span>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-4">
              <Link
                to="/dashboard"
                className="text-gray-300 hover:text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors"
              >
                Dashboard
              </Link>
              <div className="relative group">
                <button
                  type="button"
                  className="text-gray-300 hover:text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors inline-flex items-center gap-2"
                >
                  Explore
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <div className="absolute left-0 mt-2 w-64 bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                  <div className="p-4 space-y-2">
                    <Link to="/odds" className="flex flex-col rounded-lg px-3 py-2 text-sm text-gray-200 hover:bg-gray-800">
                      <span className="font-semibold">All Odds</span>
                      <span className="text-xs text-gray-500">Live & upcoming</span>
                    </Link>
                    <Link to="/sports" className="flex flex-col rounded-lg px-3 py-2 text-sm text-gray-200 hover:bg-gray-800">
                      <span className="font-semibold">Sports Hub</span>
                      <span className="text-xs text-gray-500">Leagues & markets</span>
                    </Link>
                  </div>
                </div>
              </div>

              <div className="relative group">
                <button
                  type="button"
                  className="text-gray-300 hover:text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors inline-flex items-center gap-2"
                >
                  AI Tools
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <div className="absolute left-0 mt-2 w-64 bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                  <div className="p-4 space-y-2">
                    <Link to="/predictions" className="flex flex-col rounded-lg px-3 py-2 text-sm text-gray-200 hover:bg-gray-800">
                      <span className="font-semibold">Predictions</span>
                      <span className="text-xs text-gray-500">Match insights</span>
                    </Link>
                    <Link to="/chat" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-200 hover:bg-gray-800">
                      <span className="text-lg">🤖</span>
                      <div>
                        <p className="font-semibold leading-tight">AI Chat</p>
                        <p className="text-xs text-gray-500">Ask betting questions</p>
                      </div>
                    </Link>
                    <Link to="/parlay-calculator" className="flex flex-col rounded-lg px-3 py-2 text-sm text-gray-200 hover:bg-gray-800">
                      <span className="font-semibold">Parlay Builder</span>
                      <span className="text-xs text-gray-500">Stack your slips</span>
                    </Link>
                  </div>
                </div>
              </div>

              <div className="relative group">
                <button
                  type="button"
                  className="text-gray-300 hover:text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors inline-flex items-center gap-2"
                >
                  Quick Filters
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <div className="absolute left-0 mt-2 w-72 bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                  <div className="p-4 space-y-2">
                    <Link to={`/odds?sport=${SPORTS.SOCCER.apiParam}`} className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-gray-200 hover:bg-gray-800">
                      <span className="flex items-center gap-2">
                        <span>{SPORTS.SOCCER.icon}</span>
                        {SPORTS.SOCCER.displayName}
                      </span>
                      <span className="text-xs text-gray-500">Live</span>
                    </Link>
                    <Link to={`/odds?sport=${SPORTS.NFL.apiParam}`} className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-gray-200 hover:bg-gray-800">
                      <span className="flex items-center gap-2">
                        <span>{SPORTS.NFL.icon}</span>
                        {SPORTS.NFL.displayName}
                      </span>
                      <span className="text-xs text-gray-500">Upcoming</span>
                    </Link>
                    <Link to={`/odds?sport=${SPORTS.BASKETBALL.apiParam}`} className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-gray-200 hover:bg-gray-800">
                      <span className="flex items-center gap-2">
                        <span>{SPORTS.BASKETBALL.icon}</span>
                        {SPORTS.BASKETBALL.displayName}
                      </span>
                      <span className="text-xs text-gray-500">Trending</span>
                    </Link>
                  </div>
                </div>
              </div>

              <Link
                to="/profile"
                className="text-gray-300 hover:text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors inline-flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Profile
              </Link>
            </div>

            {/* User Menu */}
            <div className="flex items-center space-x-3">
              {/* Role Switcher (Admin Only) */}
              <RoleSwitcher />
              
              {/* Balance Display */}
              <div className="hidden sm:flex items-center bg-gray-800 rounded-lg px-4 py-2 border border-gray-700">
                <span className="text-gray-400 text-sm mr-2">Balance:</span>
                <span className="text-green-400 font-bold text-lg">
                  ${user?.balance?.toFixed(2) || '0.00'}
                </span>
              </div>

              {/* Wallet Buttons */}
              <button
                onClick={() => openWallet('deposit')}
                className="hidden sm:flex items-center bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors shadow-lg shadow-green-500/30"
              >
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                  />
                </svg>
                Deposit
              </button>

              {/* Mobile Balance (visible on small screens) */}
              <button
                onClick={() => openWallet('deposit')}
                className="sm:hidden bg-gray-800 rounded-lg px-3 py-2 border border-gray-700"
              >
                <span className="text-green-400 font-bold text-sm">
                  ${user?.balance?.toFixed(2) || '0.00'}
                </span>
              </button>

              {/* Logout Button */}
              <button
                onClick={handleLogout}
                className="hidden md:flex items-center bg-red-500/20 hover:bg-red-500/30 text-red-400 px-4 py-2 rounded-lg font-semibold text-sm transition-colors border border-red-500/50"
              >
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
                Logout
              </button>

              {/* Mobile Menu Button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
                aria-expanded={isMobileMenuOpen}
                className="md:hidden text-gray-300 hover:text-white p-2"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  {isMobileMenuOpen ? (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  ) : (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 6h16M4 12h16M4 18h16"
                    />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-gray-800 bg-gray-900">
            <div className="px-2 pt-2 pb-3 space-y-1">
              <button
                onClick={() => handleNavigation('/dashboard')}
                className="w-full text-left text-gray-300 hover:text-white hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                Dashboard
              </button>
              <button
                onClick={() => handleNavigation('/odds')}
                className="w-full text-left text-gray-300 hover:text-white hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                Odds
              </button>
              <button
                onClick={() => handleNavigation('/sports')}
                className="w-full text-left text-gray-300 hover:text-white hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                Sports
              </button>
              <button
                onClick={() => handleNavigation('/predictions')}
                className="w-full text-left text-gray-300 hover:text-white hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                Predictions
              </button>
              <button
                onClick={() => handleNavigation('/bets')}
                className="w-full text-left text-gray-300 hover:text-white hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                My Bets
              </button>
              <button
                onClick={() => handleNavigation('/chat')}
                className="w-full text-left text-gray-300 hover:text-white hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                🤖 AI Chat
              </button>
              <button
                onClick={() => handleNavigation('/profile')}
                className="w-full text-left text-gray-300 hover:text-white hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                👤 Profile
              </button>
              <button
                onClick={() => openWallet('deposit')}
                className="w-full text-left text-green-400 hover:text-green-300 hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                💰 Deposit
              </button>
              <button
                onClick={() => openWallet('withdraw')}
                className="w-full text-left text-blue-400 hover:text-blue-300 hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                💸 Withdraw
              </button>
              <button
                onClick={handleLogout}
                className="w-full text-left text-red-400 hover:text-red-300 hover:bg-gray-800 block px-3 py-2 rounded-lg text-base font-medium transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* Wallet Modal */}
      <WalletModal
        isOpen={isWalletOpen}
        onClose={() => setIsWalletOpen(false)}
        initialTab={walletTab}
        currentBalance={user?.balance || 0}
      />
    </>
  );
});

Navbar.displayName = 'Navbar';

export default Navbar;
