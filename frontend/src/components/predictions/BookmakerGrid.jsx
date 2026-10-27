import { useState } from "react";
import { Grid3X3, ShieldCheck } from "lucide-react";
import "./BookmakerGrid.css";

const outcomes = ["home_win", "draw", "away_win"];
const labels = ["1", "X", "2"];
const validProbability = (value) =>
  Number.isFinite(value) && value >= 0 && value <= 1;
const timestamp = (value) =>
  value ? new Date(value).toLocaleString() : "Not recorded";

function comparisonValue(fixture, quote, outcome, mode) {
  if (!quote?.fresh) return null;
  return {
    odds: quote.prices[outcome],
    probability: marketProbability(quote, outcome),
    ev: estimatedValue(modelProbability(fixture, outcome), quote.prices[outcome]),
  }[mode];
}

function marketProbability(quote, outcome) {
  return probabilityOrNull(quote.fair_probabilities?.[outcome]);
}

function modelProbability(fixture, outcome) {
  const prediction = fixture.prediction;
  if (!prediction || prediction.status !== "current") return null;
  return probabilityOrNull(prediction.probabilities?.[outcome]);
}

function probabilityOrNull(value) {
  return validProbability(value) ? value : null;
}

function estimatedValue(probability, price) {
  if (!validProbability(probability) || !Number.isFinite(price) || price <= 1)
    return null;
  return probability * price - 1;
}

function HeatCell({ value, ev = false, odds = false, title }) {
  if (!Number.isFinite(value))
    return (
      <td className="bc-cell bc-missing" title={title}>
        <div>—</div>
      </td>
    );
  const { strength, tone } = heatAppearance(value, ev, odds);
  return (
    <td className={`bc-cell bc-${tone}`} title={title}>
      <div
        style={{ "--heat-strength": strength }}
        className={strength >= 0.6 ? "bc-strong" : undefined}
      >
        <span>{formatValue(value, ev, odds)}</span>
      </div>
    </td>
  );
}

function heatAppearance(value, ev, odds) {
  if (odds) return { strength: 0, tone: "price" };
  return {
    strength: heatStrength(value, ev),
    tone: ev && value < 0 ? "negative" : "positive",
  };
}

function heatStrength(value, ev) {
  return Math.min(ev ? Math.abs(value) / 0.5 : value, 1);
}

function formatValue(value, ev, odds) {
  if (odds) return value.toFixed(2);
  return `${ev && value > 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
}

function modelDescription(prediction) {
  if (!prediction) return "Current prediction unavailable";
  return `${prediction.model_kind === "evaluated_league_candidate" ? "Evaluated league model" : "Model"} v${prediction.model_version} · Generated ${timestamp(prediction.generated_at)} · ${prediction.status}`;
}

function quoteDescription(quote, outcome) {
  if (!quote) return "Fresh complete quote unavailable";
  return `Decimal odds ${quote.prices[outcome] ?? "unavailable"} · Observed ${timestamp(quote.observed_at)}${quote.fresh ? "" : " · Fresh complete quote unavailable"}`;
}

function bookmakerLabel(book) {
  const [name, region] = book.split(":");
  const names = {
    ababet: "AbaBet",
    betpawa: "betPawa",
    bovada: "Bovada",
    fortebet: "Fortebet",
    sportpesa: "SportPesa",
  };
  return `${names[name] ?? name}${region ? ` · ${region}` : ""}`;
}

function FixtureRow({ fixture, books, mode }) {
  return (
    <tr>
      <th scope="row" className="bc-fixture">
        <span>{fixture.competition} · 1X2</span>
        <strong>
          {fixture.home_team} <i>vs</i> {fixture.away_team}
        </strong>
        <time dateTime={fixture.kickoff}>{timestamp(fixture.kickoff)}</time>
      </th>
      {outcomes.map((outcome) => {
        return (
          <HeatCell
            key={outcome}
            value={modelProbability(fixture, outcome)}
            title={`FootballHeritage · ${outcome.replaceAll("_", " ")} · ${modelDescription(fixture.prediction)}`}
          />
        );
      })}
      {books.map((book) => {
        const quote = fixture.market?.quotes?.find(
          (item) => item.bookmaker === book,
        );
        return outcomes.map((outcome) => (
          <HeatCell
            key={`${book}-${outcome}`}
            value={comparisonValue(fixture, quote, outcome, mode)}
            ev={mode === "ev"}
            odds={mode === "odds"}
            title={`${book} · ${outcome.replaceAll("_", " ")} · ${quoteDescription(quote, outcome)}`}
          />
        ));
      })}
    </tr>
  );
}

export default function BookmakerGrid({ fixtures, bookmakers = [] }) {
  const [mode, setMode] = useState("probability");
  const currentBooks = new Set(
    fixtures.flatMap((fixture) =>
      (fixture.market?.quotes ?? [])
        .filter((quote) => quote.fresh)
        .map((quote) => quote.bookmaker),
    ),
  );
  const books = [
    ...new Set(
      bookmakers.length
        ? bookmakers.map((book) => book.bookmaker)
        : fixtures.flatMap((fixture) =>
            (fixture.market?.quotes ?? []).map((quote) => quote.bookmaker),
          ),
    ),
  ].sort((a, b) => Number(currentBooks.has(b)) - Number(currentBooks.has(a)) || a.localeCompare(b));
  const names = new Map(bookmakers.map((book) => [book.bookmaker, book.name]));
  const availability = (book) =>
    currentBooks.has(book)
      ? "Fresh prices linked"
      : fixtures.some((fixture) =>
            fixture.market?.quotes?.some((quote) => quote.bookmaker === book),
          )
        ? "Prices stale or incomplete"
        : "No linked prices";
  const view = {
    odds: {
      label: "Decimal odds",
      legend: "Captured decimal price",
      caption: "FootballHeritage probabilities and captured bookmaker decimal odds",
      explanation:
        "Decimal odds include the returned stake. Prices are captured public offers; account availability, taxes and final bet-slip payouts may differ.",
    },
    probability: {
      label: "Market probability",
      legend: "Higher probability",
      caption:
        "FootballHeritage model probabilities and margin-removed bookmaker implied probabilities",
      explanation:
        "Bookmaker probabilities remove the margin from each complete 1X2 market: (1 / outcome odds) divided by the sum of all three implied probabilities.",
    },
    ev: {
      label: "Estimated EV",
      legend: "Positive estimated EV",
      caption:
        "FootballHeritage probabilities and estimated EV at each bookmaker's decimal odds",
      explanation:
        "Bookmaker EV = (model probability × decimal odds − 1) × 100%. This is gross EV before tax and fees. +5% means an estimated +0.05 units per unit staked. FootballHeritage stays as the model probability baseline.",
    },
  }[mode];
  return (
    <section className="bc-panel" aria-labelledby="bc-title">
      <header className="bc-heading">
        <div>
          <p className="pd-eyebrow">
            <Grid3X3 size={14} /> SIDE BY SIDE
          </p>
          <h2 id="bc-title">One fixture. Every perspective.</h2>
          <p className="bc-intro">
            FootballHeritage first. All requested bookmakers stay visible across
            competitions and pages, with populated sources first. {currentBooks.size} of {books.length}{" "}
            sources have fresh prices for these fixtures.
          </p>
        </div>
        <label className="pd-filter-label">
          Comparison metric
          <select
            value={mode}
            onChange={(event) => setMode(event.target.value)}
          >
            <option value="probability">Outcome probabilities</option>
            <option value="odds">Decimal odds</option>
            <option value="ev">Estimated EV</option>
          </select>
        </label>
      </header>
      <div className="bc-legend">
        <span>
          <ShieldCheck size={14} /> FootballHeritage · model probabilities
        </span>
        <span>
          <b className="bc-swatch" /> {view.legend}
        </span>
        {mode === "ev" && (
          <span>
            <b className="bc-swatch bc-swatch-negative" /> Negative estimated EV
          </span>
        )}
        <span>1 Home · X Draw · 2 Away</span>
      </div>
      <div
        className="bc-scroll"
        role="region"
        aria-label="Bookmaker comparison grid"
        tabIndex={0}
      >
        <table className="bc-table">
          <caption className="bc-caption">{view.caption}</caption>
          <thead>
            <tr>
              <th
                rowSpan={2}
                scope="col"
                className="bc-head bc-fixture bc-corner"
              >
                Fixture <small>Regulation time · local kickoff</small>
              </th>
              <th colSpan={3} scope="colgroup" className="bc-head bc-brand">
                <span>FH</span> FootballHeritage<small>Model probability</small>
              </th>
              {books.map((book) => (
                <th
                  key={book}
                  colSpan={3}
                  scope="colgroup"
                  className="bc-head bc-book"
                >
                  {names.get(book) ?? bookmakerLabel(book)}
                  <small>{view.label}</small>
                  <small>{availability(book)}</small>
                  <small>
                    {fixtures.filter((fixture) => fixture.market?.quotes?.some((quote) => quote.bookmaker === book && quote.fresh)).length}
                    /{fixtures.length} fixtures with fresh prices
                  </small>
                </th>
              ))}
            </tr>
            <tr>
              {["FootballHeritage", ...books].flatMap((book) =>
                labels.map((label) => (
                  <th
                    key={`${book}-${label}`}
                    scope="col"
                    className="bc-head bc-outcome"
                  >
                    {label}
                  </th>
                )),
              )}
            </tr>
          </thead>
          <tbody>
            {fixtures.map((fixture) => (
              <FixtureRow
                key={fixture.match_id}
                fixture={fixture}
                books={books}
                mode={mode}
              />
            ))}
          </tbody>
        </table>
      </div>
      <footer className="bc-footnote">
        <p>{view.explanation}</p>
        <p>
          No linked prices means we have not collected and matched a current
          quote for these fixtures. It does not mean the bookmaker does not
          offer them.
        </p>
        <p>
          — means a current prediction or fresh complete market is unavailable.
          Freshness follows the 24-hour dashboard policy. Hover over a cell for
          its price and source time.
        </p>
        {books.length === 0 && (
          <p>No bookmaker prices are linked to these fixtures yet.</p>
        )}
      </footer>
    </section>
  );
}
