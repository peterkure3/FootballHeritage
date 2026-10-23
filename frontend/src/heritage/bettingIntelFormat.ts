import { number, text, type RecordData } from './services';

export const percent = (value: unknown) => number(value) === null ? '—' : `${(Number(value)*100).toFixed(1)}%`;
export const decimalPrice = (value: unknown) => number(value) === null ? '—' : Number(value).toFixed(3);
export function selectionName(row: RecordData, value: unknown) {
  if (value === 'home_win') return text(row.home_team);
  if (value === 'away_win') return text(row.away_team);
  return text(value);
}
export const metric = (summary: RecordData, key: string) => Number(summary[key] ?? 0);
