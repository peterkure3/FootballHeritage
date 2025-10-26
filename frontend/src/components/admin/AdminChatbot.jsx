import { useState, useRef, useEffect } from 'react';
import { 
  MessageSquare, 
  Send, 
  X, 
  Minimize2, 
  Maximize2,
  Sparkles,
  Loader2
} from 'lucide-react';
import useSettingsStore from '../../stores/settingsStore.js';
import './AdminChatbot.css';

/**
 * Admin AI Chatbot Component
 * Floating chatbot for admin assistance and insights
 */

const AdminChatbot = () => {
  const { chatbotEnabled } = useSettingsStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      content: "👋 Hi! I'm your admin assistant. I can help you with:\n\n• Platform analytics\n• User insights\n• Betting trends\n• Quick actions\n• Data queries\n\nWhat would you like to know?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && !isMinimized) {
      inputRef.current?.focus();
    }
  }, [isOpen, isMinimized]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Simulate AI response (replace with actual API call)
    setTimeout(() => {
      const aiResponse = generateAIResponse(userMessage.content);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'ai',
        content: aiResponse,
        timestamp: new Date()
      }]);
      setIsLoading(false);
    }, 1000);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Mock AI responses (replace with actual AI integration)
  const generateAIResponse = (query) => {
    const lowerQuery = query.toLowerCase();

    if (lowerQuery.includes('user') || lowerQuery.includes('how many')) {
      return "📊 **User Statistics:**\n\n• Total Users: 1,247\n• Active Today: 342 (27.4%)\n• New This Week: 89\n• Verified: 1,156 (92.7%)\n\nWould you like more detailed user analytics?";
    }

    if (lowerQuery.includes('revenue') || lowerQuery.includes('money')) {
      return "💰 **Revenue Overview:**\n\n• Total Revenue: $45,678.90\n• This Week: $8,234.50 (+26%)\n• Average Bet: $51.20\n• Top Earner: Premier League\n\nNeed a detailed revenue breakdown?";
    }

    if (lowerQuery.includes('bet') || lowerQuery.includes('betting')) {
      return "🎲 **Betting Insights:**\n\n• Total Bets: 8,934\n• Active Bets: 234\n• Win Rate: 47.3%\n• Most Popular: Soccer (68%)\n\nWant to see betting trends?";
    }

    if (lowerQuery.includes('alert') || lowerQuery.includes('fraud')) {
      return "⚠️ **Security Alerts:**\n\n• Fraud Alerts: 3 (requires attention)\n• Pending Withdrawals: 12\n• Suspicious Activity: 2 accounts flagged\n\nShall I show you the details?";
    }

    if (lowerQuery.includes('help') || lowerQuery.includes('what can you')) {
      return "🤖 **I can help you with:**\n\n1. **Analytics** - User stats, revenue, trends\n2. **Quick Actions** - Verify users, approve withdrawals\n3. **Insights** - Betting patterns, fraud detection\n4. **Reports** - Generate custom reports\n5. **Navigation** - Find specific data quickly\n\nJust ask me anything!";
    }

    // Default response
    return `I understand you're asking about "${query}". Let me help you with that.\n\nCould you be more specific? For example:\n• "Show me user statistics"\n• "What's the revenue this week?"\n• "Are there any fraud alerts?"\n• "Show betting trends"`;
  };

  // Quick action buttons
  const quickActions = [
    { label: 'User Stats', icon: '👥', query: 'Show me user statistics' },
    { label: 'Revenue', icon: '💰', query: 'What is the revenue?' },
    { label: 'Alerts', icon: '⚠️', query: 'Show me alerts' },
    { label: 'Help', icon: '❓', query: 'What can you help me with?' },
  ];

  const handleQuickAction = (query) => {
    setInput(query);
    setTimeout(() => handleSend(), 100);
  };

  // Don't render if chatbot is disabled in settings
  if (!chatbotEnabled) {
    return null;
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-br from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center group z-50"
        aria-label="Open AI Assistant"
      >
        <Sparkles className="w-6 h-6 group-hover:scale-110 transition-transform" />
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse"></span>
      </button>
    );
  }

  return (
    <div 
      className={`fixed bottom-6 right-6 bg-gray-800 border border-gray-700 shadow-2xl z-50 transition-all duration-300 ease-in-out flex flex-col ${
        isMinimized ? 'w-14 h-14 rounded-full scale-100 opacity-100 overflow-hidden' : 'w-96 h-[600px] rounded-2xl scale-100 opacity-100'
      }`}
      style={{
        transformOrigin: 'bottom right'
      }}
    >
      {/* Header - Always show when expanded */}
      {!isMinimized && (
        <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gradient-to-r from-green-500/10 to-blue-500/10 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">AI Assistant</h3>
              <p className="text-xs text-gray-400">Always here to help</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsMinimized(true)}
              className="p-1.5 hover:bg-gray-700 rounded-lg transition-colors"
              aria-label="Minimize"
            >
              <Minimize2 className="w-4 h-4 text-gray-400" />
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 hover:bg-gray-700 rounded-lg transition-colors"
              aria-label="Close"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>
      )}

      {/* Minimized button */}
      {isMinimized && (
        <button
          onClick={() => setIsMinimized(false)}
          className="w-full h-full flex items-center justify-center bg-gradient-to-br from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 transition-all"
          aria-label="Expand AI Assistant"
        >
          <Sparkles className="w-6 h-6 text-white" />
        </button>
      )}

      {!isMinimized && (
        <>
          {/* Messages */}
          <div 
            className="chatbot-messages flex-1 overflow-y-auto px-4 pt-12 pb-4 space-y-4 h-[420px]"
            style={{
              scrollbarWidth: 'thin',
              scrollbarColor: '#4B5563 #1F2937'
            }}
          >
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    message.type === 'user'
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-700 text-gray-100'
                  }`}
                >
                  <p className="text-sm whitespace-pre-line">{message.content}</p>
                  <span className="text-xs opacity-70 mt-1 block">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-700 rounded-2xl px-4 py-3 flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 text-green-400 animate-spin" />
                  <span className="text-sm text-gray-300">Thinking...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          {messages.length <= 1 && (
            <div className="px-4 pb-3 -mt-2">
              <p className="text-xs text-gray-400 mb-2">Quick actions:</p>
              <div className="grid grid-cols-2 gap-2">
                {quickActions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuickAction(action.query)}
                    className="flex items-center space-x-2 px-3 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                  >
                    <span className="text-base flex-shrink-0 leading-none">{action.icon}</span>
                    <span className="text-xs text-gray-300 font-medium leading-none">{action.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-gray-700">
            <div className="flex items-end space-x-2">
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask me anything..."
                  rows="1"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 resize-none text-sm"
                  style={{ maxHeight: '100px' }}
                />
              </div>
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="p-3 bg-green-500 hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-xl transition-colors"
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </>
      )}
    </div>
  );
};

export default AdminChatbot;
