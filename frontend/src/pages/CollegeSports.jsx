import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { api } from '../utils/api';

// NCAA Team logos mapping - using ESPN CDN for team logos
const NCAAB_TEAMS = {
  // Top 25 + Major Programs
  'Duke': { id: '150', color: '#003087', conference: 'ACC' },
  'North Carolina': { id: '153', color: '#7BAFD4', conference: 'ACC' },
  'Kentucky': { id: '96', color: '#0033A0', conference: 'SEC' },
  'Kansas': { id: '2305', color: '#0051BA', conference: 'Big 12' },
  'UCLA': { id: '26', color: '#2D68C4', conference: 'Big Ten' },
  'Gonzaga': { id: '2250', color: '#002967', conference: 'WCC' },
  'Villanova': { id: '222', color: '#13294B', conference: 'Big East' },
  'Michigan State': { id: '127', color: '#18453B', conference: 'Big Ten' },
  'UConn': { id: '41', color: '#0E1A3E', conference: 'Big East' },
  'Arizona': { id: '12', color: '#CC0033', conference: 'Big 12' },
  'Purdue': { id: '2509', color: '#CEB888', conference: 'Big Ten' },
  'Houston': { id: '248', color: '#C8102E', conference: 'Big 12' },
  'Tennessee': { id: '2633', color: '#FF8200', conference: 'SEC' },
  'Alabama': { id: '333', color: '#9E1B32', conference: 'SEC' },
  'Auburn': { id: '2', color: '#0C2340', conference: 'SEC' },
  'Baylor': { id: '239', color: '#154734', conference: 'Big 12' },
  'Texas': { id: '251', color: '#BF5700', conference: 'SEC' },
  'Indiana': { id: '84', color: '#990000', conference: 'Big Ten' },
  'Louisville': { id: '97', color: '#AD0000', conference: 'ACC' },
  'Syracuse': { id: '183', color: '#F76900', conference: 'ACC' },
  'Michigan': { id: '130', color: '#00274C', conference: 'Big Ten' },
  'Ohio State': { id: '194', color: '#BB0000', conference: 'Big Ten' },
  'Florida': { id: '57', color: '#0021A5', conference: 'SEC' },
  'Wisconsin': { id: '275', color: '#C5050C', conference: 'Big Ten' },
  'Iowa': { id: '2294', color: '#FFCD00', conference: 'Big Ten' },
  'Marquette': { id: '269', color: '#003366', conference: 'Big East' },
  'Creighton': { id: '156', color: '#005CA9', conference: 'Big East' },
  'St. Johns': { id: '2599', color: '#BA0C2F', conference: 'Big East' },
  'Arkansas': { id: '8', color: '#9D2235', conference: 'SEC' },
  'Illinois': { id: '356', color: '#E84A27', conference: 'Big Ten' },
  'Oregon': { id: '2483', color: '#154733', conference: 'Big Ten' },
  'Memphis': { id: '235', color: '#003087', conference: 'AAC' },
  'San Diego State': { id: '21', color: '#A6192E', conference: 'MWC' },
  'FAU': { id: '2226', color: '#003366', conference: 'AAC' },
  'Miami': { id: '2390', color: '#F47321', conference: 'ACC' },
};

// Get team logo URL from ESPN
const getTeamLogo = (teamName) => {
  const team = NCAAB_TEAMS[teamName];
  if (team) {
    return `https://a.espncdn.com/i/teamlogos/ncaa/500/${team.id}.png`;
  }
  // Fallback to a generic basketball icon
  return null;
};

const getTeamColor = (teamName) => {
  return NCAAB_TEAMS[teamName]?.color || '#6B7280';
};

const getTeamConference = (teamName) => {
  return NCAAB_TEAMS[teamName]?.conference || 'NCAA';
};

const CollegeSports = () => {
  const [ncaabGames, setNcaabGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all', 'live', 'upcoming', 'finished'

  useEffect(() => {
    fetchNcaabData();
    // Auto-refresh every 60 seconds for live games
    const interval = setInterval(fetchNcaabData, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchNcaabData = async () => {
    try {
      setLoading(true);
      // Fetch from backend events endpoint filtered by NCAAB
      const response = await api.getOdds();
      const events = response?.events || [];
      
      // Filter for basketball/NCAAB events
      const ncaabEvents = events.filter(event => 
        event.sport?.toLowerCase().includes('basketball') ||
        event.sport_key?.includes('ncaab') ||
        event.competition?.toLowerCase().includes('ncaa')
      );
      
      setNcaabGames(ncaabEvents);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch NCAAB data:', err);
      setError('Failed to load college basketball data');
    } finally {
      setLoading(false);
    }
  };

  const filteredGames = ncaabGames.filter(game => {
    if (filter === 'all') return true;
    if (filter === 'live') return game.status === 'LIVE' || game.status === 'IN_PROGRESS';
    if (filter === 'upcoming') return game.status === 'UPCOMING' || game.status === 'SCHEDULED';
    if (filter === 'finished') return game.status === 'FINISHED' || game.status === 'COMPLETED';
    return true;
  });

  const TeamCard = ({ teamName, score, isHome, isWinner }) => {
    const logoUrl = getTeamLogo(teamName);
    const teamColor = getTeamColor(teamName);
    
    return (
      <div className={`flex items-center gap-3 p-3 rounded-lg ${isWinner ? 'bg-green-900/30 border border-green-500/30' : 'bg-gray-800/50'}`}>
        <div 
          className="w-12 h-12 rounded-full flex items-center justify-center overflow-hidden"
          style={{ backgroundColor: teamColor + '20', border: `2px solid ${teamColor}` }}
        >
          {logoUrl ? (
            <img 
              src={logoUrl} 
              alt={teamName}
              className="w-10 h-10 object-contain"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'flex';
              }}
            />
          ) : null}
          <span 
            className="text-white font-bold text-sm"
            style={{ display: logoUrl ? 'none' : 'flex' }}
          >
            {teamName?.substring(0, 2).toUpperCase()}
          </span>
        </div>
        <div className="flex-1">
          <p className={`font-semibold ${isWinner ? 'text-green-400' : 'text-white'}`}>
            {teamName}
          </p>
          <p className="text-xs text-gray-400">
            {isHome ? 'Home' : 'Away'} • {getTeamConference(teamName)}
          </p>
        </div>
        {score !== null && score !== undefined && (
          <span className={`text-2xl font-bold ${isWinner ? 'text-green-400' : 'text-white'}`}>
            {score}
          </span>
        )}
      </div>
    );
  };

  const GameCard = ({ game }) => {
    const homeScore = game.home_score;
    const awayScore = game.away_score;
    const isFinished = game.status === 'FINISHED' || game.status === 'COMPLETED';
    const isLive = game.status === 'LIVE' || game.status === 'IN_PROGRESS';
    const homeWins = isFinished && homeScore > awayScore;
    const awayWins = isFinished && awayScore > homeScore;

    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden hover:border-orange-500/50 transition-all">
        {/* Header */}
        <div className="px-4 py-2 bg-gray-900/50 flex items-center justify-between">
          <span className="text-xs text-gray-400">
            {game.competition || 'NCAA Basketball'}
          </span>
          <span className={`px-2 py-1 rounded text-xs font-semibold ${
            isLive ? 'bg-red-500 text-white animate-pulse' :
            isFinished ? 'bg-gray-600 text-gray-300' :
            'bg-orange-500/20 text-orange-400'
          }`}>
            {isLive ? '🔴 LIVE' : isFinished ? 'Final' : 'Upcoming'}
          </span>
        </div>

        {/* Teams */}
        <div className="p-4 space-y-2">
          <TeamCard 
            teamName={game.away_team} 
            score={awayScore}
            isHome={false}
            isWinner={awayWins}
          />
          <div className="text-center text-gray-500 text-xs">VS</div>
          <TeamCard 
            teamName={game.home_team} 
            score={homeScore}
            isHome={true}
            isWinner={homeWins}
          />
        </div>

        {/* Footer with odds */}
        {!isFinished && game.odds && (
          <div className="px-4 py-3 bg-gray-900/30 border-t border-gray-700">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Spread</span>
              <span className="text-white font-medium">{game.odds.spread || 'N/A'}</span>
            </div>
            <div className="flex justify-between text-sm mt-1">
              <span className="text-gray-400">Total</span>
              <span className="text-white font-medium">{game.odds.total || 'N/A'}</span>
            </div>
          </div>
        )}

        {/* Game time */}
        <div className="px-4 py-2 bg-gray-900/50 text-center">
          <span className="text-xs text-gray-400">
            {new Date(game.commence_time || game.date).toLocaleString()}
          </span>
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
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl flex items-center justify-center shadow-lg">
              <span className="text-3xl">🏀</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">College Sports</h1>
              <p className="text-gray-400">NCAA Basketball • March Madness</p>
            </div>
          </div>

          {/* Quick Links */}
          <div className="flex flex-wrap gap-3 mt-6">
            <Link 
              to="/college/bracket"
              className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-semibold transition-colors flex items-center gap-2"
            >
              <span>🏆</span> March Madness Bracket
            </Link>
            <Link 
              to="/predictions?sport=ncaab"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-semibold transition-colors flex items-center gap-2"
            >
              <span>📊</span> NCAAB Predictions
            </Link>
            <Link 
              to="/odds?sport=basketball_ncaab"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-semibold transition-colors flex items-center gap-2"
            >
              <span>💰</span> NCAAB Odds
            </Link>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {['all', 'live', 'upcoming', 'finished'].map(tab => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                filter === tab 
                  ? 'bg-orange-500 text-white' 
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {tab === 'all' && '📋 All Games'}
              {tab === 'live' && '🔴 Live'}
              {tab === 'upcoming' && '📅 Upcoming'}
              {tab === 'finished' && '✅ Finished'}
            </button>
          ))}
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <p className="text-gray-400 text-sm">Total Games</p>
            <p className="text-2xl font-bold text-white">{ncaabGames.length}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <p className="text-gray-400 text-sm">Live Now</p>
            <p className="text-2xl font-bold text-red-400">
              {ncaabGames.filter(g => g.status === 'LIVE' || g.status === 'IN_PROGRESS').length}
            </p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <p className="text-gray-400 text-sm">Upcoming</p>
            <p className="text-2xl font-bold text-orange-400">
              {ncaabGames.filter(g => g.status === 'UPCOMING' || g.status === 'SCHEDULED').length}
            </p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <p className="text-gray-400 text-sm">Completed</p>
            <p className="text-2xl font-bold text-green-400">
              {ncaabGames.filter(g => g.status === 'FINISHED' || g.status === 'COMPLETED').length}
            </p>
          </div>
        </div>

        {/* Games Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-400 mb-4">{error}</p>
            <button 
              onClick={fetchNcaabData}
              className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg"
            >
              Retry
            </button>
          </div>
        ) : filteredGames.length === 0 ? (
          <div className="text-center py-20">
            <span className="text-6xl mb-4 block">🏀</span>
            <p className="text-gray-400 text-lg">No {filter !== 'all' ? filter : ''} games found</p>
            <p className="text-gray-500 text-sm mt-2">Check back later for more games</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredGames.map((game, index) => (
              <GameCard key={game.id || index} game={game} />
            ))}
          </div>
        )}

        {/* Top Teams Section */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-6">Top Programs</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {Object.entries(NCAAB_TEAMS).slice(0, 12).map(([name, team]) => (
              <div 
                key={name}
                className="bg-gray-800 rounded-xl p-4 border border-gray-700 hover:border-orange-500/50 transition-all cursor-pointer text-center"
              >
                <div 
                  className="w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-3 overflow-hidden"
                  style={{ backgroundColor: team.color + '20', border: `2px solid ${team.color}` }}
                >
                  <img 
                    src={`https://a.espncdn.com/i/teamlogos/ncaa/500/${team.id}.png`}
                    alt={name}
                    className="w-12 h-12 object-contain"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
                <p className="text-white font-semibold text-sm truncate">{name}</p>
                <p className="text-gray-400 text-xs">{team.conference}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CollegeSports;
