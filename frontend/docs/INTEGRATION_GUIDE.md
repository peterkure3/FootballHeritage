# Frontend-Backend Integration Guide

This guide explains how to connect the React frontend with the Rust backend for the SportsBet application.

## 🔗 Quick Start

### 1. Start the Backend
```bash
cd backend
.\run.ps1  # Windows PowerShell
# OR
./run.sh   # Linux/Mac
```

Backend will start on: `https://localhost:8443`

### 2. Start the Frontend
```bash
cd frontend
npm install  # First time only
npm run dev
```

Frontend will start on: `http://localhost:5173`

### 3. Open Browser
Navigate to `http://localhost:5173` and you should see the login page.

## ⚙️ Configuration

### Backend Configuration

Ensure your backend `config.toml` or environment has CORS enabled:

```toml
[server]
host = "0.0.0.0"
port = 8443
tls_enabled = true
tls_cert_path = "certs/server.crt"
tls_key_path = "certs/server.key"

[cors]
allowed_origins = ["http://localhost:5173", "http://localhost:5174"]
allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
allowed_headers = ["Content-Type", "Authorization", "X-CSRF-Token"]
max_age = 3600
```

### Frontend Configuration

Edit `frontend/.env`:

```bash
# For HTTPS backend (development with TLS)
VITE_API_URL=https://localhost:8443/api

# For HTTP backend (if TLS disabled)
VITE_API_URL=http://localhost:8080/api

VITE_ENV=development
VITE_SESSION_TIMEOUT=15
VITE_ENABLE_DEBUG=true
```

## 🔐 TLS/SSL Certificate Handling

### Development (Self-Signed Certificates)

When using HTTPS in development, your browser will show a security warning.

**Option 1: Accept the Certificate in Browser**
1. Navigate to `https://localhost:8443` directly
2. Click "Advanced" → "Proceed to localhost (unsafe)"
3. This allows all requests from the frontend

**Option 2: Disable TLS for Development**
In backend config:
```toml
tls_enabled = false
port = 8080
```

In frontend `.env`:
```bash
VITE_API_URL=http://localhost:8080/api
```

**Option 3: Trust the Certificate (Recommended)**

Windows:
```powershell
# Import certificate to Trusted Root
certutil -addstore -f "ROOT" backend\certs\server.crt
```

Linux:
```bash
sudo cp backend/certs/server.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

Mac:
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain backend/certs/server.crt
```

### Production

Use proper SSL certificates from:
- **Let's Encrypt** (free, automated)
- **Commercial CA** (DigiCert, Sectigo, etc.)
- **Cloud Provider** (AWS ACM, Azure Key Vault, GCP Certificate Manager)

## 📡 API Endpoints

### Authentication Endpoints

#### Register
```http
POST /api/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "dob": "2000-01-01"
}

Response: 200 OK
{
  "token": "eyJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "balance": 0.0
  }
}
```

#### Login
```http
POST /api/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

Response: 200 OK
{
  "token": "eyJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "balance": 1000.0
  }
}
```

### User Endpoints

#### Get User Data
```http
GET /api/user
Authorization: Bearer eyJhbGc...
X-CSRF-Token: abc123...

Response: 200 OK
{
  "id": 1,
  "email": "user@example.com",
  "balance": 1000.0,
  "bets": [
    {
      "id": 1,
      "event_id": 10,
      "event_name": "Chiefs vs Bills",
      "amount": 50.0,
      "odds": 2.1,
      "type": "moneyline",
      "status": "pending",
      "placed_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Wallet Endpoints

#### Deposit
```http
POST /api/deposit
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "amount": 100.0
}

Response: 200 OK
{
  "new_balance": 1100.0,
  "amount": 100.0,
  "transaction_id": "txn_123"
}
```

#### Withdraw
```http
POST /api/withdraw
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "amount": 50.0
}

Response: 200 OK
{
  "new_balance": 1050.0,
  "amount": 50.0,
  "transaction_id": "txn_124"
}
```

### Betting Endpoints

#### Get Odds
```http
GET /api/odds
Authorization: Bearer eyJhbGc...

Response: 200 OK
[
  {
    "id": 10,
    "home_team": "Kansas City Chiefs",
    "away_team": "Buffalo Bills",
    "event_time": "2024-01-21T18:00:00Z",
    "status": "upcoming",
    "moneyline_home": 1.95,
    "moneyline_away": 1.85,
    "spread_home": -3.5,
    "spread_away": 3.5,
    "spread_odds_home": 1.91,
    "spread_odds_away": 1.91,
    "total": 52.5,
    "over_odds": 1.91,
    "under_odds": 1.91,
    "league": "NFL"
  }
]
```

#### Place Bet
```http
POST /api/bets
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "event_id": 10,
  "amount": 25.0,
  "odds": 1.95,
  "type": "moneyline"
}

Response: 200 OK
{
  "bet_id": 123,
  "new_balance": 975.0,
  "bet": {
    "id": 123,
    "event_id": 10,
    "amount": 25.0,
    "odds": 1.95,
    "type": "moneyline",
    "status": "pending",
    "placed_at": "2024-01-15T10:45:00Z"
  }
}
```

## 🔒 Authentication Flow

### 1. User Registers/Logs In
```
Frontend → POST /api/login
Backend → Returns JWT token
Frontend → Stores encrypted token in localStorage
Frontend → Stores token in Zustand authStore
```

### 2. Authenticated Requests
```
Frontend → Makes API request
Frontend → Adds Authorization: Bearer {token}
Frontend → Adds X-CSRF-Token: {csrf}
Backend → Validates token
Backend → Returns data
```

### 3. Token Expiration
```
Backend → Returns 401 Unauthorized
Frontend → Detects 401
Frontend → Clears token from storage
Frontend → Redirects to /login
```

### 4. Session Timeout
```
Frontend → Tracks user activity
Frontend → 15 minutes of inactivity
Frontend → Auto-logout
Frontend → Redirects to /login
```

## 🐛 Common Issues & Solutions

### Issue: CORS Error
**Symptom**: `Access-Control-Allow-Origin` error in browser console

**Solution**:
1. Check backend CORS configuration includes `http://localhost:5173`
2. Restart backend after config changes
3. Verify OPTIONS preflight requests are handled

### Issue: 401 Unauthorized
**Symptom**: All API requests return 401

**Solutions**:
1. Token expired - login again
2. Token invalid - clear localStorage and login
3. Backend not validating tokens - check backend JWT middleware

### Issue: TLS Certificate Error
**Symptom**: `NET::ERR_CERT_AUTHORITY_INVALID`

**Solutions**:
1. Accept certificate in browser (see TLS section above)
2. Use HTTP for development
3. Trust the self-signed certificate

### Issue: Odds Not Updating
**Symptom**: Odds page shows "No games available"

**Solutions**:
1. Check backend `/api/odds` endpoint is working: `curl https://localhost:8443/api/odds -k`
2. Verify database has odds data
3. Check backend logs for errors
4. Ensure React Query is refetching (check Network tab)

### Issue: Bet Placement Fails
**Symptom**: Error when clicking "Place Bet"

**Solutions**:
1. Check session limit not exceeded ($100)
2. Verify sufficient balance
3. Check bet amount within limits ($1-$100)
4. Verify backend `/api/bets` endpoint is working

### Issue: Balance Not Updating
**Symptom**: Balance doesn't change after deposit/withdraw/bet

**Solutions**:
1. Check React Query is refetching user data
2. Verify backend returns `new_balance` in response
3. Check Zustand store is updating (`useAuthStore.updateBalance()`)
4. Force refresh: logout and login again

## 🧪 Testing the Integration

### 1. Test Backend Directly
```bash
# Test login
curl -X POST https://localhost:8443/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test123!"}' \
  -k

# Test odds (with token from login)
curl https://localhost:8443/api/odds \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -k
```

### 2. Test Frontend API Layer
Open browser console on `http://localhost:5173`:
```javascript
// Test API utility
import api from './utils/api';

// Login
await api.login('test@test.com', 'Test123!');

// Get odds
const odds = await api.getOdds();
console.log(odds);

// Place bet
const bet = await api.placeBet(10, 25.0, 1.95, 'moneyline');
console.log(bet);
```

### 3. Test Complete Flow
1. Open `http://localhost:5173`
2. Click "Register here"
3. Fill form with DOB 21+ years ago
4. Accept age verification
5. Navigate to Dashboard
6. Click "Deposit" → Deposit $100
7. Navigate to Odds page
8. Click any bet button
9. Enter amount and confirm
10. Check bet appears in Dashboard and Bets page

## 📊 Monitoring & Debugging

### Frontend Debugging

**Browser DevTools**:
- **Console**: Check for errors and warnings
- **Network**: Monitor API requests and responses
- **Application → LocalStorage**: View stored tokens
- **React DevTools**: Inspect component state

**Useful Console Commands**:
```javascript
// Check auth state
useAuthStore.getState()

// Check betting state
useBettingStore.getState()

// Clear all data
localStorage.clear()

// Check if authenticated
useAuthStore.getState().isAuthenticated
```

### Backend Debugging

**Check Logs**:
```bash
# Backend should log all requests
[2024-01-15 10:30:15] INFO POST /api/login 200 OK
[2024-01-15 10:30:20] INFO GET /api/odds 200 OK
[2024-01-15 10:30:25] INFO POST /api/bets 200 OK
```

**Database Queries**:
```bash
# Connect to PostgreSQL
psql -U postgres -d betting_db

# Check users
SELECT * FROM users;

# Check bets
SELECT * FROM bets ORDER BY created_at DESC LIMIT 10;

# Check events
SELECT * FROM events;
```

## 🚀 Production Deployment

### Frontend Deployment

**Build for Production**:
```bash
cd frontend
npm run build
```

**Deploy to Static Hosting**:
- **Vercel**: `vercel deploy`
- **Netlify**: `netlify deploy --prod`
- **AWS S3 + CloudFront**: Upload `dist/` folder
- **Nginx**: Copy `dist/` to `/var/www/html`

**Update .env for Production**:
```bash
VITE_API_URL=https://api.yourdomain.com/api
VITE_ENV=production
VITE_ENABLE_DEBUG=false
```

### Backend Deployment

See backend documentation for:
- PostgreSQL setup
- SSL certificate installation
- Environment configuration
- Docker deployment
- Load balancing

### Security Checklist

- [ ] Use HTTPS in production
- [ ] Use proper SSL certificates (not self-signed)
- [ ] Enable CORS only for production domain
- [ ] Set secure JWT secret (not default)
- [ ] Enable rate limiting
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS-only cookies
- [ ] Implement CSP headers
- [ ] Regular security audits
- [ ] Monitor for suspicious activity

## 📞 Support

**Frontend Issues**:
- Check browser console for errors
- Verify `.env` configuration
- Clear cache and localStorage
- Check React Query DevTools

**Backend Issues**:
- Check backend logs
- Verify database connection
- Test endpoints with curl/Postman
- Check CORS configuration

**Integration Issues**:
- Verify both frontend and backend are running
- Check network requests in DevTools
- Test backend endpoints directly
- Verify token is being sent in requests

## 🎯 Next Steps

1. **Add WebSocket**: Real-time odds updates without polling
2. **Add Push Notifications**: Notify users of bet outcomes
3. **Add Analytics**: Track user behavior and betting patterns
4. **Add Social Features**: Friends, leaderboards, sharing
5. **Add More Sports**: NBA, MLB, NHL, Soccer
6. **Add Live Betting**: Bet during games with live odds
7. **Add Payment Gateway**: Real deposit/withdrawal processing
8. **Add KYC/AML**: Identity verification for compliance
9. **Add Multi-language**: Internationalization (i18n)
10. **Add Mobile Apps**: React Native for iOS/Android

---

**Happy Betting! 🎰🏈**

Remember: Gamble responsibly. If you have a problem, call 1-800-522-4700.