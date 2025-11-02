import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Settings Store
 * Manages application settings and preferences
 * 
 * Features:
 * - Dark mode toggle with system preference detection
 * - Chatbot visibility control
 * - Persistent storage across sessions
 * - Accessibility preferences
 */

const useSettingsStore = create(
  persist(
    (set, get) => ({
      // ============================================
      // DARK MODE SETTINGS
      // ============================================
      
      /**
       * Dark mode state
       * - 'light': Light theme
       * - 'dark': Dark theme (default)
       * - 'system': Follow system preference
       */
      theme: 'dark',
      
      /**
       * Toggle between light and dark themes
       * Cycles through: dark → light → system → dark
       */
      toggleTheme: () => set((state) => {
        const themeOrder = ['dark', 'light', 'system'];
        const currentIndex = themeOrder.indexOf(state.theme);
        const nextTheme = themeOrder[(currentIndex + 1) % themeOrder.length];
        
        // Apply theme to document
        applyTheme(nextTheme);
        
        return { theme: nextTheme };
      }),
      
      /**
       * Set specific theme
       * @param {string} theme - 'light', 'dark', or 'system'
       */
      setTheme: (theme) => set(() => {
        applyTheme(theme);
        return { theme };
      }),
      
      /**
       * Get the effective theme (resolves 'system' to actual theme)
       */
      getEffectiveTheme: () => {
        const { theme } = get();
        if (theme === 'system') {
          return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        return theme;
      },
      
      // ============================================
      // CHATBOT SETTINGS
      // ============================================
      
      /**
       * Admin Assistant chatbot visibility
       */
      chatbotEnabled: true,
      
      /**
       * Toggle chatbot visibility
       */
      toggleChatbot: () => set((state) => ({ 
        chatbotEnabled: !state.chatbotEnabled 
      })),
      
      /**
       * Enable chatbot
       */
      enableChatbot: () => set({ chatbotEnabled: true }),
      
      /**
       * Disable chatbot
       */
      disableChatbot: () => set({ chatbotEnabled: false }),
      
      // ============================================
      // ACCESSIBILITY SETTINGS
      // ============================================
      
      /**
       * Reduce motion for animations (respects prefers-reduced-motion)
       */
      reducedMotion: false,
      
      /**
       * Toggle reduced motion
       */
      toggleReducedMotion: () => set((state) => ({
        reducedMotion: !state.reducedMotion
      })),
      
      /**
       * High contrast mode for better visibility
       */
      highContrast: false,
      
      /**
       * Toggle high contrast mode
       */
      toggleHighContrast: () => set((state) => ({
        highContrast: !state.highContrast
      })),
      
      // ============================================
      // NOTIFICATION SETTINGS
      // ============================================
      
      /**
       * Enable/disable toast notifications
       */
      notificationsEnabled: true,
      
      /**
       * Toggle notifications
       */
      toggleNotifications: () => set((state) => ({
        notificationsEnabled: !state.notificationsEnabled
      })),
      
      /**
       * Sound effects for actions
       */
      soundEnabled: false,
      
      /**
       * Toggle sound effects
       */
      toggleSound: () => set((state) => ({
        soundEnabled: !state.soundEnabled
      })),
    }),
    {
      name: 'football-heritage-settings',
      version: 1,
      
      // Initialize theme on load
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyTheme(state.theme);
        }
      },
    }
  )
);

/**
 * Apply theme to document
 * Updates the HTML class and meta theme-color
 * 
 * @param {string} theme - 'light', 'dark', or 'system'
 */
function applyTheme(theme) {
  const root = document.documentElement;
  
  // Resolve 'system' to actual theme
  let effectiveTheme = theme;
  if (theme === 'system') {
    effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  
  // Apply theme class to HTML element
  if (effectiveTheme === 'dark') {
    root.classList.add('dark');
    root.classList.remove('light');
  } else {
    root.classList.add('light');
    root.classList.remove('dark');
  }
  
  // Update meta theme-color for mobile browsers
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute(
      'content',
      effectiveTheme === 'dark' ? '#1f2937' : '#ffffff'
    );
  }
  
  // Store in localStorage for SSR/initial load
  localStorage.setItem('theme', theme);
}

/**
 * Listen for system theme changes
 * Automatically updates theme when system preference changes
 */
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const store = useSettingsStore.getState();
    if (store.theme === 'system') {
      applyTheme('system');
    }
  });
}

export default useSettingsStore;
