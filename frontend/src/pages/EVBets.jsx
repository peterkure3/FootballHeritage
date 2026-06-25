import { Fragment, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import LoadingSkeleton from "../components/LoadingSkeleton";
import EmptyState from "../components/EmptyState";
import { useEvBets } from "../hooks/useIntelligence";
import { api } from "../utils/api";

const toNumber = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
};

const formatPct = (v) => {
  const n = toNumber(v);
  if (n === null) return "--";
  return `${(n * 100).toFixed(2)}%`;
};

const formatMoney = (v) => {
  const n = toNumber(v);
  if (n === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(n);
};

const formatDecimalOdds = (v) => {
  const n = toNumber(v);
  if (n === null) return "--";
  return n.toFixed(3);
};

const formatMatchLabel = (row) => {
  const home = row?.event_home_team;
  const away = row?.event_away_team;
  if (home && away) return `${home} vs ${away}`;
  return row?.pipeline_match_id || "";
};

const LEAGUES = [
  { value: "", label: "All Leagues" },
  { value: "soccer_epl", label: "Premier League" },
  { value: "soccer_spain_la_liga", label: "La Liga" },
  { value: "soccer_germany_bundesliga", label: "Bundesliga" },
  { value: "soccer_italy_serie_a", label: "Serie A" },
  { value: "soccer_france_ligue_one", label: "Ligue 1" },
  { value: "soccer_uefa_champs_league", label: "Champions League" },
  { value: "americanfootball_nfl", label: "NFL" },
  { value: "basketball_nba", label: "NBA" },
  { value: "basketball_ncaab", label: "NCAA Basketball" },
];

const EVBets = () => {
  const [pipelineMatchId, setPipelineMatchId] = useState("");
  const [eventId, setEventId] = useState("");
  const [bookmaker, setBookmaker] = useState("");
  const [market, setMarket] = useState("");
  const [league, setLeague] = useState("");
  const [minEvPct, setMinEvPct] = useState(0.0);
  const [limit, setLimit] = useState(200);
  const [sortKey, setSortKey] = useState("expected_value_pct");
  const [sortDir, setSortDir] = useState("desc");
  const [expandedId, setExpandedId] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const params = useMemo(() => {
    const p = { limit };
    if (pipelineMatchId.trim()) p.pipeline_match_id = pipelineMatchId.trim();
    if (eventId.trim()) p.event_id = eventId.trim();
    if (bookmaker.trim()) p.bookmaker = bookmaker.trim();
    if (market.trim()) p.market = market.trim();
    if (league) p.league = league;
    if (minEvPct !== null && Number.isFinite(minEvPct)) p.min_ev_pct = minEvPct;
    return p;
  }, [pipelineMatchId, eventId, bookmaker, market, league, minEvPct, limit]);

  const { data, isLoading, isError, error, refetch } = useEvBets(params);

  const rows = useMemo(() => {
    const list = Array.isArray(data) ? [...data] : [];

    const dir = sortDir === "asc" ? 1 : -1;
    const getValue = (row) => {
      switch (sortKey) {
        case "created_at":
          return row.created_at ? new Date(row.created_at).getTime() : 0;
        case "expected_value_pct":
          return toNumber(row.expected_value_pct) ?? 0;
        case "expected_value":
          return toNumber(row.expected_value) ?? 0;
        case "true_probability":
          return toNumber(row.true_probability) ?? 0;
        case "odds":
          return toNumber(row.odds) ?? 0;
        case "stake":
          return toNumber(row.stake) ?? 0;
        case "league":
          return row?.league ?? "";
        default:
          return row?.[sortKey] ?? "";
      }
    };

    list.sort((a, b) => {
      const av = getValue(a);
      const bv = getValue(b);
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv)) * dir;
    });

    return list;
  }, [data, sortKey, sortDir]);

  const toggleSort = (key) => {
    setExpandedId(null);
    setSortKey((prevKey) => {
      if (prevKey !== key) {
        setSortDir("desc");
        return key;
      }
      setSortDir((prevDir) => (prevDir === "asc" ? "desc" : "asc"));
      return prevKey;
    });
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header className="flex items-start justify-between gap-4 flex-wrap" style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <div>
            <p className="text-sm uppercase tracking-wide font-semibold mb-1" style={{ color: '#10b981' }}>Value Analysis</p>
            <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight">+EV Bets</h1>
            <p className="text-sm mt-1" style={{ color: '#64748b' }}>Ranked by expected value percentage.</p>
          </div>
          <button
            onClick={async () => {
              setIsRefreshing(true);
              try {
                await api.refreshIntelligence();
                await refetch();
              } catch (err) {
                console.error("Failed to refresh intelligence:", err);
              } finally {
                setIsRefreshing(false);
              }
            }}
            disabled={isRefreshing}
            className={`px-4 py-2 rounded-lg font-semibold transition-all card-glow text-white ${isRefreshing ? 'opacity-50 cursor-not-allowed' : ''}`}
            style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', border: '1px solid var(--color-card-border)' }}
            type="button"
          >
            {isRefreshing ? "Refreshing..." : "Refresh"}
          </button>
        </header>

        <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.4s ease-out 0.06s both' }}>
          <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-7 gap-3">
            <select
              className="rounded-lg px-3 py-2 text-white focus:outline-none"
              style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}
              value={league}
              onChange={(e) => setLeague(e.target.value)}
            >
              {LEAGUES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
            <input
              className="rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:ring-2 transition-all"
              style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
              placeholder="bookmaker"
              value={bookmaker}
              onChange={(e) => setBookmaker(e.target.value)}
            />
            <input
              className="rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:ring-2 transition-all"
              style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
              placeholder="market"
              value={market}
              onChange={(e) => setMarket(e.target.value)}
            />
            <select
              className="rounded-lg px-3 py-2 text-white focus:outline-none"
              style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}
              value={minEvPct}
              onChange={(e) => setMinEvPct(Number(e.target.value))}
            >
              <option value={0}>Min EV 0%</option>
              <option value={0.02}>Min EV 2%</option>
              <option value={0.05}>Min EV 5%</option>
              <option value={0.1}>Min EV 10%</option>
            </select>
            <select
              className="rounded-lg px-3 py-2 text-white focus:outline-none"
              style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            >
              <option value={50}>Limit 50</option>
              <option value={200}>Limit 200</option>
              <option value={500}>Limit 500</option>
              <option value={1000}>Limit 1000</option>
            </select>
            <input
              className="rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:ring-2 transition-all"
              style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
              placeholder="pipeline_match_id"
              value={pipelineMatchId}
              onChange={(e) => setPipelineMatchId(e.target.value)}
            />
            <input
              className="rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:ring-2 transition-all"
              style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
              placeholder="event_id (uuid)"
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
            />
          </div>
        </div>

        {isLoading ? (
          <LoadingSkeleton type="list" count={1} />
        ) : isError ? (
          <div className="rounded-xl p-4 border" style={{ background: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>
            {error?.message || "Failed to load EV bets."}
          </div>
        ) : !rows || rows.length === 0 ? (
          <div className="card-glow rounded-xl border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
            <EmptyState type="data" title="No EV bets" description="No rows match your current filters." />
          </div>
        ) : (
          <div className="card-glow rounded-xl border overflow-hidden" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead style={{ background: 'var(--color-card)', borderBottom: '1px solid var(--color-card-border)' }}>
                  <tr style={{ color: '#64748b' }}>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("created_at")}>Created</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("league")}>League</th>
                    <th className="text-left px-4 py-3 font-semibold">Match</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("bookmaker")}>Book</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("market")}>Market</th>
                    <th className="text-left px-4 py-3 font-semibold">Selection</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("odds")}>Odds (Dec)</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("true_probability")}>True Prob</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("stake")}>Stake</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("expected_value")}>EV</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none font-semibold" onClick={() => toggleSort("expected_value_pct")}>EV %</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const evPct = toNumber(row.expected_value_pct) ?? 0;
                    const isExpanded = expandedId === row.id;
                    return (
                      <Fragment key={row.id}>
                        <tr
                          className="cursor-pointer"
                          style={{ borderBottom: '1px solid var(--color-card-border)', color: '#cbd5e1' }}
                          onClick={() => setExpandedId(isExpanded ? null : row.id)}
                        >
                          <td className="px-4 py-3 whitespace-nowrap">{row.created_at ? new Date(row.created_at).toLocaleString() : "--"}</td>
                          <td className="px-4 py-3 whitespace-nowrap">{row.league || "--"}</td>
                          <td className="px-4 py-3">
                            <div className="font-semibold" style={{ color: 'white' }}>{formatMatchLabel(row) || "--"}</div>
                            <div className="text-xs" style={{ color: '#64748b' }}>{row.event_date ? new Date(row.event_date).toLocaleString() : ""}</div>
                          </td>
                          <td className="px-4 py-3">{row.bookmaker || "--"}</td>
                          <td className="px-4 py-3">{row.market}</td>
                          <td className="px-4 py-3">{row.selection}</td>
                          <td className="px-4 py-3">{formatDecimalOdds(row.odds)}</td>
                          <td className="px-4 py-3">{formatPct(row.true_probability)}</td>
                          <td className="px-4 py-3">{formatMoney(row.stake)}</td>
                          <td className="px-4 py-3">{formatMoney(row.expected_value)}</td>
                          <td className="px-4 py-3">
                            <span className="font-semibold" style={{ color: evPct >= 0 ? '#34d399' : '#fca5a5' }}>
                              {formatPct(row.expected_value_pct)}
                            </span>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr style={{ borderBottom: '1px solid var(--color-card-border)', background: 'rgba(0,0,0,0.2)' }}>
                            <td className="px-4 py-3" colSpan={11}>
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs" style={{ color: '#94a3b8' }}>
                                <div>
                                  <div style={{ color: '#64748b' }}>Event ID</div>
                                  <div className="font-mono break-all">{row.event_id || "--"}</div>
                                </div>
                                <div>
                                  <div style={{ color: '#64748b' }}>Source Updated</div>
                                  <div>{row.source_updated_at ? new Date(row.source_updated_at).toLocaleString() : "--"}</div>
                                </div>
                                <div>
                                  <div style={{ color: '#64748b' }}>Row ID</div>
                                  <div className="font-mono break-all">{row.id}</div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EVBets;
