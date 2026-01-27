import { Fragment, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import LoadingSkeleton from "../components/LoadingSkeleton";
import EmptyState from "../components/EmptyState";
import { useEvBets } from "../hooks/useIntelligence";

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

const EVBets = () => {
  const [pipelineMatchId, setPipelineMatchId] = useState("");
  const [eventId, setEventId] = useState("");
  const [bookmaker, setBookmaker] = useState("");
  const [market, setMarket] = useState("");
  const [minEvPct, setMinEvPct] = useState(0.0);
  const [limit, setLimit] = useState(200);
  const [sortKey, setSortKey] = useState("expected_value_pct");
  const [sortDir, setSortDir] = useState("desc");
  const [expandedId, setExpandedId] = useState(null);

  const params = useMemo(() => {
    const p = { limit };
    if (pipelineMatchId.trim()) p.pipeline_match_id = pipelineMatchId.trim();
    if (eventId.trim()) p.event_id = eventId.trim();
    if (bookmaker.trim()) p.bookmaker = bookmaker.trim();
    if (market.trim()) p.market = market.trim();
    if (minEvPct !== null && Number.isFinite(minEvPct)) p.min_ev_pct = minEvPct;
    return p;
  }, [pipelineMatchId, eventId, bookmaker, market, minEvPct, limit]);

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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-bold text-white">+EV Bets</h1>
            <p className="text-gray-400 mt-1">Ranked by expected value percentage.</p>
          </div>

          <button
            onClick={() => refetch()}
            className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg font-semibold border border-gray-700"
            type="button"
          >
            Refresh
          </button>
        </div>

        <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
            <input
              className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white placeholder-gray-600"
              placeholder="pipeline_match_id"
              value={pipelineMatchId}
              onChange={(e) => setPipelineMatchId(e.target.value)}
            />
            <input
              className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white placeholder-gray-600"
              placeholder="event_id (uuid)"
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
            />
            <input
              className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white placeholder-gray-600"
              placeholder="bookmaker"
              value={bookmaker}
              onChange={(e) => setBookmaker(e.target.value)}
            />
            <input
              className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white placeholder-gray-600"
              placeholder="market"
              value={market}
              onChange={(e) => setMarket(e.target.value)}
            />
            <select
              className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white"
              value={minEvPct}
              onChange={(e) => setMinEvPct(Number(e.target.value))}
            >
              <option value={0}>Min EV 0%</option>
              <option value={0.02}>Min EV 2%</option>
              <option value={0.05}>Min EV 5%</option>
              <option value={0.1}>Min EV 10%</option>
            </select>
            <select
              className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            >
              <option value={50}>Limit 50</option>
              <option value={200}>Limit 200</option>
              <option value={500}>Limit 500</option>
              <option value={1000}>Limit 1000</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <LoadingSkeleton type="list" count={1} />
        ) : isError ? (
          <div className="bg-red-500/10 border border-red-500/30 text-red-200 rounded-xl p-4">
            {error?.message || "Failed to load EV bets."}
          </div>
        ) : !rows || rows.length === 0 ? (
          <div className="bg-gray-900/60 border border-gray-800 rounded-2xl">
            <EmptyState type="data" title="No EV bets" description="No rows match your current filters." />
          </div>
        ) : (
          <div className="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-900 border-b border-gray-800">
                  <tr className="text-gray-400">
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("created_at")}>Created</th>
                    <th className="text-left px-4 py-3">Match</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("bookmaker")}>Book</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("market")}>Market</th>
                    <th className="text-left px-4 py-3">Selection</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("odds")}>Odds (Dec)</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("true_probability")}>True Prob</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("stake")}>Stake</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("expected_value")}>EV</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("expected_value_pct")}>EV %</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const evPct = toNumber(row.expected_value_pct) ?? 0;
                    const isExpanded = expandedId === row.id;
                    return (
                      <Fragment key={row.id}>
                        <tr
                          className="border-b border-gray-800/60 text-gray-200 hover:bg-gray-900/60 cursor-pointer"
                          onClick={() => setExpandedId(isExpanded ? null : row.id)}
                        >
                          <td className="px-4 py-3 whitespace-nowrap">{row.created_at ? new Date(row.created_at).toLocaleString() : "--"}</td>
                          <td className="px-4 py-3">
                            <div className="font-semibold">{formatMatchLabel(row) || "--"}</div>
                            <div className="text-xs text-gray-500">{row.event_date ? new Date(row.event_date).toLocaleString() : ""}</div>
                          </td>
                          <td className="px-4 py-3">{row.bookmaker || "--"}</td>
                          <td className="px-4 py-3">{row.market}</td>
                          <td className="px-4 py-3">{row.selection}</td>
                          <td className="px-4 py-3">{formatDecimalOdds(row.odds)}</td>
                          <td className="px-4 py-3">{formatPct(row.true_probability)}</td>
                          <td className="px-4 py-3">{formatMoney(row.stake)}</td>
                          <td className="px-4 py-3">{formatMoney(row.expected_value)}</td>
                          <td className="px-4 py-3">
                            <span className={evPct >= 0 ? "text-green-400 font-semibold" : "text-red-400 font-semibold"}>
                              {formatPct(row.expected_value_pct)}
                            </span>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="border-b border-gray-800/60 bg-gray-950/40">
                            <td className="px-4 py-3" colSpan={10}>
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-gray-300">
                                <div>
                                  <div className="text-gray-500">Event ID</div>
                                  <div className="font-mono break-all">{row.event_id || "--"}</div>
                                </div>
                                <div>
                                  <div className="text-gray-500">Source Updated</div>
                                  <div>{row.source_updated_at ? new Date(row.source_updated_at).toLocaleString() : "--"}</div>
                                </div>
                                <div>
                                  <div className="text-gray-500">Row ID</div>
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
