import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import { 
  TrendingUp, 
  TrendingDown,
  Users,
  DollarSign,
  Dice3,
  ArrowUp,
  Calendar
} from 'lucide-react';

/**
 * Admin Analytics/Statistics Page
 * Platform performance metrics and insights
 */

const AdminAnalytics = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    if (!user?.is_admin && !user?.is_super_admin) {
      toast.error('Access denied. Admin privileges required.');
      navigate('/');
      return;
    }
  }, [user, navigate]);

  const stats = {
    revenue: { current: 45678.90, previous: 36234.50, change: 26.1 },
    users: { current: 1247, previous: 1112, change: 12.1 },
    bets: { current: 8934, previous: 7234, change: 23.5 },
    winRate: { current: 47.3, previous: 45.8, change: 3.3 }
  };

  return (
    <div>
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">Analytics & Statistics</h1>
              <p className="text-gray-400 mt-1 text-sm">
                Platform performance metrics and insights
              </p>
            </div>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500"
            >
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
            </select>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-green-500/10 rounded-lg flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-400" />
              </div>
              <div className={`flex items-center space-x-1 px-2 py-1 rounded-full ${
                stats.revenue.change > 0 ? 'bg-green-400/10' : 'bg-red-400/10'
              }`}>
                {stats.revenue.change > 0 ? (
                  <TrendingUp className="w-3 h-3 text-green-400" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-red-400" />
                )}
                <span className={`text-xs font-medium ${
                  stats.revenue.change > 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {stats.revenue.change}%
                </span>
              </div>
            </div>
            <p className="text-3xl font-bold text-white mb-1">${stats.revenue.current.toLocaleString()}</p>
            <p className="text-sm text-gray-400">Total Revenue</p>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-400" />
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-green-400/10 rounded-full">
                <TrendingUp className="w-3 h-3 text-green-400" />
                <span className="text-xs font-medium text-green-400">{stats.users.change}%</span>
              </div>
            </div>
            <p className="text-3xl font-bold text-white mb-1">{stats.users.current.toLocaleString()}</p>
            <p className="text-sm text-gray-400">Total Users</p>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center">
                <Dice3 className="w-6 h-6 text-purple-400" />
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-green-400/10 rounded-full">
                <TrendingUp className="w-3 h-3 text-green-400" />
                <span className="text-xs font-medium text-green-400">{stats.bets.change}%</span>
              </div>
            </div>
            <p className="text-3xl font-bold text-white mb-1">{stats.bets.current.toLocaleString()}</p>
            <p className="text-sm text-gray-400">Total Bets</p>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-orange-500/10 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-orange-400" />
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-green-400/10 rounded-full">
                <ArrowUp className="w-3 h-3 text-green-400" />
                <span className="text-xs font-medium text-green-400">{stats.winRate.change}%</span>
              </div>
            </div>
            <p className="text-3xl font-bold text-white mb-1">{stats.winRate.current}%</p>
            <p className="text-sm text-gray-400">Win Rate</p>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Revenue Chart */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Revenue Trend</h3>
            <div className="h-64 flex items-end justify-between space-x-2">
              {[40, 65, 45, 80, 55, 90, 70, 85, 95, 75, 88, 100].map((height, i) => (
                <div key={i} className="flex-1 flex flex-col justify-end">
                  <div
                    className="w-full bg-gradient-to-t from-green-500 to-green-400 rounded-t-lg hover:from-green-400 hover:to-green-300 transition-all cursor-pointer"
                    style={{ height: `${height}%` }}
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-4 text-xs text-gray-500">
              <span>Jan</span>
              <span>Feb</span>
              <span>Mar</span>
              <span>Apr</span>
              <span>May</span>
              <span>Jun</span>
            </div>
          </div>

          {/* User Growth Chart */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">User Growth</h3>
            <div className="h-64 flex items-end justify-between space-x-2">
              {[30, 45, 40, 60, 55, 75, 70, 80, 85, 78, 90, 95].map((height, i) => (
                <div key={i} className="flex-1 flex flex-col justify-end">
                  <div
                    className="w-full bg-gradient-to-t from-blue-500 to-blue-400 rounded-t-lg hover:from-blue-400 hover:to-blue-300 transition-all cursor-pointer"
                    style={{ height: `${height}%` }}
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-4 text-xs text-gray-500">
              <span>Jan</span>
              <span>Feb</span>
              <span>Mar</span>
              <span>Apr</span>
              <span>May</span>
              <span>Jun</span>
            </div>
          </div>
        </div>

        {/* Top Performers */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Top Sports by Revenue</h3>
            <div className="space-y-4">
              {[
                { name: 'Soccer', revenue: 18234, percentage: 68 },
                { name: 'Basketball', revenue: 8456, percentage: 24 },
                { name: 'Tennis', revenue: 3234, percentage: 8 },
              ].map((sport, idx) => (
                <div key={idx}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-300">{sport.name}</span>
                    <span className="text-sm font-medium text-white">${sport.revenue.toLocaleString()}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full transition-all"
                      style={{ width: `${sport.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Recent Activity</h3>
            <div className="space-y-3">
              {[
                { action: 'New user registered', time: '2 minutes ago', type: 'user' },
                { action: 'Large bet placed ($500)', time: '5 minutes ago', type: 'bet' },
                { action: 'Withdrawal approved', time: '12 minutes ago', type: 'transaction' },
                { action: 'Event settled', time: '18 minutes ago', type: 'event' },
              ].map((activity, idx) => (
                <div key={idx} className="flex items-center space-x-3 p-3 bg-gray-700/50 rounded-lg">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-sm text-white">{activity.action}</p>
                    <p className="text-xs text-gray-400">{activity.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminAnalytics;
