/**
 * Redis Cache Service for RAG System
 * Provides sub-10ms cache lookups for frequent queries
 */

import Redis from 'ioredis';
import { createHash } from 'crypto';
import dotenv from 'dotenv';

dotenv.config();

// Initialize Redis client
const redis = new Redis({
    host: process.env.REDIS_HOST || 'localhost',
    port: process.env.REDIS_PORT || 6379,
    password: process.env.REDIS_PASSWORD,
    db: 0,
    maxRetriesPerRequest: 3,
    retryStrategy: (times) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
    },
    enableReadyCheck: true,
    lazyConnect: false,
});

// Event handlers
redis.on('connect', () => {
    console.log('✅ Redis connected successfully');
});

redis.on('ready', () => {
    console.log('✅ Redis ready to accept commands');
});

redis.on('error', (err) => {
    console.error('❌ Redis error:', err.message);
});

redis.on('close', () => {
    console.log('⚠️  Redis connection closed');
});

redis.on('reconnecting', () => {
    console.log('🔄 Redis reconnecting...');
});

/**
 * Generate deterministic cache key from query and context
 * @param {string} query - User query
 * @param {string} userId - User ID
 * @param {object} context - Additional context (intent, filters, etc.)
 * @returns {string} Cache key
 */
function getCacheKey(query, userId, context = {}) {
    const normalizedQuery = query.toLowerCase().trim();
    const contextStr = JSON.stringify(context);
    
    const hash = createHash('sha256')
        .update(`${normalizedQuery}:${userId}:${contextStr}`)
        .digest('hex')
        .substring(0, 16);
    
    return `rag:v1:${hash}`;
}

/**
 * Get cached response
 * @param {string} query - User query
 * @param {string} userId - User ID
 * @param {object} context - Additional context
 * @returns {Promise<object|null>} Cached response or null
 */
async function getCached(query, userId, context = {}) {
    try {
        const key = getCacheKey(query, userId, context);
        const startTime = Date.now();
        
        const cached = await redis.get(key);
        
        if (cached) {
            const latency = Date.now() - startTime;
            console.log(`🎯 Cache HIT: ${key} (${latency}ms)`);
            
            const parsed = JSON.parse(cached);
            return {
                ...parsed,
                cached: true,
                cacheLatency: latency,
            };
        }
        
        const latency = Date.now() - startTime;
        console.log(`❌ Cache MISS: ${key} (${latency}ms)`);
        return null;
    } catch (error) {
        console.error('Cache get error:', error.message);
        return null; // Fail gracefully
    }
}

/**
 * Set cached response with TTL
 * @param {string} query - User query
 * @param {string} userId - User ID
 * @param {object} response - Response to cache
 * @param {object} context - Additional context
 * @param {number} ttl - Time to live in seconds (default: 300 = 5 minutes)
 * @returns {Promise<void>}
 */
async function setCached(query, userId, response, context = {}, ttl = 300) {
    try {
        const key = getCacheKey(query, userId, context);
        const startTime = Date.now();
        
        // Remove cached flag before storing
        const { cached, cacheLatency, ...dataToCache } = response;
        
        await redis.setex(key, ttl, JSON.stringify(dataToCache));
        
        const latency = Date.now() - startTime;
        console.log(`💾 Cached: ${key} (TTL: ${ttl}s, ${latency}ms)`);
    } catch (error) {
        console.error('Cache set error:', error.message);
        // Don't throw - caching failure shouldn't break the app
    }
}

/**
 * Invalidate cache for a specific user
 * Useful when user places a bet or updates preferences
 * @param {string} userId - User ID
 * @returns {Promise<number>} Number of keys deleted
 */
async function invalidateUserCache(userId) {
    try {
        const pattern = `rag:v1:*${userId}*`;
        const keys = await redis.keys(pattern);
        
        if (keys.length > 0) {
            const deleted = await redis.del(...keys);
            console.log(`🗑️  Invalidated ${deleted} cache entries for user ${userId}`);
            return deleted;
        }
        
        return 0;
    } catch (error) {
        console.error('Cache invalidation error:', error.message);
        return 0;
    }
}

/**
 * Invalidate all RAG cache entries
 * Use sparingly - only when odds are updated or events change
 * @returns {Promise<number>} Number of keys deleted
 */
async function invalidateAllCache() {
    try {
        const pattern = 'rag:v1:*';
        const keys = await redis.keys(pattern);
        
        if (keys.length > 0) {
            const deleted = await redis.del(...keys);
            console.log(`🗑️  Invalidated ${deleted} total cache entries`);
            return deleted;
        }
        
        return 0;
    } catch (error) {
        console.error('Cache invalidation error:', error.message);
        return 0;
    }
}

/**
 * Get cache statistics
 * @returns {Promise<object>} Cache stats
 */
async function getCacheStats() {
    try {
        const info = await redis.info('stats');
        const lines = info.split('\r\n');
        
        const stats = {};
        lines.forEach(line => {
            const [key, value] = line.split(':');
            if (key && value) {
                stats[key] = value;
            }
        });
        
        const hitRate = stats.keyspace_hits && stats.keyspace_misses
            ? (parseInt(stats.keyspace_hits) / 
               (parseInt(stats.keyspace_hits) + parseInt(stats.keyspace_misses)) * 100).toFixed(2)
            : 0;
        
        return {
            hits: parseInt(stats.keyspace_hits) || 0,
            misses: parseInt(stats.keyspace_misses) || 0,
            hitRate: parseFloat(hitRate),
            totalKeys: await redis.dbsize(),
        };
    } catch (error) {
        console.error('Cache stats error:', error.message);
        return {
            hits: 0,
            misses: 0,
            hitRate: 0,
            totalKeys: 0,
        };
    }
}

/**
 * Warm up cache with common queries
 * Run this periodically or after odds updates
 * @param {Array<object>} queries - Array of {query, userId, response} objects
 * @returns {Promise<number>} Number of queries cached
 */
async function warmCache(queries) {
    try {
        let cached = 0;
        
        for (const { query, userId, response, context, ttl } of queries) {
            await setCached(query, userId, response, context, ttl);
            cached++;
        }
        
        console.log(`🔥 Cache warmed with ${cached} queries`);
        return cached;
    } catch (error) {
        console.error('Cache warm error:', error.message);
        return 0;
    }
}

/**
 * Check if Redis is connected
 * @returns {boolean}
 */
function isConnected() {
    return redis.status === 'ready';
}

/**
 * Close Redis connection gracefully
 * @returns {Promise<void>}
 */
async function close() {
    try {
        await redis.quit();
        console.log('✅ Redis connection closed gracefully');
    } catch (error) {
        console.error('Error closing Redis:', error.message);
    }
}

// Export functions
export {
    getCached,
    setCached,
    invalidateUserCache,
    invalidateAllCache,
    getCacheStats,
    warmCache,
    isConnected,
    close,
    redis,
};

// Handle process termination
process.on('SIGTERM', close);
process.on('SIGINT', close);
