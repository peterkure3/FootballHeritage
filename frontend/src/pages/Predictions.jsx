import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, Activity, Layers3 } from "lucide-react";
import { predictionService } from "../services/predictionService";
import ForecastCard from "../components/predictions/ForecastCard";
import BookmakerGrid from "../components/predictions/BookmakerGrid";
import PredictionResults from "../components/predictions/PredictionResults";
import ModelPreview from "../components/predictions/ModelPreview";
import PaperTrial from "../components/predictions/PaperTrial";
import Pagination from "../components/predictions/Pagination";
import QueryState from "../components/predictions/QueryState";
import "./Predictions.css";

function FixtureToolbar({ filters, setFilters, feed }) {
  const competitions = feed.data?.competitions ?? [];
  function filter(key, value) {
    setFilters((previous) => ({ ...previous, [key]: value, page: 1 }));
  }
  return (
    <div className="pd-toolbar">
      <div className="pd-filters">
        <label>
          Competition
          <select
            value={filters.competition}
            onChange={(event) => filter("competition", event.target.value)}
          >
            <option value="">All competitions</option>
            {competitions.map((league) => (
              <option key={league} value={league}>
                {feed.data?.competition_labels?.[league] ?? league}
              </option>
            ))}
          </select>
        </label>
        <label>
          Kickoff date (UTC)
          <input
            type="date"
            value={filters.match_date}
            onChange={(event) => filter("match_date", event.target.value)}
          />
        </label>
      </div>
      <button
        className="pd-button pd-button-outline"
        disabled={feed.isFetching}
        onClick={() => void feed.refetch()}
      >
        <RefreshCw size={15} />
        {feed.isFetching ? "Refreshing…" : "Refresh"}
      </button>
    </div>
  );
}
function FixtureList({ data, filters, setFilters, busy, comparison }) {
  if (data.items.length === 0)
    return (
      <div className="pd-empty">
        <h2>No upcoming fixtures match these filters.</h2>
        <p>Choose another competition or kickoff date.</p>
      </div>
    );
  return (
    <>
      <div className="pd-feed-summary">
        <span>
          <strong>{data.total_count}</strong> upcoming fixtures
        </span>
        <span>Soccer · league models / active v{data.active_model_version}</span>
        <span>Updated {new Date(data.generated_at).toLocaleTimeString()}</span>
      </div>
      {comparison ? (
        <BookmakerGrid fixtures={data.items} bookmakers={data.bookmakers} />
      ) : (
        <div className="pd-forecast-grid">
          {data.items.map((fixture) => (
            <ForecastCard key={fixture.match_id} fixture={fixture} />
          ))}
        </div>
      )}
      <Pagination
        page={filters.page}
        total={data.total_count}
        pageSize={filters.page_size}
        busy={busy}
        onPage={(page) => setFilters((previous) => ({ ...previous, page }))}
      />
    </>
  );
}
function Fixtures({ comparison = false }) {
  const [filters, setFilters] = useState({
    page: 1,
    page_size: comparison ? 20 : 6,
    competition: "",
    match_date: "",
  });
  const feed = useQuery({
    queryKey: ["prediction-dashboard", filters],
    queryFn: ({ signal }) => predictionService.getDashboard(filters, signal),
    staleTime: 30000,
    refetchInterval: 60000,
    retry: 1,
  });
  return (
    <section aria-label="Upcoming predictions">
      <FixtureToolbar filters={filters} setFilters={setFilters} feed={feed} />
      <QueryState
        query={feed}
        loading="Loading fixture predictions…"
        failure="Could not refresh predictions"
      >
        {(data) => (
          <FixtureList
            data={data}
            filters={filters}
            setFilters={setFilters}
            busy={feed.isFetching}
            comparison={comparison}
          />
        )}
      </QueryState>
    </section>
  );
}

export default function Predictions() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get("view");
  const tab = [
    "fixtures",
    "comparisons",
    "history",
    "models",
    "trials",
  ].includes(requestedTab)
    ? requestedTab
    : "fixtures";
  const views = {
    fixtures: <Fixtures />,
    comparisons: <Fixtures key="comparisons" comparison />,
    history: <PredictionResults />,
    models: <ModelPreview />,
    trials: <PaperTrial />,
  };
  return (
    <main className="pd-page">
      <header className="pd-hero">
        <div>
          <p className="pd-eyebrow">
            <Activity size={15} /> PREDICTION INTELLIGENCE
          </p>
          <h1>
            See the probabilities.
            <br />
            <em>Understand the evidence.</em>
          </h1>
          <p>
            Match forecasts, bookmaker prices and measured performance — with
            the source behind every number.
          </p>
        </div>
        <div className="pd-hero-note">
          <Layers3 size={25} />
          <strong>Models, with context.</strong>
          <p>
            Fixtures show evaluated league forecasts where available, alongside
            the active soccer model. Explore sport candidates in the model lab.
          </p>
        </div>
      </header>
      <nav className="pd-tabs" aria-label="Prediction views">
        {[
          ["fixtures", "Upcoming fixtures"],
          ["comparisons", "Bookmaker grid"],
          ["history", "Settled performance"],
          ["models", "Model lab"],
          ["trials", "Paper trials"],
        ].map(([key, label]) => (
          <button
            key={key}
            aria-current={tab === key ? "page" : undefined}
            onClick={() =>
              setSearchParams((previous) => {
                const next = new URLSearchParams(previous);
                next.set("view", key);
                return next;
              })
            }
          >
            {label}
          </button>
        ))}
      </nav>
      {views[tab]}
      <p className="pd-footer-note">
        Probabilities are estimates. Positive estimated value does not establish
        an advantage over bookmakers. No bets are placed here.
      </p>
    </main>
  );
}
