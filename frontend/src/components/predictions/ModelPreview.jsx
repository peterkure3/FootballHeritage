import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import QueryState from "./QueryState";
import TeamSearch from "./TeamSearch";
import { FlaskConical } from "lucide-react";
import { predictionService } from "../../services/predictionService";

const profiles = {
  football: ["Soccer", ""],
  basketball: ["NBA", "basketball_nba"],
  wnba: ["WNBA", "basketball_wnba"],
  ncaab: ["NCAA basketball · men", "basketball_ncaab"],
  ncaabw: ["NCAA basketball · women", "basketball_wncaab"],
  nfl: ["NFL", "americanfootball_nfl"],
  ncaaf: ["College football", "americanfootball_ncaaf"],
};
function PreviewResult({ result }) {
  const labels = {
    home_win: result.home_team,
    away_win: result.away_team,
    draw: "Draw",
  };
  return (
    <article className="pd-forecast">
      <div className="pd-card-heading">
        <h3>
          {result.home_team} vs {result.away_team}
        </h3>
        <span className="pd-badge">Candidate preview · inactive</span>
      </div>
      <div className="pd-probabilities">
        {Object.entries(result.probabilities).map(([key, value]) => (
          <div className="pd-outcome" key={key}>
            <span>{labels[key] || key}</span>
            <strong>{(value * 100).toFixed(1)}%</strong>
            <div className="pd-probability-track">
              <div style={{ width: `${value * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
      <dl className="pd-preview-details">
        <dt>Model</dt>
        <dd>{result.model_version}</dd>
        <dt>History through</dt>
        <dd>{new Date(result.history_through).toLocaleString()}</dd>
        <dt>Kickoff</dt>
        <dd>{new Date(result.kickoff).toLocaleString()}</dd>
        <dt>Settlement</dt>
        <dd>{result.settlement_rule.replaceAll("_", " ").toLowerCase()}</dd>
        <dt>Probability basis</dt>
        <dd>{result.probability_basis.replaceAll("_", " ").toLowerCase()}</dd>
        <dt>Bookmaker features</dt>
        <dd>{result.market_features_used ? "Used" : "Not used"}</dd>
      </dl>
      <p className="pd-muted">
        Hypothetical matchup using saved training history. Current rosters and
        injuries are not included. No bookmaker quote or estimated betting value
        is attached to this preview.
      </p>
    </article>
  );
}
function modelChoices(runs) {
  return runs.flatMap((run) =>
    Object.entries(run.sports)
      .filter(
        ([sport, model]) => profiles[sport] && model.status === "candidate",
      )
      .map(([sport]) => ({
        id: `${run.candidate_id}|${sport}`,
        candidate: run.candidate_id,
        sport,
        label: profiles[sport][0],
      })),
  );
}
function PreviewAction({ selected, pending }) {
  return (
    <button className="pd-button" disabled={!selected || pending}>
      {pending ? "Generating preview…" : "Preview matchup"}
    </button>
  );
}
function teamStatus(selected, query, teams) {
  if (!selected) return "Choose a trained model to load its teams.";
  if (query.isPending) return "Loading teams…";
  if (query.isError) return "Could not load teams.";
  if (teams.length === 0) return "No teams are available for this candidate.";
  return "Type part of a team name or browse the dropdown. Select a different team for each side.";
}
function PreviewForm({ choices }) {
  const preview = useMutation({
    mutationFn: (body) => predictionService.previewSportModel(body),
  });
  const [form, setForm] = useState({
    selection: choices[0]?.id || "",
    home: "",
    away: "",
    kickoff: "",
    neutral: false,
  });
  const selected = choices.find((choice) => choice.id === form.selection);
  const teamQuery = useQuery({
    queryKey: ["sport-model-teams", form.selection],
    queryFn: ({ signal }) => predictionService.getSportModelTeams({
      candidate_id: selected.candidate,
      sport: selected.sport,
      league: profiles[selected.sport][1] || null,
    }, signal),
    enabled: Boolean(selected),
    staleTime: 300000,
    retry: 1,
  });
  const teams = teamQuery.data?.teams || [];
  const validTeams = teams.includes(form.home) && teams.includes(form.away) && form.home !== form.away;
  function update(key, value) {
    setForm((previous) => key === "selection"
      ? { ...previous, selection: value, home: "", away: "", neutral: false }
      : { ...previous, [key]: value });
    preview.reset();
  }
  function submit(event) {
    event.preventDefault();
    if (!selected || !validTeams || teamQuery.isError) return;
    preview.mutate({
      candidate_id: selected.candidate,
      sport: selected.sport,
      league: profiles[selected.sport][1] || null,
      home_team: form.home.trim(),
      away_team: form.away.trim(),
      kickoff: new Date(form.kickoff).toISOString(),
      neutral_site: form.neutral,
    });
  }
  return (
    <>
      <form className="pd-preview-form" onSubmit={submit}>
        <div className="pd-filters">
          <label>
            Sport / candidate
            <select
              required
              value={form.selection}
              onChange={(event) => update("selection", event.target.value)}
            >
              <option value="">Choose a trained model</option>
              {choices.map((choice) => (
                <option value={choice.id} key={choice.id}>
                  {choice.label} · {choice.candidate}
                </option>
              ))}
            </select>
          </label>
          <TeamSearch key={`home-${form.selection}`} label="Home team" value={form.home}
            onChange={(value) => update("home", value)} teams={teams} excluded={form.away}
            disabled={!selected} loading={teamQuery.isPending} unavailable={teamQuery.isError} />
          <TeamSearch key={`away-${form.selection}`} label="Away team" value={form.away}
            onChange={(value) => update("away", value)} teams={teams} excluded={form.home}
            disabled={!selected} loading={teamQuery.isPending} unavailable={teamQuery.isError} />
          <label>
            Kickoff (your local time)
            <input
              required
              type="datetime-local"
              value={form.kickoff}
              onChange={(event) => update("kickoff", event.target.value)}
            />
          </label>
        </div>
        <div className="pd-muted" role="status">
          {teamStatus(selected, teamQuery, teams)}
        </div>
        {teamQuery.isError && <button type="button" className="pd-button pd-button-outline"
          onClick={() => teamQuery.refetch()}>Retry team list</button>}
        <label className="pd-checkbox">
          <input
            type="checkbox"
            checked={form.neutral}
            disabled={selected?.sport === "football"}
            onChange={(event) => update("neutral", event.target.checked)}
          />
          Neutral venue (supported by sport candidates)
        </label>
        <p className="pd-muted">
          Kickoff must be after the selected model's training date. Unknown
          teams are rejected. NFL probabilities are conditional on no final tie;
          ties void the market.
        </p>
        <PreviewAction selected={selected && validTeams && !teamQuery.isError} pending={preview.isPending} />
      </form>
      {preview.error && (
        <p className="pd-notice" role="alert">
          Could not preview matchup: {preview.error.message}
        </p>
      )}
      {preview.data && <PreviewResult result={preview.data} />}
    </>
  );
}
function CatalogContent({ data }) {
  const choices = modelChoices(data.runs);
  if (choices.length === 0)
    return (
      <p className="pd-empty">No trained sport candidates are available.</p>
    );
  return <PreviewForm choices={choices} />;
}
export default function ModelPreview() {
  const catalog = useQuery({
    queryKey: ["sport-model-catalog"],
    queryFn: ({ signal }) => predictionService.getSportModels(signal),
    retry: 1,
  });
  return (
    <section aria-label="Candidate sport models">
      <div className="pd-section-heading">
        <p className="pd-eyebrow">
          <FlaskConical size={15} /> MODEL LAB
        </p>
        <h2>Explore a matchup. Keep the evidence in view.</h2>
        <p>
          Independent models for NBA, WNBA, NCAA basketball, NFL, college
          football and soccer. Candidates are available for inspection and do
          not replace the active model.
        </p>
      </div>
      <QueryState
        query={catalog}
        loading="Loading model catalog…"
        failure="Model catalog unavailable"
      >
        {(data) => <CatalogContent data={data} />}
      </QueryState>
    </section>
  );
}
