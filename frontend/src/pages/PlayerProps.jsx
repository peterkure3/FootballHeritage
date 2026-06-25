import { useState } from 'react';
import { SPORTS } from '../utils/constants';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

const SPORT_PARAM_MAP = {
  nfl: 'americanfootball',
  hockey: 'icehockey',
};

const PlayerProps = () => {
  const [selectedSport, setSelectedSport] = useState('all');
  const [props, setProps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sportsList = Object.values(SPORTS).filter(s => s.key !== 'NBA_CUP');

  const fetchProps = async (sport) => {
    setLoading(true);
    setError(null);
    try {
      const dbSport = SPORT_PARAM_MAP[sport] || sport;
      const params = sport !== 'all' ? `?sport=${dbSport}` : '';
      const res = await fetch(`${API_BASE}/player-props${params}`);
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      setProps(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Player Props</h1>
          <p className="text-gray-400">Player-specific betting markets across all sports</p>
        </div>

        <div className="flex flex-wrap gap-3 mb-8">
          <button
            onClick={() => { setSelectedSport('all'); fetchProps('all'); }}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
              selectedSport === 'all'
                ? 'bg-green-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            All Sports
          </button>
          {sportsList.map((sport) => (
            <button
              key={sport.key}
              onClick={() => { setSelectedSport(sport.apiParam); fetchProps(sport.apiParam); }}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 ${
                selectedSport === sport.apiParam
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              <span>{sport.icon}</span>
              {sport.displayName}
            </button>
          ))}
        </div>

        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-green-500 mx-auto mb-4" />
            <p className="text-gray-400">Loading player props...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-900/30 border border-red-800 rounded-lg p-4 text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && props.length === 0 && (
          <div className="text-center py-16 bg-gray-800/50 rounded-xl border border-gray-700">
            <p className="text-4xl mb-4">🎯</p>
            <p className="text-gray-400 text-lg">No player props available yet</p>
            <p className="text-gray-600 text-sm mt-2">
              Player props will appear here once data is ingested from The Odds API
            </p>
          </div>
        )}

        {props.length > 0 && (
          <div className="grid gap-4">
            {props.map((prop) => (
              <div key={prop.id} className="bg-gray-800/70 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="text-white font-semibold">{prop.player_name}</span>
                    {prop.team && <span className="text-gray-500 text-sm ml-2">{prop.team}</span>}
                  </div>
                  <span className="text-xs text-gray-500">{prop.league}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">{prop.market} — {prop.line}</span>
                  <div className="flex gap-3">
                    {prop.over_odds && (
                      <span className="bg-green-900/40 text-green-300 px-3 py-1 rounded text-sm font-mono">
                        O {prop.over_odds}
                      </span>
                    )}
                    {prop.under_odds && (
                      <span className="bg-red-900/40 text-red-300 px-3 py-1 rounded text-sm font-mono">
                        U {prop.under_odds}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PlayerProps;
