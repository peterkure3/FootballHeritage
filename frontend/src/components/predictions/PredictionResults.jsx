import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { predictionService } from "../../services/predictionService";
import Pagination from "./Pagination";
import QueryState from "./QueryState";
import EvidenceTable from "./EvidenceTable";
import { publicSnapshot } from "../../utils/publicSnapshot.mjs";

const date = (value) =>
  value ? new Date(value).toLocaleString() : "Unavailable";
const metric = (value, suffix = "") =>
  typeof value === "number" ? `${value.toFixed(2)}${suffix}` : "Unavailable";

function PerformanceSummary({ data }) {
  return (
    <>
      <div className="pd-stat-grid">
        {[
          ["Pre-kickoff accuracy", metric(data.overall_accuracy, "%")],
          ["Eligible fixtures", data.total_predictions],
          ["Log loss", metric(data.log_loss)],
          ["Brier score", metric(data.brier_score)],
        ].map(([label, value]) => (
          <div className="pd-stat" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <p className="pd-notice">
        {data.evidence_note} Missing kickoff dates:{" "}
        {data.excluded.unknown_kickoff +
          data.excluded.unknown_kickoff_outside_date_window}
        . No valid pre-kickoff prediction in this window:{" "}
        {data.excluded.no_valid_pre_kickoff}.
      </p>
      <p className="pd-muted">
        Sample: {date(data.sample_start)} — {date(data.sample_end)}. Lower log
        loss and Brier score indicate better probability estimates. Bookmaker
        baseline and calibration are unavailable for this sample.
      </p>
      <div className="pd-league-grid">
        {data.by_league.map((league) => (
          <div key={league.league}>
            <span>{league.league}</span>
            <strong>{metric(league.accuracy_pct, "%")}</strong>
            <small>
              {league.correct} / {league.total} correct
            </small>
          </div>
        ))}
      </div>
    </>
  );
}

function HistoryTable({ data }) {
  const result = { home_win: "Home", draw: "Draw", away_win: "Away" };
  return (
    <EvidenceTable
      headers={[
        "Fixture / kickoff",
        "Model probabilities",
        "Prediction",
        "Result",
        "Model / generated",
      ]}
    >
      {data.predictions.map((row) => (
        <tr key={`${row.match_id}-${row.model_version}`}>
          <td>
            {row.home_team} vs {row.away_team}
            <small>
              {row.competition} · {date(row.match_date)}
            </small>
          </td>
          <td>
            H {metric(row.home_prob * 100, "%")}
            <small>
              D {metric(row.draw_prob * 100, "%")} · A{" "}
              {metric(row.away_prob * 100, "%")}
            </small>
          </td>
          <td>{result[row.predicted_winner]}</td>
          <td>
            <span
              className={`pd-badge ${row.is_correct ? "pd-badge-green" : ""}`}
            >
              {row.is_correct ? "Correct" : "Incorrect"}
            </span>
            <small>
              {result[row.actual_result]} · {row.home_score ?? "–"} :{" "}
              {row.away_score ?? "–"}
            </small>
          </td>
          <td>
            v{row.model_version}
            <small>{date(row.prediction_created_at)}</small>
          </td>
        </tr>
      ))}
    </EvidenceTable>
  );
}

function activePeriod(filters) {
  return filters.start_date || filters.end_date ? "custom" : filters.days;
}
function HistoryFilters({ filters, setFilters, setPaging, versions }) {
  function filter(key, value) {
    setFilters((previous) => ({ ...previous, [key]: value }));
    setPaging((previous) => ({ ...previous, page: 1 }));
  }
  return (
    <div className="pd-filters pd-history-filters">
      <label>
        Competition
        <input
          value={filters.league}
          placeholder="Exact competition name"
          onChange={(event) => filter("league", event.target.value)}
        />
      </label>
      <label>
        Model version
        <select
          value={filters.model_version}
          onChange={(event) => filter("model_version", event.target.value)}
        >
          <option value="">Latest eligible per fixture</option>
          {versions.map((version) => (
            <option key={version.version} value={version.version}>
              v{version.version}
            </option>
          ))}
        </select>
      </label>
      <label>
        Period
        <select
          value={activePeriod(filters)}
          onChange={(event) => {
            setFilters((previous) => ({
              ...previous,
              days: event.target.value,
              start_date: "",
              end_date: "",
            }));
            setPaging((previous) => ({ ...previous, page: 1 }));
          }}
        >
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
          <option value="">All dated history</option>
          <option value="custom" disabled>
            Custom dates
          </option>
        </select>
      </label>
      <label>
        From (UTC)
        <input
          type="date"
          value={filters.start_date}
          onChange={(event) => filter("start_date", event.target.value)}
        />
      </label>
      <label>
        Through (UTC)
        <input
          type="date"
          value={filters.end_date}
          onChange={(event) => filter("end_date", event.target.value)}
        />
      </label>
    </div>
  );
}
function HistoryResults({ data, paging, setPaging, busy }) {
  return (
    <>
      <p className="pd-muted">
        {data.total_count} matching fixtures · {data.correct_count} correct.
        Correctness filters apply to this table; the performance summary keeps
        the complete selected sample.
      </p>
      {data.predictions.length ? (
        <HistoryTable data={data} />
      ) : (
        <div className="pd-empty">
          No eligible settled predictions match these filters.
        </div>
      )}
      <Pagination
        page={paging.page}
        total={data.total_count}
        pageSize={10}
        busy={busy}
        onPage={(page) => setPaging((previous) => ({ ...previous, page }))}
      />
    </>
  );
}

export default function PredictionResults() {
  const [filters, setFilters] = useState({
    league: "",
    days: 30,
    start_date: "",
    end_date: "",
    model_version: "",
  });
  const [paging, setPaging] = useState({ page: 1, result_filter: "all" });
  const feed = useQuery({
    queryKey: ["prediction-history", filters, paging],
    ...publicSnapshot(["prediction-history", filters, paging], ({ signal }) =>
      predictionService.getHistory(
        { ...filters, ...paging, page_size: 10 },
        signal,
      )),
    retry: 1,
  });
  const versions = useQuery({
    queryKey: ["prediction-versions"],
    ...publicSnapshot(["prediction-versions"], ({ signal }) => predictionService.getVersions(signal)),
    enabled: !feed.isPending,
    retry: 1,
  });
  const summary = useQuery({
    queryKey: ["prediction-accuracy", filters],
    ...publicSnapshot(["prediction-accuracy", filters], ({ signal }) => predictionService.getAccuracy(filters, signal)),
    enabled: !feed.isPending,
    retry: 1,
  });
  return (
    <section aria-label="Settled prediction performance">
      <div className="pd-section-heading">
        <h2>Measured, with a clear denominator.</h2>
        <p>
          One valid prediction per fixture, generated before kickoff. Model and
          date filters apply to both the summary and history.
        </p>
      </div>
      <HistoryFilters
        filters={filters}
        setFilters={setFilters}
        setPaging={setPaging}
        versions={versions.data?.versions ?? []}
      />
      <QueryState
        query={summary}
        loading="Loading performance evidence…"
        failure="Performance unavailable"
        showRefresh
      >
        {(data) => <PerformanceSummary data={data} />}
      </QueryState>
      <div className="pd-toolbar">
        <h3>Settled history</h3>
        <label className="pd-filter-label">
          Result
          <select
            value={paging.result_filter}
            onChange={(event) =>
              setPaging({ page: 1, result_filter: event.target.value })
            }
          >
            <option value="all">All results</option>
            <option value="correct">Correct only</option>
            <option value="incorrect">Incorrect only</option>
          </select>
        </label>
      </div>
      <QueryState
        query={feed}
        loading="Loading settled history…"
        failure="History unavailable"
        showRefresh
      >
        {(data) => (
          <HistoryResults
            data={data}
            paging={paging}
            setPaging={setPaging}
            busy={feed.isFetching}
          />
        )}
      </QueryState>
    </section>
  );
}
