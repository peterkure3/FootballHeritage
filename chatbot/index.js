/**
 * Football Heritage Chatbot Service
 * 
 * A Genkit-powered microservice that provides AI-driven betting advice
 * using Google's Gemini 1.5 Flash model (free tier).
 * 
 * Features:
 * - JWT authentication (validates tokens from Rust backend)
 * - PostgreSQL integration for sports data and odds
 * - Rate limiting and security headers
 * - Async/await for optimal performance
 * - Connection pooling for database efficiency
 */

import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';
import jwt from 'jsonwebtoken';
import { chatFlow } from './flows/chat.js';

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// ============================================================================
// MIDDLEWARE CONFIGURATION
// ============================================================================

// Security headers
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
    },
  },
}));

// CORS configuration
const allowedOrigins = process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:5173'];
app.use(cors({
  origin: (origin, callback) => {
    // Allow requests with no origin (mobile apps, Postman, etc.)
    if (!origin) return callback(null, true);
    
    if (allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('CORS policy violation'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// Body parser
app.use(express.json({ limit: '10kb' })); // Limit payload size for security

// Rate limiting - 20 requests per minute per IP
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 60000,
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 20,
  message: {
    error: 'Too many requests from this IP, please try again later.',
  },
  standardHeaders: true,
  legacyHeaders: false,
});

app.use('/chat', limiter);

// ============================================================================
// JWT AUTHENTICATION MIDDLEWARE
// ============================================================================

/**
 * Validates JWT tokens from the Rust backend
 * Extracts user_id from token and attaches to request
 */
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({ 
      error: 'Authentication required',
      message: 'No token provided' 
    });
  }

  try {
    // Verify token using same secret as Rust backend
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.userId = decoded.sub || decoded.user_id; // Support both formats
    next();
  } catch (error) {
    console.error('JWT verification failed:', error.message);
    return res.status(403).json({ 
      error: 'Invalid token',
      message: 'Token verification failed' 
    });
  }
};

// ============================================================================
// ROUTES
// ============================================================================

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'chatbot',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

/**
 * Chat endpoint - Main chatbot interface
 * 
 * POST /chat
 * Body: { prompt: string }
 * Headers: Authorization: Bearer <token>
 * 
 * Returns: { response: string, confidence?: number, data?: object }
 */
app.post('/chat', authenticateToken, async (req, res) => {
  try {
    const { prompt } = req.body;

    // Input validation
    if (!prompt || typeof prompt !== 'string') {
      return res.status(400).json({ 
        error: 'Invalid input',
        message: 'Prompt is required and must be a string' 
      });
    }

    // Sanitize input - remove excessive whitespace, limit length
    const sanitizedPrompt = prompt.trim().slice(0, 500);

    if (sanitizedPrompt.length === 0) {
      return res.status(400).json({ 
        error: 'Invalid input',
        message: 'Prompt cannot be empty' 
      });
    }

    console.log(`[${new Date().toISOString()}] Chat request from user ${req.userId}: "${sanitizedPrompt.substring(0, 50)}..."`);

    // Call Genkit chat flow
    const result = await chatFlow({
      prompt: sanitizedPrompt,
      userId: req.userId,
    });

    // Return response
    res.json({
      response: result.response,
      confidence: result.confidence,
      data: result.data,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Chat error:', error);
    
    // Handle specific error types
    if (error.message.includes('API key')) {
      return res.status(500).json({ 
        error: 'Configuration error',
        message: 'AI service is not properly configured' 
      });
    }

    if (error.message.includes('database') || error.message.includes('connection')) {
      return res.status(503).json({ 
        error: 'Service unavailable',
        message: 'Database connection failed' 
      });
    }

    // Generic error response
    res.status(500).json({ 
      error: 'Internal server error',
      message: 'Failed to process chat request' 
    });
  }
});

/**
 * 404 handler
 */
app.use((req, res) => {
  res.status(404).json({ 
    error: 'Not found',
    message: `Route ${req.method} ${req.path} not found` 
  });
});

/**
 * Global error handler
 */
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong' 
  });
});

// ============================================================================
// SERVER STARTUP
// ============================================================================

app.listen(PORT, () => {
  console.log('='.repeat(60));
  console.log('🤖 Football Heritage Chatbot Service');
  console.log('='.repeat(60));
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`Server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Chat endpoint: http://localhost:${PORT}/chat`);
  console.log('='.repeat(60));
  
  // Validate required environment variables
  const requiredVars = ['GEMINI_API_KEY', 'DATABASE_URL', 'JWT_SECRET'];
  const missing = requiredVars.filter(v => !process.env[v]);
  
  if (missing.length > 0) {
    console.warn('⚠️  WARNING: Missing required environment variables:');
    missing.forEach(v => console.warn(`   - ${v}`));
    console.warn('   Please check your .env file');
  } else {
    console.log('✅ All required environment variables are set');
  }
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully...');
  process.exit(0);
});
