import { memo } from 'react';
import { 
  Inbox, 
  TrendingUp, 
  Users, 
  Calendar, 
  AlertCircle,
  FileText,
  Activity
} from 'lucide-react';

/**
 * Empty State Component
 * Displays friendly messages when no data is available
 */

const EmptyState = memo(({ 
  type = 'default',
  title,
  description,
  action,
  icon: CustomIcon 
}) => {
  // Predefined empty state configurations
  const emptyStates = {
    bets: {
      icon: TrendingUp,
      title: 'No Bets Yet',
      description: 'You haven\'t placed any bets yet. Start by exploring available odds and place your first bet!',
      iconColor: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
    },
    odds: {
      icon: Calendar,
      title: 'No Events Available',
      description: 'There are no upcoming events at the moment. Check back later for new betting opportunities!',
      iconColor: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
    },
    users: {
      icon: Users,
      title: 'No Users Found',
      description: 'No users match your current filters. Try adjusting your search criteria.',
      iconColor: 'text-green-400',
      bgColor: 'bg-green-500/10',
    },
    activity: {
      icon: Activity,
      title: 'No Recent Activity',
      description: 'There hasn\'t been any activity yet. Activity will appear here as users interact with the platform.',
      iconColor: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
    search: {
      icon: AlertCircle,
      title: 'No Results Found',
      description: 'We couldn\'t find anything matching your search. Try different keywords or filters.',
      iconColor: 'text-yellow-400',
      bgColor: 'bg-yellow-500/10',
    },
    data: {
      icon: FileText,
      title: 'No Data Available',
      description: 'There is no data to display at this time.',
      iconColor: 'text-gray-400',
      bgColor: 'bg-gray-500/10',
    },
    default: {
      icon: Inbox,
      title: 'Nothing Here',
      description: 'There\'s nothing to show right now.',
      iconColor: 'text-gray-400',
      bgColor: 'bg-gray-500/10',
    },
  };

  // Get configuration for the specified type
  const config = emptyStates[type] || emptyStates.default;
  
  // Use custom values if provided, otherwise use config defaults
  const Icon = CustomIcon || config.icon;
  const displayTitle = title || config.title;
  const displayDescription = description || config.description;

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      {/* Icon */}
      <div className={`w-20 h-20 rounded-full ${config.bgColor} flex items-center justify-center mb-6`}>
        <Icon className={`w-10 h-10 ${config.iconColor}`} />
      </div>

      {/* Title */}
      <h3 className="text-xl font-semibold text-white mb-2">
        {displayTitle}
      </h3>

      {/* Description */}
      <p className="text-gray-400 text-sm max-w-md mb-6">
        {displayDescription}
      </p>

      {/* Optional Action Button */}
      {action && (
        <button
          onClick={action.onClick}
          className="px-6 py-2.5 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-lg transition-colors shadow-lg shadow-green-500/30"
        >
          {action.label}
        </button>
      )}
    </div>
  );
});

EmptyState.displayName = 'EmptyState';

export default EmptyState;
