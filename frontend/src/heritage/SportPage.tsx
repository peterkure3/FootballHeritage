import { Link, useParams, useSearchParams } from "react-router-dom";
import { Heart } from "lucide-react";
import AppShell from "./AppShell";
import HomePage from "./HomePage";
import { sports, slug, sportPath, leagues, type Sport } from "./data";
import { useFixtures, formatDate, type Fixture } from "./services";
import { DataState, Dialog } from "./ui";
import { usePreferences } from "./preferences";
import { useState } from "react";
export function MatchCard({ match }: { match: Fixture }) {
  return (
    <Link
      className="fh-match"
      to={`${sportPath(match.sport, "scores")}?match=${encodeURIComponent(match.id)}`}
    >
      <small>
        {match.league || match.sport} · {formatDate(match.date)}
      </small>
      <div>
        <span>{match.home}</span>
        <strong>
          {match.homeScore ?? "—"} : {match.awayScore ?? "—"}
        </strong>
        <span>{match.away}</span>
      </div>
      <small>{match.status || "Status unavailable"}</small>
    </Link>
  );
}
function FixturesPage({ sport, section }: { sport: Sport; section: string }) {
  const [params, setParams] = useSearchParams();
  const competition = params.get("competition") || "";
  const date = params.get("date") || "";
  const { data, isPending, error, refetch } = useFixtures(
    sport,
    competition,
    date,
  );
  const selected = data?.find((match) => match.id === params.get("match"));
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("match");
    setParams(next);
  };
  return (
    <AppShell
      sport={sport}
      title={
        section === "schedule"
          ? "The next chapter."
          : "Every score. Every story."
      }
    >
      <section className="fh-card fh-section">
        <h2>{section === "schedule" ? "Schedule" : "Scores"}</h2>
        <p className="fh-muted">
          Latest records from{" "}
          {sport === "Football"
            ? "the statistical pipeline"
            : "the authenticated event API"}
          . This is not a real-time score feed.
        </p>
        <div className="fh-filters">
          <label>
            Competition
            <select
              value={competition}
              onChange={(event) => update("competition", event.target.value)}
            >
              <option value="">All competitions</option>
              {Array.from(
                new Set(
                  [...Object.keys(leagues[sport]), competition].filter(Boolean),
                ),
              ).map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            Match date
            <input
              type="date"
              value={date}
              onChange={(event) => update("date", event.target.value)}
            />
          </label>
          <button
            className="fh-button fh-button-secondary"
            onClick={() => void refetch()}
          >
            Refresh
          </button>
        </div>
        {isPending || error || !data?.length ? (
          <DataState
            loading={isPending}
            error={error}
            empty="No fixtures match these filters."
            retry={() => void refetch()}
          />
        ) : (
          data.map((match) => <MatchCard key={match.id} match={match} />)
        )}
        {params.has("match") && !isPending && !selected && (
          <p className="fh-data-note">
            This match is unavailable in the current results.
          </p>
        )}
      </section>
      {selected && (
        <Dialog
          title={`${selected.home} versus ${selected.away}`}
          onClose={() => {
            const next = new URLSearchParams(params);
            next.delete("match");
            setParams(next);
          }}
        >
          <span className="fh-eyebrow">{selected.league}</span>
          <h2>
            {selected.home} v {selected.away}
          </h2>
          <p className="fh-match-score">
            {selected.homeScore ?? "—"} : {selected.awayScore ?? "—"}
          </p>
          <p>
            {formatDate(selected.date)} · {selected.status}
          </p>
          <p className="fh-muted">
            Fixture ID: {selected.id}. Additional match statistics are not
            provided by this endpoint.
          </p>
        </Dialog>
      )}
    </AppShell>
  );
}
export function TeamsPage({
  sport = "Football",
  followedOnly = false,
}: {
  sport?: Sport;
  followedOnly?: boolean;
}) {
  const follows = usePreferences("teams");
  const [params] = useSearchParams();
  const [search, setSearch] = useState(params.get("team") || "");
  // Team names below are a static template navigation directory, not a live team-data feed.
  const groups = followedOnly
    ? { "Your teams": follows.values }
    : leagues[sport];
  return (
    <AppShell
      title={followedOnly ? "Your teams. Your game." : "Find your team."}
      sport={sport}
    >
      <section className="fh-card fh-section">
        <h2>{followedOnly ? "Followed teams" : `${sport} directory`}</h2>
        <p className="fh-muted">
          {followedOnly
            ? "Account-scoped preferences on this device. Server sync is unavailable."
            : "Static navigation directory from the template; live team profiles and statistics are not connected."}
        </p>
        <label className="fh-search">
          Search teams
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Team or league name"
          />
        </label>
        {followedOnly && !follows.authenticated ? (
          <div className="fh-state">
            <p>Log in to follow teams.</p>
            <Link className="fh-button" to="/login">
              Log in
            </Link>
          </div>
        ) : (
          Object.entries(groups).map(([league, teams]) => (
            <div className="fh-team-group" key={league}>
              <h3>{league}</h3>
              {teams
                .filter((team) =>
                  team.toLowerCase().includes(search.toLowerCase()),
                )
                .map((team) => (
                  <div key={team}>
                    <span className="fh-team-badge">
                      {team.slice(0, 2).toUpperCase()}
                    </span>
                    <span>{team}</span>
                    {follows.authenticated ? (
                      <button
                        aria-label={`${follows.values.includes(team) ? "Unfollow" : "Follow"} ${team}`}
                        aria-pressed={follows.values.includes(team)}
                        onClick={() => follows.toggle(team)}
                      >
                        <Heart
                          size={17}
                          fill={
                            follows.values.includes(team)
                              ? "currentColor"
                              : "none"
                          }
                        />
                      </button>
                    ) : (
                      <Link to="/login" aria-label={`Log in to follow ${team}`}>
                        <Heart size={17} />
                      </Link>
                    )}
                  </div>
                ))}
            </div>
          ))
        )}
        {followedOnly && follows.authenticated && !follows.values.length && (
          <DataState empty="No followed teams yet." />
        )}
      </section>
    </AppShell>
  );
}
export default function SportPage() {
  const { sport: sportSlug, section = "home" } = useParams();
  const sport = sports.find((item) => slug(item) === sportSlug);
  if (!sport)
    return (
      <AppShell title="Sport not found.">
        <Link to="/">Return home</Link>
      </AppShell>
    );
  if (section === "home") return <HomePage sport={sport} />;
  if (section === "scores" || section === "schedule")
    return <FixturesPage sport={sport} section={section} />;
  if (section === "teams") return <TeamsPage key={sport} sport={sport} />;
  if (section !== "standings" && section !== "insights")
    return (
      <AppShell sport={sport} title="Page not found.">
        <Link className="fh-button" to={sportPath(sport)}>
          Return to sport home
        </Link>
      </AppShell>
    );
  return (
    <AppShell
      sport={sport}
      title={
        section === "standings"
          ? "The season, in perspective."
          : "Beyond the score."
      }
    >
      <section className="fh-card fh-section">
        <h2>{section === "standings" ? "Standings" : "Insights"}</h2>
        {section === "standings" ? (
          <DataState
            error={
              new Error(
                "There is no standings API contract in this repository. A sample league table will not be presented as current data.",
              )
            }
          />
        ) : (
          <>
            <p className="fh-muted">
              Use the existing analytics views to inspect available data.
              Sport-specific model coverage varies; a navigation entry does not
              imply model support.
            </p>
            <div className="fh-link-grid">
              <Link to="/predictions">Match predictions →</Link>
              <Link to="/intelligence/devigged-odds">Devigged odds →</Link>
              <Link to="/intelligence/ev-bets">Expected value →</Link>
              <Link to="/intelligence/arbitrage">Arbitrage →</Link>
              <Link to="/player-props">Player props →</Link>
              <Link to="/college">College sports →</Link>
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}
