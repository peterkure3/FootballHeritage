import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Trophy, RefreshCw, ArrowUpRight, Search, Users } from "lucide-react";
import { Footer } from "../heritage/AppShell";
import { DataState } from "../heritage/ui";
import "./MarchMadness.css";

import { PIPELINE_API_URL as API, apiFetch } from '../utils/api';
const regions = ["East", "West", "South", "Midwest"];
const dateLabel = (value) =>
  value
    ? new Date(value).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "Time unavailable";
async function loadBracket(season, refresh = false) {
  const response = await apiFetch(
    `${API}/ncaab/bracket?season=${season}&refresh=${refresh}`,
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Tournament data is unavailable.",
    );
  if (!Array.isArray(data.games) || !Array.isArray(data.teams))
    throw new Error("Tournament data is incomplete.");
  return data;
}

function TeamLogo({ team }) {
  return team.logo ? (
    <img
      src={team.logo}
      alt=""
      loading="lazy"
      onError={(event) => {
        event.currentTarget.style.display = "none";
      }}
    />
  ) : (
    <span className="mm-logo-fallback">{team.name?.slice(0, 2)}</span>
  );
}

function GameCard({ game, onTeam }) {
  return (
    <article className="fh-card mm-game">
      <div className="mm-game-heading">
        <span>{game.region || game.round}</span>
        <span className={game.status === "live" ? "mm-live" : ""}>
          {game.status_detail || game.status}
        </span>
      </div>
      {game.teams.map((team) => (
        <button
          className={`mm-team-row ${team.winner ? "mm-winner" : ""}`}
          key={team.id}
          onClick={() => onTeam(team.name)}
          aria-label={`Track ${team.name}`}
        >
          <small className="mm-seed">{team.seed ?? "—"}</small>
          <TeamLogo team={team} />
          <span>{team.name}</span>
          <strong>{team.score ?? "—"}</strong>
          {team.winner && (
            <span className="mm-win-mark" aria-label="Winner">
              ✓
            </span>
          )}
        </button>
      ))}
      <div className="mm-game-footer">
        <time dateTime={game.date}>{dateLabel(game.date)}</time>
        {game.source_url && (
          <a href={game.source_url} target="_blank" rel="noreferrer">
            Game details
            <ArrowUpRight size={11} />
          </a>
        )}
      </div>
    </article>
  );
}

export default function MarchMadness() {
  const currentYear = new Date().getFullYear();
  const [season, setSeason] = useState(currentYear);
  const [view, setView] = useState("bracket");
  const [region, setRegion] = useState("");
  const [round, setRound] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["march-madness", season],
    queryFn: () => loadBracket(season),
    staleTime: 60000,
    retry: false,
  });
  const refresh = useMutation({
    mutationFn: (year) => loadBracket(year, true),
    onSuccess: (data, year) =>
      client.setQueryData(["march-madness", year], data),
  });
  const data = query.data;
  const games = (data?.games || []).filter(
    (game) =>
      (!region || game.region === region) &&
      (!round || game.round === round) &&
      (!status || game.status === status) &&
      game.teams.some((team) =>
        team.name.toLowerCase().includes(search.toLowerCase()),
      ),
  );
  const teams = (data?.teams || []).filter(
    (team) =>
      (!region || team.region === region) &&
      `${team.name} ${team.full_name}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const shownRounds = (data?.rounds || []).filter((name) =>
    games.some((game) => game.round === name),
  );
  const clearFilters = () => {
    setRegion("");
    setRound("");
    setStatus("");
    setSearch("");
  };
  return (
    <div className="fh-page mm-page">
      <header className="fh-intro">
        <div>
          <span className="fh-eyebrow">NCAAB / THE NCAA MEN'S TOURNAMENT</span>
          <h1>March Madness</h1>
        </div>
        <Link className="fh-button fh-button-secondary" to="/sport/ncaab">
          Back to NCAAB
          <ArrowUpRight size={14} />
        </Link>
      </header>
      <main id="main-content">
        <section className="fh-card mm-hero">
          <div>
            <span className="fh-eyebrow">
              <Trophy size={15} />
              {season} TOURNAMENT
            </span>
            <h2>Every round. Every result.</h2>
            <p>
              Follow the field from the First Four to the national championship.
            </p>
            <div className="mm-hero-meta">
              <span>
                {data ? `${data.teams.length} teams` : "Teams loading"}
              </span>
              <span>
                {data ? `${data.games.length} games` : "Games loading"}
              </span>
              <span>
                {data?.status === "complete"
                  ? "Tournament complete"
                  : data?.games.length
                    ? "Tournament in progress"
                    : "Awaiting tournament data"}
              </span>
            </div>
          </div>
          {data?.champion && (
            <div className="mm-champion">
              <TeamLogo team={data.champion} />
              <div>
                <span className="fh-eyebrow">National champion</span>
                <h3>{data.champion.name}</h3>
                <p>{data.champion.record || ""}</p>
              </div>
            </div>
          )}
        </section>
        <section
          className="fh-card mm-controls"
          aria-label="Tournament controls"
        >
          <div className="mm-toolbar">
            <div className="mm-view-switch">
              <button
                aria-pressed={view === "bracket"}
                onClick={() => setView("bracket")}
              >
                <Trophy size={15} />
                Bracket & results
              </button>
              <button
                aria-pressed={view === "teams"}
                onClick={() => setView("teams")}
              >
                <Users size={15} />
                Tournament teams
              </button>
            </div>
            <div className="mm-refresh">
              <label>
                Season
                <select
                  value={season}
                  aria-label="Season"
                  onChange={(event) => {
                    setSeason(Number(event.target.value));
                    clearFilters();
                    refresh.reset();
                  }}
                >
                  {[currentYear, currentYear - 1, currentYear - 2].map(
                    (year) => (
                      <option key={year}>{year}</option>
                    ),
                  )}
                </select>
              </label>
              <button
                className="fh-button fh-button-secondary"
                disabled={refresh.isPending || query.isPending}
                onClick={() => refresh.mutate(season)}
              >
                <RefreshCw size={14} />
                {refresh.isPending ? "Refreshing..." : "Refresh data"}
              </button>
            </div>
          </div>
          <div className="mm-filters">
            <label className="mm-search">
              <span>
                <Search size={13} />
                Find a team
              </span>
              <input
                type="search"
                value={search}
                aria-label="Find a team"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search tournament teams"
              />
            </label>
            <label>
              Region
              <select
                value={region}
                aria-label="Region"
                onChange={(event) => setRegion(event.target.value)}
              >
                <option value="">All regions</option>
                {regions.map((name) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
            </label>
            {view === "bracket" && (
              <>
                <label>
                  Round
                  <select
                    value={round}
                    aria-label="Round"
                    onChange={(event) => {
                      setRound(event.target.value);
                      if (
                        ["Final Four", "Championship"].includes(
                          event.target.value,
                        )
                      )
                        setRegion("");
                    }}
                  >
                    <option value="">All rounds</option>
                    {(data?.rounds || []).map((name) => (
                      <option key={name}>{name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Game status
                  <select
                    value={status}
                    aria-label="Game status"
                    onChange={(event) => setStatus(event.target.value)}
                  >
                    <option value="">All games</option>
                    <option value="finished">Finished</option>
                    <option value="live">Live</option>
                    <option value="upcoming">Upcoming</option>
                  </select>
                </label>
              </>
            )}
            <button
              className="fh-button fh-button-secondary"
              onClick={clearFilters}
            >
              Clear filters
            </button>
          </div>
        </section>
        {refresh.isError && (
          <div className="fh-state fh-error" role="alert">
            {refresh.error.message}
            <button
              className="fh-button"
              onClick={() => refresh.mutate(season)}
            >
              Retry refresh
            </button>
          </div>
        )}
        {data?.stale && (
          <p className="mm-notice" role="status">
            {data.warning}
          </p>
        )}
        {query.isPending ? (
          <div className="fh-card">
            <DataState loading />
          </div>
        ) : query.isError ? (
          <div className="fh-card">
            <DataState error={query.error} retry={() => query.refetch()} />
          </div>
        ) : !data.games.length ? (
          <div className="fh-card">
            <DataState
              empty={`No confirmed ${season} tournament games available.`}
            />
          </div>
        ) : view === "bracket" ? (
          <>
            <div className="mm-section-heading">
              <h2>{region ? `${region} region` : "The tournament"}</h2>
              <span>
                {games.length} games · Select a team to track its results
              </span>
            </div>
            {games.length ? (
              <div
                className="mm-bracket-scroll"
                tabIndex={0}
                role="region"
                aria-label="Tournament rounds; scroll horizontally to see later rounds"
              >
                <div className="mm-bracket">
                  {shownRounds.map((name) => (
                    <section className="mm-round" key={name}>
                      <header>
                        <span className="fh-eyebrow">
                          {games.filter((game) => game.round === name).length}{" "}
                          GAMES
                        </span>
                        <h3>{name}</h3>
                      </header>
                      <div>
                        {games
                          .filter((game) => game.round === name)
                          .map((game) => (
                            <GameCard
                              key={game.id}
                              game={game}
                              onTeam={setSearch}
                            />
                          ))}
                      </div>
                    </section>
                  ))}
                </div>
              </div>
            ) : (
              <div className="fh-card">
                <DataState empty="No games match these filters." />
              </div>
            )}
          </>
        ) : (
          <>
            <div className="mm-section-heading">
              <h2>The tournament field</h2>
              <span>
                {teams.length} teams · Seeds and regions from tournament games
              </span>
            </div>
            {teams.length ? (
              <div className="mm-team-grid">
                {teams.map((team) => (
                  <article className="fh-card mm-team-card" key={team.id}>
                    <TeamLogo team={team} />
                    <div>
                      <span className="fh-eyebrow">
                        {team.region || "Region unavailable"} · Seed{" "}
                        {team.seed ?? "—"}
                      </span>
                      <h3>{team.name}</h3>
                      <p className="fh-muted">
                        {team.full_name}
                        {team.record ? ` · ${team.record}` : ""}
                      </p>
                      <button
                        onClick={() => {
                          setSearch(team.name);
                          setRegion("");
                          setRound("");
                          setStatus("");
                          setView("bracket");
                        }}
                      >
                        View tournament games
                        <ArrowUpRight size={12} />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="fh-card">
                <DataState empty="No teams match these filters." />
              </div>
            )}
          </>
        )}
        {data && (
          <footer className="mm-source">
            <span>
              Source: ESPN · Fetched{" "}
              {new Date(data.fetched_at).toLocaleString()}. Scores reflect this
              snapshot.
            </span>
            <a
              href={data.official_bracket_url}
              target="_blank"
              rel="noreferrer"
            >
              Official NCAA bracket
              <ArrowUpRight size={12} />
            </a>
          </footer>
        )}
      </main>
      <Footer />
    </div>
  );
}
