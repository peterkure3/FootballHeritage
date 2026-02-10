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
      className={`bg-gray-800/50 border rounded-lg p-3 hover:bg-gray-800/70 transition-colors cursor-pointer ${
        isCaptain ? "border-yellow-500/60 ring-1 ring-yellow-500/30" : 
        isViceCaptain ? "border-blue-500/60" : "border-gray-700/50"
      }`}
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
            <span className="text-sm text-gray-400">{player.team_name}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-green-400">
            {player.expected_points?.toFixed(1)} xPts
          </div>
          <div className="text-sm text-gray-400">£{player.price}m</div>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-700/50 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div>
            <span className="text-gray-500">Form</span>
            <div className="font-semibold text-white">{player.form}</div>
          </div>
          <div>
            <span className="text-gray-500">PPG</span>
            <div className="font-semibold text-white">{player.points_per_game}</div>
          </div>
          <div>
            <span className="text-gray-500">Total Pts</span>
            <div className="font-semibold text-white">{player.total_points}</div>
          </div>
          <div>
            <span className="text-gray-500">Ownership</span>
            <div className="font-semibold text-white">{player.selected_by_percent}%</div>
          </div>
          <div>
            <span className="text-gray-500">Value Score</span>
            <div className="font-semibold text-green-400">{player.value_score?.toFixed(2)}</div>
          </div>
          <div>
            <span className="text-gray-500">Fixture Diff</span>
            <div className={`font-semibold ${
              player.fixture_difficulty_avg <= 2.5 ? "text-green-400" :
              player.fixture_difficulty_avg <= 3.5 ? "text-yellow-400" : "text-red-400"
            }`}>
              {player.fixture_difficulty_avg?.toFixed(1)}
            </div>
          </div>
          {player.news && (
            <div className="col-span-2 sm:col-span-4">
              <span className="text-gray-500">News</span>
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
          <span className="text-gray-400">
            Cost: <span className="text-white font-semibold">£{team.total_cost}m</span>
          </span>
          <span className="text-gray-400">
            Expected: <span className="text-green-400 font-semibold">{team.expected_points} pts</span>
          </span>
        </div>
      </div>

      {/* Pitch visualization */}
      <div className="bg-gradient-to-b from-green-900/30 to-green-800/20 rounded-xl p-4 border border-green-700/30">
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
        <h4 className="text-sm font-semibold text-gray-400 mb-2">Bench</h4>
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
    <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        {Icon && <Icon className="w-5 h-5 text-green-400" />}
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      {description && <p className="text-sm text-gray-400 mb-3">{description}</p>}

      <div className="space-y-2">
        {displayPlayers?.map((player) => (
          <PlayerCard key={player.id} player={player} />
        ))}
      </div>

      {players?.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="mt-3 w-full py-2 text-sm text-gray-400 hover:text-white flex items-center justify-center gap-1"
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
          // Data not found, need to refresh
          return null;
        }
        throw new Error("Failed to fetch FPL advice");
      }
      return response.json();
    },
    staleTime: 300000, // 5 minutes
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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Trophy className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">FPL Advisor</h1>
                <p className="text-gray-400">
                  Fantasy Premier League team optimization
                </p>
              </div>
            </div>
            <button
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded-lg transition-colors"
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
                <span className="text-sm text-gray-500">
                  Updated: {new Date(advice.generated_at).toLocaleString()}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-purple-600 text-white"
                  : "bg-gray-800/50 text-gray-400 hover:text-white hover:bg-gray-700/50"
              }`}
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
            <p className="text-gray-400 mb-4">{error?.message}</p>
            <button
              onClick={() => refreshMutation.mutate()}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
            >
              Fetch FPL Data
            </button>
          </div>
        ) : !advice ? (
          <div className="text-center py-12">
            <Trophy className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">No FPL Data Available</h3>
            <p className="text-gray-400 mb-4">Click the button below to fetch the latest FPL data.</p>
            <button
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
            >
              {refreshMutation.isPending ? "Fetching..." : "Fetch FPL Data"}
            </button>
          </div>
        ) : (
          <div>
            {/* Optimal Team Tab */}
            {activeTab === "team" && advice.optimal_team && (
              <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                    <div className="text-sm text-gray-400">Expected Points</div>
                    <div className="text-2xl font-bold text-green-400">
                      {advice.optimal_team.expected_points}
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                    <div className="text-sm text-gray-400">Team Cost</div>
                    <div className="text-2xl font-bold text-white">
                      £{advice.optimal_team.total_cost}m
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                    <div className="text-sm text-gray-400">Budget Left</div>
                    <div className="text-2xl font-bold text-blue-400">
                      £{advice.optimal_team.budget_remaining}m
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                    <div className="text-sm text-gray-400">Captain</div>
                    <div className="text-xl font-bold text-yellow-400">
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
