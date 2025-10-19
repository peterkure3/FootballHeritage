import { memo } from 'react';

const LoadingSkeleton = memo(({ type = 'card', count = 1 }) => {
  // Render different skeleton types
  const renderSkeleton = () => {
    switch (type) {
      case 'card':
        return <BetCardSkeleton />;
      case 'odds':
        return <OddsRowSkeleton />;
      case 'list':
        return <ListSkeleton />;
      case 'stats':
        return <StatsSkeleton />;
      default:
        return <DefaultSkeleton />;
    }
  };

  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index}>{renderSkeleton()}</div>
      ))}
    </div>
  );
});

// Bet Card Skeleton
const BetCardSkeleton = () => (
  <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 animate-pulse">
    <div className="flex items-start justify-between mb-3">
      <div className="flex-1">
        <div className="h-6 bg-gray-700 rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-gray-700 rounded w-1/2"></div>
      </div>
      <div className="h-6 w-20 bg-gray-700 rounded-full"></div>
    </div>

    <div className="grid grid-cols-2 gap-3 mb-3">
      <div>
        <div className="h-3 bg-gray-700 rounded w-16 mb-2"></div>
        <div className="h-5 bg-gray-700 rounded w-24"></div>
      </div>
      <div>
        <div className="h-3 bg-gray-700 rounded w-16 mb-2"></div>
        <div className="h-5 bg-gray-700 rounded w-20"></div>
      </div>
    </div>

    <div className="border-t border-gray-700 pt-3 grid grid-cols-2 gap-3">
      <div>
        <div className="h-3 bg-gray-700 rounded w-12 mb-2"></div>
        <div className="h-7 bg-gray-700 rounded w-20"></div>
      </div>
      <div>
        <div className="h-3 bg-gray-700 rounded w-16 mb-2"></div>
        <div className="h-7 bg-gray-700 rounded w-24"></div>
      </div>
    </div>
  </div>
);

// Odds Row Skeleton
const OddsRowSkeleton = () => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 animate-pulse">
    <div className="flex items-center justify-between mb-4">
      <div className="flex-1">
        <div className="h-6 bg-gray-700 rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-gray-700 rounded w-1/2"></div>
      </div>
      <div className="h-6 w-24 bg-gray-700 rounded-full"></div>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {[1, 2, 3].map((index) => (
        <div key={index} className="bg-gray-900/50 rounded-lg p-3 border border-gray-700">
          <div className="h-4 bg-gray-700 rounded w-20 mb-3"></div>
          <div className="space-y-2">
            <div className="h-10 bg-gray-700 rounded"></div>
            <div className="h-10 bg-gray-700 rounded"></div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// List Skeleton
const ListSkeleton = () => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 animate-pulse">
    <div className="space-y-3">
      {[1, 2, 3].map((index) => (
        <div key={index} className="flex items-center justify-between">
          <div className="flex-1">
            <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-700 rounded w-1/2"></div>
          </div>
          <div className="h-8 w-20 bg-gray-700 rounded"></div>
        </div>
      ))}
    </div>
  </div>
);

// Stats Skeleton
const StatsSkeleton = () => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
    {[1, 2, 3].map((index) => (
      <div
        key={index}
        className="bg-gray-800 border border-gray-700 rounded-lg p-4 animate-pulse"
      >
        <div className="h-4 bg-gray-700 rounded w-1/2 mb-3"></div>
        <div className="h-8 bg-gray-700 rounded w-3/4"></div>
      </div>
    ))}
  </div>
);

// Default Skeleton
const DefaultSkeleton = () => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 animate-pulse">
    <div className="h-6 bg-gray-700 rounded w-3/4 mb-3"></div>
    <div className="h-4 bg-gray-700 rounded w-full mb-2"></div>
    <div className="h-4 bg-gray-700 rounded w-5/6"></div>
  </div>
);

LoadingSkeleton.displayName = 'LoadingSkeleton';

export default LoadingSkeleton;
