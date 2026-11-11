import { useQuery } from '@tanstack/react-query';
import { predictionService } from '../services/predictionService';
import { slug, type Sport } from './data';
import { array, number, record, text, type Fixture } from './services';

export const utcDay = (value = new Date()) => value.toISOString().slice(0, 10);
export function shiftDay(day: string, amount: number) {
  const value = new Date(`${day}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + amount);
  return utcDay(value);
}
export function validDay(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && utcDay(new Date(value)) === value;
}
export const isFinal = (match: Fixture) => ['FINISHED', 'FINAL', 'COMPLETED', 'FT'].includes(match.status.toUpperCase())
  && match.homeScore !== null && match.awayScore !== null;

export function useSportSchedule(sport: Sport, start = shiftDay(utcDay(), -7), end = shiftDay(utcDay(), 7)) {
  return useQuery({
    queryKey: ['sport-schedule', slug(sport), start, end],
    queryFn: async ({ signal }) => {
      const raw: unknown = sport === 'Football'
        ? await predictionService.getMatches({ limit: 1000 }, { signal })
        : await predictionService.getSportSchedule(slug(sport), { start_date: start, end_date: end }, signal);
      const payload = record(raw);
      if (sport !== 'Football' && (payload.sport !== slug(sport) || !Array.isArray(payload.items))) {
        throw new Error(`The schedule source did not return ${sport} fixtures.`);
      }
      if (sport === 'Football' && !Array.isArray(raw)) throw new Error('The fixture service returned an unsupported response.');
      const seen = new Set<string>();
      const items: Fixture[] = array(sport === 'Football' ? raw : payload.items).map(record).filter(row =>
        sport === 'Football' || row.sport === slug(sport),
      ).map(row => ({
        id: String(row.id ?? row.match_id ?? ''), sport, league: text(row.league ?? row.competition),
        home: text(row.home_team), away: text(row.away_team), date: text(row.date), status: text(row.status),
        homeScore: number(row.home_score), awayScore: number(row.away_score),
      })).filter(row => {
        if (!row.id || !row.home || !row.away || !Number.isFinite(Date.parse(row.date))) return false;
        const day = utcDay(new Date(row.date));
        const key = `${row.home.toLowerCase()}|${row.away.toLowerCase()}|${new Date(row.date).toISOString()}`;
        if (day < start || day > end || seen.has(key)) return false;
        seen.add(key);
        return true;
      }).sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
      return { items, issues: array(payload.source_issues).filter((issue): issue is string => typeof issue === 'string') };
    },
    staleTime: 30000, refetchInterval: 60000, retry: 1,
  });
}
