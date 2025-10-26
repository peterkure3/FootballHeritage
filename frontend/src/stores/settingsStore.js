import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Settings Store
 * Manages application settings and preferences
 */

const useSettingsStore = create(
  persist(
    (set) => ({
      // Admin Assistant Settings
      chatbotEnabled: true,
      
      // Toggle chatbot visibility
      toggleChatbot: () => set((state) => ({ 
        chatbotEnabled: !state.chatbotEnabled 
      })),
      
      // Enable chatbot
      enableChatbot: () => set({ chatbotEnabled: true }),
      
      // Disable chatbot
      disableChatbot: () => set({ chatbotEnabled: false }),
    }),
    {
      name: 'football-heritage-settings',
    }
  )
);

export default useSettingsStore;
