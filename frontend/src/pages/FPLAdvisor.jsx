import { apiFetch, PIPELINE_API_URL } from '../utils/api';
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { createElement } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  Trophy,
  Users,
  TrendingUp,
  Star,
  Shield,
  Target,
  Zap,
  RefreshCw,
  ChevronDown,
  AlertCircle,
  DollarSign,
  ArrowUpRight,
} from "lucide-react";
import { Footer } from "../heritage/AppShell";
import { DataState } from "../heritage/ui";
import EditableTeam from "../components/fpl/EditableTeam";
import useAuthStore from "../stores/authStore";
import "./FPLAdvisor.css";


const tabs = [
  {
    id: "team",
    label: "Optimal Team",
    icon: Users,
    description: "Your suggested starting eleven and bench.",
  },
  {
    id: "captains",
    label: "Captain Picks",
    icon: Star,
    description: "Compare the players to lead your gameweek.",
  },
  {
    id: "positions",
    label: "By Position",
    icon: Shield,
    description: "Find the right player for every part of your squad.",
  },
  {
    id: "value",
    label: "Value Picks",
    icon: DollarSign,
    description: "Make more of your budget with points-per-million insights.",
  },
  {
    id: "differentials",
    label: "Differentials",
    icon: Zap,
    description: "Explore high-potential players with less than 10% ownership.",
  },
];
const positions = {
  GKP: "Goalkeepers",
  DEF: "Defenders",
  MID: "Midfielders",
  FWD: "Forwards",
};
const availability = {
  d: "Doubtful",
  i: "Injured",
  s: "Suspended",
  u: "Unavailable",
};
const metric = (value, digits = 1) =>
  value == null || !Number.isFinite(Number(value))
    ? "—"
    : Number(value).toFixed(digits);

function PlayerCard({ player, captainId, viceCaptainId }) {
  return (
    <details className="fpl-player">
      <summary>
        <span className={`fpl-position fpl-position-${player.position}`}>
          {player.position}
        </span>
        <span className="fpl-player-name">
          <strong>
            {player.web_name}
            {player.id === captainId && (
              <span className="fpl-captain" title="Captain">
                C
              </span>
            )}
            {player.id === viceCaptainId && (
              <span className="fpl-captain" title="Vice captain">
                V
              </span>
            )}
          </strong>
          <small>
            {player.team_name} · £{metric(player.price)}m
          </small>
          {availability[player.status] && (
            <small className="fpl-availability">
              <AlertCircle size={12} />
              {availability[player.status]}
            </small>
          )}
        </span>
        <span className="fpl-player-points">
          <b>{metric(player.expected_points)}</b>
          <small>xPts</small>
        </span>
        <ChevronDown size={14} className="fpl-disclosure" />
      </summary>
      <dl className="fpl-player-stats">
        {[
          ["Form", metric(player.form)],
          ["Points / game", metric(player.points_per_game)],
          ["Total points", metric(player.total_points, 0)],
          ["Ownership", `${metric(player.selected_by_percent)}%`],
          ["Value score", metric(player.value_score, 2)],
          ["Fixture difficulty", metric(player.fixture_difficulty_avg)],
        ].map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {player.news && <p className="fpl-player-news">{player.news}</p>}
    </details>
  );
}

function PlayerList({ title, players = [], icon: Icon, description }) {
  const [showAll, setShowAll] = useState(false);
  const list = players || [];
  return (
    <section className="fh-card fpl-panel">
      <div className="fpl-panel-heading">
        {createElement(Icon, { size: 18 })}
        <h3>{title}</h3>
        <span>{list.length} players</span>
      </div>
      {description && <p className="fh-muted fpl-description">{description}</p>}
      {list.length ? (
        <div className="fpl-player-list">
          {(showAll ? list : list.slice(0, 5)).map((player) => (
            <PlayerCard key={player.id} player={player} />
          ))}
        </div>
      ) : (
        <DataState empty="No player recommendations available." />
      )}
      {list.length > 5 && (
        <button
          className="fh-button fh-button-secondary fpl-show-more"
          onClick={() => setShowAll(!showAll)}
          aria-expanded={showAll}
        >
          {showAll ? "Show less" : `Show all ${list.length} players`}
          <ChevronDown size={14} />
        </button>
      )}
    </section>
  );
}

function TeamFormation({ team }) {
  return (
    <>
      <div className="fpl-metrics">
        {[
          ["Expected points", metric(team.expected_points)],
          ["Team cost", `£${metric(team.total_cost)}m`],
          ["Budget left", `£${metric(team.budget_remaining)}m`],
          ["Captain", team.captain?.web_name || "Unavailable"],
        ].map(([label, value]) => (
          <div className="fh-card" key={label}>
            <span className="fh-eyebrow">{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <section className="fh-card fpl-panel">
        <div className="fpl-panel-heading">
          <Users size={18} />
          <h3>Starting eleven</h3>
          <span className="fpl-badge">
            {team.formation
              ? `${team.formation.DEF}-${team.formation.MID}-${team.formation.FWD}`
              : "Formation unavailable"}
          </span>
        </div>
        <p className="fh-muted fpl-description">
          Select a player to explore form, ownership and fixture difficulty.
        </p>
        <div className="fpl-pitch">
          {["FWD", "MID", "DEF", "GKP"].map((position) => (
            <section
              className="fpl-pitch-row"
              key={position}
              aria-label={positions[position]}
            >
              <span className="fh-eyebrow">{positions[position]}</span>
              <div>
                {(team.starting_xi || [])
                  .filter((player) => player.position === position)
                  .map((player) => (
                    <PlayerCard
                      key={player.id}
                      player={player}
                      captainId={team.captain?.id}
                      viceCaptainId={team.vice_captain?.id}
                    />
                  ))}
              </div>
            </section>
          ))}
        </div>
        <div className="fpl-panel-heading fpl-bench-heading">
          <h3>The bench</h3>
          <span>Squad depth</span>
        </div>
        <div className="fpl-bench">
          {(team.bench || []).map((player) => (
            <PlayerCard key={player.id} player={player} />
          ))}
        </div>
      </section>
    </>
  );
}

export default function FPLAdvisor() {
  const userId = useAuthStore((state) => state.user?.id);
  const [activeTab, setActiveTab] = useState("team");
  const {
    data: advice,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["fpl-advice"],
    queryFn: async () => {
      const response = await apiFetch(`${PIPELINE_API_URL}/fpl/advice`);
      if (response.status === 404) return null;
      if (!response.ok) throw new Error("Failed to fetch FPL advice");
      return response.json();
    },
    staleTime: 300000,
    retry: 1,
  });
  const refreshMutation = useMutation({
    mutationFn: async () => {
      const response = await apiFetch(`${PIPELINE_API_URL}/fpl/refresh`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to refresh FPL data");
      return response.json();
    },
    onSuccess: () => {
      toast.success("FPL data refreshed successfully!");
      refetch();
    },
    onError: (err) => toast.error(`Refresh failed: ${err.message}`),
  });
  const selectedTab = tabs.find((tab) => tab.id === activeTab);
  return (
    <div className="fh-page fpl-page">
      <header className="fh-intro">
        <div>
          <span className="fh-eyebrow">Fantasy Sports / FPL Advisor</span>
          <h1>Fantasy Premier League</h1>
        </div>
        <Link
          className="fh-button fh-button-secondary"
          to="/sport/football/schedule?competition=Premier%20League"
        >
          League fixtures
          <ArrowUpRight size={14} />
        </Link>
      </header>
      <main id="main-content">
        <section className="fh-card fpl-hero">
          <div>
            <span className="fh-eyebrow">
              <Trophy size={15} />
              YOUR GAMEWEEK, CONSIDERED.
            </span>
            <h2>A stronger squad starts here.</h2>
            <p>
              Build your team. Find your captain. Discover your next
              differential.
            </p>
          </div>
          <div className="fpl-refresh">
            <span className="fpl-badge">
              {advice?.gameweek
                ? `Gameweek ${advice.gameweek}`
                : "Gameweek unavailable"}
            </span>
            <button
              className="fh-button"
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
            >
              <RefreshCw
                size={15}
                className={refreshMutation.isPending ? "animate-spin" : ""}
              />
              {refreshMutation.isPending ? "Refreshing..." : "Refresh Data"}
            </button>
            {advice?.generated_at && (
              <small>
                Updated {new Date(advice.generated_at).toLocaleString()}
              </small>
            )}
          </div>
        </section>
        <div className="fpl-workspace">
          <aside className="fpl-sidebar">
            <nav className="fh-card fpl-navigation" aria-label="FPL tools">
              <span className="fh-eyebrow">Your FPL toolkit</span>
              {tabs.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  aria-pressed={activeTab === id}
                  onClick={() => setActiveTab(id)}
                >
                  {createElement(Icon, { size: 17 })}
                  <span>{label}</span>
                  <ArrowUpRight size={13} />
                </button>
              ))}
            </nav>
            <div className="fh-card fpl-guide">
              <span className="fh-eyebrow">Behind the numbers</span>
              <h3>Make every point count.</h3>
              <p>
                xPts is a player's expected points. Compare it with price,
                recent form and upcoming fixtures when shaping your squad.
              </p>
              <p>Open any player card for a closer look.</p>
            </div>
          </aside>
          <section
            className="fh-content fpl-results"
            aria-label={selectedTab.label}
          >
            <header className="fpl-results-heading">
              <h2>{selectedTab.label}</h2>
              <p className="fh-muted">{selectedTab.description}</p>
            </header>
            {isLoading ? (
              <div className="fh-card">
                <DataState loading />
              </div>
            ) : isError ? (
              <div className="fh-card">
                <DataState error={error} retry={() => refetch()} />
              </div>
            ) : !advice ? (
              <div className="fh-card fh-state">
                <Trophy size={32} />
                <h3>No FPL Data Available</h3>
                <p>
                  Fetch the latest player data to explore your gameweek
                  recommendations.
                </p>
                <button
                  className="fh-button"
                  onClick={() => refreshMutation.mutate()}
                  disabled={refreshMutation.isPending}
                >
                  {refreshMutation.isPending ? "Fetching..." : "Fetch FPL Data"}
                </button>
              </div>
            ) : (
              <>
                {activeTab === "team" && userId != null && (
                  <EditableTeam
                    key={`${userId}:${advice.gameweek}`}
                    storageKey={`fh:${userId}:fpl-team:${advice.gameweek ?? "unknown"}`}
                    suggested={advice.optimal_team}
                    apiUrl={PIPELINE_API_URL}
                  >
                    {(team) =>
                      team ? (
                        <TeamFormation team={team} />
                      ) : (
                        <div className="fh-card">
                          <DataState empty="No optimal team available." />
                        </div>
                      )
                    }
                  </EditableTeam>
                )}
                {activeTab === "captains" && (
                  <PlayerList
                    title="Captain Recommendations"
                    players={advice.captain_picks}
                    icon={Star}
                    description="Captain options based on expected points and differential value."
                  />
                )}
                {activeTab === "positions" && (
                  <div className="fpl-position-grid">
                    {[
                      ["Top Goalkeepers", advice.top_goalkeepers, Shield],
                      ["Top Defenders", advice.top_defenders, Shield],
                      ["Top Midfielders", advice.top_midfielders, Target],
                      ["Top Forwards", advice.top_forwards, TrendingUp],
                    ].map(([title, players, icon]) => (
                      <PlayerList
                        key={title}
                        title={title}
                        players={players}
                        icon={icon}
                      />
                    ))}
                  </div>
                )}
                {activeTab === "value" && (
                  <PlayerList
                    title="Best Value Picks"
                    players={advice.value_picks}
                    icon={DollarSign}
                    description="Budget-friendly players with high points per million."
                  />
                )}
                {activeTab === "differentials" && (
                  <PlayerList
                    title="Differential Picks"
                    players={advice.differential_picks}
                    icon={Zap}
                    description="High-potential players with low ownership (under 10%)."
                  />
                )}
              </>
            )}
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
