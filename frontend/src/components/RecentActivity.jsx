import { useState } from 'react';
import { 
  UserPlus, 
  TrendingUp, 
  DollarSign, 
  ArrowUpCircle, 
  ArrowDownCircle, 
  Shield, 
  AlertCircle,
  Activity,
  Clock
} from 'lucide-react';
import EmptyState from './EmptyState';

/**
 * Recent Activity Feed Component
 * Real-time activity log showing platform events
 */

const RecentActivity = () => {
  const [activities] = useState([
    {
      id: 1,
      type: 'user_registration',
      user: 'john.doe@example.com',
      description: 'New user registered',
      timestamp: '2 minutes ago',
      icon: UserPlus,
      color: 'blue',
    },
    {
      id: 2,
      type: 'bet_placed',
      user: 'sarah.smith@example.com',
      description: 'Placed bet on Man United vs Liverpool',
      amount: '$250.00',
      timestamp: '5 minutes ago',
      icon: TrendingUp,
      color: 'purple',
    },
    {
      id: 3,
      type: 'deposit',
      user: 'mike.jones@example.com',
      description: 'Deposited funds',
      amount: '$500.00',
      timestamp: '8 minutes ago',
      icon: ArrowUpCircle,
      color: 'green',
    },
    {
      id: 4,
      type: 'withdrawal',
      user: 'emma.wilson@example.com',
      description: 'Withdrawal approved',
      amount: '$1,250.00',
      timestamp: '12 minutes ago',
      icon: ArrowDownCircle,
      color: 'orange',
    },
    {
      id: 5,
      type: 'admin_action',
      user: 'Admin',
      description: 'Verified user account',
      timestamp: '15 minutes ago',
      icon: Shield,
      color: 'cyan',
    },
    {
      id: 6,
      type: 'bet_placed',
      user: 'alex.brown@example.com',
      description: 'Placed bet on Lakers vs Warriors',
      amount: '$100.00',
      timestamp: '18 minutes ago',
      icon: TrendingUp,
      color: 'purple',
    },
    {
      id: 7,
      type: 'user_registration',
      user: 'lisa.taylor@example.com',
      description: 'New user registered',
      timestamp: '22 minutes ago',
      icon: UserPlus,
      color: 'blue',
    },
    {
      id: 8,
      type: 'system_event',
      user: 'System',
      description: 'Database backup completed',
      timestamp: '25 minutes ago',
      icon: AlertCircle,
      color: 'gray',
    },
    {
      id: 9,
      type: 'deposit',
      user: 'david.miller@example.com',
      description: 'Deposited funds',
      amount: '$750.00',
      timestamp: '30 minutes ago',
      icon: ArrowUpCircle,
      color: 'green',
    },
    {
      id: 10,
      type: 'bet_placed',
      user: 'rachel.davis@example.com',
      description: 'Placed bet on Real Madrid vs Barcelona',
      amount: '$300.00',
      timestamp: '35 minutes ago',
      icon: TrendingUp,
      color: 'purple',
    },
  ]);

  const getColorClasses = (color) => {
    const colors = {
      blue: 'bg-blue-500/10 text-blue-700',
      purple: 'bg-purple-500/10 text-purple-700',
      green: 'bg-green-500/10 text-green-700',
      orange: 'bg-orange-500/10 text-orange-700',
      cyan: 'bg-cyan-500/10 text-cyan-400',
      gray: 'bg-gray-500/10 text-heritage-muted',
    };
    return colors[color] || colors.gray;
  };

  return (
    <div className="bg-card rounded-xl border border-card-border overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-card-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
              <Activity className="w-4 h-4 text-green-700" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-heritage-ink">Recent Activity</h3>
              <p className="text-xs text-heritage-muted">Live platform events</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
            <span className="text-xs text-heritage-muted">Live</span>
          </div>
        </div>
      </div>

      {/* Activity Feed */}
      <div 
        className="max-h-[400px] overflow-y-auto"
        style={{
          scrollbarWidth: 'thin',
          scrollbarColor: '#e1e6dd #ffffff'
        }}
      >
        {activities.length === 0 ? (
          <EmptyState
            type="activity"
          />
        ) : (
          <div className="divide-y divide-gray-700">
            {activities.map((activity) => {
            const Icon = activity.icon;
            return (
              <div
                key={activity.id}
                className="p-3 hover:bg-card-hover/30 transition-colors"
              >
                <div className="flex items-start space-x-3">
                  {/* Icon */}
                  <div className={`w-8 h-8 rounded-lg ${getColorClasses(activity.color)} flex items-center justify-center flex-shrink-0`}>
                    <Icon className="w-4 h-4" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm text-heritage-ink font-medium truncate">
                          {activity.description}
                        </p>
                        <p className="text-xs text-heritage-muted mt-0.5">
                          {activity.user}
                        </p>
                      </div>
                      {activity.amount && (
                        <span className="text-sm font-semibold text-green-700 ml-2">
                          {activity.amount}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-1 mt-1">
                      <Clock className="w-3 h-3 text-heritage-muted" />
                      <span className="text-xs text-heritage-muted">{activity.timestamp}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-card-border bg-card/50">
        <button className="w-full text-xs text-heritage-muted hover:text-heritage-ink transition-colors">
          View All Activity →
        </button>
      </div>
    </div>
  );
};

export default RecentActivity;
