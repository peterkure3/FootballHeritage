import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import EventFormModal from '../components/EventFormModal';
import { 
  Plus, 
  Edit2, 
  Trash2, 
  Search, 
  Filter,
  Calendar,
  MapPin,
  Users,
  TrendingUp,
  Clock
} from 'lucide-react';

/**
 * Admin Events Management Page
 * Full CRUD operations for sports events
 */

const AdminEvents = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sportFilter, setSportFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);

  useEffect(() => {
    if (!user?.is_admin && !user?.is_super_admin) {
      toast.error('Access denied. Admin privileges required.');
      navigate('/');
      return;
    }
    fetchEvents();
  }, [user, navigate, sportFilter, statusFilter]);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (sportFilter) params.append('sport', sportFilter);
      if (statusFilter) params.append('status', statusFilter);
      
      const response = await fetch(`http://localhost:8080/api/v1/admin/events?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setEvents(data.events || []);
      } else {
        toast.error('Failed to fetch events');
      }
    } catch (error) {
      console.error('Error fetching events:', error);
      toast.error('Error loading events');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEvent = async (eventId) => {
    if (!confirm('Are you sure you want to delete this event?')) return;

    try {
      const response = await fetch(`http://localhost:8080/api/v1/admin/events/${eventId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        toast.success('Event deleted successfully');
        fetchEvents();
      } else {
        const data = await response.json();
        toast.error(data.error || 'Failed to delete event');
      }
    } catch (error) {
      console.error('Error deleting event:', error);
      toast.error('Error deleting event');
    }
  };

  const filteredEvents = events.filter(event => {
    const matchesSearch = 
      event.home_team?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      event.away_team?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      event.league?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'LIVE': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'UPCOMING': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'FINISHED': return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
      default: return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    }
  };

  const getSportIcon = (sport) => {
    const icons = {
      'SOCCER': '⚽',
      'BASKETBALL': '🏀',
      'TENNIS': '🎾',
      'ESPORTS': '🎮',
    };
    return icons[sport] || '🏅';
  };

  return (
    <div>
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Events Management</h1>
            <p className="text-gray-400 mt-1 text-sm">
              Create, edit, and manage sports events
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="w-5 h-5" />
            <span>Create Event</span>
          </button>
        </div>

        {/* Filters */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search events..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
              />
            </div>

            {/* Sport Filter */}
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <select
                value={sportFilter}
                onChange={(e) => setSportFilter(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-500 appearance-none"
              >
                <option value="">All Sports</option>
                <option value="SOCCER">⚽ Soccer</option>
                <option value="BASKETBALL">🏀 Basketball</option>
                <option value="TENNIS">🎾 Tennis</option>
                <option value="ESPORTS">🎮 eSports</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="relative">
              <Clock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-500 appearance-none"
              >
                <option value="">All Status</option>
                <option value="UPCOMING">Upcoming</option>
                <option value="LIVE">Live</option>
                <option value="FINISHED">Finished</option>
              </select>
            </div>
          </div>
        </div>

        {/* Events Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500"></div>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-12 text-center">
            <Calendar className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Events Found</h3>
            <p className="text-gray-400 mb-6">
              {searchTerm || sportFilter || statusFilter 
                ? 'Try adjusting your filters'
                : 'Create your first event to get started'}
            </p>
            {!searchTerm && !sportFilter && !statusFilter && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
              >
                Create Event
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredEvents.map((event) => (
              <div
                key={event.id}
                className="bg-gray-800 rounded-xl border border-gray-700 p-5 hover:border-gray-600 transition-colors"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-2xl">{getSportIcon(event.sport)}</span>
                    <div>
                      <p className="text-xs text-gray-400">{event.sport}</p>
                      <p className="text-sm font-medium text-gray-300">{event.league}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(event.status)}`}>
                    {event.status}
                  </span>
                </div>

                {/* Teams */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <Users className="w-4 h-4 text-gray-400" />
                      <span className="text-white font-medium">{event.home_team}</span>
                    </div>
                    {event.home_score !== null && (
                      <span className="text-white font-bold">{event.home_score}</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Users className="w-4 h-4 text-gray-400" />
                      <span className="text-white font-medium">{event.away_team}</span>
                    </div>
                    {event.away_score !== null && (
                      <span className="text-white font-bold">{event.away_score}</span>
                    )}
                  </div>
                </div>

                {/* Date */}
                <div className="flex items-center space-x-2 text-sm text-gray-400 mb-4">
                  <Calendar className="w-4 h-4" />
                  <span>{new Date(event.event_date).toLocaleString()}</span>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2 pt-4 border-t border-gray-700">
                  <button
                    onClick={() => setEditingEvent(event)}
                    className="flex-1 flex items-center justify-center space-x-2 px-3 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 rounded-lg transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                    <span className="text-sm font-medium">Edit</span>
                  </button>
                  <button
                    onClick={() => handleDeleteEvent(event.id)}
                    className="flex-1 flex items-center justify-center space-x-2 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span className="text-sm font-medium">Delete</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      <EventFormModal
        isOpen={showCreateModal || !!editingEvent}
        onClose={() => {
          setShowCreateModal(false);
          setEditingEvent(null);
        }}
        event={editingEvent}
        onSuccess={fetchEvents}
      />
    </div>
  );
};

export default AdminEvents;
