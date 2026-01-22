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

  // Load user from localStorage if exists
  const loadStoredUser = () => {
    try {
      const storedUser = sessionStorage.getItem('betting_user_data');
      return storedUser ? JSON.parse(storedUser) : null;
    } catch {
      return null;
    }
  };

  return {
    // State
    user: loadStoredUser(),
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
      tokenManager.setToken(token);
      // Store user data in localStorage
      sessionStorage.setItem('betting_user_data', JSON.stringify(user));
      set({
        user,
        isAuthenticated: true,
        error: null,
      });
      resetLogoutTimer();
    },

    logout: () => {
      tokenManager.removeToken();
      // Remove user data from localStorage
      sessionStorage.removeItem('betting_user_data');
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
