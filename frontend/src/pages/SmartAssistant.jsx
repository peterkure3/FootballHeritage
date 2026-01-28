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
  const confidenceColors = {
    High: 'bg-green-500/20 text-green-400 border-green-500/40',
    Medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
    Low: 'bg-gray-500/20 text-gray-400 border-gray-500/40',
  };

  return (
    <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700 hover:border-green-500/30 transition">
      <div className="flex justify-between items-start mb-2">
        <div>
          <p className="text-xs text-gray-500">{bet.competition || 'Football'}</p>
          <p className="text-sm font-semibold text-white">{bet.home_team} vs {bet.away_team}</p>
          <p className="text-xs text-gray-400">{formatDate(bet.match_date)}</p>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${confidenceColors[bet.confidence]}`}>
          {bet.confidence}
        </span>
      </div>
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-700">
        <div>
          <p className="text-xs text-gray-500">Bet On</p>
          <p className="text-sm font-bold text-green-400">{bet.selection}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Edge</p>
          <p className="text-lg font-bold text-green-400">+{bet.edge_pct}%</p>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2 text-center">
        <div className="bg-gray-900/50 rounded p-1">
          <p className="text-xs text-gray-500">Odds</p>
          <p className="text-sm font-semibold text-white">{bet.decimal_odds}</p>
        </div>
        <div className="bg-gray-900/50 rounded p-1">
          <p className="text-xs text-gray-500">Stake</p>
          <p className="text-sm font-semibold text-white">${bet.recommended_stake}</p>
        </div>
        <div className="bg-gray-900/50 rounded p-1">
          <p className="text-xs text-gray-500">EV</p>
          <p className="text-sm font-semibold text-green-400">${bet.expected_value}</p>
        </div>
      </div>
    </div>
  );
};

const PredictionCardComponent = ({ prediction }) => {
  const maxProb = Math.max(prediction.home_prob, prediction.draw_prob, prediction.away_prob);
  
  return (
    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
      <div className="text-center mb-3">
        <p className="text-lg font-bold text-white">
          {prediction.home_team} vs {prediction.away_team}
        </p>
        <p className="text-sm text-gray-400">Confidence: {prediction.confidence}</p>
      </div>
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400 w-20">{prediction.home_team.split(' ')[0]}</span>
          <div className="flex-1 bg-gray-700 rounded-full h-4 overflow-hidden">
            <div 
              className={`h-full rounded-full ${prediction.home_prob === maxProb ? 'bg-green-500' : 'bg-gray-600'}`}
              style={{ width: `${prediction.home_prob * 100}%` }}
            />
          </div>
          <span className="text-sm font-semibold text-white w-12 text-right">
            {(prediction.home_prob * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400 w-20">Draw</span>
          <div className="flex-1 bg-gray-700 rounded-full h-4 overflow-hidden">
            <div 
              className={`h-full rounded-full ${prediction.draw_prob === maxProb ? 'bg-green-500' : 'bg-gray-600'}`}
              style={{ width: `${prediction.draw_prob * 100}%` }}
            />
          </div>
          <span className="text-sm font-semibold text-white w-12 text-right">
            {(prediction.draw_prob * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400 w-20">{prediction.away_team.split(' ')[0]}</span>
          <div className="flex-1 bg-gray-700 rounded-full h-4 overflow-hidden">
            <div 
              className={`h-full rounded-full ${prediction.away_prob === maxProb ? 'bg-green-500' : 'bg-gray-600'}`}
              style={{ width: `${prediction.away_prob * 100}%` }}
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
  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700 flex items-center justify-between">
    <div>
      <p className="text-sm font-semibold text-white">{match.home_team} vs {match.away_team}</p>
      <p className="text-xs text-gray-500">{match.competition || 'Football'}</p>
    </div>
    <div className="text-right">
      <p className="text-sm text-gray-400">{formatDate(match.match_date)}</p>
      <p className="text-xs text-gray-500">{match.status || 'Scheduled'}</p>
    </div>
  </div>
);

const SuggestionButton = ({ text, onClick }) => (
  <button
    onClick={() => onClick(text)}
    className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-full border border-gray-700 transition"
  >
    <ChevronRight className="w-3 h-3" />
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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="mb-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Bot className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Smart Betting Assistant</h1>
              <p className="text-sm text-gray-400">AI-powered picks, predictions & analysis</p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        {messages.length <= 1 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {quickActions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(action.query)}
                className="flex flex-col items-center gap-2 p-4 bg-gray-800/60 hover:bg-gray-800 border border-gray-700 hover:border-green-500/30 rounded-xl transition"
              >
                <action.icon className="w-6 h-6 text-green-400" />
                <span className="text-sm text-gray-300">{action.label}</span>
              </button>
            ))}
          </div>
        )}

        {/* Chat Container */}
        <div className="bg-gray-800/40 rounded-2xl border border-gray-700 flex flex-col h-[calc(100vh-280px)] min-h-[400px]">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div key={message.id}>
                <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`flex gap-2 max-w-[90%] ${message.type === 'user' ? 'flex-row-reverse' : ''}`}>
                    {/* Avatar */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.type === 'user' ? 'bg-green-500' : 'bg-gray-700'
                    }`}>
                      {message.type === 'user' ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Bot className="w-4 h-4 text-green-400" />
                      )}
                    </div>

                    {/* Message Content */}
                    <div className={`rounded-2xl p-4 ${
                      message.type === 'user'
                        ? 'bg-green-500 text-white'
                        : message.type === 'error'
                        ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                        : 'bg-gray-700/80 text-gray-100'
                    }`}>
                      <div className="whitespace-pre-wrap break-words text-sm">
                        {message.content}
                      </div>
                      <div className={`text-xs mt-2 ${
                        message.type === 'user' ? 'text-green-100' : 'text-gray-500'
                      }`}>
                        {formatTime(message.timestamp)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bet Cards */}
                {message.bets && message.bets.length > 0 && (
                  <div className="mt-3 ml-10 grid gap-3 md:grid-cols-2">
                    {message.bets.slice(0, 6).map((bet, idx) => (
                      <BetCardComponent key={idx} bet={bet} />
                    ))}
                  </div>
                )}

                {/* Prediction Cards */}
                {message.predictions && message.predictions.length > 0 && (
                  <div className="mt-3 ml-10 space-y-3">
                    {message.predictions.map((pred, idx) => (
                      <PredictionCardComponent key={idx} prediction={pred} />
                    ))}
                  </div>
                )}

                {/* Match Cards */}
                {message.matches && message.matches.length > 0 && (
                  <div className="mt-3 ml-10 space-y-2">
                    {message.matches.slice(0, 8).map((match, idx) => (
                      <MatchCardComponent key={idx} match={match} />
                    ))}
                  </div>
                )}

                {/* Suggestions */}
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

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex gap-2">
                  <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-green-400" />
                  </div>
                  <div className="bg-gray-700/80 rounded-2xl p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-gray-700">
            <form onSubmit={handleSubmit} className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about bets, predictions, or teams..."
                className="flex-1 bg-gray-700/50 text-white px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500 placeholder-gray-500 border border-gray-600"
                disabled={isLoading}
                maxLength={500}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-5 py-3 rounded-xl font-semibold transition flex items-center gap-2"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-xs text-yellow-400">
            ⚠️ <strong>Disclaimer:</strong> AI predictions are for informational purposes only. 
            Always bet responsibly and within your limits.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SmartAssistant;
