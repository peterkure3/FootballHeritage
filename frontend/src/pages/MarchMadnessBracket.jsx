import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';

// NCAA Team data with ESPN IDs for logos
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

// Sample bracket data structure - in production this would come from API
const generateSampleBracket = () => {
  const teams = Object.keys(TEAM_DATA);
  const regions = ['East', 'West', 'South', 'Midwest'];
  
  return regions.map(region => ({
    name: region,
    rounds: [
      // Round of 64
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
      // Round of 32
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
      // Sweet 16
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
      // Elite 8
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

// Conference data for filtering
const CONFERENCES = ['All', 'ACC', 'Big Ten', 'Big 12', 'SEC', 'Big East', 'Pac-12', 'AAC', 'WCC', 'MWC'];

// Round names for filtering
const ROUNDS = ['All Rounds', 'Round of 64', 'Round of 32', 'Sweet 16', 'Elite 8', 'Final Four', 'Championship'];

// Game status options
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
  const [viewMode, setViewMode] = useState('region'); // 'region' or 'full'
  const [lastUpdate, setLastUpdate] = useState(new Date());
  
  // Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRound, setSelectedRound] = useState('All Rounds');
  const [selectedConference, setSelectedConference] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All Games');
  const [showFilters, setShowFilters] = useState(false);
  const [highlightedTeam, setHighlightedTeam] = useState(null);

  // Auto-refresh bracket data
  useEffect(() => {
    const fetchBracketData = async () => {
      // In production, fetch from API
      // const response = await api.getBracket();
      // setBracket(response.bracket);
      setLastUpdate(new Date());
    };

    fetchBracketData();
    const interval = setInterval(fetchBracketData, 30000); // Refresh every 30 seconds
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

  // Get team conference (would come from API in production)
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

  // Filter games based on criteria
  const filterGame = (game, roundName) => {
    // Round filter
    if (selectedRound !== 'All Rounds' && roundName !== selectedRound) {
      return false;
    }

    // Status filter
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

    // Team search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const team1Match = game.team1?.name?.toLowerCase().includes(term);
      const team2Match = game.team2?.name?.toLowerCase().includes(term);
      if (!team1Match && !team2Match) {
        return false;
      }
    }

    // Conference filter
    if (selectedConference !== 'All') {
      const team1Conf = game.team1 ? getTeamConference(game.team1.name) : null;
      const team2Conf = game.team2 ? getTeamConference(game.team2.name) : null;
      if (team1Conf !== selectedConference && team2Conf !== selectedConference) {
        return false;
      }
    }

    return true;
  };

  // Check if a team matches the search/highlight
  const isTeamHighlighted = (teamName) => {
    if (!teamName) return false;
    if (highlightedTeam && teamName.toLowerCase() === highlightedTeam.toLowerCase()) return true;
    if (searchTerm && teamName.toLowerCase().includes(searchTerm.toLowerCase())) return true;
    return false;
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchTerm('');
    setSelectedRound('All Rounds');
    setSelectedConference('All');
    setSelectedStatus('All Games');
    setHighlightedTeam(null);
  };

  // Check if any filters are active
  const hasActiveFilters = searchTerm || selectedRound !== 'All Rounds' || 
    selectedConference !== 'All' || selectedStatus !== 'All Games';

  const TeamSlot = ({ team, isWinner, isLoser, size = 'normal' }) => {
    if (!team) {
      return (
        <div className={`flex items-center gap-2 p-2 bg-gray-800/50 rounded border border-gray-700 border-dashed ${
          size === 'large' ? 'p-3' : 'p-2'
        }`}>
          <div className={`${size === 'large' ? 'w-8 h-8' : 'w-6 h-6'} rounded-full bg-gray-700`}></div>
          <span className="text-gray-500 text-sm">TBD</span>
        </div>
      );
    }

    const logoUrl = getTeamLogo(team.name);
    const teamColor = getTeamColor(team.name);
    const highlighted = isTeamHighlighted(team.name);

    return (
      <div 
        className={`flex items-center gap-2 rounded border transition-all ${
          size === 'large' ? 'p-3' : 'p-2'
        } ${
          highlighted
            ? 'bg-yellow-500/30 border-yellow-500 ring-2 ring-yellow-500/50'
            : isWinner 
              ? 'bg-green-900/40 border-green-500' 
              : isLoser 
                ? 'bg-gray-800/30 border-gray-700 opacity-50' 
                : 'bg-gray-800/50 border-gray-700 hover:border-orange-500/50'
        }`}
        onClick={() => team.name && setHighlightedTeam(highlightedTeam === team.name ? null : team.name)}
        style={{ cursor: 'pointer' }}
      >
        <span className={`${size === 'large' ? 'text-sm' : 'text-xs'} font-bold text-orange-400 w-5`}>
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
          <span className={`${size === 'large' ? 'text-lg' : 'text-sm'} font-bold ${isWinner ? 'text-green-400' : 'text-white'}`}>
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
      <div className="bg-gray-900/50 rounded-lg border border-gray-700 overflow-hidden">
        {isLive && (
          <div className="bg-red-500 text-white text-xs font-bold px-2 py-1 text-center animate-pulse">
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
    // Filter rounds based on selectedRound
    const filteredRounds = selectedRound === 'All Rounds' 
      ? region.rounds 
      : region.rounds.filter(r => r.name === selectedRound);

    if (filteredRounds.length === 0) {
      return (
        <div className="text-center py-8 text-gray-400">
          No games match the current filters in {region.name} Region
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-orange-500"></span>
          {region.name} Region
        </h3>
        
        <div className="flex gap-4 overflow-x-auto pb-4">
          {filteredRounds.map((round, roundIndex) => {
            // Filter games within the round
            const filteredGames = round.games.filter(game => filterGame(game, round.name));
            
            if (filteredGames.length === 0 && hasActiveFilters) {
              return (
                <div key={round.name} className="flex-shrink-0 w-48">
                  <h4 className="text-sm font-semibold text-gray-400 mb-3 text-center">
                    {round.name}
                  </h4>
                  <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700 border-dashed text-center">
                    <span className="text-gray-500 text-sm">No matches</span>
                  </div>
                </div>
              );
            }

            return (
              <div key={round.name} className="flex-shrink-0">
                <h4 className="text-sm font-semibold text-gray-400 mb-3 text-center">
                  {round.name}
                  {hasActiveFilters && filteredGames.length !== round.games.length && (
                    <span className="ml-2 text-xs text-orange-400">
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
      <div className="bg-gradient-to-br from-orange-900/20 to-gray-900 rounded-2xl border border-orange-500/30 p-6">
        <h3 className="text-2xl font-bold text-white text-center mb-6 flex items-center justify-center gap-2">
          <span className="text-3xl">🏆</span>
          Final Four & Championship
        </h3>
        
        <div className="flex flex-col md:flex-row items-center justify-center gap-8">
          {/* Left Semi-Final */}
          <div className="w-64">
            <h4 className="text-sm font-semibold text-gray-400 mb-2 text-center">Semi-Final 1</h4>
            <div className="bg-gray-900/50 rounded-lg border border-gray-700 p-3 space-y-2">
              <TeamSlot team={finalFour[0].team1} size="large" />
              <TeamSlot team={finalFour[0].team2} size="large" />
            </div>
          </div>

          {/* Championship */}
          <div className="w-72">
            <h4 className="text-sm font-semibold text-orange-400 mb-2 text-center">🏆 Championship</h4>
            <div className="bg-gradient-to-br from-orange-500/20 to-yellow-500/20 rounded-lg border-2 border-orange-500 p-4 space-y-3">
              <TeamSlot team={championship.team1} size="large" />
              <div className="text-center text-orange-400 font-bold">VS</div>
              <TeamSlot team={championship.team2} size="large" />
            </div>
            {championship.winner && (
              <div className="mt-4 text-center">
                <span className="text-yellow-400 text-lg">👑 Champion</span>
                <p className="text-white font-bold text-xl">{championship.winner}</p>
              </div>
            )}
          </div>

          {/* Right Semi-Final */}
          <div className="w-64">
            <h4 className="text-sm font-semibold text-gray-400 mb-2 text-center">Semi-Final 2</h4>
            <div className="bg-gray-900/50 rounded-lg border border-gray-700 p-3 space-y-2">
              <TeamSlot team={finalFour[1].team1} size="large" />
              <TeamSlot team={finalFour[1].team2} size="large" />
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-yellow-500 rounded-2xl flex items-center justify-center shadow-lg">
                <span className="text-3xl">🏆</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white">March Madness Bracket</h1>
                <p className="text-gray-400">NCAA Tournament 2026</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <span className="text-xs text-gray-500">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </span>
              <Link 
                to="/college"
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-semibold transition-colors"
              >
                ← Back to College Sports
              </Link>
            </div>
          </div>
        </div>

        {/* View Toggle & Filter Toggle */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <button
            onClick={() => setViewMode('region')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'region' 
                ? 'bg-orange-500 text-white' 
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            By Region
          </button>
          <button
            onClick={() => setViewMode('full')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'full' 
                ? 'bg-orange-500 text-white' 
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            Full Bracket
          </button>
          
          <div className="flex-1"></div>
          
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              showFilters || hasActiveFilters
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            Filters
            {hasActiveFilters && (
              <span className="bg-white text-blue-500 text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
                !
              </span>
            )}
          </button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="mb-6 p-4 bg-gray-800/50 rounded-xl border border-gray-700 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Filter Bracket</h3>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="text-sm text-red-400 hover:text-red-300 flex items-center gap-1"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Clear All
                </button>
              )}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Search by Team */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Search Team</label>
                <div className="relative">
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="e.g., Duke, Kentucky..."
                    className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-orange-500"
                  />
                  {searchTerm && (
                    <button
                      onClick={() => setSearchTerm('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>

              {/* Round Filter */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Round</label>
                <select
                  value={selectedRound}
                  onChange={(e) => setSelectedRound(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-orange-500"
                >
                  {ROUNDS.map(round => (
                    <option key={round} value={round}>{round}</option>
                  ))}
                </select>
              </div>

              {/* Conference Filter */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Conference</label>
                <select
                  value={selectedConference}
                  onChange={(e) => setSelectedConference(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-orange-500"
                >
                  {CONFERENCES.map(conf => (
                    <option key={conf} value={conf}>{conf}</option>
                  ))}
                </select>
              </div>

              {/* Game Status Filter */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Game Status</label>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-orange-500"
                >
                  {GAME_STATUS.map(status => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Active Filters Display */}
            {hasActiveFilters && (
              <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-700">
                <span className="text-sm text-gray-400">Active:</span>
                {searchTerm && (
                  <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs flex items-center gap-1">
                    Team: {searchTerm}
                    <button onClick={() => setSearchTerm('')} className="hover:text-white">✕</button>
                  </span>
                )}
                {selectedRound !== 'All Rounds' && (
                  <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs flex items-center gap-1">
                    {selectedRound}
                    <button onClick={() => setSelectedRound('All Rounds')} className="hover:text-white">✕</button>
                  </span>
                )}
                {selectedConference !== 'All' && (
                  <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs flex items-center gap-1">
                    {selectedConference}
                    <button onClick={() => setSelectedConference('All')} className="hover:text-white">✕</button>
                  </span>
                )}
                {selectedStatus !== 'All Games' && (
                  <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs flex items-center gap-1">
                    {selectedStatus}
                    <button onClick={() => setSelectedStatus('All Games')} className="hover:text-white">✕</button>
                  </span>
                )}
              </div>
            )}

            {/* Highlighted Team Info */}
            {highlightedTeam && (
              <div className="flex items-center gap-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <span className="text-yellow-400">🔍</span>
                <span className="text-white">
                  Tracking <strong>{highlightedTeam}</strong> through the bracket
                </span>
                <button
                  onClick={() => setHighlightedTeam(null)}
                  className="ml-auto text-yellow-400 hover:text-yellow-300"
                >
                  Clear
                </button>
              </div>
            )}
          </div>
        )}

        {/* Region Tabs (when in region view) */}
        {viewMode === 'region' && (
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {bracket.map(region => (
              <button
                key={region.name}
                onClick={() => setSelectedRegion(region.name)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                  selectedRegion === region.name 
                    ? 'bg-orange-500 text-white' 
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {region.name}
              </button>
            ))}
            <button
              onClick={() => setSelectedRegion('Final Four')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                selectedRegion === 'Final Four' 
                  ? 'bg-yellow-500 text-black' 
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              🏆 Final Four
            </button>
          </div>
        )}

        {/* Bracket Display */}
        {viewMode === 'region' ? (
          selectedRegion === 'Final Four' ? (
            <FinalFourBracket />
          ) : (
            <RegionBracket region={bracket.find(r => r.name === selectedRegion)} />
          )
        ) : (
          <div className="space-y-8">
            {/* Full bracket view */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {bracket.map(region => (
                <div key={region.name} className="bg-gray-800/30 rounded-xl p-4 border border-gray-700">
                  <RegionBracket region={region} />
                </div>
              ))}
            </div>
            <FinalFourBracket />
          </div>
        )}

        {/* Legend */}
        <div className="mt-8 p-4 bg-gray-800/50 rounded-xl border border-gray-700">
          <h4 className="text-sm font-semibold text-gray-400 mb-3">Legend</h4>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-green-500/40 border border-green-500"></div>
              <span className="text-gray-300">Winner</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-red-500 animate-pulse"></div>
              <span className="text-gray-300">Live Game</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-gray-700 border border-dashed border-gray-600"></div>
              <span className="text-gray-300">TBD</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-orange-400 font-bold">1</span>
              <span className="text-gray-300">Seed Number</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarchMadnessBracket;
