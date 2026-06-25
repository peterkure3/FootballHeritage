import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';
import { api } from '../utils/api';
import { SPORTS, getSportByApiParam } from '../utils/constants';

const Sports = () => {
  const navigate = useNavigate();
  const [sports, setSports] = useState([]);
  const [categories, setCategories] = useState([]);
  const [sportsLoading, setSportsLoading] = useState(true);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [sportsError, setSportsError] = useState(null);
  const [categoriesError, setCategoriesError] = useState(null);
  const [selectedView, setSelectedView] = useState('sports');
  const [expandedSports, setExpandedSports] = useState(() => new Set());

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      setSportsLoading(true);
      setCategoriesLoading(true);

      const [sportsResult, categoriesResult] = await Promise.allSettled([
        api.getSports(),
        api.getSportsCategories(),
      ]);

      if (!isMounted) return;

      if (sportsResult.status === 'fulfilled') {
        setSports(sportsResult.value?.sports || []);
        setSportsError(null);
      } else {
        setSports([]);
        setSportsError('Unable to fetch sports right now.');
        toast.error('Failed to load sports data');
      }

      if (categoriesResult.status === 'fulfilled') {
        setCategories(categoriesResult.value?.categories || []);
        setCategoriesError(null);
      } else {
        setCategories([]);
        setCategoriesError('Unable to fetch bet categories.');
      }

      setSportsLoading(false);
      setCategoriesLoading(false);
    };

    loadData();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleSportClick = (sportName) => {
    const sportConfig = getSportByApiParam(sportName);
    const sportParam = sportConfig ? sportConfig.apiParam : sportName;
    navigate(`/odds?sport=${encodeURIComponent(sportParam)}`);
  };

  const handleLeagueClick = (sportName, leagueName) => {
    const sportConfig = getSportByApiParam(sportName);
    const sportParam = sportConfig ? sportConfig.apiParam : sportName;
    navigate(`/odds?sport=${encodeURIComponent(sportParam)}&league=${encodeURIComponent(leagueName)}`);
  };

  const totals = useMemo(() => {
    const totalEvents = sports.reduce((sum, sport) => sum + (sport.event_count || 0), 0);
    const totalLeagues = sports.reduce((sum, sport) => sum + (sport.leagues?.length || 0), 0);
    return {
      totalSports: sports.length,
      totalEvents,
      totalLeagues,
    };
  }, [sports]);

  const toggleSportExpansion = (sportName) => {
    setExpandedSports((prev) => {
      const next = new Set(prev);
      if (next.has(sportName)) {
        next.delete(sportName);
      } else {
        next.add(sportName);
      }
      return next;
    });
  };

  const navigateToPredictions = (sportName) => {
    const sportConfig = getSportByApiParam(sportName);
    const sportParam = sportConfig ? sportConfig.apiParam : sportName;
    navigate(`/predictions?sport=${encodeURIComponent(sportParam)}`);
  };

  const initialLoading = sportsLoading && sports.length === 0;

  if (initialLoading) {
    return (
      <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
        <Navbar />
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-400">Loading sports...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight">
              Sports & Betting Markets
            </h1>
            <span className="text-2xl">🏆</span>
          </div>
          <p className="text-sm" style={{ color: '#64748b' }}>Explore our wide range of sports and betting options</p>
        </div>

        {/* View Toggle */}
        <div className="flex gap-4 mt-8 mb-8 flex-wrap" style={{ animation: 'slide-up 0.4s ease-out 0.06s both' }}>
          <button
            onClick={() => setSelectedView('sports')}
            className="px-6 py-3 rounded-lg font-semibold text-sm transition-all"
            style={{
              background: selectedView === 'sports' ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--color-card)',
              color: selectedView === 'sports' ? 'white' : '#94a3b8',
              border: selectedView === 'sports' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--color-card-border)',
            }}
            type="button"
            aria-pressed={selectedView === 'sports'}
          >
            🏆 Sports & Leagues
          </button>
          <button
            onClick={() => setSelectedView('categories')}
            className="px-6 py-3 rounded-lg font-semibold text-sm transition-all"
            style={{
              background: selectedView === 'categories' ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--color-card)',
              color: selectedView === 'categories' ? 'white' : '#94a3b8',
              border: selectedView === 'categories' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--color-card-border)',
            }}
            type="button"
            aria-pressed={selectedView === 'categories'}
          >
            📊 Bet Types
          </button>
          <button
            onClick={() => navigate('/predictions')}
            className="px-6 py-3 rounded-lg font-semibold text-sm transition-all card-glow flex items-center gap-2"
            style={{
              background: 'var(--color-card)',
              color: '#94a3b8',
              border: '1px solid var(--color-card-border)',
            }}
            type="button"
          >
            🤖 Predictions
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Sports View */}
        {selectedView === 'sports' && (
          <div>
            {/* Stats Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 stagger-children">
              <div className="card-glow rounded-xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs mb-1" style={{ color: '#64748b' }}>Total Sports</p>
                    <p className="text-3xl font-bold text-white font-[Oswald] tracking-tight">{totals.totalSports}</p>
                  </div>
                  <span className="text-4xl">🏅</span>
                </div>
              </div>
              <div className="card-glow rounded-xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs mb-1" style={{ color: '#64748b' }}>Total Events</p>
                    <p className="text-3xl font-bold font-[Oswald] tracking-tight" style={{ color: '#10b981' }}>
                      {totals.totalEvents}
                    </p>
                  </div>
                  <span className="text-4xl">📅</span>
                </div>
              </div>
              <div className="card-glow rounded-xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs mb-1" style={{ color: '#64748b' }}>Active Leagues</p>
                    <p className="text-3xl font-bold font-[Oswald] tracking-tight" style={{ color: '#6366f1' }}>
                      {totals.totalLeagues}
                    </p>
                  </div>
                  <span className="text-4xl">🏆</span>
                </div>
              </div>
            </div>

            {/* Sports Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-children">
              {sportsError && (
                <div className="col-span-full rounded-xl p-4 text-center border" style={{ background: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>
                  {sportsError}
                </div>
              )}
              {!sportsError && sports.length === 0 && !sportsLoading && (
                <div className="col-span-full text-center py-16">
                  <div className="text-6xl mb-4">🏅</div>
                  <h3 className="text-xl font-semibold mb-2" style={{ color: '#94a3b8' }}>No Sports Available</h3>
                  <p style={{ color: '#64748b' }}>Check back soon for upcoming events</p>
                </div>
              )}
              {sports.map((sport) => {
                const isExpanded = expandedSports.has(sport.name);
                return (
                  <div
                    key={sport.name}
                    className="card-glow rounded-xl border overflow-hidden group"
                    style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}
                  >
                    {/* Sport Header */}
                    <button
                      type="button"
                      onClick={() => handleSportClick(sport.name)}
                      className="p-6 cursor-pointer hover:opacity-90 transition-all w-full text-left"
                      aria-label={`View odds for ${sport.display_name}`}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <span className="text-4xl">{sport.icon}</span>
                          <div>
                            <h3 className="text-xl font-bold text-white font-[Oswald] tracking-tight group-hover:text-green-400 transition-colors">
                              {sport.display_name}
                            </h3>
                            <p className="text-xs" style={{ color: '#64748b' }}>
                              {sport.event_count} {sport.event_count === 1 ? 'event' : 'events'}
                            </p>
                          </div>
                        </div>
                        {sport.active && (
                          <span className="px-3 py-1 text-xs font-semibold rounded-full border" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', borderColor: 'rgba(16, 185, 129, 0.5)' }}>
                            LIVE
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        <p className="text-xs uppercase" style={{ color: '#64748b' }}>
                          Leagues Available: {sport.leagues.length}
                        </p>
                        {sport.leagues.length > 0 && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleSportExpansion(sport.name);
                            }}
                            className="text-sm hover:underline"
                            style={{ color: '#10b981' }}
                            aria-expanded={isExpanded}
                          >
                            {isExpanded ? 'Hide leagues' : 'View leagues'}
                          </button>
                        )}
                      </div>

                      {/* Leagues */}
                      {isExpanded && sport.leagues.length > 0 && (
                        <div className="space-y-2 mt-4">
                          <p className="text-xs uppercase font-semibold" style={{ color: '#64748b' }}>
                            Leagues ({sport.leagues.length})
                          </p>
                          <div className="space-y-2">
                            {sport.leagues.map((league) => (
                              <button
                                key={league.name}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleLeagueClick(sport.name, league.name);
                                }}
                                className="w-full flex items-center justify-between p-3 rounded-lg transition-all text-left card-glow"
                                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid transparent' }}
                              >
                                <span className="text-sm font-medium" style={{ color: '#cbd5e1' }}>
                                  {league.name}
                                </span>
                                <span className="text-xs font-semibold" style={{ color: '#10b981' }}>
                                  {league.upcoming_events} upcoming
                                </span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </button>

                    {/* View All Button */}
                    <div className="px-6 pb-6 space-y-2">
                      <button
                        onClick={() => handleSportClick(sport.name)}
                        className="w-full text-white py-2.5 rounded-lg font-semibold text-sm transition-all hover:opacity-90"
                        style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
                        type="button"
                      >
                        View All {sport.display_name} Odds
                      </button>
                      <button
                        onClick={() => navigateToPredictions(sport.name)}
                        className="w-full py-2.5 rounded-lg font-semibold text-sm transition-all card-glow flex items-center justify-center gap-2"
                        style={{
                          background: 'rgba(255,255,255,0.04)',
                          border: '1px solid var(--color-card-border)',
                          color: '#94a3b8',
                        }}
                        type="button"
                      >
                        AI Predictions for {sport.display_name}
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Categories View */}
        {selectedView === 'categories' && (
          <div>
            <div className="mb-6" style={{ animation: 'slide-up 0.4s ease-out 0.1s both' }}>
              <h2 className="text-2xl font-bold text-white font-[Oswald] tracking-tight mb-1">Bet Types & Categories</h2>
              <p className="text-sm" style={{ color: '#64748b' }}>Learn about different ways to bet on your favorite sports</p>
            </div>
            {categoriesLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-children">
                {[...Array(6)].map((_, index) => (
                  <div key={index} className="rounded-xl animate-pulse border" style={{ background: 'var(--color-card)', borderColor: 'var(--color-card-border)', height: '160px' }} />
                ))}
              </div>
            ) : categoriesError ? (
              <div className="rounded-xl p-6 text-center border" style={{ background: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>
                {categoriesError}
              </div>
            ) : categories.length === 0 ? (
              <div className="text-center py-16">
                <div className="text-6xl mb-4">📊</div>
                <h3 className="text-xl font-semibold mb-2" style={{ color: '#94a3b8' }}>No Bet Categories Available</h3>
                <p style={{ color: '#64748b' }}>Check back soon for more betting education.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-children">
                {categories.map((category) => (
                  <div
                    key={category.id}
                    className="card-glow rounded-xl border p-6 group"
                    style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}
                  >
                    <div className="flex items-start gap-4 mb-4">
                      <span className="text-4xl">{category.icon}</span>
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-white font-[Oswald] tracking-tight group-hover:text-green-400 transition-colors mb-2">
                          {category.name}
                        </h3>
                        <p className="text-sm" style={{ color: '#94a3b8' }}>
                          {category.description}
                        </p>
                      </div>
                    </div>

                    <div className="rounded-lg p-4 border card-glow" style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'var(--color-card-border)' }}>
                      <p className="text-xs uppercase font-semibold mb-2" style={{ color: '#64748b' }}>Example</p>
                      <p className="text-sm font-mono" style={{ color: '#94a3b8' }}>
                        {category.example}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Sports;
