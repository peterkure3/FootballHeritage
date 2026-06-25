import { memo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../stores/authStore';
import { useLogout } from '../hooks/useAuth';
import WalletModal from './WalletModal';
import RoleSwitcher from './RoleSwitcher';
import { SPORTS } from '../utils/constants';

const NavDropdown = ({ label, children }) => {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="text-gray-300 hover:text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-white/[0.04] transition-all inline-flex items-center gap-2"
      >
        {label}
        <svg
          className={`w-3.5 h-3.5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        className={`absolute left-0 mt-2 w-64 rounded-2xl shadow-2xl border transition-all duration-200 origin-top-left ${
          open ? 'opacity-100 visible scale-100' : 'opacity-0 invisible scale-95'
        }`}
        style={{
          background: '#0d0d14',
          borderColor: '#1f1f35',
          zIndex: 50,
        }}
      >
        <div className="p-3 space-y-1">{children}</div>
      </div>
    </div>
  );
};

const NavDropdownItem = ({ to, label, subtitle, accent, icon }) => (
  <Link
    to={to}
    className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all hover:bg-white/[0.04] ${
      accent ? '' : ''
    }`}
  >
    {icon && (
      <span className="text-lg shrink-0 w-7 text-center">{icon}</span>
    )}
    <div>
      <p className={`font-semibold leading-tight ${accent ? '' : 'text-gray-200'}`}
         style={accent ? { color: accent } : {}}>
        {label}
      </p>
      <p className="text-xs" style={{ color: '#64748b' }}>{subtitle}</p>
    </div>
  </Link>
);

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

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/odds', label: 'Odds' },
    { to: '/sports', label: 'Sports' },
    { to: '/bets', label: 'My Bets' },
  ];

  return (
    <>
      <nav
        className="sticky top-0 z-40 border-b"
        style={{
          background: 'rgba(13, 13, 20, 0.92)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          borderColor: '#1a1a2e',
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center">
              <Link
                to="/dashboard"
                className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
              >
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center shadow-lg"
                  style={{
                    background: 'linear-gradient(135deg, #10b981, #059669)',
                  }}
                >
                  <span className="text-white text-lg font-bold">🏈</span>
                </div>
                <span className="text-white text-lg font-bold hidden sm:block font-[Oswald] tracking-tight">
                  Football<span style={{ color: '#10b981' }}>Heritage</span>
                </span>
              </Link>

              {/* Desktop Nav Links */}
              <div className="hidden lg:flex items-center ml-8 space-x-1">
                {navLinks.map((link) => (
                  <Link
                    key={link.to}
                    to={link.to}
                    className="text-gray-400 hover:text-white px-3.5 py-2 rounded-lg text-sm font-medium hover:bg-white/[0.04] transition-all"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>

            {/* Desktop Right Side */}
            <div className="hidden md:flex items-center space-x-2">
              <NavDropdown label="Explore">
                <NavDropdownItem to="/odds" label="All Odds" subtitle="Live & upcoming" />
                <NavDropdownItem to="/sports" label="Sports Hub" subtitle="Leagues & markets" />
                <NavDropdownItem
                  to="/college"
                  label="College Sports"
                  subtitle="NCAAB & March Madness"
                  accent="#f97316"
                  icon="🏀"
                />
                <NavDropdownItem
                  to="/fpl-advisor"
                  label="FPL Advisor"
                  subtitle="Fantasy Premier League"
                  accent="#a855f7"
                  icon="⚽"
                />
              </NavDropdown>

              <NavDropdown label="AI Tools">
                <NavDropdownItem
                  to="/best-bets"
                  label="Best Value Bets"
                  subtitle="AI picks with Kelly sizing"
                  accent="#10b981"
                  icon="⚡"
                />
                <NavDropdownItem to="/predictions" label="Predictions" subtitle="Match insights" />
                <NavDropdownItem to="/intelligence/ev-bets" label="+EV Bets" subtitle="Positive expected value" />
                <NavDropdownItem to="/intelligence/arbitrage" label="Arbitrage" subtitle="Cross-book opportunities" />
                <NavDropdownItem to="/intelligence/devigged-odds" label="Devigged Odds" subtitle="Fair probabilities" />
                <NavDropdownItem
                  to="/assistant"
                  label="Smart Assistant"
                  subtitle="AI picks & analysis"
                  accent="#6366f1"
                  icon="🤖"
                />
                <NavDropdownItem to="/player-props" label="Player Props" subtitle="Player-based betting" />
                <NavDropdownItem to="/parlay-calculator" label="Parlay Builder" subtitle="Stack your slips" />
              </NavDropdown>

              <NavDropdown label="Quick Filters">
                {Object.values(SPORTS).filter(s => s.key !== 'NBA_CUP' && s.key !== 'TENNIS').map((sport) => (
                  <Link
                    key={sport.key}
                    to={`/odds?sport=${sport.apiParam}`}
                    className="flex items-center justify-between rounded-xl px-3 py-2.5 text-sm text-gray-200 hover:bg-white/[0.04] transition-all"
                  >
                    <span className="flex items-center gap-2.5">
                      <span>{sport.icon}</span>
                      {sport.displayName}
                    </span>
                    <span className="text-xs" style={{ color: '#64748b' }}>→</span>
                  </Link>
                ))}
              </NavDropdown>

              <RoleSwitcher />

              {/* Balance Pill */}
              <div
                className="flex items-center gap-2 rounded-lg px-3.5 py-1.5 border text-sm"
                style={{
                  background: 'rgba(16, 185, 129, 0.06)',
                  borderColor: 'rgba(16, 185, 129, 0.2)',
                }}
              >
                <span className="text-xs" style={{ color: '#64748b' }}>$</span>
                <span className="font-semibold" style={{ color: '#10b981' }}>
                  {user?.balance?.toFixed(2) || '0.00'}
                </span>
              </div>

              <button
                onClick={() => openWallet('deposit')}
                className="text-white px-4 py-2 rounded-lg font-semibold text-sm transition-all hover:opacity-90"
                style={{
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                }}
              >
                Deposit
              </button>

              <Link
                to="/profile"
                className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/[0.06] transition-all"
                title="Profile"
              >
                <svg className="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </Link>

              <button
                onClick={handleLogout}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                title="Logout"
              >
                <svg className="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>

            {/* Mobile: Balance + Menu */}
            <div className="flex md:hidden items-center gap-2">
              <button
                onClick={() => openWallet('deposit')}
                className="rounded-lg px-3 py-1.5 border text-sm font-semibold"
                style={{
                  color: '#10b981',
                  borderColor: 'rgba(16, 185, 129, 0.2)',
                }}
              >
                ${user?.balance?.toFixed(2) || '0.00'}
              </button>
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
                aria-expanded={isMobileMenuOpen}
                className="text-gray-300 hover:text-white p-2 rounded-lg hover:bg-white/[0.04] transition-all"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {isMobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div
            className="md:hidden border-t"
            style={{
              background: 'rgba(13, 13, 20, 0.98)',
              borderColor: '#1a1a2e',
              animation: 'fade-in 0.15s ease-out',
            }}
          >
            <div className="px-3 pt-3 pb-4 space-y-0.5 max-h-[70vh] overflow-y-auto">
              {[
                { label: 'Dashboard', path: '/dashboard' },
                { label: 'Odds', path: '/odds' },
                { label: 'Sports', path: '/sports' },
                { label: 'My Bets', path: '/bets' },
                { label: 'Best Value Bets ⚡', path: '/best-bets' },
                { label: 'Predictions', path: '/predictions' },
                { label: '+EV Bets', path: '/intelligence/ev-bets' },
                { label: 'Arbitrage', path: '/intelligence/arbitrage' },
                { label: 'Devigged Odds', path: '/intelligence/devigged-odds' },
                { label: 'Player Props', path: '/player-props' },
                { label: 'Parlay Builder', path: '/parlay-calculator' },
                { label: 'College Sports', path: '/college' },
                { label: 'March Madness', path: '/college/bracket' },
                { label: 'FPL Advisor', path: '/fpl-advisor' },
              ].map((item) => (
                <button
                  key={item.path}
                  onClick={() => handleNavigation(item.path)}
                  className="w-full text-left text-gray-300 hover:text-white hover:bg-white/[0.04] block px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
                >
                  {item.label}
                </button>
              ))}
              <div className="border-t my-2" style={{ borderColor: '#1a1a2e' }} />
              <button
                onClick={() => openWallet('deposit')}
                className="w-full text-left text-emerald-400 hover:text-emerald-300 hover:bg-white/[0.04] block px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
              >
                💰 Deposit
              </button>
              <button
                onClick={() => openWallet('withdraw')}
                className="w-full text-left text-blue-400 hover:text-blue-300 hover:bg-white/[0.04] block px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
              >
                💸 Withdraw
              </button>
              <div className="border-t my-2" style={{ borderColor: '#1a1a2e' }} />
              <button
                onClick={() => handleNavigation('/profile')}
                className="w-full text-left text-gray-300 hover:text-white hover:bg-white/[0.04] block px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
              >
                👤 Profile
              </button>
              <button
                onClick={handleLogout}
                className="w-full text-left text-red-400 hover:text-red-300 hover:bg-red-500/10 block px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
              >
                🚪 Logout
              </button>
            </div>
          </div>
        )}
      </nav>

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
