/**
 * Sports Constants
 * 
 * Centralized sport naming conventions to avoid confusion between:
 * - Soccer (Association Football - EPL, La Liga, etc.)
 * - NFL (American Football)
 * 
 * This file provides consistent labels, icons, and API parameters
 * for all sports across the application.
 */

/**
 * Sport definitions with display names, API keys, and icons
 * 
 * Structure:
 * - key: Internal identifier used in code
 * - displayName: User-facing label shown in UI
 * - apiParam: Parameter sent to backend API
 * - icon: Emoji icon for visual identification
 * - description: Brief description of the sport
 */
export const SPORTS = {
  // Association Football (Soccer)
  SOCCER: {
    key: 'SOCCER',
    displayName: 'Soccer',
    apiParam: 'soccer', // Backend expects 'soccer' for EPL, La Liga, etc.
    icon: '⚽',
    description: 'Association Football - EPL, La Liga, Champions League, etc.',
    leagues: ['English Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1', 'Champions League']
  },
  
  // American Football (NFL)
  NFL: {
    key: 'NFL',
    displayName: 'NFL',
    apiParam: 'nfl', // Backend expects 'nfl' for American Football
    icon: '🏈',
    description: 'American Football - National Football League',
    leagues: ['NFL Regular Season', 'NFL Playoffs', 'Super Bowl']
  },
  
  // Basketball
  BASKETBALL: {
    key: 'BASKETBALL',
    displayName: 'Basketball',
    apiParam: 'basketball',
    icon: '🏀',
    description: 'Professional Basketball - NBA, EuroLeague, etc.',
    leagues: ['NBA', 'EuroLeague', 'NCAA Basketball']
  },
  
  // NBA Cup (In-Season Tournament)
  NBA_CUP: {
    key: 'NBA_CUP',
    displayName: 'NBA Cup',
    apiParam: 'nba_cup',
    league: 'nba_cup', // League filter for API
    icon: '🏆',
    description: 'NBA In-Season Tournament - Mid-season championship competition',
    leagues: ['NBA Cup Group Stage', 'NBA Cup Knockout', 'NBA Cup Finals']
  },
  
  // Baseball
  BASEBALL: {
    key: 'BASEBALL',
    displayName: 'Baseball',
    apiParam: 'baseball',
    icon: '⚾',
    description: 'Professional Baseball - MLB, etc.',
    leagues: ['MLB', 'World Series']
  },
  
  // Hockey
  HOCKEY: {
    key: 'HOCKEY',
    displayName: 'Hockey',
    apiParam: 'hockey',
    icon: '🏒',
    description: 'Ice Hockey - NHL, etc.',
    leagues: ['NHL', 'Stanley Cup']
  },
  
  // Tennis
  TENNIS: {
    key: 'TENNIS',
    displayName: 'Tennis',
    apiParam: 'tennis',
    icon: '🎾',
    description: 'Professional Tennis - Grand Slams, ATP, WTA',
    leagues: ['Wimbledon', 'US Open', 'French Open', 'Australian Open']
  }
};

/**
 * Get sport configuration by API parameter
 * Useful when receiving data from backend
 * 
 * @param {string} apiParam - The API parameter (e.g., 'soccer', 'nfl')
 * @returns {object|null} Sport configuration or null if not found
 * 
 * @example
 * const sport = getSportByApiParam('soccer');
 * console.log(sport.displayName); // Output: "Soccer"
 */
export const getSportByApiParam = (apiParam) => {
  return Object.values(SPORTS).find(
    sport => sport.apiParam.toLowerCase() === apiParam?.toLowerCase()
  ) || null;
};

/**
 * Get sport configuration by key
 * Useful for internal lookups
 * 
 * @param {string} key - The sport key (e.g., 'SOCCER', 'NFL')
 * @returns {object|null} Sport configuration or null if not found
 * 
 * @example
 * const sport = getSportByKey('NFL');
 * console.log(sport.icon); // Output: "🏈"
 */
export const getSportByKey = (key) => {
  return SPORTS[key] || null;
};

/**
 * Get all available sports as an array
 * Useful for dropdowns, filters, and lists
 * 
 * @returns {array} Array of sport configurations
 * 
 * @example
 * const allSports = getAllSports();
 * allSports.forEach(sport => {
 *   console.log(`${sport.icon} ${sport.displayName}`);
 * });
 */
export const getAllSports = () => {
  return Object.values(SPORTS);
};

/**
 * Bet type constants
 * Common betting categories across all sports
 */
export const BET_TYPES = {
  MONEYLINE: {
    key: 'MONEYLINE',
    displayName: 'Moneyline',
    description: 'Pick the winner of the game',
    icon: '🎯'
  },
  SPREAD: {
    key: 'SPREAD',
    displayName: 'Point Spread',
    description: 'Bet on the margin of victory',
    icon: '📊'
  },
  OVER_UNDER: {
    key: 'OVER_UNDER',
    displayName: 'Over/Under',
    description: 'Bet on total points scored',
    icon: '🔢'
  },
  PARLAY: {
    key: 'PARLAY',
    displayName: 'Parlay',
    description: 'Combine multiple bets for higher payout',
    icon: '🎰'
  }
};

/**
 * Event status constants
 * Standardized status labels for events
 */
export const EVENT_STATUS = {
  UPCOMING: {
    key: 'upcoming',
    displayName: 'Upcoming',
    color: 'blue',
    icon: '📅'
  },
  LIVE: {
    key: 'live',
    displayName: 'Live',
    color: 'red',
    icon: '🔴',
    animated: true
  },
  IN_PROGRESS: {
    key: 'in_progress',
    displayName: 'In Progress',
    color: 'red',
    icon: '🔴',
    animated: true
  },
  FINISHED: {
    key: 'finished',
    displayName: 'Finished',
    color: 'gray',
    icon: '✅'
  },
  CANCELLED: {
    key: 'cancelled',
    displayName: 'Cancelled',
    color: 'yellow',
    icon: '⚠️'
  },
  POSTPONED: {
    key: 'postponed',
    displayName: 'Postponed',
    color: 'yellow',
    icon: '⏸️'
  }
};

/**
 * Get event status configuration
 * 
 * @param {string} statusKey - The status key (e.g., 'live', 'upcoming')
 * @returns {object|null} Status configuration or null if not found
 */
export const getEventStatus = (statusKey) => {
  return Object.values(EVENT_STATUS).find(
    status => status.key === statusKey?.toLowerCase()
  ) || null;
};

// Export default for convenience
export default {
  SPORTS,
  BET_TYPES,
  EVENT_STATUS,
  getSportByApiParam,
  getSportByKey,
  getAllSports,
  getEventStatus
};
