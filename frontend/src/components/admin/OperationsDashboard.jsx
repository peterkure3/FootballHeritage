import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Database,
  Download,
  FlaskConical,
  Globe2,
  Layers3,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { predictionService } from "../../services/predictionService";
import "../../pages/AdminDashboard.css";

const count = (value) => (value == null ? "—" : value.toLocaleString());
const percent = (value) =>
  value == null ? "Pending" : `${(value * 100).toFixed(2)}%`;
const timestamp = (value) => {
  const date = value ? new Date(value) : null;
  return date && Number.isFinite(date.getTime())
    ? date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Not recorded";
};
const readable = (value) =>
  value ? value.replaceAll("_", " ") : "Not recorded";

function DataNotice({ query, label }) {
  if (query.isPending)
    return (
      <p className="ops-notice" role="status">
        Loading {label}…
      </p>
    );
  if (!query.error) return null;
  return (
    <div className="ops-notice ops-notice-error" role="alert">
      <span>
        {label} unavailable: {query.error.message}.
        {query.data && " Showing the last successful response."}
      </span>
      <button className="ops-text-button" onClick={() => void query.refetch()}>
        Retry {label}
      </button>
    </div>
  );
}

function Metric({ icon, label, value, detail, accent }) {
  const Icon = icon;
  return (
    <article className={`ops-metric ${accent ? "ops-metric-accent" : ""}`}>
      <div className="ops-metric-label">
        <span>{label}</span>
        <Icon size={18} aria-hidden="true" />
      </div>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function PanelHeading({ eyebrow, title, children }) {
  return (
    <header className="ops-panel-heading">
      <div>
        <span className="ops-eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
      </div>
      {children}
    </header>
  );
}

function collectorHeading(outcome) {
  if (outcome === "success") return "Last collection completed";
  return `Collector ${readable(outcome)}`;
}

function collectorDetail(steps = []) {
  if (steps.length) return `${steps.length} collection step(s) need attention.`;
  return "Fixture ingestion, price collection, and paper-trial settlement.";
}

function collectorSummary(data) {
  const collector = data?.collector;
  if (!collector)
    return {
      title: data ? "No collector run recorded" : "Awaiting collection status",
      detail: collectorDetail(),
    };
  return {
    title: collectorHeading(collector.outcome),
    detail: collectorDetail(collector.failed_steps || []),
    success: collector.outcome === "success",
    attempted: collector.last_attempt_at,
    succeeded: collector.last_success_at,
  };
}

function Collector({ data }) {
  const status = collectorSummary(data);
  return (
    <section className="ops-panel ops-collector" aria-label="Collection health">
      <div className={`ops-health-icon ${status.success ? "is-success" : ""}`}>
        <Radio size={22} aria-hidden="true" />
      </div>
      <div className="ops-collector-copy">
        <span className="ops-eyebrow">COLLECTION HEALTH</span>
        <h2>{status.title}</h2>
        <p>{status.detail}</p>
      </div>
      <dl className="ops-collector-times">
        <div>
          <dt>Last attempt</dt>
          <dd>{timestamp(status.attempted)}</dd>
        </div>
        <div>
          <dt>Last successful run</dt>
          <dd>{timestamp(status.succeeded)}</dd>
        </div>
      </dl>
    </section>
  );
}

function LeagueCoverage({ data }) {
  return (
    <section className="ops-panel" aria-label="Competition coverage">
      <PanelHeading
        eyebrow="PREDICTION COVERAGE"
        title="Every fixture, accounted for"
      >
        <Link className="ops-text-link" to="/predictions?view=fixtures">
          Open predictions <ArrowUpRight size={15} />
        </Link>
      </PanelHeading>
      {!data ? (
        <p className="ops-empty">
          Coverage will appear when the operations service is available.
        </p>
      ) : !data.competitions.length ? (
        <p className="ops-empty">No eligible upcoming fixtures.</p>
      ) : (
        <div className="ops-leagues">
          {data.competitions.map((league) => (
            <div className="ops-league" key={league.competition ?? "unknown"}>
              <div className="ops-league-title">
                <h3>{league.competition || "Unspecified competition"}</h3>
                <span>{count(league.fixtures)} fixtures</span>
              </div>
              <progress
                aria-label={`${league.competition || "Unspecified competition"} forecast coverage`}
                value={league.current_forecasts}
                max={Math.max(league.fixtures, 1)}
              />
              <div className="ops-league-detail">
                <span>
                  <i className="ops-dot" />
                  {count(league.current_forecasts)} current forecasts
                </span>
                <span>{count(league.priced_fixtures)} with fresh prices</span>
              </div>
            </div>
          ))}
        </div>
      )}
      <footer className="ops-panel-footer">
        <Clock3 size={14} aria-hidden="true" />
        Current evidence is at most 24 hours old and recorded before kickoff.
      </footer>
    </section>
  );
}

function OutcomeCoverage({ summary }) {
  return (
    <section
      className="ops-panel ops-outcomes"
      aria-label="Probability and EV coverage"
    >
      <PanelHeading
        eyebrow="PROBABILITIES & VALUE"
        title="Model estimates, with context"
      >
        <Layers3 size={21} />
      </PanelHeading>
      <div className="ops-outcome-totals">
        <div>
          <strong>{count(summary?.compared_outcomes)}</strong>
          <span>outcomes compared</span>
        </div>
        <div>
          <strong>{count(summary?.positive_ev_outcomes)}</strong>
          <span>positive estimated EV</span>
        </div>
      </div>
      <p>
        Home, draw, and away outcomes use the best fresh price for each
        selection. EV is model probability × decimal odds − 1.
      </p>
      <div className="ops-caution">
        Positive estimated EV is not a settled return or proof of a profitable
        edge.
      </div>
      <Link className="ops-text-link" to="/predictions?view=comparisons">
        Inspect bookmaker comparisons <ArrowUpRight size={15} />
      </Link>
    </section>
  );
}

function SourceCoverage({ data }) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState(false);
  const books = filteredSources(data, search, filter);
  const visible = expanded ? books : books.slice(0, 7);
  return (
    <section className="ops-panel" aria-label="Sportsbook coverage">
      <PanelHeading
        eyebrow="SPORTSBOOK NETWORK"
        title="Fresh prices. Traceable sources."
      >
        <span className="ops-tag">
          {count(data?.covered_bookmakers)} /{" "}
          {count(data?.configured_bookmakers)} covered
        </span>
      </PanelHeading>
      <SourceFilters
        search={search}
        setSearch={setSearch}
        filter={filter}
        setFilter={setFilter}
      />
      <SourcesTable visible={visible} data={data} />
      <footer className="ops-source-footer">
        <span>
          Showing {visible.length} of {books.length} sources
        </span>
        {books.length > 7 && (
          <button
            className="ops-text-button"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Show fewer" : "Show all sources"}
          </button>
        )}
      </footer>
    </section>
  );
}

function PaperStudies({ studies, query }) {
  const manual =
    query.data?.studies?.filter(
      (study) => study.policy?.selection === "user_selected",
    ) ?? [];
  return (
    <section className="ops-panel" aria-label="Paper trial progress">
      <PanelHeading eyebrow="PROSPECTIVE VALIDATION" title="Paper trials">
        <Link className="ops-text-link" to="/predictions?view=trials">
          View ledger <ArrowUpRight size={15} />
        </Link>
      </PanelHeading>
      <DataNotice query={query} label="paper trials" />
      {!query.data ? (
        <p className="ops-empty">
          Trial results will appear when the evidence service is available.
        </p>
      ) : !studies.length ? (
        <p className="ops-empty">No model paper trials have been recorded.</p>
      ) : (
        studies.map((study) => (
          <PaperStudy key={study.study_id} study={study} />
        ))
      )}

      <footer className="ops-panel-footer">
        Pending selections are excluded from ROI. Both assessment gates must be
        met.
        {manual.length > 0 &&
          ` ${manual.reduce((total, study) => total + study.settled_selections, 0)} manual selection(s) tracked separately.`}
      </footer>
    </section>
  );
}

function CollectionReceipt({ receipt }) {
  return (
    <section
      className="ops-panel ops-receipt"
      aria-label="Latest collection receipt"
    >
      <PanelHeading eyebrow="LATEST SOURCE CAPTURE" title="Collection receipt">
        <Database size={20} />
      </PanelHeading>
      {receipt?.state === "available" ? (
        <>
          <div className="ops-receipt-total">
            {count(receipt.snapshot_count)}
            <span>captured market observations</span>
          </div>
          <dl>
            <div>
              <dt>Sources returning quotes</dt>
              <dd>
                {receipt.sources_with_quotes} / {receipt.sources_checked}{" "}
                checked
              </dd>
            </div>
            <div>
              <dt>Transport</dt>
              <dd>{receipt.transport}</dd>
            </div>
            <div>
              <dt>Completed</dt>
              <dd>{timestamp(receipt.completed_at)}</dd>
            </div>
          </dl>
          <p>
            Raw observations span multiple leagues. Only verified fixture
            matches reach the displayed market comparison.
          </p>
        </>
      ) : (
        <p className="ops-empty">
          {receipt?.state === "unavailable"
            ? "The latest capture receipt could not be read."
            : "No capture receipt available."}
        </p>
      )}
    </section>
  );
}

function exportOverview(operations, paper) {
  const url = URL.createObjectURL(
    new Blob(
      [JSON.stringify({ operations, paper_trials: paper ?? null }, null, 2)],
      { type: "application/json" },
    ),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `footballheritage-operations-${new Date().toISOString().slice(0, 10)}.json`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function OverviewHeader({ operations, paper }) {
  const data = operations.data;
  const refreshing = operations.isFetching || paper.isFetching;
  return (
    <header className="ops-header">
      <div>
        <span className="ops-eyebrow">
          <ShieldCheck size={13} /> ADMINISTRATION / LIVE OPERATIONS
        </span>
        <h1>
          Operations overview<span>.</span>
        </h1>
        <p>
          The data behind the platform. Collection, forecasts, and validation in
          one place.
        </p>
      </div>
      <div className="ops-header-actions">
        <span className="ops-updated">
          <i className={`ops-dot ${operations.error ? "is-muted" : ""}`} />
          {data
            ? `Checked ${timestamp(data.generated_at)}`
            : "Awaiting live data"}
        </span>
        <div>
          <button
            className="ops-button ops-button-secondary"
            disabled={!data}
            onClick={() => exportOverview(data, paper.data)}
          >
            <Download size={16} />
            Export snapshot
          </button>
          <button
            className="ops-button"
            disabled={refreshing}
            onClick={() => {
              void operations.refetch();
              void paper.refetch();
            }}
          >
            <RefreshCw size={16} className={refreshing ? "ops-spin" : ""} />
            {refreshing ? "Refreshing" : "Refresh data"}
          </button>
        </div>
      </div>
    </header>
  );
}

function fixtureMetric(data) {
  if (!data) return { value: "—", detail: "Awaiting fixture coverage" };
  return {
    value: count(data.summary.upcoming_fixtures),
    detail: `${data.competitions.length} competitions · next ${timestamp(data.summary.next_kickoff)}`,
  };
}
function bookmakerMetric(data) {
  if (!data) return { value: "— / —", detail: "Awaiting market coverage" };
  return {
    value: `${count(data.covered_bookmakers)} / ${count(data.configured_bookmakers)}`,
    detail: `${count(data.summary.fresh_quotes)} fresh fixture quotes`,
  };
}
function forecastMetric(data) {
  if (!data) return { value: "—", detail: "Awaiting active-model coverage" };
  return {
    value: count(data.summary.current_forecasts),
    detail: `Active model v${data.active_model_version} · ${data.summary.upcoming_fixtures - data.summary.current_forecasts} missing or stale`,
  };
}
function paperMetric(data, studies) {
  if (!data) return { value: "—", detail: "Awaiting trial evidence" };
  const selections = studies.reduce(
    (total, study) => total + study.pending_selections,
    0,
  );
  const forecasts = data.trials
    .filter(isModelTrial)
    .reduce((total, trial) => total + trial.pending_forecasts, 0);
  return {
    value: count(selections),
    detail: `${count(forecasts)} forecasts awaiting final results`,
  };
}
function isModelTrial(record) {
  return record.policy?.selection !== "user_selected";
}
function modelStudies(data) {
  return data ? data.studies.filter(isModelTrial) : [];
}
function OverviewMetrics({ data, paper, studies }) {
  return (
    <div className="ops-metrics">
      <Metric
        icon={Activity}
        label="Upcoming fixtures"
        {...fixtureMetric(data)}
      />
      <Metric
        icon={Globe2}
        label="Sportsbook coverage"
        {...bookmakerMetric(data)}
      />
      <Metric
        icon={Layers3}
        label="Current forecasts"
        {...forecastMetric(data)}
      />
      <Metric
        icon={FlaskConical}
        label="Pending paper selections"
        {...paperMetric(paper, studies)}
        accent
      />
    </div>
  );
}

function OverviewFooter() {
  return (
    <footer className="ops-footer">
      <span>
        <CheckCircle2 size={15} />
        Automatic refresh every 60 seconds. Timestamps use your local time.
      </span>
      <nav aria-label="Admin management">
        <Link to="/admin/events">Manage events</Link>
        <Link to="/admin/users">Manage users</Link>
        <Link to="/admin/logs">Audit logs</Link>
      </nav>
    </footer>
  );
}

function SourceFilters({ search, setSearch, filter, setFilter }) {
  return (
    <div className="ops-source-tools">
      <label className="ops-search">
        <Search size={16} aria-hidden="true" />
        <input
          aria-label="Search sportsbooks"
          placeholder="Find a sportsbook"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </label>
      <select
        aria-label="Filter sportsbook coverage"
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
      >
        <option value="all">All sources</option>
        <option value="fresh">Fresh quotes</option>
        <option value="missing">No fresh quotes</option>
      </select>
    </div>
  );
}

function SourcesTable({ visible, data }) {
  return (
    <div className="ops-table-scroll">
      <table className="ops-table">
        <thead>
          <tr>
            <th>Sportsbook</th>
            <th>Coverage</th>
            <th>Quotes</th>
            <th>Last observed</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((book) => (
            <SourceRow key={book.bookmaker} book={book} />
          ))}
        </tbody>
      </table>
      {!visible.length && (
        <p className="ops-empty">
          {data
            ? "No sportsbooks match these filters."
            : "Source coverage is unavailable."}
        </p>
      )}
    </div>
  );
}

function SourceRow({ book }) {
  return (
    <tr>
      <td>
        <span className="ops-book-icon">
          <Globe2 size={15} />
        </span>
        <strong>{book.name}</strong>
      </td>
      <td>
        <span className={`ops-status ${book.fresh_quotes ? "is-fresh" : ""}`}>
          <i />
          {book.fresh_quotes ? `${book.fixtures} fixtures` : "No fresh quotes"}
        </span>
      </td>
      <td className="ops-numeric">{count(book.fresh_quotes)}</td>
      <td className="ops-source-time">{timestamp(book.latest_quote_at)}</td>
    </tr>
  );
}

function filteredSources(data, search, filter) {
  if (!data) return [];
  return data.bookmakers.filter((book) => {
    const match = book.name.toLowerCase().includes(search.toLowerCase());
    const states = {
      all: true,
      fresh: book.fresh_quotes > 0,
      missing: book.fresh_quotes === 0,
    };
    return match && states[filter];
  });
}

function PaperStudy({ study }) {
  return (
    <article className="ops-study">
      <div className="ops-study-title">
        <FlaskConical size={18} />
        <h3 title={study.candidate_id}>Candidate {study.candidate_id}</h3>
        <span className="ops-tag">{readable(study.assessment_status)}</span>
      </div>
      <div className="ops-study-counts">
        <div>
          <strong>
            {count(study.settled_selections)}{" "}
            <small>/ {count(study.protocol.minimum_selections)}</small>
          </strong>
          <span>settled selections</span>
        </div>
        <div>
          <strong>
            {count(study.fixture_days)}{" "}
            <small>/ {count(study.protocol.minimum_fixture_days)}</small>
          </strong>
          <span>fixture days</span>
        </div>
      </div>
      <progress
        aria-label={`Settled selections for ${study.candidate_id}`}
        value={study.settled_selections}
        max={study.protocol.minimum_selections}
      />
      <div className="ops-study-facts">
        <span>{count(study.pending_selections)} pending selections</span>
        <span>{count(study.batch_count)} batches</span>
      </div>
      <dl className="ops-roi">
        <div>
          <dt>Settled paper ROI</dt>
          <dd>{percent(study.roi)}</dd>
        </div>
        <div>
          <dt>Stressed paper ROI</dt>
          <dd>{percent(study.stressed_roi)}</dd>
        </div>
      </dl>
    </article>
  );
}

export default function OperationsDashboard() {
  const operations = useQuery({
    queryKey: ["admin-operations"],
    queryFn: ({ signal }) => predictionService.getOperations(signal),
    refetchInterval: 60000,
    retry: 1,
  });
  const paper = useQuery({
    queryKey: ["paper-trials"],
    queryFn: ({ signal }) => predictionService.getPaperTrials(signal),
    refetchInterval: 60000,
    retry: 1,
  });
  const data = operations.data;
  const summary = data?.summary;
  const studies = modelStudies(paper.data);
  return (
    <div className="ops-dashboard">
      <OverviewHeader operations={operations} paper={paper} />
      <DataNotice query={operations} label="operations" />
      <OverviewMetrics data={data} paper={paper.data} studies={studies} />
      <Collector data={data} />
      <div className="ops-main-grid">
        <div className="ops-main-column">
          <LeagueCoverage data={data} />
          <SourceCoverage data={data} />
        </div>
        <aside className="ops-side-column">
          <OutcomeCoverage summary={summary} />
          <PaperStudies studies={studies} query={paper} />
          <CollectionReceipt receipt={data?.latest_collection} />
        </aside>
      </div>
      <OverviewFooter />
    </div>
  );
}
