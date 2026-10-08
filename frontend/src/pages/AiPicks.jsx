import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Bot, CheckCircle2, RefreshCw, Sparkles } from "lucide-react";
import api from "../utils/api";
import Navbar from "../components/Navbar";

const SPORTS = ["Football", "NBA", "WNBA", "NFL", "NCAAB", "College Football"];

export default function AiPicks() {
  const [sport, setSport] = useState("Football");
  const [competition, setCompetition] = useState("");
  const [picks, setPicks] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadHistory = async () => {
    try { setHistory(await api.aiPicks.list()); } catch { /* empty history is valid when the service is unavailable */ }
  };
  useEffect(() => { loadHistory(); }, []);

  const generate = async () => {
    setLoading(true); setError(""); setPicks([]);
    try {
      const response = await api.aiPicks.generate({ sport, competition: competition || undefined, limit: 10 });
      setPicks(response.picks || []); await loadHistory();
    } catch (err) { setError(err.message || "AI Picks could not be generated"); }
    finally { setLoading(false); }
  };

  return <><Navbar /><div className="min-h-screen bg-[#0d0d14] text-white px-4 py-8 sm:px-8">
    <div className="mx-auto max-w-7xl">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.25em] text-emerald-400">FootballHeritage Intelligence</p><h1 className="text-3xl font-bold sm:text-4xl">AI Picks</h1><p className="mt-2 max-w-2xl text-slate-400">Evidence-based value picks from current odds and the configured statistical models. No fabricated scores or predictions.</p></div>
        <Link to="/assistant" className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-emerald-500"><Bot size={16}/> Ask the assistant</Link>
      </div>
      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <section className="h-fit rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
          <h2 className="mb-4 font-semibold">Pick filters</h2>
          <label className="mb-4 block text-sm text-slate-400">Sport<select value={sport} onChange={(e) => setSport(e.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white">{SPORTS.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="mb-5 block text-sm text-slate-400">Competition (optional)<input value={competition} onChange={(e) => setCompetition(e.target.value)} placeholder="e.g. Premier League" className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white placeholder:text-slate-600" /></label>
          <button onClick={generate} disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-3 font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50">{loading ? <RefreshCw className="animate-spin" size={17}/> : <Sparkles size={17}/>} {loading ? "Checking evidence…" : "Generate picks"}</button>
          <p className="mt-4 text-xs leading-5 text-slate-500">Ranking uses model edge and expected value. Picks are omitted when data, freshness, or model evidence is insufficient.</p>
        </section>
        <section>
          {error && <div className="mb-5 flex items-start gap-3 rounded-xl border border-amber-900/70 bg-amber-950/30 p-4 text-amber-200"><AlertTriangle size={18} className="mt-0.5 shrink-0"/><div><p className="font-semibold">AI Picks unavailable</p><p className="mt-1 text-sm text-amber-300/80">{error}</p><button onClick={generate} className="mt-3 text-sm underline">Retry</button></div></div>}
          {!loading && !error && picks.length === 0 && <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center"><Sparkles className="mx-auto mb-3 text-emerald-400" size={28}/><h2 className="font-semibold">No picks loaded</h2><p className="mt-2 text-sm text-slate-500">Run a search to see only picks supported by live backend evidence.</p></div>}
          <div className="space-y-4">{picks.map((pick, index) => <article key={`${pick.match_id || pick.event || index}-${pick.selection}`} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs uppercase tracking-wider text-slate-500">{pick.competition || sport} · {pick.home_team || pick.event}</p><h2 className="mt-1 text-lg font-semibold">{pick.selection}</h2></div><span className="rounded-full bg-emerald-500/10 px-3 py-1 text-sm font-bold text-emerald-400">{pick.edge_pct != null ? `${pick.edge_pct}% edge` : "Value"}</span></div><div className="mt-5 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4"><Metric label="Model probability" value={pick.model_prob == null ? "—" : `${(pick.model_prob * 100).toFixed(1)}%`}/><Metric label="Implied probability" value={pick.implied_prob == null ? "—" : `${(pick.implied_prob * 100).toFixed(1)}%`}/><Metric label="Decimal odds" value={pick.decimal_odds || "—"}/><Metric label="Expected value" value={pick.expected_value == null ? "—" : pick.expected_value}/></div><div className="mt-4 flex items-center gap-2 text-xs text-slate-500"><CheckCircle2 size={14} className="text-emerald-500"/> Model: {pick.model_version || "unreported"} · probabilities are 0–1 internally</div></article>)}</div>
          {history.length > 0 && <div className="mt-8"><h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">Your recent runs</h2><div className="grid gap-2 sm:grid-cols-2">{history.slice(0, 6).map((run) => <div key={run.id} className="rounded-xl border border-slate-800 px-4 py-3 text-sm"><span className="text-slate-300">{run.sport}</span><span className="ml-2 text-slate-600">{run.competition || "All competitions"}</span><p className="mt-1 text-xs text-slate-600">{new Date(run.created_at).toLocaleString()}</p></div>)}</div></div>}
        </section>
      </div>
    </div>
  </div></>;
}

function Metric({ label, value }) { return <div className="rounded-lg bg-slate-900/80 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 font-semibold text-slate-200">{value}</p></div>; }
