import { memo, useState } from 'react';

const OddsRow = memo(({ event, onBetClick }) => {
  const [selectedType, setSelectedType] = useState(null);

  // Format team names
  const formatTeamName = (name) => {
    if (!name) return 'TBA';
    return name;
  };

  // Format odds display
  const formatOdds = (odds) => {
    if (!odds) return 'N/A';
    const numOdds = parseFloat(odds);
    if (numOdds > 0) {
      return `+${numOdds.toFixed(2)}`;
    }
    return numOdds.toFixed(2);
  };

  // Format event time
  const formatEventTime = (dateString) => {
    if (!dateString) return 'TBD';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'TBD';
    }
  };

  // Handle bet button click
  const handleBetClick = (type, odds) => {
    setSelectedType(type);
    onBetClick({
      eventId: event.id || event.event_id,
      eventName: `${formatTeamName(event.home_team)} vs ${formatTeamName(event.away_team)}`,
      type,
      odds,
    });
  };

  // Get button styles based on selection
  const getButtonStyles = (type) => {
    const isSelected = selectedType === type;
    const baseStyles = 'px-4 py-2 rounded-lg font-semibold text-sm transition-all duration-200 min-w-[100px]';

    if (isSelected) {
      return `${baseStyles} bg-green-500 text-white shadow-lg shadow-green-500/50 scale-105`;
    }

    return `${baseStyles} bg-gray-700 text-white hover:bg-green-600 hover:shadow-md hover:shadow-green-500/30 active:scale-95`;
  };

  // Check if event is live
  const isLive = event.status === 'live' || event.status === 'in_progress';
  const isPending = event.status === 'upcoming' || event.status === 'scheduled';

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-green-500/50 transition-all duration-300">
      {/* Event Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-white font-bold text-lg">
              {formatTeamName(event.home_team)} vs {formatTeamName(event.away_team)}
            </h3>
            {isLive && (
              <span className="px-2 py-1 bg-red-500 text-white text-xs font-bold rounded animate-pulse">
                LIVE
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-400">
            <span>📅 {formatEventTime(event.event_time || event.start_time)}</span>
            {event.league && <span>🏈 {event.league}</span>}
          </div>
        </div>

        {/* Event Status */}
        {isPending && (
          <span className="px-3 py-1 bg-blue-500/20 text-blue-400 text-xs font-semibold rounded-full border border-blue-500/50">
            UPCOMING
          </span>
        )}
      </div>

      {/* Betting Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Moneyline */}
        {event.moneyline_home && event.moneyline_away && (
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-700">
            <h4 className="text-gray-400 text-xs font-semibold mb-2 uppercase">Moneyline</h4>
            <div className="space-y-2">
              <button
                onClick={() => handleBetClick('moneyline', event.moneyline_home)}
                className={getButtonStyles('moneyline_home')}
                disabled={!isPending}
              >
                <div className="flex justify-between items-center">
                  <span className="truncate">{formatTeamName(event.home_team).slice(0, 10)}</span>
                  <span className="font-bold ml-2">{formatOdds(event.moneyline_home)}</span>
                </div>
              </button>
              <button
                onClick={() => handleBetClick('moneyline', event.moneyline_away)}
                className={getButtonStyles('moneyline_away')}
                disabled={!isPending}
              >
                <div className="flex justify-between items-center">
                  <span className="truncate">{formatTeamName(event.away_team).slice(0, 10)}</span>
                  <span className="font-bold ml-2">{formatOdds(event.moneyline_away)}</span>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Spread */}
        {event.spread_home && event.spread_away && (
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-700">
            <h4 className="text-gray-400 text-xs font-semibold mb-2 uppercase">Spread</h4>
            <div className="space-y-2">
              <button
                onClick={() => handleBetClick('spread', event.spread_odds_home || 1.91)}
                className={getButtonStyles('spread_home')}
                disabled={!isPending}
              >
                <div className="flex justify-between items-center">
                  <span className="truncate">{formatTeamName(event.home_team).slice(0, 10)}</span>
                  <span className="font-bold ml-2">{event.spread_home > 0 ? '+' : ''}{event.spread_home}</span>
                </div>
              </button>
              <button
                onClick={() => handleBetClick('spread', event.spread_odds_away || 1.91)}
                className={getButtonStyles('spread_away')}
                disabled={!isPending}
              >
                <div className="flex justify-between items-center">
                  <span className="truncate">{formatTeamName(event.away_team).slice(0, 10)}</span>
                  <span className="font-bold ml-2">{event.spread_away > 0 ? '+' : ''}{event.spread_away}</span>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Over/Under */}
        {event.total && (
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-700">
            <h4 className="text-gray-400 text-xs font-semibold mb-2 uppercase">Total Points</h4>
            <div className="space-y-2">
              <button
                onClick={() => handleBetClick('over_under', event.over_odds || 1.91)}
                className={getButtonStyles('over')}
                disabled={!isPending}
              >
                <div className="flex justify-between items-center">
                  <span>Over</span>
                  <span className="font-bold ml-2">{event.total}</span>
                </div>
              </button>
              <button
                onClick={() => handleBetClick('over_under', event.under_odds || 1.91)}
                className={getButtonStyles('under')}
                disabled={!isPending}
              >
                <div className="flex justify-between items-center">
                  <span>Under</span>
                  <span className="font-bold ml-2">{event.total}</span>
                </div>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Score Display for Live Events */}
      {isLive && (event.home_score !== undefined || event.away_score !== undefined) && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <div className="flex justify-center gap-8 text-center">
            <div>
              <p className="text-gray-400 text-xs mb-1">{formatTeamName(event.home_team)}</p>
              <p className="text-white text-2xl font-bold">{event.home_score || 0}</p>
            </div>
            <div className="flex items-center text-gray-500 text-xl">-</div>
            <div>
              <p className="text-gray-400 text-xs mb-1">{formatTeamName(event.away_team)}</p>
              <p className="text-white text-2xl font-bold">{event.away_score || 0}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

OddsRow.displayName = 'OddsRow';

export default OddsRow;
