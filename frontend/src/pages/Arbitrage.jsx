import { Fragment, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import LoadingSkeleton from "../components/LoadingSkeleton";
import EmptyState from "../components/EmptyState";
import { useArbitrage } from "../hooks/useIntelligence";

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

const formatAmericanOdds = (v) => {
  const n = toNumber(v);
  if (n === null || n === 0) return "--";
  return n > 0 ? `+${Math.round(n)}` : `${Math.round(n)}`;
};

const Arbitrage = () => {
  const [pipelineMatchId, setPipelineMatchId] = useState("");
  const [eventId, setEventId] = useState("");
  const [market, setMarket] = useState("");
  const [minArbPct, setMinArbPct] = useState(0.0);
  const [limit, setLimit] = useState(200);
  const [sortKey, setSortKey] = useState("arb_percentage");
  const [sortDir, setSortDir] = useState("desc");
  const [expandedId, setExpandedId] = useState(null);

  const params = useMemo(() => {
    const p = { limit };
    if (pipelineMatchId.trim()) p.pipeline_match_id = pipelineMatchId.trim();
    if (eventId.trim()) p.event_id = eventId.trim();
    if (market.trim()) p.market = market.trim();
    if (minArbPct !== null && Number.isFinite(minArbPct)) p.min_arb_pct = minArbPct;
    return p;
  }, [pipelineMatchId, eventId, market, minArbPct, limit]);

  const { data, isLoading, isError, error, refetch } = useArbitrage(params);

  const rows = useMemo(() => {
    const list = Array.isArray(data) ? [...data] : [];
    const dir = sortDir === "asc" ? 1 : -1;
    const getValue = (row) => {
      switch (sortKey) {
        case "created_at":
          return row.created_at ? new Date(row.created_at).getTime() : 0;
        case "arb_percentage":
          return toNumber(row.arb_percentage) ?? 0;
        case "total_stake":
          return toNumber(row.total_stake) ?? 0;
        case "stake_a":
          return toNumber(row.stake_a) ?? 0;
        case "stake_b":
          return toNumber(row.stake_b) ?? 0;
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
            <h1 className="text-3xl font-bold text-white">Arbitrage</h1>
            <p className="text-gray-400 mt-1">Cross-book opportunities sorted by edge.</p>
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
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
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
              placeholder="market"
              value={market}
              onChange={(e) => setMarket(e.target.value)}
            />
            <select
              className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white"
              value={minArbPct}
              onChange={(e) => setMinArbPct(Number(e.target.value))}
            >
              <option value={0}>Min Arb 0%</option>
              <option value={0.005}>Min Arb 0.5%</option>
              <option value={0.01}>Min Arb 1%</option>
              <option value={0.02}>Min Arb 2%</option>
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
            {error?.message || "Failed to load arbitrage."}
          </div>
        ) : !rows || rows.length === 0 ? (
          <div className="bg-gray-900/60 border border-gray-800 rounded-2xl">
            <EmptyState type="data" title="No arbitrage" description="No rows match your current filters." />
          </div>
        ) : (
          <div className="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-900 border-b border-gray-800">
                  <tr className="text-gray-400">
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("created_at")}>Created</th>
                    <th className="text-left px-4 py-3">Match</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("market")}>Market</th>
                    <th className="text-left px-4 py-3">Leg A</th>
                    <th className="text-left px-4 py-3">Leg B</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("arb_percentage")}>Edge</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("total_stake")}>Total Stake</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("stake_a")}>Stake A</th>
                    <th className="text-left px-4 py-3 cursor-pointer select-none" onClick={() => toggleSort("stake_b")}>Stake B</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const isExpanded = expandedId === row.id;
                    return (
                      <Fragment key={row.id}>
                        <tr
                          className="border-b border-gray-800/60 text-gray-200 hover:bg-gray-900/60 cursor-pointer"
                          onClick={() => setExpandedId(isExpanded ? null : row.id)}
                        >
                          <td className="px-4 py-3 whitespace-nowrap">{row.created_at ? new Date(row.created_at).toLocaleString() : "--"}</td>
                          <td className="px-4 py-3">
                            <div className="font-mono text-xs">{row.pipeline_match_id || ""}</div>
                          </td>
                          <td className="px-4 py-3">{row.market}</td>
                          <td className="px-4 py-3">
                            <div className="font-semibold">{row.selection_a}</div>
                            <div className="text-xs text-gray-500">{row.book_a} @ {formatAmericanOdds(row.odds_a)}</div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-semibold">{row.selection_b}</div>
                            <div className="text-xs text-gray-500">{row.book_b} @ {formatAmericanOdds(row.odds_b)}</div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-green-400 font-semibold">{formatPct(row.arb_percentage)}</span>
                          </td>
                          <td className="px-4 py-3">{formatMoney(row.total_stake)}</td>
                          <td className="px-4 py-3">{formatMoney(row.stake_a)}</td>
                          <td className="px-4 py-3">{formatMoney(row.stake_b)}</td>
                        </tr>

                        {isExpanded && (
                          <tr className="border-b border-gray-800/60 bg-gray-950/40">
                            <td className="px-4 py-3" colSpan={9}>
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

export default Arbitrage;
