import { useState, useRef, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import { tokenManager } from '../utils/api';
import Navbar from '../components/Navbar';

/**
 * Chat Page Component
 * 
 * AI-powered betting assistant using Genkit and Gemini 1.5 Flash
 * Features:
 * - Real-time chat interface
 * - Betting advice based on live odds
 * - Personalized recommendations
 * - Bet365-style green theme (#10B981)
 */

const Chat = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: "👋 Hi! I'm your AI betting assistant. Ask me about upcoming games, odds analysis, or betting strategies. For example: 'What's the best bet for the Chiefs game?' or 'Show me today's NFL odds.'",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const { user } = useAuthStore();

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  /**
   * Send message to chatbot API
   */
  const sendMessage = async (e) => {
    e.preventDefault();

    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: trimmedInput,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Get auth token
      const token = tokenManager.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      // Call chat API
      const response = await fetch('http://localhost:8080/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ prompt: trimmedInput }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to get response');
      }

      const data = await response.json();

      // Add bot response to chat
      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: data.response,
        confidence: data.confidence,
        data: data.data,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      toast.error(error.message || 'Failed to send message');

      // Add error message to chat
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: "Sorry, I'm having trouble connecting right now. Please try again in a moment.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Quick action buttons for common queries
   */
  const quickActions = [
    { label: "Today's NFL Games", query: "Show me today's NFL games and odds" },
    { label: 'Best Value Bets', query: 'What are the best value bets right now?' },
    { label: 'Chiefs Analysis', query: 'Analyze the Kansas City Chiefs next game' },
    { label: 'My Betting Stats', query: 'Show me my betting statistics and performance' },
  ];

  const handleQuickAction = (query) => {
    setInput(query);
    inputRef.current?.focus();
  };

  /**
   * Format timestamp for display
   */
  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">
            🤖 AI Betting Assistant
          </h1>
          <p className="text-gray-400">
            Get expert betting advice powered by AI. Ask about odds, strategies, or upcoming games.
          </p>
        </div>

        {/* Chat Container */}
        <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 flex flex-col h-[600px]">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-4 ${
                    message.type === 'user'
                      ? 'bg-green-500 text-white'
                      : message.type === 'error'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                      : 'bg-gray-700 text-gray-100'
                  }`}
                >
                  {/* Message Content */}
                  <div className="whitespace-pre-wrap break-words">
                    {message.content}
                  </div>

                  {/* Confidence Score (for bot messages) */}
                  {message.type === 'bot' && message.confidence && (
                    <div className="mt-2 pt-2 border-t border-gray-600">
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <span>Confidence:</span>
                        <div className="flex-1 bg-gray-600 rounded-full h-2 max-w-[100px]">
                          <div
                            className="bg-green-500 h-2 rounded-full transition-all"
                            style={{ width: `${message.confidence * 100}%` }}
                          />
                        </div>
                        <span>{(message.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  )}

                  {/* Timestamp */}
                  <div
                    className={`text-xs mt-2 ${
                      message.type === 'user' ? 'text-green-100' : 'text-gray-500'
                    }`}
                  >
                    {formatTime(message.timestamp)}
                  </div>
                </div>
              </div>
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce delay-100" />
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce delay-200" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          {messages.length === 1 && (
            <div className="px-6 py-4 border-t border-gray-700">
              <p className="text-sm text-gray-400 mb-3">Quick actions:</p>
              <div className="grid grid-cols-2 gap-2">
                {quickActions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuickAction(action.query)}
                    className="text-left px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition-colors"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="p-6 border-t border-gray-700">
            <form onSubmit={sendMessage} className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about odds, games, or betting strategies..."
                className="flex-1 bg-gray-700 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 placeholder-gray-400"
                disabled={isLoading}
                maxLength={500}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                      />
                    </svg>
                    Send
                  </>
                )}
              </button>
            </form>
            <p className="text-xs text-gray-500 mt-2">
              {input.length}/500 characters
            </p>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-sm text-yellow-400">
            ⚠️ <strong>Responsible Gambling:</strong> AI predictions are for informational purposes only. 
            Always bet responsibly and within your limits. Past performance does not guarantee future results.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Chat;
