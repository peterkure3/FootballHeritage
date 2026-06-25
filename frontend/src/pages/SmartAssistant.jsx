import { useState, useRef, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';
import { 
  Send, 
  Bot, 
  User, 
  TrendingUp, 
  Calendar, 
  Target,
  Zap,
  ChevronRight,
  DollarSign,
  Percent,
  Trophy
} from 'lucide-react';

const PIPELINE_API_URL = import.meta.env.VITE_PIPELINE_API_URL || "http://localhost:5555/api/v1";

const formatDate = (dateStr) => {
  if (!dateStr) return 'TBD';
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
};

const formatTime = (date) => {
  return new Date(date).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

const BetCardComponent = ({ bet }) => {
  const confidenceBadgeStyle = {
    High: { borderColor: 'rgba(16, 185, 129, 0.4)', color: '#34d399', background: 'rgba(16, 185, 129, 0.1)' },
    Medium: { borderColor: 'rgba(234, 179, 8, 0.4)', color: '#facc15', background: 'rgba(234, 179, 8, 0.1)' },
    Low: { borderColor: 'rgba(148, 163, 184, 0.4)', color: '#94a3b8', background: 'rgba(148, 163, 184, 0.1)' },
  };

  return (
    <div className="card-glow rounded-xl p-4 border transition-all hover:opacity-90"
      style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <p className="text-xs" style={{ color: '#64748b' }}>{bet.competition || 'Football'}</p>
          <p className="text-sm font-semibold text-white">{bet.home_team} vs {bet.away_team}</p>
          <p className="text-xs" style={{ color: '#94a3b8' }}>{formatDate(bet.match_date)}</p>
        </div>
        <span className="px-2 py-0.5 rounded text-xs font-semibold border"
          style={confidenceBadgeStyle[bet.confidence]}
        >
          {bet.confidence}
        </span>
      </div>
      <div className="flex items-center justify-between mt-2 pt-2 border-t"
        style={{ borderColor: 'var(--color-card-border)' }}
      >
        <div>
          <p className="text-xs" style={{ color: '#64748b' }}>Bet On</p>
          <p className="text-sm font-bold" style={{ color: '#34d399' }}>{bet.selection}</p>
        </div>
        <div className="text-right">
          <p className="text-xs" style={{ color: '#64748b' }}>Edge</p>
          <p className="text-lg font-bold" style={{ color: '#34d399' }}>+{bet.edge_pct}%</p>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2 text-center">
        <div className="rounded p-1" style={{ background: 'rgba(0, 0, 0, 0.2)' }}>
          <p className="text-xs" style={{ color: '#64748b' }}>Odds</p>
          <p className="text-sm font-semibold text-white">{bet.decimal_odds}</p>
        </div>
        <div className="rounded p-1" style={{ background: 'rgba(0, 0, 0, 0.2)' }}>
          <p className="text-xs" style={{ color: '#64748b' }}>Stake</p>
          <p className="text-sm font-semibold text-white">${bet.recommended_stake}</p>
        </div>
        <div className="rounded p-1" style={{ background: 'rgba(0, 0, 0, 0.2)' }}>
          <p className="text-xs" style={{ color: '#64748b' }}>EV</p>
          <p className="text-sm font-semibold" style={{ color: '#34d399' }}>${bet.expected_value}</p>
        </div>
      </div>
    </div>
  );
};

const PredictionCardComponent = ({ prediction }) => {
  const maxProb = Math.max(prediction.home_prob, prediction.draw_prob, prediction.away_prob);
  
  return (
    <div className="card-glow rounded-xl p-4 border"
      style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
    >
      <div className="text-center mb-3">
        <p className="text-lg font-bold text-white">
          {prediction.home_team} vs {prediction.away_team}
        </p>
        <p className="text-sm" style={{ color: '#94a3b8' }}>Confidence: {prediction.confidence}</p>
      </div>
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-sm w-20" style={{ color: '#94a3b8' }}>{prediction.home_team.split(' ')[0]}</span>
          <div className="flex-1 rounded-full h-4 overflow-hidden" style={{ background: 'rgba(148, 163, 184, 0.15)' }}>
            <div className="h-full rounded-full"
              style={{
                width: `${prediction.home_prob * 100}%`,
                background: prediction.home_prob === maxProb ? '#10b981' : 'rgba(71, 85, 105, 0.5)'
              }}
            />
          </div>
          <span className="text-sm font-semibold text-white w-12 text-right">
            {(prediction.home_prob * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm w-20" style={{ color: '#94a3b8' }}>Draw</span>
          <div className="flex-1 rounded-full h-4 overflow-hidden" style={{ background: 'rgba(148, 163, 184, 0.15)' }}>
            <div className="h-full rounded-full"
              style={{
                width: `${prediction.draw_prob * 100}%`,
                background: prediction.draw_prob === maxProb ? '#10b981' : 'rgba(71, 85, 105, 0.5)'
              }}
            />
          </div>
          <span className="text-sm font-semibold text-white w-12 text-right">
            {(prediction.draw_prob * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm w-20" style={{ color: '#94a3b8' }}>{prediction.away_team.split(' ')[0]}</span>
          <div className="flex-1 rounded-full h-4 overflow-hidden" style={{ background: 'rgba(148, 163, 184, 0.15)' }}>
            <div className="h-full rounded-full"
              style={{
                width: `${prediction.away_prob * 100}%`,
                background: prediction.away_prob === maxProb ? '#10b981' : 'rgba(71, 85, 105, 0.5)'
              }}
            />
          </div>
          <span className="text-sm font-semibold text-white w-12 text-right">
            {(prediction.away_prob * 100).toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
};

const MatchCardComponent = ({ match }) => (
  <div className="card-glow rounded-xl p-4 border flex items-center justify-between"
    style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
  >
    <div>
      <p className="text-sm font-semibold text-white">{match.home_team} vs {match.away_team}</p>
      <p className="text-xs" style={{ color: '#64748b' }}>{match.competition || 'Football'}</p>
    </div>
    <div className="text-right">
      <p className="text-sm" style={{ color: '#94a3b8' }}>{formatDate(match.match_date)}</p>
      <p className="text-xs" style={{ color: '#64748b' }}>{match.status || 'Scheduled'}</p>
    </div>
  </div>
);

const SuggestionButton = ({ text, onClick }) => (
  <button
    onClick={() => onClick(text)}
    className="flex items-center gap-1 px-3 py-1.5 card-glow rounded-xl border text-sm transition-all hover:opacity-90"
    style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)', color: '#cbd5e1' }}
  >
    <ChevronRight className="w-3 h-3" style={{ color: '#10b981' }} />
    {text}
  </button>
);

const SmartAssistant = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: "👋 Hey! I'm your AI betting assistant. I can help you find value bets, predict matches, and analyze teams. What would you like to know?",
      timestamp: new Date(),
      suggestions: [
        "Show me the best value bets",
        "What matches are on today?",
        "Predict Arsenal vs Liverpool",
        "How is Manchester City doing?",
      ],
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (messageText) => {
    const trimmedInput = (messageText || input).trim();
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
      const response = await fetch(`${PIPELINE_API_URL}/smart-assistant`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: trimmedInput }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: data.message,
        intent: data.intent,
        bets: data.bets,
        predictions: data.predictions,
        matches: data.matches,
        suggestions: data.suggestions || [],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);

    } catch (error) {
      console.error('Assistant error:', error);
      toast.error('Failed to get response');

      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: "Sorry, I'm having trouble connecting right now. Please make sure the pipeline API is running.",
        timestamp: new Date(),
        suggestions: ["Show me the best bets", "What matches are on today?"],
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  const quickActions = [
    { icon: Zap, label: "Best Value Bets", query: "Show me the best value bets" },
    { icon: Calendar, label: "Today's Matches", query: "What matches are on today?" },
    { icon: Target, label: "Predict Match", query: "Predict Arsenal vs Liverpool" },
    { icon: TrendingUp, label: "Team Analysis", query: "How is Manchester City doing?" },
  ];

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 py-6">
        <header style={{ animation: 'slide-up 0.4s ease-out both' }} className="mb-6">
          <p className="text-sm uppercase tracking-wide font-semibold mb-2" style={{ color: '#10b981' }}>AI Assistant</p>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg" style={{ background: 'rgba(16, 185, 129, 0.2)' }}>
              <Bot className="w-6 h-6" style={{ color: '#10b981' }} />
            </div>
            <div>
              <h1 className="text-2xl font-[Oswald] tracking-tight text-white">Smart Betting Assistant</h1>
              <p className="text-sm" style={{ color: '#64748b' }}>AI-powered picks, predictions & analysis</p>
            </div>
          </div>
        </header>

        {messages.length <= 1 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 stagger-children"
            style={{ animation: 'slide-up 0.4s ease-out 0.06s both' }}
          >
            {quickActions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(action.query)}
                className="card-glow rounded-xl p-4 border flex flex-col items-center gap-2 transition-all hover:opacity-90"
                style={{
                  background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))',
                  borderColor: 'var(--color-card-border)',
                }}
              >
                <action.icon className="w-6 h-6" style={{ color: '#10b981' }} />
                <span className="text-sm" style={{ color: '#cbd5e1' }}>{action.label}</span>
              </button>
            ))}
          </div>
        )}

        <div className="card-glow rounded-xl p-6 border flex flex-col h-[calc(100vh-280px)] min-h-[400px]"
          style={{
            background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))',
            borderColor: 'var(--color-card-border)',
            animation: 'slide-up 0.4s ease-out 0.12s both'
          }}
        >
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div key={message.id}>
                <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`flex gap-2 max-w-[90%] ${message.type === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.type === 'user' ? 'bg-green-500' : ''
                    }`}
                      style={message.type === 'user' ? {} : { background: 'var(--color-card)' }}
                    >
                      {message.type === 'user' ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Bot className="w-4 h-4" style={{ color: '#10b981' }} />
                      )}
                    </div>

                    <div
                      className={`rounded-2xl p-4 ${
                        message.type === 'user'
                          ? 'bg-green-500 text-white'
                          : message.type === 'error'
                          ? 'border'
                          : ''
                      }`}
                      style={
                        message.type === 'user'
                          ? {}
                          : message.type === 'error'
                          ? { background: 'rgba(239, 68, 68, 0.08)', color: '#fca5a5', borderColor: 'rgba(239, 68, 68, 0.2)' }
                          : { background: 'var(--color-card)', color: '#cbd5e1' }
                      }
                    >
                      <div className="whitespace-pre-wrap break-words text-sm">
                        {message.content}
                      </div>
                      <div className="text-xs mt-2"
                        style={{ color: message.type === 'user' ? '#86efac' : '#64748b' }}
                      >
                        {formatTime(message.timestamp)}
                      </div>
                    </div>
                  </div>
                </div>

                {message.bets && message.bets.length > 0 && (
                  <div className="mt-3 ml-10 grid gap-3 md:grid-cols-2">
                    {message.bets.slice(0, 6).map((bet, idx) => (
                      <BetCardComponent key={idx} bet={bet} />
                    ))}
                  </div>
                )}

                {message.predictions && message.predictions.length > 0 && (
                  <div className="mt-3 ml-10 space-y-3">
                    {message.predictions.map((pred, idx) => (
                      <PredictionCardComponent key={idx} prediction={pred} />
                    ))}
                  </div>
                )}

                {message.matches && message.matches.length > 0 && (
                  <div className="mt-3 ml-10 space-y-2">
                    {message.matches.slice(0, 8).map((match, idx) => (
                      <MatchCardComponent key={idx} match={match} />
                    ))}
                  </div>
                )}

                {message.suggestions && message.suggestions.length > 0 && message.type !== 'user' && (
                  <div className="mt-3 ml-10 flex flex-wrap gap-2">
                    {message.suggestions.map((suggestion, idx) => (
                      <SuggestionButton
                        key={idx}
                        text={suggestion}
                        onClick={handleSuggestionClick}
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="flex gap-2">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center"
                    style={{ background: 'var(--color-card)' }}
                  >
                    <Bot className="w-4 h-4" style={{ color: '#10b981' }} />
                  </div>
                  <div className="rounded-2xl p-4" style={{ background: 'var(--color-card)' }}>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#10b981', animationDelay: '0ms' }} />
                      <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#10b981', animationDelay: '150ms' }} />
                      <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#10b981', animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 border-t" style={{ borderColor: 'var(--color-card-border)' }}>
            <form onSubmit={handleSubmit} className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about bets, predictions, or teams..."
                className="flex-1 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                disabled={isLoading}
                maxLength={500}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="text-white font-semibold rounded-lg py-3 px-4 transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>

        <div className="mt-4 p-3 card-glow rounded-xl border"
          style={{
            background: 'rgba(234, 179, 8, 0.08)',
            borderColor: 'rgba(234, 179, 8, 0.2)',
            animation: 'slide-up 0.4s ease-out 0.18s both'
          }}
        >
          <p className="text-xs" style={{ color: '#fbbf24' }}>
            ⚠️ <strong>Disclaimer:</strong> AI predictions are for informational purposes only. 
            Always bet responsibly and within your limits.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SmartAssistant;
