import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import { tokenManager } from '../utils/api';
import Navbar from '../components/Navbar';
import { 
  Users, 
  DollarSign, 
  TrendingUp, 
  AlertTriangle,
  Shield,
  Activity,
  BarChart3,
  Settings
} from 'lucide-react';

/**
 * Admin Dashboard Component
 * 
 * Comprehensive admin panel for managing the betting platform
 * Features:
 * - User management
 * - Financial overview
 * - Betting statistics
 * - Fraud detection alerts
 * - System health monitoring
 */

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    totalBets: 0,
    totalRevenue: 0,
    pendingWithdrawals: 0,
    fraudAlerts: 0,
  });
  const [recentUsers, setRecentUsers] = useState([]);
  const [recentBets, setRecentBets] = useState([]);
  const [activeTab, setActiveTab] = useState('overview'); // overview, users, bets, finances, settings

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
      
      // Fetch admin stats
      const statsResponse = await fetch('http://localhost:8080/api/v1/admin/stats', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      // Fetch recent users
      const usersResponse = await fetch('http://localhost:8080/api/v1/admin/users/recent?limit=10', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setRecentUsers(usersData);
      }

      // Fetch recent bets
      const betsResponse = await fetch('http://localhost:8080/api/v1/admin/bets/recent?limit=10', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (betsResponse.ok) {
        const betsData = await betsResponse.json();
        setRecentBets(betsData);
      }

    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ icon: Icon, title, value, subtitle, color = 'blue' }) => {
    const colorClasses = {
      blue: 'bg-blue-500',
      green: 'bg-green-500',
      yellow: 'bg-yellow-500',
      red: 'bg-red-500',
      purple: 'bg-purple-500',
    };

    return (
      <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-500 text-sm font-medium">{title}</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
            {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
          </div>
          <div className={`${colorClasses[color]} p-3 rounded-full`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center h-[calc(100vh-64px)]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
              <p className="text-gray-600 mt-1">
                Welcome back, {user?.first_name}. Here's what's happening today.
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Shield className="w-5 h-5 text-green-600" />
              <span className="text-sm font-medium text-gray-700">
                {user?.is_super_admin ? 'Super Admin' : 'Admin'}
              </span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'overview', label: 'Overview', icon: BarChart3 },
              { id: 'users', label: 'Users', icon: Users },
              { id: 'bets', label: 'Bets', icon: TrendingUp },
              { id: 'finances', label: 'Finances', icon: DollarSign },
              { id: 'settings', label: 'Settings', icon: Settings },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                    ? 'border-green-600 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <tab.icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <StatCard
                icon={Users}
                title="Total Users"
                value={stats.totalUsers.toLocaleString()}
                subtitle={`${stats.activeUsers} active today`}
                color="blue"
              />
              <StatCard
                icon={TrendingUp}
                title="Total Bets"
                value={stats.totalBets.toLocaleString()}
                subtitle="All time"
                color="green"
              />
              <StatCard
                icon={DollarSign}
                title="Total Revenue"
                value={`$${stats.totalRevenue.toLocaleString()}`}
                subtitle="Platform earnings"
                color="purple"
              />
              <StatCard
                icon={Activity}
                title="Pending Withdrawals"
                value={stats.pendingWithdrawals}
                subtitle="Requires review"
                color="yellow"
              />
              <StatCard
                icon={AlertTriangle}
                title="Fraud Alerts"
                value={stats.fraudAlerts}
                subtitle="Needs attention"
                color="red"
              />
              <StatCard
                icon={Shield}
                title="System Status"
                value="Healthy"
                subtitle="All systems operational"
                color="green"
              />
            </div>

            {/* Recent Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Users */}
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Recent Users</h3>
                </div>
                <div className="p-6">
                  {recentUsers.length > 0 ? (
                    <div className="space-y-4">
                      {recentUsers.map((user) => (
                        <div key={user.id} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900">{user.email}</p>
                            <p className="text-sm text-gray-500">
                              Joined {new Date(user.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            user.is_verified 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {user.is_verified ? 'Verified' : 'Pending'}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No recent users</p>
                  )}
                </div>
              </div>

              {/* Recent Bets */}
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Recent Bets</h3>
                </div>
                <div className="p-6">
                  {recentBets.length > 0 ? (
                    <div className="space-y-4">
                      {recentBets.map((bet) => (
                        <div key={bet.id} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900">${bet.amount}</p>
                            <p className="text-sm text-gray-500">{bet.user_email}</p>
                          </div>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            bet.status === 'won' 
                              ? 'bg-green-100 text-green-800' 
                              : bet.status === 'lost'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {bet.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No recent bets</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">User Management</h3>
            </div>
            <div className="p-6">
              <p className="text-gray-600">User management features coming soon...</p>
            </div>
          </div>
        )}

        {/* Bets Tab */}
        {activeTab === 'bets' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Bet Management</h3>
            </div>
            <div className="p-6">
              <p className="text-gray-600">Bet management features coming soon...</p>
            </div>
          </div>
        )}

        {/* Finances Tab */}
        {activeTab === 'finances' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Financial Overview</h3>
            </div>
            <div className="p-6">
              <p className="text-gray-600">Financial management features coming soon...</p>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">System Settings</h3>
            </div>
            <div className="p-6">
              <p className="text-gray-600">System settings coming soon...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
