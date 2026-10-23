import { array, record, text, number, formatDate, type RecordData } from './services';
import { percent, decimalPrice, selectionName } from './bettingIntelFormat';

type CellProps = { row: RecordData; view: string };
export function ModelLabel({ row }: { row: RecordData }) {
  const candidate = row.status === 'candidate_preview' || row.model_status === 'candidate_preview';
  return <span className="bi-badge">{candidate ? 'Experimental candidate' : 'Active model'}</span>;
}
function FixtureLabel({ row }: { row: RecordData }) {
  return <><strong>{text(row.home_team)} <span className="bi-versus">vs</span> {text(row.away_team)}</strong>
    <small>{text(row.competition)} · {formatDate(text(row.kickoff))}</small></>;
}
function MarketLabel({ row }: { row: RecordData }) {
  if (!row.market) return null;
  return <small>{text(row.market).replaceAll('_',' ')}{row.player ? ` · ${text(row.player)}` : ''}{number(row.line) !== null ? ` · ${row.line}` : ''}</small>;
}
function Outcomes({ row }: { row: RecordData }) {
  return <>{Object.entries(record(row.probabilities)).map(([key,p]) => <small key={key}>{selectionName(row,key)} <b>{percent(p)}</b></small>)}</>;
}
function FairOutcomes({ row }: { row: RecordData }) {
  const legs=record(row.legs);
  return <>{Object.entries(record(row.fair_probabilities)).map(([key,p]) => <small key={key}>{selectionName(row,key)} <b>{percent(p)}</b> · {decimalPrice(record(legs[key]).decimal_odds)}</small>)}</>;
}
function ArbLegs({ row }: { row: RecordData }) {
  return <>{array(row.legs).map(record).map((leg,i) => <small key={i}>{selectionName(row,leg.selection)} · {text(leg.bookmaker)} @ {decimalPrice(leg.decimal_odds)}<br />Quote: {formatDate(text(leg.observed_at))}</small>)}</>;
}
function SelectionCell({ row, view }: CellProps) {
  if (view === 'predictions') return <Outcomes row={row} />;
  if (view === 'arbitrage') return <ArbLegs row={row} />;
  if (row.fair_probabilities) return <FairOutcomes row={row} />;
  return <><strong>{selectionName(row,row.selection)}</strong><small>{percent(row.probability)} probability</small></>;
}
function ArbPrice({ row }: { row: RecordData }) {
  return <><strong>{percent(row.gross_roi)} gross ROI</strong><small>Per 100 reference units:</small>
    {array(row.legs).map(record).map((leg,i) => <small key={i}>{selectionName(row,leg.selection)}: {number(leg.reference_stake)?.toFixed(2)}</small>)}</>;
}
function FairPrices({ row }: { row: RecordData }) {
  return <><strong>{percent(row.overround)} book margin</strong>{Object.entries(record(row.fair_probabilities)).map(([key,p]) =>
    <small key={key}>Fair {selectionName(row,key)}: {(1/Number(p)).toFixed(3)}</small>)}</>;
}
function PriceCell({ row, view }: CellProps) {
  if (view === 'arbitrage') return <ArbPrice row={row} />;
  if (row.fair_probabilities) return <FairPrices row={row} />;
  if (view === 'predictions') return <ModelLabel row={row} />;
  return <ValuePrice row={row} />;
}
function ValuePrice({ row }: { row: RecordData }) {
  return <><strong>{decimalPrice(row.decimal_odds)}</strong>{number(row.ev_pct) !== null && <small className="bi-positive">{percent(row.ev_pct)} estimated EV</small>}</>;
}
function ModelEvidence({ row }: { row: RecordData }) {
  return <><ModelLabel row={row} /><small>{text(row.model_version)}</small><small>{formatDate(text(row.generated_at))}</small>
    {row.market_features_used === false && <small>History model; no market inputs</small>}</>;
}
function BookEvidence({ row }: { row: RecordData }) {
  return <><strong>{text(row.bookmaker)}</strong><small>{row.probability_basis === 'other_book_consensus' ? 'Other-book consensus; target book excluded' : 'Bookmaker probabilities; margin removed'}</small></>;
}
function ProbabilityEvidence({ row, view }: CellProps) {
  if (view === 'arbitrage') return <span className="bi-badge">Execution unverified</span>;
  if (view === 'predictions' || row.model_version) return <ModelEvidence row={row} />;
  return <BookEvidence row={row} />;
}
function EvidenceCell({ row, view }: CellProps) {
  return <><ProbabilityEvidence row={row} view={view} /><small>{text(row.settlement_rule).replaceAll('_',' ')}</small>
    {Boolean(row.push_probability_unmodeled) && <small>Conditional on no push; push probability unmodeled</small>}
    {Boolean(row.observed_at) && <small>Quote: {formatDate(text(row.observed_at))}</small>}
    {array(row.reference_books).length>0 && <small>Reference: {array(row.reference_books).join(', ')}</small>}</>;
}
export default function BettingIntelTable({ rows, view, title }: { rows: RecordData[]; view: string; title: string }) {
  return <div className="bi-table-scroll" tabIndex={0} role="region" aria-label={`${title} results`}><table className="bi-table">
    <thead><tr><th scope="col">Game / market</th><th scope="col">Selection / probabilities</th><th scope="col">Price / return</th><th scope="col">Evidence</th></tr></thead>
    <tbody>{rows.map((row,i) => <tr key={`${row.fixture_id}-${i}`}><td><FixtureLabel row={row} /><MarketLabel row={row} /></td>
      <td><SelectionCell row={row} view={view} /></td><td><PriceCell row={row} view={view} /></td><td><EvidenceCell row={row} view={view} /></td></tr>)}</tbody>
  </table></div>;
}
