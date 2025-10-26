import { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { X, Save, Calendar, MapPin, Users, TrendingUp } from 'lucide-react';

/**
 * Event Creation/Edit Form Modal
 * Full form for creating or editing sports events
 */

const EventFormModal = ({ isOpen, onClose, event, onSuccess }) => {
  const [formData, setFormData] = useState({
    sport: '',
    league: '',
    home_team: '',
    away_team: '',
    event_date: '',
    status: 'UPCOMING',
    home_score: null,
    away_score: null,
    moneyline_home: '',
    moneyline_away: '',
    point_spread: '',
    spread_home_odds: '',
    spread_away_odds: '',
    total_points: '',
    over_odds: '',
    under_odds: '',
  });

  const [loading, setLoading] = useState(false);

  // Populate form when editing
  useEffect(() => {
    if (event) {
      setFormData({
        sport: event.sport || '',
        league: event.league || '',
        home_team: event.home_team || '',
        away_team: event.away_team || '',
        event_date: event.event_date ? new Date(event.event_date).toISOString().slice(0, 16) : '',
        status: event.status || 'UPCOMING',
        home_score: event.home_score,
        away_score: event.away_score,
        moneyline_home: event.moneyline_home || '',
        moneyline_away: event.moneyline_away || '',
        point_spread: event.point_spread || '',
        spread_home_odds: event.spread_home_odds || '',
        spread_away_odds: event.spread_away_odds || '',
        total_points: event.total_points || '',
        over_odds: event.over_odds || '',
        under_odds: event.under_odds || '',
      });
    } else {
      // Reset form for new event
      setFormData({
        sport: '',
        league: '',
        home_team: '',
        away_team: '',
        event_date: '',
        status: 'UPCOMING',
        home_score: null,
        away_score: null,
        moneyline_home: '',
        moneyline_away: '',
        point_spread: '',
        spread_home_odds: '',
        spread_away_odds: '',
        total_points: '',
        over_odds: '',
        under_odds: '',
      });
    }
  }, [event]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const url = event
        ? `http://localhost:8080/api/v1/admin/events/${event.id}`
        : 'http://localhost:8080/api/v1/admin/events';

      const method = event ? 'PUT' : 'POST';

      // Prepare payload
      const payload = {
        sport: formData.sport,
        league: formData.league,
        home_team: formData.home_team,
        away_team: formData.away_team,
        event_date: new Date(formData.event_date).toISOString(),
        status: formData.status,
        home_score: formData.home_score ? parseInt(formData.home_score) : null,
        away_score: formData.away_score ? parseInt(formData.away_score) : null,
        moneyline_home: formData.moneyline_home ? parseFloat(formData.moneyline_home) : null,
        moneyline_away: formData.moneyline_away ? parseFloat(formData.moneyline_away) : null,
        point_spread: formData.point_spread ? parseFloat(formData.point_spread) : null,
        spread_home_odds: formData.spread_home_odds ? parseFloat(formData.spread_home_odds) : null,
        spread_away_odds: formData.spread_away_odds ? parseFloat(formData.spread_away_odds) : null,
        total_points: formData.total_points ? parseFloat(formData.total_points) : null,
        over_odds: formData.over_odds ? parseFloat(formData.over_odds) : null,
        under_odds: formData.under_odds ? parseFloat(formData.under_odds) : null,
      };

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        toast.success(event ? 'Event updated successfully' : 'Event created successfully');
        onSuccess();
        onClose();
      } else {
        const data = await response.json();
        toast.error(data.error || 'Failed to save event');
      }
    } catch (error) {
      console.error('Error saving event:', error);
      toast.error('Error saving event');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl border border-gray-700 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          {/* Header */}
          <div className="sticky top-0 bg-gray-800 border-b border-gray-700 p-6 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">
                {event ? 'Edit Event' : 'Create Event'}
              </h2>
              <p className="text-gray-400 text-sm mt-1">
                {event ? 'Update event details and odds' : 'Add a new sports event to the system'}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-6 h-6 text-gray-400" />
            </button>
          </div>

          {/* Form Content */}
          <div className="p-6 space-y-6">
            {/* Basic Information */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                <MapPin className="w-5 h-5 text-green-400" />
                <span>Basic Information</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Sport *
                  </label>
                  <select
                    required
                    value={formData.sport}
                    onChange={(e) => setFormData({ ...formData, sport: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-500"
                  >
                    <option value="">Select Sport</option>
                    <option value="SOCCER">⚽ Soccer</option>
                    <option value="BASKETBALL">🏀 Basketball</option>
                    <option value="TENNIS">🎾 Tennis</option>
                    <option value="NFL">🏈 NFL Football</option>
                    <option value="NBA">🏀 NBA</option>
                    <option value="MLB">⚾ MLB Baseball</option>
                    <option value="NHL">🏒 NHL Hockey</option>
                    <option value="MMA">🥊 MMA / UFC</option>
                    <option value="BOXING">🥊 Boxing</option>
                    <option value="GOLF">⛳ Golf</option>
                    <option value="ESPORTS">🎮 eSports</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    League *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.league}
                    onChange={(e) => setFormData({ ...formData, league: e.target.value })}
                    placeholder="e.g., Premier League, NBA, Champions League"
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Home Team *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.home_team}
                    onChange={(e) => setFormData({ ...formData, home_team: e.target.value })}
                    placeholder="Home team name"
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Away Team *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.away_team}
                    onChange={(e) => setFormData({ ...formData, away_team: e.target.value })}
                    placeholder="Away team name"
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Event Date & Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={formData.event_date}
                    onChange={(e) => setFormData({ ...formData, event_date: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Status *
                  </label>
                  <select
                    required
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-500"
                  >
                    <option value="UPCOMING">Upcoming</option>
                    <option value="LIVE">Live</option>
                    <option value="FINISHED">Finished</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Scores (only for LIVE or FINISHED) */}
            {(formData.status === 'LIVE' || formData.status === 'FINISHED') && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                  <Users className="w-5 h-5 text-blue-400" />
                  <span>Scores</span>
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Home Score
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={formData.home_score || ''}
                      onChange={(e) => setFormData({ ...formData, home_score: e.target.value })}
                      placeholder="0"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Away Score
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={formData.away_score || ''}
                      onChange={(e) => setFormData({ ...formData, away_score: e.target.value })}
                      placeholder="0"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Odds */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                <TrendingUp className="w-5 h-5 text-yellow-400" />
                <span>Betting Odds</span>
              </h3>

              {/* Moneyline */}
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-400 mb-3">Moneyline</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Home Odds</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.moneyline_home}
                      onChange={(e) => setFormData({ ...formData, moneyline_home: e.target.value })}
                      placeholder="e.g., 1.85"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Away Odds</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.moneyline_away}
                      onChange={(e) => setFormData({ ...formData, moneyline_away: e.target.value })}
                      placeholder="e.g., 2.10"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                </div>
              </div>

              {/* Point Spread */}
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-400 mb-3">Point Spread</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Spread</label>
                    <input
                      type="number"
                      step="0.5"
                      value={formData.point_spread}
                      onChange={(e) => setFormData({ ...formData, point_spread: e.target.value })}
                      placeholder="e.g., -7.5"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Home Odds</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.spread_home_odds}
                      onChange={(e) => setFormData({ ...formData, spread_home_odds: e.target.value })}
                      placeholder="e.g., 1.90"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Away Odds</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.spread_away_odds}
                      onChange={(e) => setFormData({ ...formData, spread_away_odds: e.target.value })}
                      placeholder="e.g., 1.90"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                </div>
              </div>

              {/* Over/Under */}
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-3">Over/Under (Total Points)</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Total</label>
                    <input
                      type="number"
                      step="0.5"
                      value={formData.total_points}
                      onChange={(e) => setFormData({ ...formData, total_points: e.target.value })}
                      placeholder="e.g., 47.5"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Over Odds</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.over_odds}
                      onChange={(e) => setFormData({ ...formData, over_odds: e.target.value })}
                      placeholder="e.g., 1.90"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Under Odds</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.under_odds}
                      onChange={(e) => setFormData({ ...formData, under_odds: e.target.value })}
                      placeholder="e.g., 1.90"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-800 border-t border-gray-700 p-6 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-6 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center space-x-2 px-6 py-2.5 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="w-5 h-5" />
                  <span>{event ? 'Update Event' : 'Create Event'}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EventFormModal;
