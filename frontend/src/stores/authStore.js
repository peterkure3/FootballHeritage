import { create } from 'zustand';
import { tokenManager } from '../utils/api';

// Session timeout: 15 minutes in milliseconds
const SESSION_TIMEOUT = 15 * 60 * 1000;

const useAuthStore = create((set, get) => {
  let logoutTimer = null;

  // Reset the auto-logout timer
  const resetLogoutTimer = () => {
    if (logoutTimer) {
      clearTimeout(logoutTimer);
    }

    logoutTimer = setTimeout(() => {
      const { logout } = get();
      logout();
    }, SESSION_TIMEOUT);
  };

  // Initialize timer if user is already logged in
  if (tokenManager.getToken()) {
    resetLogoutTimer();
  }

  return {
    // State
    user: null,
    isAuthenticated: !!tokenManager.getToken(),
    isLoading: false,
    error: null,

    // Actions
    setUser: (user) => {
      set({ user, isAuthenticated: true, error: null });
      resetLogoutTimer();
    },

    setLoading: (isLoading) => {
      set({ isLoading });
    },

    setError: (error) => {
      set({ error });
    },

    clearError: () => {
      set({ error: null });
    },

    login: (token, user) => {
      console.log('AuthStore login - User data:', user);
      console.log('AuthStore login - is_admin:', user?.is_admin);
      console.log('AuthStore login - is_super_admin:', user?.is_super_admin);
      tokenManager.setToken(token);
      set({
        user,
        isAuthenticated: true,
        error: null,
      });
      resetLogoutTimer();
    },

    logout: () => {
      tokenManager.removeToken();
      if (logoutTimer) {
        clearTimeout(logoutTimer);
        logoutTimer = null;
      }
      set({
        user: null,
        isAuthenticated: false,
        error: null,
      });

      // Redirect to login
      window.location.href = '/login';
    },

    // Keep session alive (call this on user activity)
    keepAlive: () => {
      if (get().isAuthenticated) {
        resetLogoutTimer();
      }
    },

    // Update user balance
    updateBalance: (balance) => {
      const { user } = get();
      if (user) {
        set({
          user: {
            ...user,
            balance,
          },
        });
      }
    },

    // Add a bet to user's history
    addBet: (bet) => {
      const { user } = get();
      if (user) {
        set({
          user: {
            ...user,
            bets: [bet, ...(user.bets || [])],
          },
        });
      }
    },

    // Update entire user object
    refreshUser: (userData) => {
      set({ user: userData });
      resetLogoutTimer();
    },
  };
});

// Activity tracking - reset timer on user interaction
if (typeof window !== 'undefined') {
  const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];

  events.forEach((event) => {
    window.addEventListener(event, () => {
      const store = useAuthStore.getState();
      if (store.isAuthenticated) {
        store.keepAlive();
      }
    }, { passive: true });
  });
}

export default useAuthStore;
