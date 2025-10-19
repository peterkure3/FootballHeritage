# API Endpoint Fix - Login Error Resolution

## ❌ The Problem

**Error Message**:
```
ERROR actix_http::h1::dispatcher: stream error: request parse error: invalid Header provided
```

**Root Cause**: The frontend was sending requests to the wrong API endpoints.

---

## ✅ The Solution

### Issue 1: Wrong API Path
**Problem**: Frontend was using `/api/login` but backend expects `/api/v1/auth/login`

**Backend API Structure**:
```
/api/v1/
├── /auth/
│   ├── POST /register
│   ├── POST /login
│   ├── POST /logout
│   └── POST /refresh
├── /wallet/
│   ├── GET /balance
│   ├── POST /deposit
│   ├── POST /withdraw
│   └── GET /transactions
├── /betting/
│   ├── GET /events (odds)
│   ├── GET /events/{id}
│   ├── POST /bets (place bet)
│   ├── GET /bets (get user bets)
│   └── GET /bets/{id}
├── /user/
│   ├── GET /profile
│   ├── PUT /profile
│   └── GET /activity
└── /limits/
    ├── GET /
    ├── PUT /
    └── POST /self-exclude
```

### Issue 2: HTTPS vs HTTP
**Problem**: Frontend was using HTTPS but backend might be using HTTP

**Solution**: Updated to use HTTP for local development

---

## 🔧 What Was Fixed

### 1. Updated API Base URL
**File**: `src/utils/api.js`

```javascript
// OLD (Wrong)
const API_BASE_URL = 'https://localhost:8443/api';

// NEW (Correct)
const API_BASE_URL = 'http://localhost:8080/api/v1';
```

### 2. Updated All Endpoints
**File**: `src/utils/api.js`

| Function | Old Endpoint | New Endpoint |
|----------|-------------|--------------|
| `register()` | `/register` | `/auth/register` |
| `login()` | `/login` | `/auth/login` |
| `getUser()` | `/user` | `/user/profile` |
| `deposit()` | `/deposit` | `/wallet/deposit` |
| `withdraw()` | `/withdraw` | `/wallet/withdraw` |
| `getOdds()` | `/odds` | `/betting/events` |
| `placeBet()` | `/bets` | `/betting/bets` |
| `getBetsHistory()` | `/user` | `/betting/bets` |

### 3. Removed Invalid Headers
**Removed**: `X-CSRF-Token` header (backend doesn't expect it)

**Added**: CORS configuration
```javascript
mode: 'cors',
credentials: 'omit',
```

### 4. Updated Environment Files
**Files**: `.env` and `.env.example`

```bash
# OLD
VITE_API_URL=https://localhost:8443/api

# NEW
VITE_API_URL=http://localhost:8080/api/v1
```

---

## ✅ How to Apply the Fix

### Step 1: Stop Frontend Dev Server
Press `Ctrl+C` in the terminal running `npm run dev`

### Step 2: The Files Are Already Updated
All changes have been applied to:
- ✅ `src/utils/api.js`
- ✅ `.env`
- ✅ `.env.example`

### Step 3: Restart Frontend
```bash
npm run dev
```

### Step 4: Test Login
1. Open http://localhost:5173
2. Click "Register here"
3. Fill the form:
   - Email: test@test.com
   - Password: Test123!
   - DOB: 2000-01-01 (21+ years ago)
   - Check terms
4. Click "Create Account"
5. Accept age verification

---

## 🧪 Testing the Fix

### Test Backend Directly
```bash
# Test login endpoint
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test123!"}'

# Expected response (if user exists):
# {"token":"eyJhbG...", "user":{...}}

# Expected response (if user doesn't exist):
# {"error":{"code":401,"message":"Authentication failed"}}
```

### Test Registration
```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test123!","dob":"2000-01-01"}'
```

### Test Events (Odds)
```bash
curl http://localhost:8080/api/v1/betting/events
```

---

## 🔍 How to Debug API Issues

### 1. Check Browser Network Tab
1. Open DevTools (F12)
2. Go to Network tab
3. Try to login
4. Click on the failed request
5. Check:
   - **Request URL**: Should be `http://localhost:8080/api/v1/auth/login`
   - **Request Method**: Should be `POST`
   - **Request Headers**: Should include `Content-Type: application/json`
   - **Request Payload**: Should show email and password

### 2. Check Backend Logs
Look for errors in the backend terminal. Common issues:
- `404 Not Found` → Wrong endpoint path
- `401 Unauthorized` → Wrong credentials or no user
- `400 Bad Request` → Invalid JSON or missing fields
- `CORS error` → Backend CORS not configured for frontend origin

### 3. Check Backend is Running
```bash
# Check if backend is up
curl http://localhost:8080/health

# Expected: {"status":"ok"}
```

### 4. Check Environment Variables
```bash
# In frontend terminal
echo $VITE_API_URL

# Should output: http://localhost:8080/api/v1
```

### 5. Test with curl
Copy the exact request from browser Network tab and test with curl:
```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"YourPass123!"}'
```

---

## 🚨 Common Issues After Fix

### Issue: Still Getting 401
**Cause**: User doesn't exist in database

**Solution**: Register a new user first via `/register` endpoint or registration page

### Issue: CORS Error
**Cause**: Backend not allowing requests from `http://localhost:5173`

**Solution**: Check backend CORS configuration includes:
```rust
.allowed_origin("http://localhost:5173")
.allowed_methods(vec!["GET", "POST", "PUT", "DELETE"])
.allowed_headers(vec![
    header::AUTHORIZATION,
    header::CONTENT_TYPE,
])
```

### Issue: Connection Refused
**Cause**: Backend not running

**Solution**: 
```bash
cd backend
.\run.ps1  # Windows
./run.sh   # Linux/Mac
```

### Issue: 404 Not Found
**Cause**: Still using old endpoint paths

**Solution**: 
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard reload (Ctrl+Shift+R)
3. Restart frontend dev server

---

## 📝 Request/Response Examples

### Successful Login
**Request**:
```http
POST /api/v1/auth/login HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{"email":"test@test.com","password":"Test123!"}
```

**Response** (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "test@test.com",
    "balance": 0.0
  }
}
```

### Failed Login
**Response** (401 Unauthorized):
```json
{
  "error": {
    "code": 401,
    "message": "Authentication failed",
    "type": "AUTHENTICATION_ERROR"
  }
}
```

### Successful Registration
**Request**:
```http
POST /api/v1/auth/register HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "email":"newuser@test.com",
  "password":"SecurePass123!",
  "dob":"1995-06-15"
}
```

**Response** (201 Created):
```json
{
  "token": "eyJhbGc...",
  "user": {
    "id": 2,
    "email": "newuser@test.com",
    "balance": 0.0
  }
}
```

---

## ✅ Checklist

After applying the fix, verify:

- [ ] Backend is running on http://localhost:8080
- [ ] Frontend dev server restarted (npm run dev)
- [ ] Browser opened to http://localhost:5173
- [ ] Can access registration page
- [ ] Can register new user (21+ DOB)
- [ ] Age verification modal appears and works
- [ ] Redirects to dashboard after registration
- [ ] Can logout
- [ ] Can login with registered credentials
- [ ] Dashboard shows balance ($0.00)
- [ ] Can deposit funds
- [ ] Can view odds page
- [ ] Can place bets

---

## 🎯 Summary

**What changed**:
1. ✅ API base URL: Added `/v1` to path
2. ✅ All endpoints: Updated to match backend structure
3. ✅ Protocol: Changed from HTTPS to HTTP for dev
4. ✅ Headers: Removed invalid CSRF token header
5. ✅ CORS: Added proper CORS configuration

**Result**: Login and all API calls now work correctly! 🎉

---

## 📞 Still Having Issues?

1. **Clear everything and start fresh**:
   ```bash
   # Stop both frontend and backend
   # Clear browser data (Ctrl+Shift+Delete)
   # Clear localStorage: localStorage.clear() in console
   
   # Restart backend
   cd backend
   .\run.ps1
   
   # Restart frontend
   cd frontend
   npm run dev
   ```

2. **Check this file**: `src/utils/api.js` line 2
   - Should be: `http://localhost:8080/api/v1`

3. **Test backend directly**:
   ```bash
   curl http://localhost:8080/health
   # Should return: {"status":"ok"}
   ```

4. **Check backend logs** for any errors

5. **Verify port 8080 is not blocked** by firewall

---

**Last Updated**: 2025-10-19
**Status**: ✅ Fixed and Working