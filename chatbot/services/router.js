/**
 * Query Router Service for RAG System
 * Classifies user intent and routes queries to appropriate handlers
 */

/**
 * Extract team names from query
 * @param {string} query - User query
 * @returns {Array<string>} Extracted team names
 */
function extractTeams(query) {
    const lowerQuery = query.toLowerCase();
    const teams = [];

    // Common team patterns (expand as needed)
    const teamPatterns = [
        // NFL Teams
        'chiefs', 'bills', '49ers', 'niners', 'cowboys', 'eagles', 'dolphins',
        'lions', 'buccaneers', 'bucs', 'ravens', 'bengals', 'packers', 'vikings',
        'jets', 'patriots', 'rams', 'seahawks', 'cardinals', 'browns', 'steelers',
        'chargers', 'raiders', 'broncos', 'colts', 'titans', 'jaguars', 'texans',
        'panthers', 'saints', 'falcons', 'commanders', 'giants',
        
        // NBA Teams
        'lakers', 'celtics', 'warriors', 'heat', 'bucks', 'nets', 'suns',
        'nuggets', 'clippers', 'mavericks', 'mavs', 'grizzlies', 'pelicans',
        'kings', 'trail blazers', 'blazers', 'thunder', 'timberwolves', 'wolves',
        'jazz', 'rockets', 'spurs', 'bulls', 'cavaliers', 'cavs', 'pistons',
        'pacers', 'hornets', 'magic', 'raptors', 'wizards', '76ers', 'sixers',
        'knicks', 'hawks',
        
        // Soccer Teams
        'barcelona', 'barca', 'real madrid', 'manchester united', 'man united',
        'liverpool', 'chelsea', 'arsenal', 'manchester city', 'man city',
        'tottenham', 'spurs', 'bayern munich', 'bayern', 'psg', 'juventus',
        'inter milan', 'ac milan', 'atletico madrid', 'atletico',
    ];

    teamPatterns.forEach(team => {
        if (lowerQuery.includes(team)) {
            teams.push(team);
        }
    });

    return [...new Set(teams)]; // Remove duplicates
}

/**
 * Extract sports from query
 * @param {string} query - User query
 * @returns {Array<string>} Extracted sports
 */
function extractSports(query) {
    const lowerQuery = query.toLowerCase();
    const sports = [];

    const sportPatterns = {
        'football': ['football', 'nfl'],
        'basketball': ['basketball', 'nba'],
        'soccer': ['soccer', 'football', 'premier league', 'la liga', 'serie a', 'bundesliga'],
        'baseball': ['baseball', 'mlb'],
        'hockey': ['hockey', 'nhl'],
    };

    Object.entries(sportPatterns).forEach(([sport, patterns]) => {
        if (patterns.some(pattern => lowerQuery.includes(pattern))) {
            sports.push(sport);
        }
    });

    return [...new Set(sports)];
}

/**
 * Extract time references from query
 * @param {string} query - User query
 * @returns {object} Time context
 */
function extractTimeContext(query) {
    const lowerQuery = query.toLowerCase();

    if (/\b(today|tonight|now)\b/.test(lowerQuery)) {
        return { timeframe: 'today', priority: 'high' };
    }

    if (/\b(tomorrow)\b/.test(lowerQuery)) {
        return { timeframe: 'tomorrow', priority: 'high' };
    }

    if (/\b(this week|week)\b/.test(lowerQuery)) {
        return { timeframe: 'week', priority: 'medium' };
    }

    if (/\b(weekend|saturday|sunday)\b/.test(lowerQuery)) {
        return { timeframe: 'weekend', priority: 'medium' };
    }

    if (/\b(upcoming|soon|next)\b/.test(lowerQuery)) {
        return { timeframe: 'upcoming', priority: 'medium' };
    }

    return { timeframe: 'any', priority: 'low' };
}

/**
 * Route query to appropriate intent
 * @param {string} query - User query
 * @returns {object} Routing decision with intent, confidence, and context
 */
function routeQuery(query) {
    const lowerQuery = query.toLowerCase();

    // Extract context
    const teams = extractTeams(query);
    const sports = extractSports(query);
    const timeContext = extractTimeContext(query);

    // Intent classification patterns
    const intents = {
        games: {
            patterns: [
                /\b(game|match|event|schedule|play|playing)\b/,
                /\b(vs|versus|against)\b/,
                /\b(when|what time|date)\b/,
                /\b(today|tomorrow|upcoming)\b/,
            ],
            weight: 0,
        },
        betting: {
            patterns: [
                /\b(bet|odds|spread|moneyline|over|under|parlay|wager)\b/,
                /\b(best bet|value|pick|recommend|should i)\b/,
                /\b(line|lines|betting)\b/,
                /\b(favorite|underdog)\b/,
            ],
            weight: 0,
        },
        statistics: {
            patterns: [
                /\b(stat|stats|record|history|performance)\b/,
                /\b(win rate|average|total|count)\b/,
                /\b(how many|how much)\b/,
                /\b(trend|pattern|analysis)\b/,
            ],
            weight: 0,
        },
        account: {
            patterns: [
                /\b(my|account|balance|wallet|profile)\b/,
                /\b(deposit|withdraw|transaction)\b/,
                /\b(bet history|my bets)\b/,
            ],
            weight: 0,
        },
        help: {
            patterns: [
                /\b(help|how to|what is|explain)\b/,
                /\b(tutorial|guide|instructions)\b/,
            ],
            weight: 0,
        },
    };

    // Calculate weights for each intent
    Object.entries(intents).forEach(([intent, config]) => {
        config.patterns.forEach(pattern => {
            if (pattern.test(lowerQuery)) {
                config.weight += 1;
            }
        });
    });

    // Find intent with highest weight
    let maxWeight = 0;
    let selectedIntent = 'general';

    Object.entries(intents).forEach(([intent, config]) => {
        if (config.weight > maxWeight) {
            maxWeight = config.weight;
            selectedIntent = intent;
        }
    });

    // Calculate confidence
    const totalMatches = Object.values(intents).reduce((sum, config) => sum + config.weight, 0);
    const confidence = totalMatches > 0 ? maxWeight / totalMatches : 0.5;

    // Build routing decision
    const decision = {
        intent: selectedIntent,
        confidence: parseFloat(confidence.toFixed(2)),
        context: {
            teams,
            sports,
            timeContext,
            hasTeams: teams.length > 0,
            hasSports: sports.length > 0,
            isTimeSpecific: timeContext.priority === 'high',
        },
        metadata: {
            queryLength: query.length,
            wordCount: query.split(/\s+/).length,
            matchedPatterns: maxWeight,
        },
    };

    console.log(`🎯 Routed to: ${decision.intent} (confidence: ${(confidence * 100).toFixed(0)}%)`);

    return decision;
}

/**
 * Determine if query needs real-time data
 * @param {object} routing - Routing decision
 * @returns {boolean}
 */
function needsRealTimeData(routing) {
    return (
        routing.intent === 'betting' ||
        routing.context.isTimeSpecific ||
        routing.context.timeContext.timeframe === 'today'
    );
}

/**
 * Determine cache TTL based on query type
 * @param {object} routing - Routing decision
 * @returns {number} TTL in seconds
 */
function getCacheTTL(routing) {
    // Real-time queries: shorter TTL
    if (needsRealTimeData(routing)) {
        return 180; // 3 minutes
    }

    // Account queries: very short TTL
    if (routing.intent === 'account') {
        return 60; // 1 minute
    }

    // Statistics and general queries: longer TTL
    if (routing.intent === 'statistics' || routing.intent === 'help') {
        return 600; // 10 minutes
    }

    // Default: 5 minutes
    return 300;
}

/**
 * Build search strategy based on routing
 * @param {object} routing - Routing decision
 * @returns {object} Search strategy
 */
function buildSearchStrategy(routing) {
    const strategy = {
        useVectorSearch: true,
        useKeywordSearch: true,
        useTeamFilter: routing.context.hasTeams,
        useSportFilter: routing.context.hasSports,
        limit: 5,
        vectorWeight: 0.5,
        keywordWeight: 0.5,
    };

    // Adjust weights based on intent
    if (routing.intent === 'betting' && routing.context.hasTeams) {
        // Betting queries with specific teams: favor keyword search
        strategy.keywordWeight = 0.7;
        strategy.vectorWeight = 0.3;
        strategy.limit = 3;
    } else if (routing.intent === 'games' && !routing.context.hasTeams) {
        // General game queries: favor vector search for semantic understanding
        strategy.vectorWeight = 0.7;
        strategy.keywordWeight = 0.3;
        strategy.limit = 10;
    } else if (routing.context.isTimeSpecific) {
        // Time-specific queries: favor keyword search
        strategy.keywordWeight = 0.6;
        strategy.vectorWeight = 0.4;
    }

    return strategy;
}

// Export functions
export {
    routeQuery,
    extractTeams,
    extractSports,
    extractTimeContext,
    needsRealTimeData,
    getCacheTTL,
    buildSearchStrategy,
};
