import { makeRequest } from "../utils/api";
import { predictionService } from "../services/predictionService";
import { useQuery } from "@tanstack/react-query";
import useAuthStore from "../stores/authStore";
import type { Sport } from "./data";
import { SPORTS } from "../utils/constants";

export type RecordData = Record<string, unknown>;
export const record = (value: unknown): RecordData =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as RecordData)
    : {};
export const text = (value: unknown) =>
  typeof value === "string" ? value : "";
export const number = (value: unknown) =>
  typeof value === "number" && Number.isFinite(value) ? value : null;
export const array = (value: unknown): unknown[] =>
  Array.isArray(value) ? value : [];
export async function request(
  path: string,
  options: RequestInit = {},
): Promise<unknown> {
  return makeRequest(path, {
    ...options,
    signal: options.signal ?? AbortSignal.timeout(35000),
  });
}
export interface Fixture {
  id: string;
  sport: Sport;
  league: string;
  home: string;
  away: string;
  date: string;
  status: string;
  homeScore: number | null;
  awayScore: number | null;
}
function normalize(value: unknown, sport: Sport): Fixture {
  const row = record(value);
  return {
    id: String(row.match_id ?? row.id ?? row.event_id ?? ""),
    sport,
    league: text(row.competition ?? row.league),
    home: text(row.home_team),
    away: text(row.away_team),
    date: text(row.date ?? row.event_date ?? row.start_time),
    status: text(row.status),
    homeScore: number(row.home_score),
    awayScore: number(row.away_score),
  };
}
export function useFixtures(
  sport: Sport = "Football",
  competition = "",
  date = "",
) {
  const authenticated = useAuthStore((s) => s.isAuthenticated);
  const userId = useAuthStore((s) => s.user?.id);
  return useQuery({
    queryKey: [
      "heritage-fixtures",
      sport,
      competition,
      date,
      authenticated,
      userId,
    ],
    queryFn: async ({ signal }) => {
      let raw: unknown;
      if (sport === "Football")
        raw = await predictionService.getMatches(
          { competition, date, limit: 100 },
          { signal },
        );
      else {
        if (!authenticated)
          throw new Error(
            "Log in to load this sport’s fixtures from the betting API.",
          );
        raw = await request("/betting/events", { signal });
      }
      if (!Array.isArray(raw))
        throw new Error(
          "The fixture service returned an unsupported response.",
        );
      return raw
        .filter((value) => {
          const row = record(value);
          const apiSport = text(row.sport).toLowerCase();
          const league = text(row.league).toLowerCase();
          // The original API uses "basketball" for several leagues. Do not
          // mislabel EuroLeague or women's/college fixtures as NBA games.
          const basketballLeague =
            sport === "NBA"
              ? /^nba(?:\s|$)/.test(league)
              : sport === "WNBA"
                ? /^wnba(?:\s|$)/.test(league)
                : sport === "NCAAB" &&
                  /^(ncaab|ncaa basketball)(?:\s|$)/.test(league);
          return (
            sport === "Football" ||
            apiSport === sport.toLowerCase() ||
            (apiSport === SPORTS.BASKETBALL.apiParam && basketballLeague)
          );
        })
        .map((value) => normalize(value, sport))
        .filter((row) => row.id && row.home && row.away)
        .filter(
          (row) =>
            (!competition || row.league === competition) &&
            (!date || row.date.slice(0, 10) === date),
        );
    },
    retry: false,
    staleTime: 30000,
  });
}
export function formatDate(value: string) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Time unavailable"
    : date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}
