# Football Heritage Chatbot Service

A Genkit-powered AI chatbot microservice that provides intelligent betting advice using Google's Gemini 1.5 Flash model (free tier).

## 🚀 Features

- **AI-Powered Advice**: Uses Google Gemini 1.5 Flash for intelligent betting recommendations
- **Real-Time Data**: Queries PostgreSQL database for live odds and sports statistics
- **Personalized**: Analyzes user betting history for tailored advice
- **Secure**: JWT authentication, rate limiting, and input sanitization
- **Zero-Cost**: Uses free Gemini API tier and local PostgreSQL
- **Production-Ready**: Helmet security headers, CORS, error handling

## 📋 Prerequisites

- **Node.js**: v18.0.0 or higher
- **PostgreSQL**: Same database as Rust backend
- **Gemini API Key**: Free from [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🔧 Installation

### 1. Install Dependencies

```bash
cd chatbot
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Chatbot Service Configuration
PORT=3000
NODE_ENV=development

# Get your free API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Same database as Rust backend
DATABASE_URL=postgresql://username:password@localhost:5432/football_heritage

# Must match Rust backend JWT secret
JWT_SECRET=your_jwt_secret_here

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,https://localhost:8080

# Rate Limiting
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=20
```

### 3. Get Gemini API Key (Free)

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key to your `.env` file

**Note**: The free tier includes:
- 15 requests per minute
- 1 million tokens per day
- No credit card required

## 🏃 Running the Service

### Development Mode (with auto-reload)

```bash
npm run dev
```

### Production Mode

```bash
npm start
```

The service will start on `http://localhost:3000`

## 🔌 API Endpoints

### POST /chat

Send a chat message to the AI assistant.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "What's the best bet for the Chiefs game?"
}
```

**Response:**
```json
{
  "response": "Based on current odds, the Chiefs are favored at -150...",
  "confidence": 0.85,
  "data": {
    "eventsFound": 1,
    "teamsMatched": ["chiefs"],
    "userStats": {
      "totalBets": 15,
      "winRate": 60.0
    }
  },
  "timestamp": "2024-10-23T00:00:00.000Z"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "chatbot",
  "timestamp": "2024-10-23T00:00:00.000Z",
  "uptime": 123.456
}
```

## 🏗️ Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │─────▶│ Rust Backend│─────▶│   Chatbot   │
│  (Vite/React)│      │  (Actix-web)│      │  (Node.js)  │
└─────────────┘      └─────────────┘      └─────────────┘
                            │                      │
                            │                      │
                            ▼                      ▼
                     ┌─────────────────────────────┐
                     │      PostgreSQL Database     │
                     │  (Users, Events, Odds, Bets) │
                     └─────────────────────────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │ Gemini API  │
                            │ (Free Tier) │
                            └─────────────┘
```

## 📊 How It Works

1. **User sends prompt** via frontend chat interface
2. **Rust backend** validates JWT and proxies to chatbot service
3. **Chatbot service**:
   - Extracts team names from prompt
   - Queries PostgreSQL for relevant events and odds
   - Fetches user betting history
   - Constructs AI prompt with data
   - Calls Gemini 1.5 Flash API
   - Returns betting advice
4. **Frontend** displays response with confidence score

## 🔒 Security Features

- **JWT Authentication**: Validates tokens from Rust backend
- **Rate Limiting**: 20 requests per minute per IP
- **Input Sanitization**: Limits prompt length, removes malicious content
- **Helmet Security Headers**: XSS protection, content security policy
- **CORS**: Restricts origins to configured domains
- **Parameterized Queries**: Prevents SQL injection
- **TLS Support**: Optional SSL for database connections

## 🎯 Example Queries

The chatbot understands natural language queries like:

- "What's the best bet for the Chiefs game?"
- "Show me today's NFL odds"
- "Analyze the Lakers vs Celtics matchup"
- "What are my betting statistics?"
- "Which team has better value in the Cowboys game?"
- "Show me high-confidence bets"

## 🐛 Troubleshooting

### Database Connection Failed

**Error**: `Failed to connect to database`

**Solution**:
- Verify `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- Check database credentials
- Test connection: `psql $DATABASE_URL`

### Gemini API Error

**Error**: `AI service is not properly configured`

**Solution**:
- Verify `GEMINI_API_KEY` in `.env`
- Check API key is valid at [Google AI Studio](https://makersuite.google.com)
- Ensure you haven't exceeded free tier limits (15 req/min)

### JWT Verification Failed

**Error**: `Invalid or expired token`

**Solution**:
- Ensure `JWT_SECRET` matches Rust backend
- Check token is being sent in Authorization header
- Verify token hasn't expired (15 min default)

### CORS Error

**Error**: `CORS policy violation`

**Solution**:
- Add frontend URL to `ALLOWED_ORIGINS` in `.env`
- Format: `http://localhost:5173,https://localhost:8080`
- Restart chatbot service after changes

## 📈 Performance Optimization

- **Connection Pooling**: Max 10 database connections
- **Async/Await**: Non-blocking I/O operations
- **Rate Limiting**: Prevents API abuse
- **Timeout Protection**: 30-second request timeout
- **Efficient Queries**: Indexed database lookups

## 🧪 Testing

```bash
# Test health endpoint
curl http://localhost:3000/health

# Test chat endpoint (requires JWT token)
curl -X POST http://localhost:3000/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me today'\''s games"}'
```

## 📝 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | 3000 | Service port |
| `NODE_ENV` | No | development | Environment (development/production) |
| `GEMINI_API_KEY` | **Yes** | - | Google Gemini API key (free) |
| `DATABASE_URL` | **Yes** | - | PostgreSQL connection string |
| `JWT_SECRET` | **Yes** | - | JWT signing secret (match backend) |
| `ALLOWED_ORIGINS` | No | http://localhost:5173 | Comma-separated CORS origins |
| `RATE_LIMIT_WINDOW_MS` | No | 60000 | Rate limit window (ms) |
| `RATE_LIMIT_MAX_REQUESTS` | No | 20 | Max requests per window |

## 🚀 Deployment

### Production Checklist

- [ ] Set `NODE_ENV=production`
- [ ] Use strong `JWT_SECRET`
- [ ] Enable database SSL (`sslmode=require`)
- [ ] Configure production `ALLOWED_ORIGINS`
- [ ] Set up process manager (PM2, systemd)
- [ ] Configure reverse proxy (nginx)
- [ ] Enable HTTPS
- [ ] Set up monitoring and logging

### PM2 Example

```bash
npm install -g pm2
pm2 start index.js --name chatbot
pm2 save
pm2 startup
```

## 📚 Additional Resources

- [Genkit Documentation](https://firebase.google.com/docs/genkit)
- [Google AI Studio](https://makersuite.google.com)
- [Gemini API Docs](https://ai.google.dev/docs)
- [Node.js PostgreSQL](https://node-postgres.com/)

## 🤝 Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs: `console.log` statements in code
3. Test endpoints with curl/Postman
4. Verify environment variables

## 📄 License

MIT License - See main project LICENSE file
