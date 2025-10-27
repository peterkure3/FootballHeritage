import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import useAuthStore from "../stores/authStore";
import {
  Sparkles,
  Zap,
  TrendingUp,
  Users,
  Send,
  Loader2,
  BarChart3,
  DollarSign,
  Trophy,
} from "lucide-react";

/**
 * Admin SportsGPT Page
 * AI-powered sports betting insights and analytics
 */

const AdminSportsGPT = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "ai",
      content:
        "👋 Hello! I'm SportsGPT, your AI betting analyst. I can help you with:\n\n• Match predictions & analysis\n• Betting strategy recommendations\n• Odds value identification\n• Historical performance data\n• Risk assessment\n\nWhat would you like to analyze today?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!user?.is_admin && !user?.is_super_admin) {
      toast.error("Access denied");
      navigate("/");
    }
  }, [user, navigate]);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle send message
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: messages.length + 1,
      type: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const userQuery = input;
    setInput("");
    setIsLoading(true);

    // Mock response (commented out)
    // setTimeout(() => {
    //   const aiResponse = {
    //     id: messages.length + 2,
    //     type: 'ai',
    //     content: generateMockResponse(input),
    //     timestamp: new Date()
    //   };
    //   setMessages(prev => [...prev, aiResponse]);
    //   setIsLoading(false);
    // }, 1500);

    // Actual Genkit API call
    try {
      // Get JWT token from auth store
      const token = useAuthStore.getState().token;
      if (!token) {
        toast.error("Please log in to use SportsGPT");
        return;
      }

      const response = await fetch("http://localhost:3000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          prompt: userQuery,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      const aiResponse = {
        id: messages.length + 2,
        type: "ai",
        content: data.response || "Sorry, I couldn't generate a response.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      console.error("Genkit API error:", error);
      toast.error("Failed to get AI response. Please try again.");

      const errorResponse = {
        id: messages.length + 2,
        type: "ai",
        content:
          "⚠️ Sorry, I'm having trouble connecting to the AI service. Please check that the Genkit server is running on port 3000.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  // Mock response generator (replace with Genkit API)
  const generateMockResponse = (query) => {
    const lowerQuery = query.toLowerCase();

    if (lowerQuery.includes("predict") || lowerQuery.includes("match")) {
      return "📊 Based on historical data and current form:\n\n**Match Analysis:**\n• Home team win probability: 58%\n• Draw probability: 24%\n• Away team win probability: 18%\n\n**Recommended Bet:** Home team to win @ 1.85 odds\n**Confidence Level:** High (78%)\n**Suggested Stake:** 3-4% of bankroll";
    }

    if (lowerQuery.includes("strategy") || lowerQuery.includes("betting")) {
      return "💡 **Betting Strategy Recommendation:**\n\n1. **Value Betting:** Focus on odds above 2.0 with 60%+ win probability\n2. **Bankroll Management:** Never stake more than 5% on a single bet\n3. **Diversification:** Spread bets across multiple matches\n4. **Track Performance:** Monitor ROI and adjust strategy monthly\n\nWould you like me to analyze specific matches?";
    }

    if (lowerQuery.includes("odds") || lowerQuery.includes("value")) {
      return "🎯 **Value Bet Opportunities:**\n\n1. **Liverpool vs Arsenal** - Over 2.5 goals @ 1.95 (Expected: 2.10)\n2. **Man City -1** @ 1.75 (Expected: 1.85)\n3. **Chelsea Draw No Bet** @ 1.65 (Expected: 1.72)\n\nAll bets show 8-12% value based on my models.";
    }

    return "I can help you with match predictions, betting strategies, odds analysis, and risk assessment. What specific information would you like?";
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Quick action prompts
  const quickPrompts = [
    {
      icon: <Trophy className="w-4 h-4" />,
      label: "Predict Today's Matches",
      query: "Predict outcomes for today's top matches",
    },
    {
      icon: <BarChart3 className="w-4 h-4" />,
      label: "Value Bets",
      query: "Show me the best value bets available",
    },
    {
      icon: <DollarSign className="w-4 h-4" />,
      label: "Betting Strategy",
      query: "Recommend a betting strategy for this week",
    },
    {
      icon: <Zap className="w-4 h-4" />,
      label: "Live Analysis",
      query: "Analyze current live matches",
    },
  ];

  return (
    <div>
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center space-x-3 mb-2">
            <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-blue-500 rounded-xl flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">SportsGPT</h1>
              <p className="text-gray-400 text-sm">
                AI-Powered Sports Analytics & Insights
              </p>
            </div>
          </div>
        </div>

        {/* Quick Prompts */}
        {messages.length <= 1 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            {quickPrompts.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setInput(prompt.query);
                  setTimeout(() => handleSend(), 100);
                }}
                className="flex items-center space-x-3 p-4 bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-green-500 rounded-xl transition-all text-left"
              >
                <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  {prompt.icon}
                </div>
                <span className="text-sm font-medium text-white">
                  {prompt.label}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Chat Interface */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 flex flex-col h-[calc(100vh-280px)]">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.type === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-5 py-4 ${
                    message.type === "user"
                      ? "bg-green-500 text-white"
                      : "bg-gray-700 text-gray-100"
                  }`}
                >
                  <p className="text-sm whitespace-pre-line leading-relaxed">
                    {message.content}
                  </p>
                  <span className="text-xs opacity-70 mt-2 block">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-700 rounded-2xl px-5 py-4">
                  <Loader2 className="w-5 h-5 text-green-400 animate-spin" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-700">
            <div className="flex items-center space-x-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about predictions, strategies, odds analysis..."
                className="flex-1 h-12 px-4 bg-gray-700 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 text-sm"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="h-12 w-12 bg-green-500 hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-xl transition-colors flex-shrink-0 flex items-center justify-center"
                aria-label="Send message"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Press Enter to send • Powered by Genkit AI
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminSportsGPT;
