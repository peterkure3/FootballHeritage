import { TrendingUp, TrendingDown, Users, DollarSign, Activity, Target, Percent, Clock } from 'lucide-react';

/**
 * KPI Dashboard Component
 * Displays key performance indicators with trend indicators
 */

const KPIDashboard = () => {
  const kpis = [
    {
      id: 1,
      title: "Today's Revenue",
      value: "$12,450",
      change: "+26%",
      trend: "up",
      comparison: "vs yesterday",
      icon: DollarSign,
      color: "green",
    },
    {
      id: 2,
      title: "Active Users",
      value: "342",
      change: "+12%",
      trend: "up",
      comparison: "vs last week",
      icon: Users,
      color: "blue",
    },
    {
      id: 3,
      title: "Bets Today",
      value: "1,247",
      change: "+18%",
      trend: "up",
      comparison: "vs yesterday",
      icon: Activity,
      color: "purple",
    },
    {
      id: 4,
      title: "Conversion Rate",
      value: "68%",
      change: "+5%",
      trend: "up",
      comparison: "vs last month",
      icon: Target,
      color: "orange",
    },
    {
      id: 5,
      title: "Avg Bet Size",
      value: "$125",
      change: "-3%",
      trend: "down",
      comparison: "vs yesterday",
      icon: DollarSign,
      color: "cyan",
    },
    {
      id: 6,
      title: "Win Rate",
      value: "45%",
      change: "+2%",
      trend: "up",
      comparison: "platform average",
      icon: Percent,
      color: "pink",
    },
    {
      id: 7,
      title: "Total Users",
      value: "8,934",
      change: "+15%",
      trend: "up",
      comparison: "this month",
      icon: Users,
      color: "blue",
    },
    {
      id: 8,
      title: "Monthly Revenue",
      value: "$345K",
      change: "+22%",
      trend: "up",
      comparison: "vs last month",
      icon: DollarSign,
      color: "green",
    },
    {
      id: 9,
      title: "Pending Bets",
      value: "156",
      change: "+8%",
      trend: "up",
      comparison: "live events",
      icon: Clock,
      color: "yellow",
    },
    {
      id: 10,
      title: "New Signups",
      value: "47",
      change: "+12%",
      trend: "up",
      comparison: "today",
      icon: Users,
      color: "cyan",
    },
  ];

  const getColorClasses = (color) => {
    const colors = {
      green: 'bg-green-500/10 text-green-400',
      blue: 'bg-blue-500/10 text-blue-400',
      purple: 'bg-purple-500/10 text-purple-400',
      orange: 'bg-orange-500/10 text-orange-400',
      cyan: 'bg-cyan-500/10 text-cyan-400',
      pink: 'bg-pink-500/10 text-pink-400',
      yellow: 'bg-yellow-500/10 text-yellow-400',
    };
    return colors[color] || colors.green;
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Key Metrics</h3>
          <p className="text-sm text-gray-400">Real-time performance indicators</p>
        </div>
        <div className="flex items-center space-x-2 text-xs text-gray-400">
          <Clock className="w-3 h-3" />
          <span>Updated just now</span>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.id}
              className="bg-gray-800 rounded-xl border border-gray-700 p-4 hover:border-gray-600 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div className={`w-10 h-10 rounded-lg ${getColorClasses(kpi.color)} flex items-center justify-center`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${
                  kpi.trend === 'up' 
                    ? 'bg-green-500/10 text-green-400' 
                    : 'bg-red-500/10 text-red-400'
                }`}>
                  {kpi.trend === 'up' ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  <span>{kpi.change}</span>
                </div>
              </div>
              
              <div>
                <p className="text-xs text-gray-400 mb-1">{kpi.title}</p>
                <p className="text-2xl font-bold text-white mb-1">{kpi.value}</p>
                <p className="text-xs text-gray-500">{kpi.comparison}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Bar */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
            <span className="text-sm text-gray-300">All systems operational</span>
          </div>
          <div className="flex items-center space-x-6 text-xs">
            <div>
              <span className="text-gray-400">Uptime: </span>
              <span className="text-white font-medium">99.9%</span>
            </div>
            <div>
              <span className="text-gray-400">Response: </span>
              <span className="text-white font-medium">45ms</span>
            </div>
            <div>
              <span className="text-gray-400">Load: </span>
              <span className="text-green-400 font-medium">Low</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KPIDashboard;
