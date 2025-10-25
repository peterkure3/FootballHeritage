import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import { tokenManager } from '../utils/api';
import Navbar from '../components/Navbar';
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
  ArrowDown
} from 'lucide-react';

/**
 * Admin Dashboard Component
 * Modern dark theme with lime-green accents
 * Layout: Left side - data table, Right side - summary cards
 */

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
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
  const [recentBets, setRecentBets] = useState([]);
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
      const token = tokenManager.getToken();
      
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
      <div className="min-h-screen bg-gray-900">
        <Navbar />
        <div className="flex items-center justify-center h-[calc(100vh-64px)]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <Navbar />
      
      <div className="max-w-[1800px] mx-auto px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
              <p className="text-gray-400 mt-1 text-sm">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </p>
            </div>
            <div className="flex items-center space-x-2 px-4 py-2 bg-gray-800 rounded-lg border border-gray-700">
              <Shield className="w-4 h-4 text-green-400" />
              <span className="text-sm font-medium text-gray-300">
                {user?.is_super_admin ? 'Super Admin' : 'Admin'}
              </span>
            </div>
          </div>
        </div>

        {/* Main Layout: Left (KPIs) + Middle (Table) + Right (Cards) */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Side - KPI Dashboard */}
          <div className="lg:col-span-1">
            <KPIDashboard />
          </div>

          {/* Middle - Users Table & Activity Feed */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              {/* Table Header */}
              <div className="p-4 border-b border-gray-700">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-4">
                    <h2 className="text-lg font-semibold text-white">Recent Users</h2>
                    <span className="text-sm text-gray-400">{recentUsers.length} users</span>
                    {selectedUsers.length > 0 && (
                      <span className="text-sm text-green-400">
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
                          className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 font-medium rounded-lg transition-colors text-sm border border-red-500/30"
                        >
                          Delete Selected
                        </button>
                      </>
                    )}
                    <button className="p-2 hover:bg-gray-700 rounded-lg transition-colors">
                      <Filter className="w-4 h-4 text-gray-400" />
                    </button>
                  </div>
                </div>
                
                {/* Search Bar */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-green-400 text-sm"
                  />
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="px-4 py-3 w-12">
                        <input
                          type="checkbox"
                          checked={selectedUsers.length === recentUsers.length && recentUsers.length > 0}
                          onChange={handleSelectAll}
                          className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-green-400 focus:ring-green-400 focus:ring-offset-gray-800"
                        />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Email
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Joined
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Balance
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
                        className="hover:bg-gray-700/50 transition-colors cursor-pointer"
                        onClick={() => handleUserClick(userItem)}
                      >
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedUsers.includes(userItem.id)}
                            onChange={() => handleSelectUser(userItem.id)}
                            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-green-400 focus:ring-green-400 focus:ring-offset-gray-800"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center">
                            <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center mr-3">
                              <span className="text-xs font-medium text-gray-300">
                                {userItem.email.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <span className="text-sm text-white">{userItem.email}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-400">
                          {new Date(userItem.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-white">
                          ${userItem.balance.toFixed(2)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            userItem.is_verified 
                              ? 'bg-green-400/10 text-green-400' 
                              : 'bg-yellow-400/10 text-yellow-400'
                          }`}>
                            {userItem.is_verified ? 'Verified' : 'Pending'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                          <button 
                            aria-label="User actions menu"
                            className="p-1 hover:bg-gray-600 rounded transition-colors"
                          >
                            <MoreVertical className="w-4 h-4 text-gray-400" />
                          </button>
                        </td>
                      </tr>
                    )))}
                  </tbody>
                </table>
              </div>

              {/* Table Footer */}
              <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between">
                <span className="text-sm text-gray-400">
                  Showing {recentUsers.length} of {stats.totalUsers} users
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
            </div>

            {/* Recent Activity Feed */}
            <RecentActivity />
          </div>

          {/* Right Side - Summary Cards (1/3 width) */}
          <div className="space-y-6">
            {/* Quick Stats Card */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
              <h3 className="text-sm font-medium text-gray-400 mb-4">Platform Overview</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                      <Users className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Total Users</p>
                      <p className="text-lg font-bold text-white">{stats.totalUsers.toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1 text-green-400 text-sm">
                    <ArrowUp className="w-4 h-4" />
                    <span>12%</span>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                      <Activity className="w-5 h-5 text-green-400" />
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Active Today</p>
                      <p className="text-lg font-bold text-white">{stats.activeUsers}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1 text-green-400 text-sm">
                    <ArrowUp className="w-4 h-4" />
                    <span>8%</span>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                      <TrendingUp className="w-5 h-5 text-purple-400" />
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Total Bets</p>
                      <p className="text-lg font-bold text-white">{stats.totalBets.toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1 text-green-400 text-sm">
                    <ArrowUp className="w-4 h-4" />
                    <span>24%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Revenue Card */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-400">Revenue</h3>
                <div className="flex items-center space-x-1 px-2 py-1 bg-green-400/10 rounded-full">
                  <ArrowUp className="w-3 h-3 text-green-400" />
                  <span className="text-xs font-medium text-green-400">26%</span>
                </div>
              </div>
              <div className="mb-4">
                <p className="text-3xl font-bold text-white">${stats.totalRevenue.toLocaleString()}</p>
                <p className="text-xs text-gray-400 mt-1">Last 30 days</p>
              </div>
              
              {/* Mini Bar Chart */}
              <div className="flex items-end space-x-1 h-20">
                {[40, 60, 45, 80, 55, 90, 70, 85, 95, 75, 88, 100].map((height, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-green-400/20 hover:bg-green-400/40 rounded-t transition-colors cursor-pointer"
                    style={{ height: `${height}%` }}
                  />
                ))}
              </div>
            </div>

            {/* Alerts Card */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
              <h3 className="text-sm font-medium text-gray-400 mb-4">Alerts</h3>
              <div className="space-y-3">
                <div className="flex items-start space-x-3 p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                  <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-400">Fraud Alerts</p>
                    <p className="text-xs text-gray-400 mt-1">{stats.fraudAlerts} suspicious activities detected</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
                  <DollarSign className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-yellow-400">Pending Withdrawals</p>
                    <p className="text-xs text-gray-400 mt-1">{stats.pendingWithdrawals} requests awaiting approval</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
              <h3 className="text-sm font-medium text-gray-400 mb-4">Quick Actions</h3>
              <div className="space-y-2">
                <button 
                  onClick={() => navigate('/admin/users')}
                  className="w-full px-4 py-2.5 bg-green-400 hover:bg-green-500 text-gray-900 font-medium rounded-lg transition-colors text-sm"
                >
                  View All Users
                </button>
                <button 
                  onClick={() => navigate('/admin/bets')}
                  className="w-full px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors text-sm"
                >
                  Manage Bets
                </button>
                <button 
                  onClick={() => navigate('/admin/reports')}
                  className="w-full px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors text-sm"
                >
                  Financial Reports
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Withdrawal Queue & Fraud Alerts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <WithdrawalQueue />
          <FraudAlerts />
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
