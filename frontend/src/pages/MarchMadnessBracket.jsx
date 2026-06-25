import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';

const TEAM_DATA = {
  'Duke': { id: '150', color: '#003087', seed: 1 },
  'North Carolina': { id: '153', color: '#7BAFD4', seed: 2 },
  'Kentucky': { id: '96', color: '#0033A0', seed: 3 },
  'Kansas': { id: '2305', color: '#0051BA', seed: 1 },
  'UCLA': { id: '26', color: '#2D68C4', seed: 4 },
  'Gonzaga': { id: '2250', color: '#002967', seed: 2 },
  'Villanova': { id: '222', color: '#13294B', seed: 5 },
  'Michigan State': { id: '127', color: '#18453B', seed: 6 },
  'UConn': { id: '41', color: '#0E1A3E', seed: 1 },
  'Arizona': { id: '12', color: '#CC0033', seed: 2 },
  'Purdue': { id: '2509', color: '#CEB888', seed: 1 },
  'Houston': { id: '248', color: '#C8102E', seed: 1 },
  'Tennessee': { id: '2633', color: '#FF8200', seed: 2 },
  'Alabama': { id: '333', color: '#9E1B32', seed: 4 },
  'Auburn': { id: '2', color: '#0C2340', seed: 4 },
  'Baylor': { id: '239', color: '#154734', seed: 3 },
  'Texas': { id: '251', color: '#BF5700', seed: 7 },
  'Indiana': { id: '84', color: '#990000', seed: 8 },
  'Louisville': { id: '97', color: '#AD0000', seed: 9 },
  'Syracuse': { id: '183', color: '#F76900', seed: 10 },
  'Michigan': { id: '130', color: '#00274C', seed: 11 },
  'Ohio State': { id: '194', color: '#BB0000', seed: 12 },
  'Florida': { id: '57', color: '#0021A5', seed: 5 },
  'Wisconsin': { id: '275', color: '#C5050C', seed: 6 },
  'Iowa': { id: '2294', color: '#FFCD00', seed: 8 },
  'Marquette': { id: '269', color: '#003366', seed: 2 },
  'Creighton': { id: '156', color: '#005CA9', seed: 3 },
  'St. Johns': { id: '2599', color: '#BA0C2F', seed: 6 },
  'Arkansas': { id: '8', color: '#9D2235', seed: 7 },
  'Illinois': { id: '356', color: '#E84A27', seed: 5 },
  'Oregon': { id: '2483', color: '#154733', seed: 11 },
  'Memphis': { id: '235', color: '#003087', seed: 8 },
};

const generateSampleBracket = () => {
  const teams = Object.keys(TEAM_DATA);
  const regions = ['East', 'West', 'South', 'Midwest'];

  return regions.map(region => ({
    name: region,
    rounds: [
      {
        name: 'Round of 64',
        games: Array(8).fill(null).map((_, i) => ({
          id: `${region}-r64-${i}`,
          team1: { name: teams[i % teams.length], seed: (i * 2 + 1), score: null },
          team2: { name: teams[(i + 8) % teams.length], seed: (16 - i * 2), score: null },
          winner: null,
          status: 'upcoming'
        }))
      },
      {
        name: 'Round of 32',
        games: Array(4).fill(null).map((_, i) => ({
          id: `${region}-r32-${i}`,
          team1: null,
          team2: null,
          winner: null,
          status: 'pending'
        }))
      },
      {
        name: 'Sweet 16',
        games: Array(2).fill(null).map((_, i) => ({
          id: `${region}-s16-${i}`,
          team1: null,
          team2: null,
          winner: null,
          status: 'pending'
        }))
      },
      {
        name: 'Elite 8',
        games: [{
          id: `${region}-e8-0`,
          team1: null,
          team2: null,
          winner: null,
          status: 'pending'
        }]
      }
    ]
  }));
};

const CONFERENCES = ['All', 'ACC', 'Big Ten', 'Big 12', 'SEC', 'Big East', 'Pac-12', 'AAC', 'WCC', 'MWC'];

const ROUNDS = ['All Rounds', 'Round of 64', 'Round of 32', 'Sweet 16', 'Elite 8', 'Final Four', 'Championship'];

const GAME_STATUS = ['All Games', 'Live', 'Upcoming', 'Finished'];

const MarchMadnessBracket = () => {
  const [bracket, setBracket] = useState(generateSampleBracket());
  const [finalFour, setFinalFour] = useState([
    { id: 'ff-1', team1: null, team2: null, winner: null, status: 'pending' },
    { id: 'ff-2', team1: null, team2: null, winner: null, status: 'pending' }
  ]);
  const [championship, setChampionship] = useState({
    id: 'championship',
    team1: null,
    team2: null,
    winner: null,
    status: 'pending'
  });
  const [selectedRegion, setSelectedRegion] = useState('East');
  const [viewMode, setViewMode] = useState('region');
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRound, setSelectedRound] = useState('All Rounds');
  const [selectedConference, setSelectedConference] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All Games');
  const [showFilters, setShowFilters] = useState(false);
  const [highlightedTeam, setHighlightedTeam] = useState(null);

  useEffect(() => {
    const fetchBracketData = async () => {
      setLastUpdate(new Date());
    };

    fetchBracketData();
    const interval = setInterval(fetchBracketData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getTeamLogo = (teamName) => {
    const team = TEAM_DATA[teamName];
    if (team) {
      return `https://a.espncdn.com/i/teamlogos/ncaa/500/${team.id}.png`;
    }
    return null;
  };

  const getTeamColor = (teamName) => {
    return TEAM_DATA[teamName]?.color || '#6B7280';
  };

  const getTeamConference = (teamName) => {
    const conferenceMap = {
      'Duke': 'ACC', 'North Carolina': 'ACC', 'Louisville': 'ACC', 'Syracuse': 'ACC', 'Miami': 'ACC',
      'Kentucky': 'SEC', 'Tennessee': 'SEC', 'Alabama': 'SEC', 'Auburn': 'SEC', 'Florida': 'SEC', 'Arkansas': 'SEC', 'Texas': 'SEC',
      'Kansas': 'Big 12', 'Baylor': 'Big 12', 'Houston': 'Big 12', 'Arizona': 'Big 12',
      'UCLA': 'Big Ten', 'Michigan State': 'Big Ten', 'Purdue': 'Big Ten', 'Indiana': 'Big Ten', 'Michigan': 'Big Ten',
      'Ohio State': 'Big Ten', 'Wisconsin': 'Big Ten', 'Iowa': 'Big Ten', 'Illinois': 'Big Ten', 'Oregon': 'Big Ten',
      'Gonzaga': 'WCC',
      'Villanova': 'Big East', 'UConn': 'Big East', 'Marquette': 'Big East', 'Creighton': 'Big East', 'St. Johns': 'Big East',
      'Memphis': 'AAC',
      'San Diego State': 'MWC',
    };
    return conferenceMap[teamName] || 'NCAA';
  };

  const filterGame = (game, roundName) => {
    if (selectedRound !== 'All Rounds' && roundName !== selectedRound) {
      return false;
    }

    if (selectedStatus !== 'All Games') {
      const statusMap = {
        'Live': ['live', 'in_progress'],
        'Upcoming': ['upcoming', 'pending', 'scheduled'],
        'Finished': ['finished', 'completed']
      };
      const validStatuses = statusMap[selectedStatus] || [];
      if (!validStatuses.includes(game.status?.toLowerCase())) {
        return false;
      }
    }

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const team1Match = game.team1?.name?.toLowerCase().includes(term);
      const team2Match = game.team2?.name?.toLowerCase().includes(term);
      if (!team1Match && !team2Match) {
        return false;
      }
    }

    if (selectedConference !== 'All') {
      const team1Conf = game.team1 ? getTeamConference(game.team1.name) : null;
      const team2Conf = game.team2 ? getTeamConference(game.team2.name) : null;
      if (team1Conf !== selectedConference && team2Conf !== selectedConference) {
        return false;
      }
    }

    return true;
  };

  const isTeamHighlighted = (teamName) => {
    if (!teamName) return false;
    if (highlightedTeam && teamName.toLowerCase() === highlightedTeam.toLowerCase()) return true;
    if (searchTerm && teamName.toLowerCase().includes(searchTerm.toLowerCase())) return true;
    return false;
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedRound('All Rounds');
    setSelectedConference('All');
    setSelectedStatus('All Games');
    setHighlightedTeam(null);
  };

  const hasActiveFilters = searchTerm || selectedRound !== 'All Rounds' ||
    selectedConference !== 'All' || selectedStatus !== 'All Games';

  const TeamSlot = ({ team, isWinner, isLoser, size = 'normal' }) => {
    if (!team) {
      return (
        <div
          className={`card-glow rounded-xl p-4 border border-dashed flex items-center gap-2 ${size === 'large' ? 'p-3' : 'p-2'}`}
          style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
        >
          <div className={`${size === 'large' ? 'w-8 h-8' : 'w-6 h-6'} rounded-full`} style={{ background: 'var(--color-card)' }}></div>
          <span className="text-sm" style={{ color: '#64748b' }}>TBD</span>
        </div>
      );
    }

    const logoUrl = getTeamLogo(team.name);
    const teamColor = getTeamColor(team.name);
    const highlighted = isTeamHighlighted(team.name);

    return (
      <div
        className={`card-glow rounded-xl p-4 border flex items-center gap-2 transition-all ${size === 'large' ? 'p-3' : 'p-2'}`}
        onClick={() => team.name && setHighlightedTeam(highlightedTeam === team.name ? null : team.name)}
        style={{
          background: highlighted
            ? 'rgba(250, 204, 21, 0.15)'
            : isWinner
              ? 'rgba(16, 185, 129, 0.08)'
              : 'var(--color-card)',
          borderColor: highlighted
            ? 'rgba(250, 204, 21, 0.5)'
            : isWinner
              ? 'rgba(16, 185, 129, 0.3)'
              : 'var(--color-card-border)',
          opacity: isLoser ? 0.5 : 1,
          cursor: 'pointer'
        }}
      >
        <span className={`${size === 'large' ? 'text-sm' : 'text-xs'} font-bold w-5`} style={{ color: '#10b981' }}>
          {team.seed}
        </span>
        <div
          className={`${size === 'large' ? 'w-8 h-8' : 'w-6 h-6'} rounded-full flex items-center justify-center overflow-hidden`}
          style={{ backgroundColor: teamColor + '20', border: `1px solid ${teamColor}` }}
        >
          {logoUrl && (
            <img
              src={logoUrl}
              alt={team.name}
              className={`${size === 'large' ? 'w-6 h-6' : 'w-5 h-5'} object-contain`}
              onError={(e) => e.target.style.display = 'none'}
            />
          )}
        </div>
        <span className={`${size === 'large' ? 'text-sm' : 'text-xs'} font-medium text-white truncate flex-1`}>
          {team.name}
        </span>
        {team.score !== null && (
          <span className={`${size === 'large' ? 'text-lg' : 'text-sm'} font-bold`} style={{ color: isWinner ? '#10b981' : 'white' }}>
            {team.score}
          </span>
        )}
      </div>
    );
  };

  const GameCard = ({ game, roundName }) => {
    const isFinished = game.status === 'finished';
    const isLive = game.status === 'live';
    const team1Wins = isFinished && game.winner === game.team1?.name;
    const team2Wins = isFinished && game.winner === game.team2?.name;

    return (
      <div
        className="card-glow rounded-xl p-4 border overflow-hidden"
        style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
      >
        {isLive && (
          <div
            className="text-white text-xs font-bold px-2 py-1 text-center animate-pulse"
            style={{ background: '#ef4444' }}
          >
            🔴 LIVE
          </div>
        )}
        <div className="p-2 space-y-1">
          <TeamSlot team={game.team1} isWinner={team1Wins} isLoser={team2Wins && isFinished} />
          <TeamSlot team={game.team2} isWinner={team2Wins} isLoser={team1Wins && isFinished} />
        </div>
      </div>
    );
  };

  const RegionBracket = ({ region }) => {
    const filteredRounds = selectedRound === 'All Rounds'
      ? region.rounds
      : region.rounds.filter(r => r.name === selectedRound);

    if (filteredRounds.length === 0) {
      return (
        <div className="text-center py-8" style={{ color: '#94a3b8' }}>
          No games match the current filters in {region.name} Region
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="w-3 h-3 rounded-full" style={{ background: '#10b981' }}></span>
          {region.name} Region
        </h3>

        <div className="flex gap-4 overflow-x-auto pb-4">
          {filteredRounds.map((round, roundIndex) => {
            const filteredGames = round.games.filter(game => filterGame(game, round.name));

            if (filteredGames.length === 0 && hasActiveFilters) {
              return (
                <div key={round.name} className="flex-shrink-0 w-48">
                  <h4 className="text-sm font-semibold mb-3 text-center" style={{ color: '#94a3b8' }}>
                    {round.name}
                  </h4>
                  <div
                    className="card-glow rounded-xl p-4 border border-dashed text-center"
                    style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
                  >
                    <span className="text-sm" style={{ color: '#64748b' }}>No matches</span>
                  </div>
                </div>
              );
            }

            return (
              <div key={round.name} className="flex-shrink-0">
                <h4 className="text-sm font-semibold mb-3 text-center" style={{ color: '#94a3b8' }}>
                  {round.name}
                  {hasActiveFilters && filteredGames.length !== round.games.length && (
                    <span className="ml-2 text-xs" style={{ color: '#10b981' }}>
                      ({filteredGames.length}/{round.games.length})
                    </span>
                  )}
                </h4>
                <div className="space-y-2" style={{ marginTop: `${roundIndex * 20}px` }}>
                  {(hasActiveFilters ? filteredGames : round.games).map((game, gameIndex) => (
                    <div
                      key={game.id}
                      className="w-48"
                      style={{ marginTop: gameIndex > 0 ? `${Math.pow(2, roundIndex) * 8}px` : 0 }}
                    >
                      <GameCard game={game} roundName={round.name} />
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const FinalFourBracket = () => {
    return (
      <div
        className="card-glow rounded-xl p-6 border"
        style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}
      >
        <h3 className="text-2xl font-bold text-white text-center mb-6 flex items-center justify-center gap-2 font-[Oswald] tracking-tight">
          <span className="text-3xl">🏆</span>
          Final Four & Championship
        </h3>

        <div className="flex flex-col md:flex-row items-center justify-center gap-8">
          <div className="w-64">
            <h4 className="text-sm font-semibold mb-2 text-center" style={{ color: '#94a3b8' }}>Semi-Final 1</h4>
            <div
              className="card-glow rounded-xl p-4 border space-y-2"
              style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
            >
              <TeamSlot team={finalFour[0].team1} size="large" />
              <TeamSlot team={finalFour[0].team2} size="large" />
            </div>
          </div>

          <div className="w-72">
            <h4 className="text-sm font-semibold mb-2 text-center" style={{ color: '#10b981' }}>🏆 Championship</h4>
            <div
              className="card-glow rounded-xl p-4 border space-y-3"
              style={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.1), rgba(5,150,105,0.1))', borderColor: '#10b981' }}
            >
              <TeamSlot team={championship.team1} size="large" />
              <div className="text-center font-bold" style={{ color: '#10b981' }}>VS</div>
              <TeamSlot team={championship.team2} size="large" />
            </div>
            {championship.winner && (
              <div className="mt-4 text-center">
                <span className="text-lg" style={{ color: '#34d399' }}>👑 Champion</span>
                <p className="text-white font-bold text-xl">{championship.winner}</p>
              </div>
            )}
          </div>

          <div className="w-64">
            <h4 className="text-sm font-semibold mb-2 text-center" style={{ color: '#94a3b8' }}>Semi-Final 2</h4>
            <div
              className="card-glow rounded-xl p-4 border space-y-2"
              style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}
            >
              <TeamSlot team={finalFour[1].team1} size="large" />
              <TeamSlot team={finalFour[1].team2} size="large" />
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 py-8">
        <header style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <p className="text-sm uppercase tracking-wide font-semibold mb-2" style={{ color: '#10b981' }}>NCAA Tournament</p>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-yellow-500 rounded-2xl flex items-center justify-center shadow-lg">
                <span className="text-3xl">🏆</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white font-[Oswald] tracking-tight">March Madness Bracket</h1>
                <p className="text-sm" style={{ color: '#64748b' }}>NCAA Tournament 2026</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <span className="text-xs" style={{ color: '#64748b' }}>
                Last updated: {lastUpdate.toLocaleTimeString()}
              </span>
              <Link
                to="/college"
                className="card-glow rounded-lg py-3 px-4 font-semibold transition-all hover:opacity-90"
                style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', color: '#cbd5e1' }}
              >
                ← Back to College Sports
              </Link>
            </div>
          </div>
        </header>

        <div className="flex flex-wrap items-center gap-2 mb-6">
          <button
            onClick={() => setViewMode('region')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${viewMode === 'region' ? 'text-white font-semibold' : 'card-glow'}`}
            style={viewMode === 'region'
              ? { background: 'linear-gradient(135deg, #10b981, #059669)' }
              : { background: 'var(--color-card)', border: '1px solid var(--color-card-border)', color: '#94a3b8' }
            }
          >
            By Region
          </button>
          <button
            onClick={() => setViewMode('full')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${viewMode === 'full' ? 'text-white font-semibold' : 'card-glow'}`}
            style={viewMode === 'full'
              ? { background: 'linear-gradient(135deg, #10b981, #059669)' }
              : { background: 'var(--color-card)', border: '1px solid var(--color-card-border)', color: '#94a3b8' }
            }
          >
            Full Bracket
          </button>

          <div className="flex-1"></div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`card-glow rounded-lg px-4 py-2 font-medium transition-all flex items-center gap-2`}
            style={{
              background: showFilters || hasActiveFilters ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--color-card)',
              border: showFilters || hasActiveFilters ? 'none' : '1px solid var(--color-card-border)',
              color: showFilters || hasActiveFilters ? 'white' : '#94a3b8'
            }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            Filters
            {hasActiveFilters && (
              <span
                className="text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold"
                style={{ background: 'white', color: '#10b981' }}
              >
                !
              </span>
            )}
          </button>
        </div>

        {showFilters && (
          <div
            className="card-glow rounded-xl p-6 border space-y-4 mb-6"
            style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Filter Bracket</h3>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="text-sm flex items-center gap-1"
                  style={{ color: '#fca5a5' }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Clear All
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm mb-2" style={{ color: '#94a3b8' }}>Search Team</label>
                <div className="relative">
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="e.g., Duke, Kentucky..."
                    className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                    style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                  />
                  {searchTerm && (
                    <button
                      onClick={() => setSearchTerm('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 hover:text-white"
                      style={{ color: '#64748b' }}
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm mb-2" style={{ color: '#94a3b8' }}>Round</label>
                <select
                  value={selectedRound}
                  onChange={(e) => setSelectedRound(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                  style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                >
                  {ROUNDS.map(round => (
                    <option key={round} value={round}>{round}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm mb-2" style={{ color: '#94a3b8' }}>Conference</label>
                <select
                  value={selectedConference}
                  onChange={(e) => setSelectedConference(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                  style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                >
                  {CONFERENCES.map(conf => (
                    <option key={conf} value={conf}>{conf}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm mb-2" style={{ color: '#94a3b8' }}>Game Status</label>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                  style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', '--tw-ring-color': '#10b981' }}
                >
                  {GAME_STATUS.map(status => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </select>
              </div>
            </div>

            {hasActiveFilters && (
              <div className="flex flex-wrap gap-2 pt-2" style={{ borderTop: '1px solid var(--color-card-border)' }}>
                <span className="text-sm" style={{ color: '#94a3b8' }}>Active:</span>
                {searchTerm && (
                  <span className="px-2 py-1 rounded text-xs flex items-center gap-1" style={{ background: 'rgba(234,179,8,0.2)', color: '#eab308' }}>
                    Team: {searchTerm}
                    <button onClick={() => setSearchTerm('')} className="hover:text-white">✕</button>
                  </span>
                )}
                {selectedRound !== 'All Rounds' && (
                  <span className="px-2 py-1 rounded text-xs flex items-center gap-1" style={{ background: 'rgba(59,130,246,0.2)', color: '#60a5fa' }}>
                    {selectedRound}
                    <button onClick={() => setSelectedRound('All Rounds')} className="hover:text-white">✕</button>
                  </span>
                )}
                {selectedConference !== 'All' && (
                  <span className="px-2 py-1 rounded text-xs flex items-center gap-1" style={{ background: 'rgba(168,85,247,0.2)', color: '#a78bfa' }}>
                    {selectedConference}
                    <button onClick={() => setSelectedConference('All')} className="hover:text-white">✕</button>
                  </span>
                )}
                {selectedStatus !== 'All Games' && (
                  <span className="px-2 py-1 rounded text-xs flex items-center gap-1" style={{ background: 'rgba(16,185,129,0.2)', color: '#34d399' }}>
                    {selectedStatus}
                    <button onClick={() => setSelectedStatus('All Games')} className="hover:text-white">✕</button>
                  </span>
                )}
              </div>
            )}

            {highlightedTeam && (
              <div
                className="flex items-center gap-3 p-3 rounded-lg"
                style={{ background: 'rgba(250, 204, 21, 0.1)', border: '1px solid rgba(250, 204, 21, 0.3)' }}
              >
                <span style={{ color: '#eab308' }}>🔍</span>
                <span className="text-white">
                  Tracking <strong>{highlightedTeam}</strong> through the bracket
                </span>
                <button
                  onClick={() => setHighlightedTeam(null)}
                  className="ml-auto"
                  style={{ color: '#eab308' }}
                >
                  Clear
                </button>
              </div>
            )}
          </div>
        )}

        {viewMode === 'region' && (
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {bracket.map(region => (
              <button
                key={region.name}
                onClick={() => setSelectedRegion(region.name)}
                className={`px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${selectedRegion === region.name ? 'text-white font-semibold' : 'card-glow'}`}
                style={selectedRegion === region.name
                  ? { background: 'linear-gradient(135deg, #10b981, #059669)' }
                  : { background: 'var(--color-card)', border: '1px solid var(--color-card-border)', color: '#94a3b8' }
                }
              >
                {region.name}
              </button>
            ))}
            <button
              onClick={() => setSelectedRegion('Final Four')}
              className={`px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${selectedRegion === 'Final Four' ? 'text-white font-semibold' : 'card-glow'}`}
              style={selectedRegion === 'Final Four'
                ? { background: 'linear-gradient(135deg, #10b981, #059669)' }
                : { background: 'var(--color-card)', border: '1px solid var(--color-card-border)', color: '#94a3b8' }
              }
            >
              🏆 Final Four
            </button>
          </div>
        )}

        {viewMode === 'region' ? (
          selectedRegion === 'Final Four' ? (
            <FinalFourBracket />
          ) : (
            <RegionBracket region={bracket.find(r => r.name === selectedRegion)} />
          )
        ) : (
          <div className="space-y-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {bracket.map(region => (
                <div
                  key={region.name}
                  className="card-glow rounded-xl p-4 border"
                  style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}
                >
                  <RegionBracket region={region} />
                </div>
              ))}
            </div>
            <FinalFourBracket />
          </div>
        )}

        <div
          className="card-glow rounded-xl p-6 border mt-8"
          style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}
        >
          <h4 className="text-sm font-semibold mb-3" style={{ color: '#94a3b8' }}>Legend</h4>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded" style={{ background: 'rgba(16,185,129,0.4)', border: '1px solid #10b981' }}></div>
              <span style={{ color: '#cbd5e1' }}>Winner</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded animate-pulse" style={{ background: '#ef4444' }}></div>
              <span style={{ color: '#cbd5e1' }}>Live Game</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded border border-dashed" style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)' }}></div>
              <span style={{ color: '#cbd5e1' }}>TBD</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-bold" style={{ color: '#10b981' }}>1</span>
              <span style={{ color: '#cbd5e1' }}>Seed Number</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarchMadnessBracket;
