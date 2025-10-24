import { useState } from 'react';
import { Search, Filter, TrendingUp, CheckCircle, X, Clock, Eye, MoreVertical } from 'lucide-react';
import { toast } from 'react-hot-toast';

/**
 * Bet Management Component
 * Displays all bets with filtering, search, and management controls
 */

const BetManagement = () => {
  const [bets, setBets] = useState([
    {
      id: 1,
      user_email: 'user1@example.com',
      user_id: 'uuid-1',
      event: 'Manchester United vs Liverpool',
      bet_type: 'Match Winner',
      selection: 'Manchester United',
      odds: 2.5,
      stake: 100.00,
      potential_win: 250.00,
      status: 'pending',
      placed_at: '2025-10-24T14:30:00Z',
      sport: 'Football',
    },
    {
      id: 2,
      user_email: 'user2@example.com',
      user_id: 'uuid-2',
      event: 'Real Madrid vs Barcelona',
      bet_type: 'Over/Under 2.5',
      selection: 'Over 2.5',
      odds: 1.85,
      stake: 500.00,
      potential_win: 925.00,
      status: 'won',
      placed_at: '2025-10-24T12:00:00Z',
      settled_at: '2025-10-24T16:45:00Z',
      sport: 'Football',
    },
    {
      id: 3,
      user_email: 'user3@example.com',
      user_id: 'uuid-3',
      event: 'Lakers vs Warriors',
      bet_type: 'Point Spread',
      selection: 'Lakers -5.5',
      odds: 1.90,
      stake: 250.00,
      potential_win: 475.00,
      status: 'lost',
      placed_at: '2025-10-24T10:15:00Z',
      settled_at: '2025-10-24T13:30:00Z',
      sport: 'Basketball',
    },
    {
      id: 4,
      user_email: 'user4@example.com',
      user_id: 'uuid-4',
      event: 'Djokovic vs Nadal',
      bet_type: 'Match Winner',
      selection: 'Djokovic',
      odds: 1.75,
      stake: 1000.00,
      potential_win: 1750.00,
      status: 'pending',
      placed_at: '2025-10-24T09:00:00Z',
      sport: 'Tennis',
    },
    {
      id: 5,
      user_email: 'user5@example.com',
      user_id: 'uuid-5',
      event: 'Chelsea vs Arsenal',
      bet_type: 'Both Teams to Score',
      selection: 'Yes',
      odds: 1.65,
      stake: 150.00,
      potential_win: 247.50,
      status: 'void',
      placed_at: '2025-10-24T08:30:00Z',
      sport: 'Football',
    },
  ]);

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sportFilter, setSportFilter] = useState('all');
  const [selectedBet, setSelectedBet] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  const handleViewDetails = (bet) => {
    setSelectedBet(bet);
    setShowDetailsModal(true);
  };

  const handleSettle = async (betId, result) => {
    try {
      // TODO: API call to settle bet
      setBets(bets.map(b => 
        b.id === betId ? { ...b, status: result, settled_at: new Date().toISOString() } : b
      ));
      toast.success(`Bet settled as ${result}`);
      setShowDetailsModal(false);
    } catch (error) {
      toast.error('Failed to settle bet');
    }
  };

  const handleVoid = async (betId) => {
    try {
      // TODO: API call to void bet
      setBets(bets.map(b => 
        b.id === betId ? { ...b, status: 'void' } : b
      ));
      toast.success('Bet voided successfully');
      setShowDetailsModal(false);
    } catch (error) {
      toast.error('Failed to void bet');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'won':
        return 'bg-green-400/10 text-green-400 border-green-400/20';
      case 'lost':
        return 'bg-red-400/10 text-red-400 border-red-400/20';
      case 'pending':
        return 'bg-yellow-400/10 text-yellow-400 border-yellow-400/20';
      case 'void':
        return 'bg-gray-400/10 text-gray-400 border-gray-400/20';
      default:
        return 'bg-gray-400/10 text-gray-400 border-gray-400/20';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'won':
        return <CheckCircle className="w-4 h-4" />;
      case 'lost':
        return <X className="w-4 h-4" />;
      case 'pending':
        return <Clock className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const filteredBets = bets.filter(bet => {
    const matchesSearch = bet.event.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         bet.user_email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || bet.status === statusFilter;
    const matchesSport = sportFilter === 'all' || bet.sport === sportFilter;
    return matchesSearch && matchesStatus && matchesSport;
  });

  const stats = {
    total: bets.length,
    pending: bets.filter(b => b.status === 'pending').length,
    won: bets.filter(b => b.status === 'won').length,
    lost: bets.filter(b => b.status === 'lost').length,
    totalStake: bets.reduce((sum, b) => sum + b.stake, 0),
    totalPayout: bets.filter(b => b.status === 'won').reduce((sum, b) => sum + b.potential_win, 0),
  };

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Bet Management</h2>
              <p className="text-sm text-gray-400">{filteredBets.length} bets</p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="flex items-center space-x-6">
            <div className="text-right">
              <p className="text-xs text-gray-400">Total Stake</p>
              <p className="text-sm font-semibold text-white">${stats.totalStake.toFixed(2)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">Total Payout</p>
              <p className="text-sm font-semibold text-green-400">${stats.totalPayout.toFixed(2)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">Pending</p>
              <p className="text-sm font-semibold text-yellow-400">{stats.pending}</p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-3">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by event or user..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-green-400 text-sm"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-green-400"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="won">Won</option>
            <option value="lost">Lost</option>
            <option value="void">Void</option>
          </select>

          {/* Sport Filter */}
          <select
            value={sportFilter}
            onChange={(e) => setSportFilter(e.target.value)}
            className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-green-400"
          >
            <option value="all">All Sports</option>
            <option value="Football">Football</option>
            <option value="Basketball">Basketball</option>
            <option value="Tennis">Tennis</option>
          </select>

          <button className="p-2 hover:bg-gray-700 rounded-lg transition-colors">
            <Filter className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Bets Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Event
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                User
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Selection
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Odds
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Stake
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Potential Win
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {filteredBets.map((bet) => (
              <tr 
                key={bet.id} 
                className="hover:bg-gray-700/50 transition-colors cursor-pointer"
                onClick={() => handleViewDetails(bet)}
              >
                <td className="px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-white">{bet.event}</p>
                    <p className="text-xs text-gray-400">{bet.sport} • {bet.bet_type}</p>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm text-gray-300">{bet.user_email}</p>
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm text-white">{bet.selection}</p>
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm font-medium text-white">{bet.odds.toFixed(2)}</p>
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm font-medium text-white">${bet.stake.toFixed(2)}</p>
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm font-medium text-green-400">${bet.potential_win.toFixed(2)}</p>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(bet.status)}`}>
                    {getStatusIcon(bet.status)}
                    <span>{bet.status.toUpperCase()}</span>
                  </span>
                </td>
                <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                  <button className="p-1 hover:bg-gray-600 rounded transition-colors">
                    <MoreVertical className="w-4 h-4 text-gray-400" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {filteredBets.length === 0 && (
        <div className="p-12 text-center">
          <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No bets found</p>
          <p className="text-sm text-gray-500 mt-2">Try adjusting your filters</p>
        </div>
      )}

      {/* Pagination */}
      {filteredBets.length > 0 && (
        <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between">
          <span className="text-sm text-gray-400">
            Showing {filteredBets.length} of {bets.length} bets
          </span>
          <div className="flex items-center space-x-2">
            <button className="px-3 py-1 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors">
              Previous
            </button>
            <button className="px-3 py-1 text-sm bg-green-400 text-gray-900 font-medium rounded">
              1
            </button>
            <button className="px-3 py-1 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors">
              2
            </button>
            <button className="px-3 py-1 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors">
              Next
            </button>
          </div>
        </div>
      )}

      {/* Bet Details Modal */}
      {showDetailsModal && selectedBet && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setShowDetailsModal(false)}
          />

          {/* Modal */}
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-gray-800 rounded-xl shadow-2xl border border-gray-700 w-full max-w-2xl">
              {/* Header */}
              <div className="flex items-center justify-between p-5 border-b border-gray-700">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                    <TrendingUp className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">Bet Details</h3>
                    <p className="text-sm text-gray-400">ID: #{selectedBet.id}</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="p-1 hover:bg-gray-700 rounded transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              {/* Content */}
              <div className="p-5">
                <div className="grid grid-cols-2 gap-6">
                  {/* Event Info */}
                  <div className="col-span-2">
                    <h4 className="text-sm font-semibold text-white mb-3">Event Information</h4>
                    <div className="bg-gray-900 rounded-lg p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Event:</span>
                        <span className="text-sm text-white font-medium">{selectedBet.event}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Sport:</span>
                        <span className="text-sm text-white">{selectedBet.sport}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Bet Type:</span>
                        <span className="text-sm text-white">{selectedBet.bet_type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Selection:</span>
                        <span className="text-sm text-white font-medium">{selectedBet.selection}</span>
                      </div>
                    </div>
                  </div>

                  {/* Bet Details */}
                  <div>
                    <h4 className="text-sm font-semibold text-white mb-3">Bet Details</h4>
                    <div className="bg-gray-900 rounded-lg p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Odds:</span>
                        <span className="text-sm text-white font-medium">{selectedBet.odds.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Stake:</span>
                        <span className="text-sm text-white font-medium">${selectedBet.stake.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Potential Win:</span>
                        <span className="text-sm text-green-400 font-medium">${selectedBet.potential_win.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Status:</span>
                        <span className={`text-sm font-medium ${
                          selectedBet.status === 'won' ? 'text-green-400' :
                          selectedBet.status === 'lost' ? 'text-red-400' :
                          selectedBet.status === 'pending' ? 'text-yellow-400' :
                          'text-gray-400'
                        }`}>
                          {selectedBet.status.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* User & Timing */}
                  <div>
                    <h4 className="text-sm font-semibold text-white mb-3">User & Timing</h4>
                    <div className="bg-gray-900 rounded-lg p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">User:</span>
                        <span className="text-sm text-white">{selectedBet.user_email}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-400">Placed:</span>
                        <span className="text-sm text-white">
                          {new Date(selectedBet.placed_at).toLocaleString()}
                        </span>
                      </div>
                      {selectedBet.settled_at && (
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-400">Settled:</span>
                          <span className="text-sm text-white">
                            {new Date(selectedBet.settled_at).toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Footer - Admin Actions */}
              {selectedBet.status === 'pending' && (
                <div className="flex items-center justify-end space-x-3 p-5 border-t border-gray-700">
                  <button
                    onClick={() => handleVoid(selectedBet.id)}
                    className="px-4 py-2 text-sm text-gray-400 hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    Void Bet
                  </button>
                  <button
                    onClick={() => handleSettle(selectedBet.id, 'lost')}
                    className="px-4 py-2 text-sm bg-red-500/20 hover:bg-red-500/30 text-red-400 font-medium rounded-lg transition-colors border border-red-500/30"
                  >
                    Settle as Lost
                  </button>
                  <button
                    onClick={() => handleSettle(selectedBet.id, 'won')}
                    className="px-4 py-2 text-sm bg-green-400 hover:bg-green-500 text-gray-900 font-medium rounded-lg transition-colors"
                  >
                    Settle as Won
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BetManagement;
