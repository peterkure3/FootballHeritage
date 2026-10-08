import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import UserDetailsModal from '../components/UserDetailsModal';
import WithdrawalQueue from '../components/WithdrawalQueue';
import FraudAlerts from '../components/FraudAlerts';
import KPIDashboard from '../components/KPIDashboard';
import RecentActivity from '../components/RecentActivity';
import EmptyState from '../components/EmptyState';
import { 
  Users, 
  DollarSign, 
  TrendingUp, 
  AlertTriangle,
  Shield,
  Activity,
  Search,
  Filter,
  MoreVertical,
  ArrowUp,
  ArrowDown,
  Dice3,
  Download,
  RefreshCw,
  Calendar
} from 'lucide-react';

/**
 * Admin Dashboard Component - Reorganized Layout
 * 
 * Layout: 
 * - Top: Quick Stats Cards (4 cards in a row)
 * - Main: Users Table (2/3 width) + Right Sidebar (1/3 width)
 * - Right Sidebar: Action Items, Quick Charts, Recent Activity
 */

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [stats] = useState({
    totalUsers: 1247,
    activeUsers: 342,
    totalBets: 8934,
    totalRevenue: 45678.90,
    pendingWithdrawals: 12,
    fraudAlerts: 3,
  });
  const [recentUsers, setRecentUsers] = useState([
    { id: 1, email: 'user1@example.com', created_at: '2025-10-24', is_verified: true, balance: 1250.50 },
    { id: 2, email: 'user2@example.com', created_at: '2025-10-24', is_verified: false, balance: 500.00 },
    { id: 3, email: 'user3@example.com', created_at: '2025-10-23', is_verified: true, balance: 3200.75 },
    { id: 4, email: 'user4@example.com', created_at: '2025-10-23', is_verified: true, balance: 890.25 },
    { id: 5, email: 'user5@example.com', created_at: '2025-10-22', is_verified: false, balance: 150.00 },
  ]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);

  useEffect(() => {
    // Check if user is admin
    if (!user?.is_admin && !user?.is_super_admin) {
      toast.error('Access denied. Admin privileges required.');
      navigate('/');
      return;
    }

    fetchDashboardData();
  }, [user, navigate]);

  const fetchDashboardData = async () => {
    try {
      
      // TODO: Fetch real data from backend
      // For now using mock data
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      toast.error('Failed to load dashboard data');
      setLoading(false);
    }
  };

  const handleUserClick = (user) => {
    setSelectedUser(user);
    setIsModalOpen(true);
  };

  const handleUserUpdate = (updatedUser) => {
    setRecentUsers(recentUsers.map(u => u.id === updatedUser.id ? updatedUser : u));
    toast.success('User updated successfully');
  };

  const handleSelectUser = (userId) => {
    setSelectedUsers(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const handleSelectAll = () => {
    if (selectedUsers.length === recentUsers.length) {
      setSelectedUsers([]);
    } else {
      setSelectedUsers(recentUsers.map(u => u.id));
    }
  };

  const handleBulkVerify = () => {
    if (selectedUsers.length === 0) {
      toast.error('No users selected');
      return;
    }
    // TODO: API call for bulk verify
    toast.success(`${selectedUsers.length} users verified`);
    setSelectedUsers([]);
  };

  const handleBulkDelete = () => {
    if (selectedUsers.length === 0) {
      toast.error('No users selected');
      return;
    }
    if (window.confirm(`Are you sure you want to delete ${selectedUsers.length} users?`)) {
      // TODO: API call for bulk delete
      setRecentUsers(recentUsers.filter(u => !selectedUsers.includes(u.id)));
      toast.success(`${selectedUsers.length} users deleted`);
      setSelectedUsers([]);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-heritage-ink">Dashboard Overview</h1>
              <p className="text-heritage-muted mt-1 text-sm">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <button className="flex items-center space-x-2 px-4 py-2 bg-card hover:bg-card-hover rounded-lg border border-card-border transition-colors">
                <Download className="w-4 h-4 text-heritage-muted" />
                <span className="text-sm font-medium text-heritage-ink">Export</span>
              </button>
              <button className="flex items-center space-x-2 px-4 py-2 bg-card hover:bg-card-hover rounded-lg border border-card-border transition-colors">
                <RefreshCw className="w-4 h-4 text-heritage-muted" />
              </button>
            </div>
          </div>
        </div>

        {/* Quick Stats Cards - Top Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {/* Total Users Card */}
          <div className="bg-card rounded-xl border border-card-border p-5 hover:border-green-500/50 transition-colors">
            <div className="flex items-center justify-between mb-3">
              <div className="w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-700" />
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-green-400/10 rounded-full">
                <ArrowUp className="w-3 h-3 text-green-700" />
                <span className="text-xs font-medium text-green-700">12%</span>
              </div>
            </div>
            <p className="text-2xl font-bold text-heritage-ink mb-1">{stats.totalUsers.toLocaleString()}</p>
            <p className="text-sm text-heritage-muted">Total Users</p>
          </div>

          {/* Revenue Card */}
          <div className="bg-card rounded-xl border border-card-border p-5 hover:border-green-500/50 transition-colors">
            <div className="flex items-center justify-between mb-3">
              <div className="w-12 h-12 rounded-lg bg-green-500/10 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-700" />
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-green-400/10 rounded-full">
                <ArrowUp className="w-3 h-3 text-green-700" />
                <span className="text-xs font-medium text-green-700">26%</span>
              </div>
            </div>
            <p className="text-2xl font-bold text-heritage-ink mb-1">${stats.totalRevenue.toLocaleString()}</p>
            <p className="text-sm text-heritage-muted">Total Revenue</p>
          </div>

          {/* Total Bets Card */}
          <div className="bg-card rounded-xl border border-card-border p-5 hover:border-green-500/50 transition-colors">
            <div className="flex items-center justify-between mb-3">
              <div className="w-12 h-12 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Dice3 className="w-6 h-6 text-purple-700" />
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-green-400/10 rounded-full">
                <ArrowUp className="w-3 h-3 text-green-700" />
                <span className="text-xs font-medium text-green-700">24%</span>
              </div>
            </div>
            <p className="text-2xl font-bold text-heritage-ink mb-1">{stats.totalBets.toLocaleString()}</p>
            <p className="text-sm text-heritage-muted">Total Bets</p>
          </div>

          {/* Alerts Card */}
          <div className="bg-card rounded-xl border border-card-border p-5 hover:border-red-500/50 transition-colors">
            <div className="flex items-center justify-between mb-3">
              <div className="w-12 h-12 rounded-lg bg-red-500/10 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-700" />
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-red-400/10 rounded-full">
                <span className="text-xs font-medium text-red-700">{stats.fraudAlerts + stats.pendingWithdrawals}</span>
              </div>
            </div>
            <p className="text-2xl font-bold text-heritage-ink mb-1">{stats.fraudAlerts + stats.pendingWithdrawals}</p>
            <p className="text-sm text-heritage-muted">Pending Actions</p>
          </div>
        </div>

        {/* Main Content: Users Table (2/3) + Right Sidebar (1/3) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Middle - Users Table & Activity Feed */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-card rounded-xl border border-card-border overflow-hidden">
              {/* Table Header */}
              <div className="p-4 border-b border-card-border">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-4">
                    <h2 className="text-lg font-semibold text-heritage-ink">Recent Users</h2>
                    <span className="text-sm text-heritage-muted">{recentUsers.length} users</span>
                    {selectedUsers.length > 0 && (
                      <span className="text-sm text-green-700">
                        {selectedUsers.length} selected
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    {selectedUsers.length > 0 && (
                      <>
                        <button 
                          onClick={handleBulkVerify}
                          className="px-3 py-1.5 bg-green-400 hover:bg-green-500 text-gray-900 font-medium rounded-lg transition-colors text-sm"
                        >
                          Verify Selected
                        </button>
                        <button 
                          onClick={handleBulkDelete}
                          className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-700 font-medium rounded-lg transition-colors text-sm border border-red-500/30"
                        >
                          Delete Selected
                        </button>
                      </>
                    )}
                    <button className="p-2 hover:bg-card-hover rounded-lg transition-colors">
                      <Filter className="w-4 h-4 text-heritage-muted" />
                    </button>
                  </div>
                </div>
                
                {/* Search Bar */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-heritage-muted" />
                  <input
                    type="text"
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-card border border-card-border rounded-lg text-heritage-ink placeholder-gray-500 focus:outline-none focus:border-green-400 text-sm"
                  />
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-card-border">
                      <th className="px-4 py-3 w-12">
                        <input
                          type="checkbox"
                          checked={selectedUsers.length === recentUsers.length && recentUsers.length > 0}
                          onChange={handleSelectAll}
                          className="w-4 h-4 rounded border-card-border bg-card-hover text-green-700 focus:ring-green-400 focus:ring-offset-gray-800"
                        />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-heritage-muted uppercase tracking-wider">
                        Email
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-heritage-muted uppercase tracking-wider">
                        Joined
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-heritage-muted uppercase tracking-wider">
                        Balance
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-heritage-muted uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-heritage-muted uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {recentUsers.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="px-4 py-8">
                          <EmptyState
                            type="users"
                            title="No Users Found"
                            description="No users match your current search or filter criteria."
                          />
                        </td>
                      </tr>
                    ) : (
                      recentUsers.map((userItem) => (
                      <tr 
                        key={userItem.id} 
                        className="hover:bg-card-hover/50 transition-colors cursor-pointer"
                        onClick={() => handleUserClick(userItem)}
                      >
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedUsers.includes(userItem.id)}
                            onChange={() => handleSelectUser(userItem.id)}
                            className="w-4 h-4 rounded border-card-border bg-card-hover text-green-700 focus:ring-green-400 focus:ring-offset-gray-800"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center">
                            <div className="w-8 h-8 rounded-full bg-card-hover flex items-center justify-center mr-3">
                              <span className="text-xs font-medium text-heritage-ink">
                                {userItem.email.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <span className="text-sm text-heritage-ink">{userItem.email}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-heritage-muted">
                          {new Date(userItem.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-heritage-ink">
                          ${userItem.balance.toFixed(2)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            userItem.is_verified 
                              ? 'bg-green-400/10 text-green-700'
                              : 'bg-yellow-400/10 text-yellow-700'
                          }`}>
                            {userItem.is_verified ? 'Verified' : 'Pending'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                          <button 
                            aria-label="User actions menu"
                            className="p-1 hover:bg-card-hover rounded transition-colors"
                          >
                            <MoreVertical className="w-4 h-4 text-heritage-muted" />
                          </button>
                        </td>
                      </tr>
                    )))}
                  </tbody>
                </table>
              </div>

              {/* Table Footer */}
              <div className="px-4 py-3 border-t border-card-border flex items-center justify-between">
                <span className="text-sm text-heritage-muted">
                  Showing {recentUsers.length} of {stats.totalUsers} users
                </span>
                <div className="flex items-center space-x-2">
                  <button className="px-3 py-1 text-sm text-heritage-muted hover:text-heritage-ink hover:bg-card-hover rounded transition-colors">
                    Previous
                  </button>
                  <button className="px-3 py-1 text-sm bg-green-400 text-gray-900 font-medium rounded">
                    1
                  </button>
                  <button className="px-3 py-1 text-sm text-heritage-muted hover:text-heritage-ink hover:bg-card-hover rounded transition-colors">
                    2
                  </button>
                  <button className="px-3 py-1 text-sm text-heritage-muted hover:text-heritage-ink hover:bg-card-hover rounded transition-colors">
                    Next
                  </button>
                </div>
              </div>
            </div>

          </div>

          {/* Right Sidebar - Action Items & Charts */}
          <div className="lg:col-span-1 space-y-6">
            {/* Action Items Card */}
            <div className="bg-card rounded-xl border border-card-border p-5">
              <h3 className="text-sm font-medium text-heritage-muted mb-4">⚡ Action Items</h3>
              <div className="space-y-3">
                <button 
                  onClick={() => navigate('/admin/bets')}
                  className="w-full flex items-center justify-between p-3 bg-yellow-500/10 hover:bg-yellow-500/20 rounded-lg border border-yellow-500/20 transition-colors group"
                >
                  <div className="flex items-center space-x-3">
                    <DollarSign className="w-5 h-5 text-yellow-700" />
                    <div className="text-left">
                      <p className="text-sm font-medium text-yellow-700">Pending Withdrawals</p>
                      <p className="text-xs text-heritage-muted">{stats.pendingWithdrawals} awaiting approval</p>
                    </div>
                  </div>
                  <ArrowUp className="w-4 h-4 text-yellow-700 transform rotate-90 group-hover:translate-x-1 transition-transform" />
                </button>

                <button 
                  onClick={() => navigate('/admin/users')}
                  className="w-full flex items-center justify-between p-3 bg-red-500/10 hover:bg-red-500/20 rounded-lg border border-red-500/20 transition-colors group"
                >
                  <div className="flex items-center space-x-3">
                    <AlertTriangle className="w-5 h-5 text-red-700" />
                    <div className="text-left">
                      <p className="text-sm font-medium text-red-700">Fraud Alerts</p>
                      <p className="text-xs text-heritage-muted">{stats.fraudAlerts} suspicious activities</p>
                    </div>
                  </div>
                  <ArrowUp className="w-4 h-4 text-red-700 transform rotate-90 group-hover:translate-x-1 transition-transform" />
                </button>

                <button 
                  onClick={() => navigate('/admin/users')}
                  className="w-full flex items-center justify-between p-3 bg-blue-500/10 hover:bg-blue-500/20 rounded-lg border border-blue-500/20 transition-colors group"
                >
                  <div className="flex items-center space-x-3">
                    <Users className="w-5 h-5 text-blue-700" />
                    <div className="text-left">
                      <p className="text-sm font-medium text-blue-700">Unverified Users</p>
                      <p className="text-xs text-heritage-muted">15 pending verification</p>
                    </div>
                  </div>
                  <ArrowUp className="w-4 h-4 text-blue-700 transform rotate-90 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>

            {/* Revenue Chart Card */}
            <div className="bg-card rounded-xl border border-card-border p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-heritage-muted">📈 Revenue (7 Days)</h3>
                <div className="flex items-center space-x-1 px-2 py-1 bg-green-400/10 rounded-full">
                  <ArrowUp className="w-3 h-3 text-green-700" />
                  <span className="text-xs font-medium text-green-700">+26%</span>
                </div>
              </div>
              <p className="text-2xl font-bold text-heritage-ink mb-4">${stats.totalRevenue.toLocaleString()}</p>
              
              {/* Mini Bar Chart */}
              <div className="bg-card rounded-lg p-3">
                <div className="flex items-end justify-between gap-2 h-32">
                  {[40, 60, 45, 80, 55, 90, 70].map((height, i) => (
                    <div key={i} className="flex flex-col items-center flex-1 group">
                      <div className="w-full flex flex-col justify-end h-full">
                        <div
                          className="w-full bg-gradient-to-t from-green-500 to-green-400 hover:from-green-400 hover:to-green-300 rounded-t-lg transition-all duration-300 cursor-pointer shadow-lg shadow-green-500/20 group-hover:shadow-green-500/40"
                          style={{ height: `${height}%`, minHeight: '8px' }}
                        />
                      </div>
                      <span className="text-[10px] text-heritage-muted mt-2 font-medium">
                        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* User Growth Chart */}
            <div className="bg-card rounded-xl border border-card-border p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-heritage-muted">👥 User Growth</h3>
                <div className="flex items-center space-x-1 px-2 py-1 bg-blue-400/10 rounded-full">
                  <ArrowUp className="w-3 h-3 text-blue-700" />
                  <span className="text-xs font-medium text-blue-700">+12%</span>
                </div>
              </div>
              <p className="text-2xl font-bold text-heritage-ink mb-4">{stats.activeUsers}</p>
              
              {/* Mini Bar Chart */}
              <div className="bg-card rounded-lg p-3">
                <div className="flex items-end justify-between gap-2 h-32">
                  {[30, 45, 40, 60, 55, 75, 70].map((height, i) => (
                    <div key={i} className="flex flex-col items-center flex-1 group">
                      <div className="w-full flex flex-col justify-end h-full">
                        <div
                          className="w-full bg-gradient-to-t from-blue-500 to-blue-400 hover:from-blue-400 hover:to-blue-300 rounded-t-lg transition-all duration-300 cursor-pointer shadow-lg shadow-blue-500/20 group-hover:shadow-blue-500/40"
                          style={{ height: `${height}%`, minHeight: '8px' }}
                        />
                      </div>
                      <span className="text-[10px] text-heritage-muted mt-2 font-medium">
                        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recent Activity Feed */}
            <RecentActivity />
          </div>
        </div>
      </div>

      {/* User Details Modal */}
      <UserDetailsModal
        user={selectedUser}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onUpdate={handleUserUpdate}
      />
    </div>
  );
};

export default AdminDashboard;
