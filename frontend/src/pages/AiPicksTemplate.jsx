import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { AlertTriangle, ArrowRight, ArrowUpRight, MessageSquare, RefreshCw, Sparkles } from "lucide-react";
import api from "../utils/api";
import Navbar from "../components/Navbar";
import "../template-theme.css";
import "../template-overrides.css";

const SPORTS = ["Football", "NBA", "WNBA", "NFL", "NCAAB", "College Football"];

export default function AiPicksTemplate() {
  const location = useLocation();
  const chatMode = location.pathname.endsWith("/chat");
  const [sport, setSport] = useState("Football");
  const [competition, setCompetition] = useState("");
  const [date, setDate] = useState(() => new Intl.DateTimeFormat("en-CA", { timeZone: "Africa/Kampala" }).format(new Date()));
  const [picks, setPicks] = useState([]);
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { setError(""); }, [chatMode]);

  const generate = async () => {
    setLoading(true); setError(""); setPicks([]);
    try {
      const response = await api.aiPicks.generate({ sport, competition: competition || undefined, date, limit: 10 });
      setPicks(Array.isArray(response.picks) ? response.picks : []);
    } catch (err) { setError(err.message || "The AI Picks service is unavailable"); }
    finally { setLoading(false); }
  };

  const sendMessage = async (event) => {
    event.preventDefault();
    const content = prompt.trim();
    if (!content || loading) return;
    const next = [...messages, { role: "user", content }];
    setMessages(next); setPrompt(""); setLoading(true); setError("");
    try {
      const response = await api.aiPicks.chat({ sport, messages: next });
      setMessages([...next, { role: "assistant", content: response.reply || "The provider returned no explanation." }]);
    } catch (err) { setError(err.message || "The chat provider is unavailable"); }
    finally { setLoading(false); }
  };

  return <>
    <Navbar />
    <div className="page-wrap ai-page">
      <div className="intro"><div><div className="eyebrow">FOOTBALLHERITAGE AI</div><h1>{chatMode ? "Talk through the numbers." : "A smarter look at matchday."}</h1></div><span className="intro-note"><span className="green-dot" /> Model-backed intelligence</span></div>
      <div className="layout ai-layout">
        <aside className="left-sidebar">
          <div className="card your-game"><span className="eyebrow">AI PICKS</span><h2>Let the data lead.</h2><p>Evidence-based selections from the connected statistical pipeline. No fabricated predictions.</p><Link className="primary-button" to={chatMode ? "/ai-picks" : "/ai-picks/chat"}><MessageSquare size={15} /> {chatMode ? "Best picks" : "Ask the agent"}</Link></div>
          <div className="card side-links"><h3>Supported models</h3>{SPORTS.map(item => <button key={item} onClick={() => setSport(item)}><span className="sport-symbol">{item.includes("Football") ? "◈" : "◉"}</span>{item}<ArrowUpRight size={13} /></button>)}</div>
          <div className="newsletter"><Sparkles size={20} /><h3>Responsible insight.</h3><p>Probabilities are estimates, not guarantees. AI Picks never places bets or moves money.</p></div>
        </aside>
        <main><div className="card section-card ai-panel">
          <span className="eyebrow"><Sparkles size={13} /> {chatMode ? "AI PICKS CHAT" : "BEST PICKS"}</span>
          <p className="muted">{chatMode ? "Ask about fixtures, form and model evidence. Numerical claims are grounded in provider results." : "Generate model-backed selections and inspect the evidence behind each value pick."}</p>
          <div className="ai-filters"><label>Sport<select value={sport} onChange={event => setSport(event.target.value)}>{SPORTS.map(item => <option key={item}>{item}</option>)}</select></label>{!chatMode && <><label>Competition<input value={competition} onChange={event => setCompetition(event.target.value)} placeholder="Premier League" maxLength={120} /></label><label>Match date<input type="date" value={date} onChange={event => setDate(event.target.value)} /></label></>}</div>
          {error && <div className="ai-error" role="alert"><AlertTriangle size={16} /> {error}<button onClick={chatMode ? () => sendMessage({ preventDefault: () => {} }) : generate}>Retry</button></div>}
          {!chatMode ? <><button className="primary-button" disabled={loading || !date} onClick={generate}>{loading ? <RefreshCw size={15} /> : <Sparkles size={15} />} {loading ? "Analyzing matchups…" : "Generate best picks"}</button>{picks.length === 0 && !loading && !error && <div className="ai-empty"><Sparkles size={28} /><h3>No picks loaded.</h3><p>Choose a sport and generate picks to see only selections supported by live model evidence.</p></div>}{picks.map((pick, index) => <article className="ai-pick" key={`${pick.match_id || pick.event || index}-${pick.selection}`}><span className="eyebrow">{pick.model_version || "Configured model"}</span><h3>{pick.home_team && pick.away_team ? `${pick.home_team} v ${pick.away_team}` : pick.event || "Fixture"}</h3><div><b>{pick.selection}</b><strong>{pick.model_prob == null ? "—" : `${(pick.model_prob * 100).toFixed(1)}%`}<small>model probability</small></strong></div><p>{pick.edge_pct == null ? "Value details returned by the statistical service." : `${pick.edge_pct}% edge · ${pick.expected_value == null ? "EV unavailable" : `expected value ${pick.expected_value}`}`}</p></article>)}</> : <><div className="ai-chat" aria-live="polite">{messages.length === 0 ? <div className="ai-empty"><MessageSquare size={28} /><h3>Start with a question.</h3><p>Which matchups have the strongest model signals?</p></div> : messages.map((message, index) => <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}><small>{message.role === "user" ? "YOU" : "AI PICKS"}</small><p>{message.content}</p></div>)}</div><form className="chat-compose" onSubmit={sendMessage}><textarea value={prompt} onChange={event => setPrompt(event.target.value)} placeholder="Ask about a matchup…" maxLength={4000} disabled={loading} /><button className="primary-button" disabled={loading || !prompt.trim()}>{loading ? "Thinking…" : "Send"}<ArrowRight size={15} /></button></form></>}
          <p className="ai-footnote">Probabilities are estimates, not guarantees. Backend-unavailable data is shown as unavailable rather than replaced with demo values.</p>
        </div></main>
      </div>
    </div>
  </>;
}
