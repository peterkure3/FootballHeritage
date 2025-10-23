import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';
import useAuthStore from '../stores/authStore';

/**
 * Sports Page Component
 * 
 * Displays all supported sports, leagues, and bet categories
 * Provides quick navigation to filtered odds
 */

const Sports = () => {
  const navigate = useNavigate();
  const [sports, setSports] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedView, setSelectedView] = useState('sports'); // 'sports' or 'categories'

  useEffect(() => {
    fetchSportsData();
    fetchCategories();
  }, []);

  /**
   * Fetch sports and leagues data
   */
  const fetchSportsData = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('https://localhost:8080/api/v1/sports', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch sports data');
      }

      const data = await response.json();
      setSports(data.sports || []);
    } catch (error) {
      console.error('Error fetching sports:', error);
      toast.error('Failed to load sports data');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Fetch bet categories
   */
  const fetchCategories = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('https://localhost:8080/api/v1/sports/categories', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch categories');
      }

      const data = await response.json();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  /**
   * Navigate to odds page with sport filter
   */
  const handleSportClick = (sportName) => {
    navigate(`/odds?sport=${encodeURIComponent(sportName)}`);
  };

  /**
   * Navigate to odds page with league filter
   */
  const handleLeagueClick = (sportName, leagueName) => {
    navigate(`/odds?sport=${encodeURIComponent(sportName)}&league=${encodeURIComponent(leagueName)}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            Sports & Betting Markets
          </h1>
          <p className="text-gray-400">
            Explore our wide range of sports and betting options
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex gap-4 mb-8">
          <button
            onClick={() => setSelectedView('sports')}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              selectedView === 'sports'
                ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            🏆 Sports & Leagues
          </button>
          <button
            onClick={() => setSelectedView('categories')}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              selectedView === 'categories'
                ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            📊 Bet Types
          </button>
        </div>

        {/* Sports View */}
        {selectedView === 'sports' && (
          <div>
            {/* Stats Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm mb-1">Total Sports</p>
                    <p className="text-3xl font-bold text-white">{sports.length}</p>
                  </div>
                  <div className="text-4xl">🏅</div>
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm mb-1">Total Events</p>
                    <p className="text-3xl font-bold text-green-400">
                      {sports.reduce((sum, sport) => sum + sport.event_count, 0)}
                    </p>
                  </div>
                  <div className="text-4xl">📅</div>
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm mb-1">Active Leagues</p>
                    <p className="text-3xl font-bold text-blue-400">
                      {sports.reduce((sum, sport) => sum + sport.leagues.length, 0)}
                    </p>
                  </div>
                  <div className="text-4xl">🏆</div>
                </div>
              </div>
            </div>

            {/* Sports Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {sports.map((sport) => (
                <div
                  key={sport.name}
                  className="bg-gray-800 rounded-lg border border-gray-700 hover:border-green-500 transition-all overflow-hidden group"
                >
                  {/* Sport Header */}
                  <div
                    onClick={() => handleSportClick(sport.name)}
                    className="p-6 cursor-pointer hover:bg-gray-750 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <span className="text-4xl">{sport.icon}</span>
                        <div>
                          <h3 className="text-xl font-bold text-white group-hover:text-green-400 transition-colors">
                            {sport.display_name}
                          </h3>
                          <p className="text-sm text-gray-400">
                            {sport.event_count} {sport.event_count === 1 ? 'event' : 'events'}
                          </p>
                        </div>
                      </div>
                      {sport.active && (
                        <span className="px-3 py-1 bg-green-500/20 text-green-400 text-xs font-semibold rounded-full border border-green-500/50">
                          LIVE
                        </span>
                      )}
                    </div>

                    {/* Leagues */}
                    {sport.leagues.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-2">
                          Leagues ({sport.leagues.length})
                        </p>
                        <div className="space-y-2">
                          {sport.leagues.slice(0, 3).map((league) => (
                            <button
                              key={league.name}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleLeagueClick(sport.name, league.name);
                              }}
                              className="w-full flex items-center justify-between p-3 bg-gray-700/50 hover:bg-gray-700 rounded-lg transition-colors text-left"
                            >
                              <span className="text-gray-300 text-sm font-medium">
                                {league.name}
                              </span>
                              <span className="text-green-400 text-xs font-semibold">
                                {league.upcoming_events} upcoming
                              </span>
                            </button>
                          ))}
                          {sport.leagues.length > 3 && (
                            <p className="text-xs text-gray-500 text-center pt-2">
                              +{sport.leagues.length - 3} more leagues
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* View All Button */}
                  <div className="px-6 pb-6">
                    <button
                      onClick={() => handleSportClick(sport.name)}
                      className="w-full bg-green-500 hover:bg-green-600 text-white py-2 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                    >
                      View All {sport.display_name} Odds
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {sports.length === 0 && (
              <div className="text-center py-16">
                <div className="text-6xl mb-4">🏅</div>
                <h3 className="text-xl font-semibold text-gray-400 mb-2">
                  No Sports Available
                </h3>
                <p className="text-gray-500">
                  Check back soon for upcoming events
                </p>
              </div>
            )}
          </div>
        )}

        {/* Categories View */}
        {selectedView === 'categories' && (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">Bet Types & Categories</h2>
              <p className="text-gray-400">
                Learn about different ways to bet on your favorite sports
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {categories.map((category) => (
                <div
                  key={category.id}
                  className="bg-gray-800 rounded-lg border border-gray-700 hover:border-green-500 transition-all p-6 group"
                >
                  <div className="flex items-start gap-4 mb-4">
                    <span className="text-4xl">{category.icon}</span>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-white group-hover:text-green-400 transition-colors mb-2">
                        {category.name}
                      </h3>
                      <p className="text-gray-400 text-sm mb-3">
                        {category.description}
                      </p>
                    </div>
                  </div>

                  <div className="bg-gray-700/50 rounded-lg p-4 border border-gray-600">
                    <p className="text-xs text-gray-500 uppercase font-semibold mb-2">
                      Example
                    </p>
                    <p className="text-gray-300 text-sm font-mono">
                      {category.example}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sports;
