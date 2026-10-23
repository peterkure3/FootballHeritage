import { useQuery } from "@tanstack/react-query";
import { predictionService } from "../../services/predictionService";
import QueryState from "./QueryState";
import EvidenceTable from "./EvidenceTable";

const percent = (value) => value == null ? "Pending" : `${(value * 100).toFixed(2)}%`;
const outcome = { home_win: "Home win", draw: "Draw", away_win: "Away win" };
const number = (value) => value == null ? "—" : value.toFixed(2);
const collectionSteps = {
  "scripts.refresh_trial_fixtures": "Fixture refresh",
  "scripts.refresh_regional_pipeline": "Price collection and settlement",
  "scripts.assess_paper_trial": "Formal assessment",
};

function selectionLabel(row) {
  return outcome[row.selected_outcome] ?? (row.status === "recorded_pregame" ? "No selection" : "Excluded");
}

function settlementLabel(row) {
  const reason = row.reason ? `: ${row.reason}` : "";
  const result = row.result ? ` · ${outcome[row.result]}` : "";
  return `${row.settlement_status}${reason}${result}`;
}

function TrialRow({ row }) {
  const evidence = row.selection_evidence;
  return <tr>
    <td>{row.home} – {row.away}<br /><small>{new Date(row.kickoff).toLocaleString()}</small></td>
    <td>{selectionLabel(row)}</td>
    <td>{number(evidence?.decimal_odds)}</td>
    <td>{evidence ? percent(evidence.estimated_ev) : "—"}</td>
    <td>{settlementLabel(row)}</td>
    <td>{number(row.profit_units)}</td>
  </tr>;
}

function TrialEvidence({ trial }) {
  const manual = isManual(trial);
  return <article className="pd-empty">
    <h3>{manual ? "Manual paper selection" : `Soccer candidate ${trial.candidate_id}`}</h3>
    <p>{trial.settled_selections} settled selections · {trial.pending_forecasts} pending forecasts · Paper ROI: {percent(trial.roi)} · Stressed ROI: {percent(trial.stressed_roi)}</p>
    <p>{trial.evidence_note}</p>
    <EvidenceTable headers={["Fixture", "Paper selection", "Quote", "Estimated EV", "Settlement", "Profit (units)"]}>
      {trial.fixtures.map((row) => <TrialRow row={row} key={`${row.home}-${row.away}-${row.kickoff}`} />)}
    </EvidenceTable>
    {manual ? <p>Bookmaker: {trial.fixtures[0]?.bookmaker}. User-selected one-unit paper pick. Settles automatically against the official regulation-time result; excluded from the frozen model trial.</p> : <p>Bookmaker: Bovada. Fixed one-unit paper policy; 5% minimum estimated EV after a 2% payout reduction. Regional quote comparisons are separate from this trial.</p>}
  </article>;
}

function TrialList({ trials }) {
  if (!trials.length) return <p>No prospective forecasts have been imported.</p>;
  return trials.map((trial) => <TrialEvidence trial={trial} key={trial.trial_sha256 ?? trial.candidate_id} />);
}

function StudyProgress({ study }) {
  return <article className="pd-empty" aria-label={`Study progress ${study.candidate_id}`}>
    <h3>Study progress — {study.candidate_id}</h3>
    <p>{study.settled_selections} / {study.protocol.minimum_selections} settled selections · {study.fixture_days} / {study.protocol.minimum_fixture_days} fixture days</p>
    <progress aria-label="Settled selection progress" value={study.settled_selections} max={study.protocol.minimum_selections} />
    <p>{study.pending_selections} pending selections · {study.batch_count} recorded batches · Combined paper ROI: {percent(study.roi)} · Stressed ROI: {percent(study.stressed_roi)}</p>
    <p>Assessment: {study.assessment_status.replaceAll("_", " ")}. Both sample targets and complete settlement through the assessment date are required.</p>
    <AssessmentResult assessment={study.assessment} />
    <p>Model and policy remain fixed. The first eligible cohort receives one formal assessment; later batches do not rerun that decision.</p>
  </article>;
}

function AssessmentResult({ assessment }) {
  if (!assessment?.stressed_roi_ci95) return null;
  const interval = assessment.stressed_roi_ci95;
  return <>
    <p>Frozen cohort: {assessment.selections} selections across {assessment.fixture_days} days. Stressed ROI 95% interval: {percent(interval[0])} to {percent(interval[1])}. Maximum stressed drawdown: {number(assessment.max_stressed_drawdown_units)} units.</p>
    {assessment.paper_evidence_passed && <p>Positive prospective paper evidence. Executable profit remains unverified.</p>}
  </>;
}

function CollectorHealth({ collector }) {
  return <>
    <p>Collector: {collectorOutcome(collector)}. Last successful run: {collectorSuccess(collector)}.</p>
    <CollectorFailure collector={collector} />
  </>;
}

function collectorOutcome(collector) {
  return collector?.outcome ?? "No run recorded";
}

function collectorSuccess(collector) {
  return collector?.last_success_at ? new Date(collector.last_success_at).toLocaleString() : "None recorded";
}

function CollectorFailure({ collector }) {
  const steps = collector?.failed_steps ?? [];
  return steps.length ? <p role="status">Collection needs attention: {steps.map((step) => collectionSteps[step] ?? "Collection step").join(", ")}.</p> : null;
}

function TrialDashboard({ data }) {
  return <>
    <CollectorHealth collector={data.collector} />
    {(data.studies ?? []).filter((study) => !isManual(study)).map((study) => <StudyProgress study={study} key={study.study_id} />)}
    <TrialList trials={data.trials} />
  </>;
}

function isManual(record) {
  return record.policy?.selection === "user_selected";
}

export default function PaperTrial() {
  const query = useQuery({
    queryKey: ["paper-trials"],
    queryFn: ({ signal }) => predictionService.getPaperTrials(signal),
    refetchInterval: 60000,
    retry: 1,
  });
  return <section aria-label="Prospective paper trials">
    <h2>Prospective paper trials</h2>
    <p>Forecasts saved before kickoff, checked against verified final results. Estimated EV is not demonstrated profit.</p>
    <QueryState query={query} loading="Loading paper trial evidence…" failure="Could not load paper trial evidence">
      {(data) => <TrialDashboard data={data} />}
    </QueryState>
  </section>;
}
