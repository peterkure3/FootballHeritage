/**
 * Prediction Service
 * 
 * Service for fetching ML predictions from the pipeline API
 * Provides predictions, match data, and what-if scenarios
 */

const PIPELINE_API_URL = import.meta.env.VITE_PIPELINE_API_URL || 'http://localhost:5555/api/v1';

export const predictionService = {
  /**
   * Get prediction for a specific match
   * @param {number|string} matchId - The match ID from pipeline database
   * @returns {Promise<Object|null>} Prediction with probabilities or null if not found
   */
  async getPrediction(matchId) {
    if (!matchId) return null;
    
    try {
      const response = await fetch(`${PIPELINE_API_URL}/predictions/${matchId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.status === 404) {
        console.log(`No prediction available for match ${matchId}`);
        return null;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching prediction:', error);
      return null;
    }
  },

  /**
   * Get all matches with odds from pipeline
   * @param {Object} filters - Optional filters
   * @param {string} filters.competition - Filter by competition name
   * @param {string} filters.date - Filter by date (YYYY-MM-DD)
   * @param {number} filters.limit - Maximum number of results (default: 100)
   * @returns {Promise<Array>} List of matches
   */
  async getMatches(filters = {}) {
    try {
      const params = new URLSearchParams();
      
      if (filters.competition) {
        params.append('competition', filters.competition);
      }
      if (filters.date) {
        params.append('date', filters.date);
      }
      if (filters.limit) {
        params.append('limit', filters.limit.toString());
      }
      
      const url = `${PIPELINE_API_URL}/matches${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching matches:', error);
      throw error;
    }
  },

  /**
   * Get prediction for any matchup (What-If scenario)
   * Allows users to predict outcomes for any two teams
   * 
   * @param {string} homeTeam - Home team name
   * @param {string} awayTeam - Away team name
   * @returns {Promise<Object>} Prediction with probabilities and recommendation
   * 
   * @example
   * const prediction = await predictMatchup('Arsenal', 'Chelsea');
   * console.log(prediction.winner); // 'home_win', 'draw', or 'away_win'
   * console.log(prediction.recommendation); // AI-generated recommendation
   */
  async predictMatchup(homeTeam, awayTeam) {
    if (!homeTeam || !awayTeam) {
      throw new Error('Both home and away team names are required');
    }
    
    try {
      const params = new URLSearchParams({
        home_team: homeTeam,
        away_team: awayTeam
      });
      
      const response = await fetch(`${PIPELINE_API_URL}/predict-matchup?${params}`);
      
      if (!response.ok) {
        if (response.status === 503) {
          throw new Error('Model not trained yet. Please train the model first.');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error predicting matchup:', error);
      throw error;
    }
  },

  /**
   * Check pipeline API health
   * @returns {Promise<Object>} Health status including database connection and last run
   */
  async healthCheck() {
    try {
      const response = await fetch(`${PIPELINE_API_URL}/health`);
      return await response.json();
    } catch (error) {
      console.error('Error checking API health:', error);
      return {
        status: 'error',
        database_connected: false,
        last_pipeline_run: null,
        error: error.message
      };
    }
  },

  /**
   * Batch fetch predictions for multiple matches
   * @param {Array<number|string>} matchIds - Array of match IDs
   * @returns {Promise<Map>} Map of matchId -> prediction
   */
  async getBatchPredictions(matchIds) {
    if (!matchIds || matchIds.length === 0) {
      return new Map();
    }
    
    const predictions = new Map();
    
    // Fetch predictions in parallel
    const promises = matchIds.map(async (matchId) => {
      const prediction = await this.getPrediction(matchId);
      if (prediction) {
        predictions.set(matchId, prediction);
      }
    });
    
    await Promise.all(promises);
    return predictions;
  },

  /**
   * Calculate betting edge (expected value)
   * Compares ML prediction probabilities with bookmaker odds
   * 
   * @param {Object} prediction - Prediction object with probabilities
   * @param {Object} odds - Odds object with home_win, draw, away_win
   * @returns {Object} Edge calculations for each outcome
   */
  calculateBettingEdge(prediction, odds) {
    if (!prediction || !odds) {
      return null;
    }
    
    const homeEdge = (prediction.home_prob * odds.home_win) - 1;
    const drawEdge = (prediction.draw_prob * odds.draw) - 1;
    const awayEdge = (prediction.away_prob * odds.away_win) - 1;
    
    const edges = [
      { outcome: 'home', edge: homeEdge, probability: prediction.home_prob },
      { outcome: 'draw', edge: drawEdge, probability: prediction.draw_prob },
      { outcome: 'away', edge: awayEdge, probability: prediction.away_prob }
    ];
    
    // Find best value bet
    const bestBet = edges.reduce((best, current) => 
      current.edge > best.edge ? current : best
    );
    
    return {
      home: homeEdge,
      draw: drawEdge,
      away: awayEdge,
      bestBet: bestBet.edge > 0 ? bestBet : null
    };
  }
};

export default predictionService;
