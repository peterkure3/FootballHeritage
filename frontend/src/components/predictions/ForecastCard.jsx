import { Clock3, ArrowUpRight } from "lucide-react";
import EvidenceTable from "./EvidenceTable";
const percent = (value) =>
  typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "Unavailable";
const date = (value) =>
  value
    ? new Date(value).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Not recorded";
const statuses = {
  current: "Active model",
  stale: "Stale prediction",
  invalid: "Invalid prediction",
};

function Outcomes({ prediction, labels }) {
  if (!prediction?.probabilities)
    return (
      <p className="pd-notice">
        {prediction
          ? "The stored probabilities could not be validated."
          : "The active model has not generated a prediction for this fixture."}
      </p>
    );
  return (
    <div className="pd-probabilities" aria-label="Outcome probabilities">
      {Object.entries(prediction.probabilities).map(([key, value]) => (
        <div
          key={key}
          className={
            prediction.winner === key ? "pd-outcome pd-favorite" : "pd-outcome"
          }
        >
          <span>{labels[key] || key}</span>
          <strong>{percent(value)}</strong>
          <div className="pd-probability-track">
            <div style={{ width: `${value * 100}%` }} />
          </div>
          <small>
            {prediction.winner === key ? "Most likely" : "Model probability"}
          </small>
        </div>
      ))}
    </div>
  );
}

function MarketNotice({ market, status }) {
  const messages = {
    missing:
      "Market unavailable. No bookmaker quotes are linked to this fixture.",
    unverified_or_stale:
      "Quotes are stale, incomplete, or have no observation time. Estimated value is unavailable.",
  };
  const message =
    messages[market.state] ||
    (status !== "current"
      ? "Current quotes are available. A fresh prediction is required to estimate value."
      : "");
  if (!message) return null;
  return <p className="pd-muted">{message}</p>;
}
function signedEv(value) {
  return `${value > 0 ? "+" : ""}${value.toFixed(3)}`;
}
function difference(value) {
  return typeof value === "number" ? `${value.toFixed(1)} pp` : "Unavailable";
}
function MarketPrices({ comparisons, labels }) {
  if (!comparisons.length) return null;
  return (
    <EvidenceTable
      headers={[
        "Outcome / bookmaker",
        "Odds",
        "Market fair",
        "Model − market",
        "Est. EV / unit",
      ]}
    >
      {comparisons.map((item) => (
        <tr key={item.outcome}>
          <td>
            {labels[item.outcome]}
            <small>
              {item.bookmaker} · {date(item.observed_at)}
            </small>
          </td>
          <td>{item.decimal_odds.toFixed(2)}</td>
          <td>{percent(item.consensus_prob)}</td>
          <td>{difference(item.consensus_difference_pp)}</td>
          <td className={item.estimated_ev_units > 0 ? "pd-positive" : ""}>
            {signedEv(item.estimated_ev_units)}
          </td>
        </tr>
      ))}
    </EvidenceTable>
  );
}
function ValueNote({ comparisons, labels }) {
  const best = [...comparisons].sort(
    (a, b) => b.estimated_ev_units - a.estimated_ev_units,
  )[0];
  if (!best) return null;
  return (
    <p className="pd-value-note">
      <ArrowUpRight size={15} />
      {best.estimated_ev_units > 0
        ? `Highest estimated value: ${labels[best.outcome]}.`
        : "No positive estimated value at the available prices."}
    </p>
  );
}
function Market({ market, labels, status }) {
  return (
    <div className="pd-market">
      <div className="pd-card-heading">
        <h3>Bookmaker comparison</h3>
        <span className="pd-badge">Decimal odds</span>
      </div>
      <MarketNotice market={market} status={status} />
      <MarketPrices comparisons={market.comparisons} labels={labels} />
      <ValueNote comparisons={market.comparisons} labels={labels} />
    </div>
  );
}

function ModelEvidence({ prediction }) {
  if (!prediction?.test_metrics) return null;
  return <>
    <dt>Held-out evaluation</dt>
    <dd>{prediction.test_metrics.samples} games · {percent(prediction.test_metrics.accuracy)} accuracy</dd>
    <dt>Model inputs</dt>
    <dd>League match history; bookmaker prices excluded</dd>
  </>;
}

function modelStatus(model) {
  if (model.status === "current" && model.model_kind === "evaluated_league_candidate")
    return "Evaluated league model";
  return statuses[model.status] || "Prediction pending";
}

function Provenance({ prediction, market, labels }) {
  const model = prediction || {};
  return (
    <details className="pd-details">
      <summary>Model & source details</summary>
      <dl>
        <dt>Model version</dt>
        <dd>{model.model_version || "Unavailable"}</dd>
        <dt>Prediction generated</dt>
        <dd>{date(model.generated_at)}</dd>
        <dt>Feature cutoff</dt>
        <dd>{date(model.feature_cutoff)}</dd>
        <ModelEvidence prediction={model} />
        <dt>Market settlement</dt>
        <dd>Regulation time · home / draw / away</dd>
        <dt>Freshness policy</dt>
        <dd>Prediction and complete bookmaker quotes within 24 hours</dd>
      </dl>
      <p className="pd-muted">
        Market fair probabilities remove margin within each bookmaker, then
        average equally across current books. EV uses the actual price shown.
        Neither proves bookmaker advantage.
      </p>
      {market.quotes.map((quote) => (
        <p className="pd-muted" key={quote.bookmaker}>
          {quote.bookmaker}:{" "}
          {Object.entries(quote.prices)
            .map(([key, price]) => `${labels[key]} ${price ?? "unavailable"}`)
            .join(" · ")}
          . Observed: {date(quote.observed_at)}.
        </p>
      ))}
    </details>
  );
}

export default function ForecastCard({ fixture }) {
  const { prediction, market } = fixture;
  const model = prediction || {};
  const labels = {
    home_win: fixture.home_team,
    draw: "Draw",
    away_win: fixture.away_team,
  };
  return (
    <article className="pd-forecast">
      <header className="pd-card-heading">
        <span className="pd-eyebrow">{fixture.competition}</span>
        <span
          className={`pd-badge ${model.status === "current" ? "pd-badge-green" : ""}`}
        >
          {modelStatus(model)}
        </span>
      </header>
      <h2>
        {fixture.home_team}
        <span className="pd-versus">vs</span>
        {fixture.away_team}
      </h2>
      <p className="pd-muted pd-kickoff">
        <Clock3 size={14} />
        {date(fixture.kickoff)} · local time
      </p>
      <Outcomes prediction={prediction} labels={labels} />
      <Market market={market} labels={labels} status={model.status} />
      <Provenance prediction={prediction} market={market} labels={labels} />
    </article>
  );
}
