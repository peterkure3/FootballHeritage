import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import Navbar from "../components/Navbar";
import LoadingSkeleton from "../components/LoadingSkeleton";
import EmptyState from "../components/EmptyState";
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
  ChevronUp,
  AlertCircle,
  DollarSign,
} from "lucide-react";

const PIPELINE_API_URL =
  import.meta.env.VITE_PIPELINE_API_URL || "http://localhost:5555/api/v1";

const positionColors = {
  GKP: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  DEF: "bg-blue-500/20 text-blue-400 border-blue-500/40",
  MID: "bg-green-500/20 text-green-400 border-green-500/40",
  FWD: "bg-red-500/20 text-red-400 border-red-500/40",
};

const difficultyColors = {
  1: "bg-green-600",
  2: "bg-green-500",
  3: "bg-yellow-500",
  4: "bg-orange-500",
  5: "bg-red-500",
};

const statusIcons = {
  a: null,
  d: <AlertCircle className="w-4 h-4 text-yellow-400" />,
  i: <AlertCircle className="w-4 h-4 text-red-400" />,
  s: <AlertCircle className="w-4 h-4 text-red-400" />,
  u: <AlertCircle className="w-4 h-4 text-gray-400" />,
};

const PlayerCard = ({ player, showCaptainBadge = false, isCaptain = false, isViceCaptain = false }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`card-glow rounded-xl p-4 border transition-colors cursor-pointer ${
        isCaptain ? "ring-1 ring-yellow-500/30" : ""
      }`}
      style={{
        background: 'var(--color-card)',
        borderColor: isCaptain
          ? 'rgba(234, 179, 8, 0.6)'
          : isViceCaptain
            ? 'rgba(59, 130, 246, 0.6)'
            : 'var(--color-card-border)'
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span
            className={`px-2 py-1 text-xs font-bold rounded border ${
              positionColors[player.position] || "bg-gray-500/20 text-gray-400"
            }`}
          >
            {player.position}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white">{player.web_name}</span>
              {isCaptain && (
                <span className="px-1.5 py-0.5 text-xs font-bold bg-yellow-500 text-black rounded">C</span>
              )}
              {isViceCaptain && (
                <span className="px-1.5 py-0.5 text-xs font-bold bg-blue-500 text-white rounded">V</span>
              )}
              {statusIcons[player.status]}
            </div>
            <span className="text-sm" style={{ color: '#94a3b8' }}>{player.team_name}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-green-400">
            {player.expected_points?.toFixed(1)} xPts
          </div>
          <div className="text-sm" style={{ color: '#94a3b8' }}>£{player.price}m</div>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm" style={{ borderColor: 'var(--color-card-border)' }}>
          <div>
            <span style={{ color: '#64748b' }}>Form</span>
            <div className="font-semibold text-white">{player.form}</div>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>PPG</span>
            <div className="font-semibold text-white">{player.points_per_game}</div>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Total Pts</span>
            <div className="font-semibold text-white">{player.total_points}</div>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Ownership</span>
            <div className="font-semibold text-white">{player.selected_by_percent}%</div>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Value Score</span>
            <div className="font-semibold text-green-400">{player.value_score?.toFixed(2)}</div>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Fixture Diff</span>
            <div className={`font-semibold ${
              player.fixture_difficulty_avg <= 2.5 ? "text-green-400" :
              player.fixture_difficulty_avg <= 3.5 ? "text-yellow-400" : "text-red-400"
            }`}>
              {player.fixture_difficulty_avg?.toFixed(1)}
            </div>
          </div>
          {player.news && (
            <div className="col-span-2 sm:col-span-4">
              <span style={{ color: '#64748b' }}>News</span>
              <div className="text-yellow-400 text-xs">{player.news}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const TeamFormation = ({ team }) => {
  if (!team) return null;

  const formation = team.formation;
  const formationStr = `${formation.DEF}-${formation.MID}-${formation.FWD}`;

  const groupedPlayers = {
    GKP: team.starting_xi.filter((p) => p.position === "GKP"),
    DEF: team.starting_xi.filter((p) => p.position === "DEF"),
    MID: team.starting_xi.filter((p) => p.position === "MID"),
    FWD: team.starting_xi.filter((p) => p.position === "FWD"),
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Formation: {formationStr}</h3>
        <div className="flex items-center gap-4 text-sm">
          <span style={{ color: '#94a3b8' }}>
            Cost: <span className="text-white font-semibold">£{team.total_cost}m</span>
          </span>
          <span style={{ color: '#94a3b8' }}>
            Expected: <span className="text-green-400 font-semibold">{team.expected_points} pts</span>
          </span>
        </div>
      </div>

      {/* Pitch visualization */}
      <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
        {/* Forwards */}
        <div className="flex justify-center gap-2 mb-4">
          {groupedPlayers.FWD.map((p) => (
            <PlayerCard
              key={p.id}
              player={p}
              isCaptain={p.id === team.captain?.id}
              isViceCaptain={p.id === team.vice_captain?.id}
            />
          ))}
        </div>

        {/* Midfielders */}
        <div className="flex justify-center gap-2 mb-4 flex-wrap">
          {groupedPlayers.MID.map((p) => (
            <PlayerCard
              key={p.id}
              player={p}
              isCaptain={p.id === team.captain?.id}
              isViceCaptain={p.id === team.vice_captain?.id}
            />
          ))}
        </div>

        {/* Defenders */}
        <div className="flex justify-center gap-2 mb-4 flex-wrap">
          {groupedPlayers.DEF.map((p) => (
            <PlayerCard
              key={p.id}
              player={p}
              isCaptain={p.id === team.captain?.id}
              isViceCaptain={p.id === team.vice_captain?.id}
            />
          ))}
        </div>

        {/* Goalkeeper */}
        <div className="flex justify-center">
          {groupedPlayers.GKP.map((p) => (
            <PlayerCard key={p.id} player={p} />
          ))}
        </div>
      </div>

      {/* Bench */}
      <div>
        <h4 className="text-sm font-semibold mb-2" style={{ color: '#64748b' }}>Bench</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {team.bench?.map((p) => (
            <PlayerCard key={p.id} player={p} />
          ))}
        </div>
      </div>
    </div>
  );
};

const PlayerList = ({ title, players, icon: Icon, description }) => {
  const [showAll, setShowAll] = useState(false);
  const displayPlayers = showAll ? players : players?.slice(0, 5);

  return (
    <div className="card-glow rounded-xl p-4 border" style={{ animation: 'slide-up 0.4s ease-out 0.06s both', background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
      <div className="flex items-center gap-2 mb-3">
        {Icon && <Icon className="w-5 h-5 text-green-400" />}
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      {description && <p className="text-sm mb-3" style={{ color: '#94a3b8' }}>{description}</p>}

      <div className="space-y-2">
        {displayPlayers?.map((player) => (
          <PlayerCard key={player.id} player={player} />
        ))}
      </div>

      {players?.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="mt-3 w-full py-2 text-sm flex items-center justify-center gap-1 hover:text-white transition-colors"
          style={{ color: '#64748b' }}
        >
          {showAll ? (
            <>
              Show Less <ChevronUp className="w-4 h-4" />
            </>
          ) : (
            <>
              Show All ({players.length}) <ChevronDown className="w-4 h-4" />
            </>
          )}
        </button>
      )}
    </div>
  );
};

const FPLAdvisor = () => {
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
      const response = await fetch(`${PIPELINE_API_URL}/fpl/advice`);
      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error("Failed to fetch FPL advice");
      }
      return response.json();
    },
    staleTime: 300000,
    retry: 1,
  });

  const refreshMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${PIPELINE_API_URL}/fpl/refresh`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to refresh FPL data");
      return response.json();
    },
    onSuccess: () => {
      toast.success("FPL data refreshed successfully!");
      refetch();
    },
    onError: (err) => {
      toast.error(`Refresh failed: ${err.message}`);
    },
  });

  const tabs = [
    { id: "team", label: "Optimal Team", icon: Users },
    { id: "captains", label: "Captain Picks", icon: Star },
    { id: "positions", label: "By Position", icon: Shield },
    { id: "value", label: "Value Picks", icon: DollarSign },
    { id: "differentials", label: "Differentials", icon: Zap },
  ];

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <header style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <p className="text-sm uppercase tracking-wide font-semibold mb-4" style={{ color: '#10b981' }}>FPL Advisor</p>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <Trophy className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h1 className="text-2xl font-[Oswald] tracking-tight text-white">FPL Advisor</h1>
                <p style={{ color: '#64748b' }}>
                  Fantasy Premier League team optimization
                </p>
              </div>
            </div>
            <button
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
              className="card-glow rounded-lg px-4 py-2 border text-white font-semibold transition-all hover:opacity-90 flex items-center gap-2"
              style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
            >
              <RefreshCw
                className={`w-4 h-4 ${refreshMutation.isPending ? "animate-spin" : ""}`}
              />
              {refreshMutation.isPending ? "Refreshing..." : "Refresh Data"}
            </button>
          </div>

          {advice?.gameweek && (
            <div className="mt-4 flex items-center gap-4">
              <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm font-medium">
                Gameweek {advice.gameweek}
              </span>
              {advice.generated_at && (
                <span className="text-sm" style={{ color: '#64748b' }}>
                  Updated: {new Date(advice.generated_at).toLocaleString()}
                </span>
              )}
            </div>
          )}
        </header>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2" style={{ animation: 'slide-up 0.4s ease-out 0.06s both' }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              style={
                activeTab === tab.id
                  ? { background: 'linear-gradient(135deg, #10b981, #059669)' }
                  : { background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }
              }
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {isLoading ? (
          <LoadingSkeleton count={6} />
        ) : isError ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">Error Loading Data</h3>
            <p className="text-sm mb-4" style={{ color: '#64748b' }}>{error?.message}</p>
            <button
              onClick={() => refreshMutation.mutate()}
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
              className="text-white font-semibold rounded-lg py-3 px-4 transition-all hover:opacity-90"
            >
              Fetch FPL Data
            </button>
          </div>
        ) : !advice ? (
          <div className="text-center py-12">
            <Trophy className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">No FPL Data Available</h3>
            <p className="text-sm mb-4" style={{ color: '#64748b' }}>Click the button below to fetch the latest FPL data.</p>
            <button
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
              className="text-white font-semibold rounded-lg py-3 px-4 transition-all hover:opacity-90"
            >
              {refreshMutation.isPending ? "Fetching..." : "Fetch FPL Data"}
            </button>
          </div>
        ) : (
          <div>
            {/* Optimal Team Tab */}
            {activeTab === "team" && advice.optimal_team && (
              <div className="space-y-6" style={{ animation: 'slide-up 0.4s ease-out 0.12s both' }}>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
                    <div className="text-sm" style={{ color: '#64748b' }}>Expected Points</div>
                    <div className="text-2xl font-[Oswald] tracking-tight text-green-400">
                      {advice.optimal_team.expected_points}
                    </div>
                  </div>
                  <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
                    <div className="text-sm" style={{ color: '#64748b' }}>Team Cost</div>
                    <div className="text-2xl font-[Oswald] tracking-tight text-white">
                      £{advice.optimal_team.total_cost}m
                    </div>
                  </div>
                  <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
                    <div className="text-sm" style={{ color: '#64748b' }}>Budget Left</div>
                    <div className="text-2xl font-[Oswald] tracking-tight" style={{ color: '#34d399' }}>
                      £{advice.optimal_team.budget_remaining}m
                    </div>
                  </div>
                  <div className="card-glow rounded-xl p-4 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
                    <div className="text-sm" style={{ color: '#64748b' }}>Captain</div>
                    <div className="text-xl font-[Oswald] tracking-tight text-yellow-400">
                      {advice.optimal_team.captain?.web_name}
                    </div>
                  </div>
                </div>

                <TeamFormation team={advice.optimal_team} />
              </div>
            )}

            {/* Captain Picks Tab */}
            {activeTab === "captains" && (
              <PlayerList
                title="Captain Recommendations"
                players={advice.captain_picks}
                icon={Star}
                description="Best captain options based on expected points and differential value"
              />
            )}

            {/* By Position Tab */}
            {activeTab === "positions" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <PlayerList
                  title="Top Goalkeepers"
                  players={advice.top_goalkeepers}
                  icon={Shield}
                />
                <PlayerList
                  title="Top Defenders"
                  players={advice.top_defenders}
                  icon={Shield}
                />
                <PlayerList
                  title="Top Midfielders"
                  players={advice.top_midfielders}
                  icon={Target}
                />
                <PlayerList
                  title="Top Forwards"
                  players={advice.top_forwards}
                  icon={TrendingUp}
                />
              </div>
            )}

            {/* Value Picks Tab */}
            {activeTab === "value" && (
              <PlayerList
                title="Best Value Picks"
                players={advice.value_picks}
                icon={DollarSign}
                description="Budget-friendly players with high points-per-million"
              />
            )}

            {/* Differentials Tab */}
            {activeTab === "differentials" && (
              <PlayerList
                title="Differential Picks"
                players={advice.differential_picks}
                icon={Zap}
                description="High-potential players with low ownership (<10%)"
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FPLAdvisor;
