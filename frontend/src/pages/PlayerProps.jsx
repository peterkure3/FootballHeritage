import { useState } from 'react';
import { SPORTS } from '../utils/constants';
import Navbar from '../components/Navbar';

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
    <div className="min-h-screen" style={{ background: 'var(--color-surface, #0d0d14)' }}>
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl font-bold text-white font-[Oswald] tracking-tight">Player Props</h1>
            <span className="text-xl">⭐</span>
          </div>
          <p className="text-sm" style={{ color: '#64748b' }}>Player-specific betting markets across all sports</p>
        </div>

        {/* Sport Filters */}
        <div className="flex flex-wrap gap-2 mt-8 mb-8" style={{ animation: 'slide-up 0.4s ease-out 0.06s both' }}>
          <button
            onClick={() => { setSelectedSport('all'); fetchProps('all'); }}
            className="px-4 py-2 rounded-lg text-sm font-semibold transition-all"
            style={{
              background: selectedSport === 'all'
                ? 'linear-gradient(135deg, #10b981, #059669)'
                : 'var(--color-card, #14141f)',
              color: selectedSport === 'all' ? 'white' : '#94a3b8',
              border: selectedSport === 'all' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--color-card-border, #1f1f35)',
            }}
          >
            All Sports
          </button>
          {sportsList.map((sport) => (
            <button
              key={sport.key}
              onClick={() => { setSelectedSport(sport.apiParam); fetchProps(sport.apiParam); }}
              className="px-4 py-2 rounded-lg text-sm font-semibold transition-all flex items-center gap-2 card-glow"
              style={{
                background: selectedSport === sport.apiParam
                  ? 'linear-gradient(135deg, #10b981, #059669)'
                  : 'var(--color-card, #14141f)',
                color: selectedSport === sport.apiParam ? 'white' : '#94a3b8',
                border: selectedSport === sport.apiParam
                  ? '1px solid rgba(16, 185, 129, 0.3)'
                  : '1px solid var(--color-card-border, #1f1f35)',
              }}
            >
              <span>{sport.icon}</span>
              {sport.displayName}
            </button>
          ))}
        </div>

        {/* Loading */}
        {loading && (
          <div className="text-center py-16" style={{ animation: 'fade-in 0.2s ease-out' }}>
            <div
              className="w-8 h-8 rounded-full border-2 mx-auto mb-4 animate-spin"
              style={{
                borderColor: 'transparent',
                borderTopColor: '#10b981',
                boxShadow: '0 0 12px rgba(16, 185, 129, 0.3)',
              }}
            />
            <p className="text-sm" style={{ color: '#64748b' }}>Loading player props...</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div
            className="rounded-xl p-4 text-sm mb-8"
            style={{
              background: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              color: '#fca5a5',
              animation: 'fade-in 0.2s ease-out',
            }}
          >
            {error}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && props.length === 0 && (
          <div
            className="text-center py-20 rounded-xl border card-glow"
            style={{
              background: 'linear-gradient(135deg, var(--color-card, #14141f), var(--color-card-hover, #1a1a2e))',
              borderColor: 'var(--color-card-border, #1f1f35)',
              animation: 'slide-up 0.4s ease-out 0.1s both',
            }}
          >
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
              <span className="text-2xl">🎯</span>
            </div>
            <p className="text-white text-lg font-semibold mb-1 font-[Oswald]">No player props available yet</p>
            <p className="text-sm" style={{ color: '#64748b' }}>
              Player props will appear here once data is ingested from The Odds API
            </p>
          </div>
        )}

        {/* Props Grid */}
        {props.length > 0 && (
          <div className="grid gap-3 stagger-children">
            {props.map((prop) => (
              <div
                key={prop.id}
                className="rounded-xl p-4 border card-glow"
                style={{
                  background: 'linear-gradient(135deg, var(--color-card, #14141f), var(--color-card-hover, #1a1a2e))',
                  borderColor: 'var(--color-card-border, #1f1f35)',
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-white font-semibold">{prop.player_name}</span>
                    {prop.team && <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'rgba(100, 116, 139, 0.15)', color: '#64748b' }}>{prop.team}</span>}
                  </div>
                  <span className="text-xs" style={{ color: '#64748b' }}>{prop.league}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm" style={{ color: '#94a3b8' }}>
                    {prop.market.replace(/_/g, ' ')} — <span className="text-white font-mono">{prop.line}</span>
                  </span>
                  <div className="flex gap-2">
                    {prop.over_odds && (
                      <span className="font-mono text-xs font-bold px-3 py-1 rounded-lg" style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#34d399' }}>
                        O {prop.over_odds}
                      </span>
                    )}
                    {prop.under_odds && (
                      <span className="font-mono text-xs font-bold px-3 py-1 rounded-lg" style={{ background: 'rgba(239, 68, 68, 0.12)', color: '#f87171' }}>
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
