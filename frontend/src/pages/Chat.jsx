import { useState, useRef, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import { tokenManager } from '../utils/api';
import Navbar from '../components/Navbar';

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (e) => {
    e.preventDefault();

    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;

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
      const token = tokenManager.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch('http://localhost:3000/chat', {
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

  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        <header style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <p className="text-sm uppercase tracking-wide font-semibold mb-2" style={{ color: '#10b981' }}>AI Assistant</p>
          <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight mb-2">AI Betting Assistant</h1>
          <p className="text-sm max-w-3xl" style={{ color: '#64748b' }}>
            Get expert betting advice powered by AI. Ask about odds, strategies, or upcoming games.
          </p>
        </header>

        <div className="card-glow rounded-xl border flex flex-col h-[600px]" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.4s ease-out 0.06s both' }}>
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-xl p-4 ${
                    message.type === 'user'
                      ? 'text-white'
                      : message.type === 'error'
                      ? 'border'
                      : ''
                  }`}
                  style={{
                    background: message.type === 'user'
                      ? 'linear-gradient(135deg, #10b981, #059669)'
                      : message.type === 'error'
                        ? 'rgba(239, 68, 68, 0.08)'
                        : 'var(--color-card)',
                    borderColor: message.type === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'var(--color-card-border)',
                    color: message.type === 'error' ? '#fca5a5' : message.type === 'user' ? 'white' : '#e2e8f0',
                  }}
                >
                  <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                    {message.content}
                  </div>

                  {message.type === 'bot' && message.confidence && (
                    <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--color-card-border)' }}>
                      <div className="flex items-center gap-2 text-xs" style={{ color: '#64748b' }}>
                        <span>Confidence:</span>
                        <div className="flex-1 rounded-full h-2 max-w-[100px]" style={{ background: '#1a1a2e' }}>
                          <div
                            className="h-2 rounded-full transition-all"
                            style={{ width: `${message.confidence * 100}%`, background: 'linear-gradient(90deg, #10b981, #059669)' }}
                          />
                        </div>
                        <span style={{ color: '#34d399' }}>{(message.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  )}

                  <div
                    className={`text-xs mt-2`}
                    style={{ color: message.type === 'user' ? 'rgba(255,255,255,0.6)' : '#475569' }}
                  >
                    {formatTime(message.timestamp)}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="card-glow rounded-xl p-4 border" style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#10b981' }} />
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#10b981', animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#10b981', animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {messages.length === 1 && (
            <div className="px-6 py-4" style={{ borderTop: '1px solid var(--color-card-border)' }}>
              <p className="text-sm mb-3" style={{ color: '#64748b' }}>Quick actions:</p>
              <div className="grid grid-cols-2 gap-2">
                {quickActions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuickAction(action.query)}
                    className="text-left px-4 py-2 rounded-lg text-sm transition-all card-glow"
                    style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', color: '#94a3b8' }}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="p-6" style={{ borderTop: '1px solid var(--color-card-border)' }}>
            <form onSubmit={sendMessage} className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about odds, games, or betting strategies..."
                className="flex-1 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all placeholder:text-gray-500"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                disabled={isLoading}
                maxLength={500}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="text-white px-6 py-3 rounded-xl font-semibold transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    Send
                  </>
                )}
              </button>
            </form>
            <p className="text-xs mt-2" style={{ color: '#475569' }}>
              {input.length}/500 characters
            </p>
          </div>
        </div>

        <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'rgba(234, 179, 8, 0.2)', animation: 'slide-up 0.4s ease-out 0.12s both' }}>
          <p className="text-sm" style={{ color: '#eab308' }}>
            <strong>Responsible Gambling:</strong> AI predictions are for informational purposes only. Always bet responsibly and within your limits. Past performance does not guarantee future results.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Chat;
