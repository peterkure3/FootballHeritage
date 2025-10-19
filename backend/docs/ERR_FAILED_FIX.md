# 🚨 ERR_FAILED Fix - Backend Not Responding

## ❌ The Problem

**Error in Browser Console**:
```
POST http://localhost:8080/api/v1/auth/login net::ERR_FAILED
```

This means the browser **cannot connect to the backend at all**.

---

## 🔍 Root Cause

The backend is listening on `127.0.0.1:8080` instead of `0.0.0.0:8080`.

**What's the difference?**
- `127.0.0.1` = Loopback interface only (local connections only)
- `0.0.0.0` = All network interfaces (allows browser connections)

**Why this matters**:
- When the browser tries to connect to `localhost:8080`, it may resolve to a different interface
- CORS and network stack treat `127.0.0.1` differently than `localhost`
- Some Windows network configurations block browser → `127.0.0.1` connections

---

## ✅ The Solution

### Step 1: Fix Backend .env

**File**: `backend/.env`

Change this line:
```bash
HOST=127.0.0.1  ❌
```

To this:
```bash
HOST=0.0.0.0  ✅
```

### Step 2: Run the Fix Script (Automatic)

```powershell
cd backend
.\fix_host.ps1
```

This script will automatically update your .env file.

### Step 3: Restart Backend

```powershell
# Stop backend (Ctrl+C)
.\run.ps1
```

**Look for this in logs**:
```
INFO Starting server on 0.0.0.0:8080  ✅
```

NOT:
```
INFO Starting server on 127.0.0.1:8080  ❌
```

### Step 4: Verify Backend is Listening

```powershell
netstat -ano | findstr :8080
```

Should show:
```
TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING
```

NOT:
```
TCP    127.0.0.1:8080         0.0.0.0:0              LISTENING
```

### Step 5: Test Connection

```bash
# Test from command line
curl http://localhost:8080/health
```

Should return: `{"status":"ok"}`

### Step 6: Try Login in Browser

1. Open http://localhost:5173
2. Go to Login page
3. Try to login
4. ✅ Should work now!

---

## 🧪 Detailed Verification

### Check 1: Backend Listening Address

After starting backend, check:

```powershell
# Windows
netstat -ano | findstr :8080

# Should show 0.0.0.0:8080, not 127.0.0.1:8080
```

### Check 2: Backend Startup Logs

Look for:
```
INFO  Server configuration loaded
INFO  CORS allowed origins: ["http://localhost:5173", ...]
INFO  Starting server on 0.0.0.0:8080  ← This should say 0.0.0.0
INFO  Listening on http://0.0.0.0:8080
```

### Check 3: Health Check

```bash
curl http://localhost:8080/health
```

Expected:
```json
{"status":"ok"}
```

### Check 4: API Endpoint

```bash
curl http://localhost:8080/api/v1/auth/login \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test123!"}'
```

Should return JSON response (not connection error).

### Check 5: Browser DevTools

1. Open http://localhost:5173
2. Press F12 (DevTools)
3. Go to Network tab
4. Try login
5. Check the failed request:
   - Should NOT show `net::ERR_FAILED`
   - Should show actual HTTP response (200, 401, etc.)

---

## 🔧 Manual Fix (Without Script)

If the script doesn't work, manually edit `.env`:

### Step 1: Open .env

```powershell
cd backend
notepad .env
```

### Step 2: Find HOST Line

Look for:
```
HOST=127.0.0.1
```

### Step 3: Change to 0.0.0.0

```
HOST=0.0.0.0
```

### Step 4: Save and Close

### Step 5: Verify Other Settings

While you're in `.env`, also verify:

```bash
# These should be set correctly
PORT=8080
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database (adjust as needed)
DATABASE_URL=postgresql://postgres:password@localhost:5432/betting_db

# JWT Secret (use a real secret in production)
JWT_SECRET=your-secret-key-here
```

### Step 6: Restart Backend

```powershell
.\run.ps1
```

---

## 🚨 Still Getting ERR_FAILED?

### Issue 1: Port Already in Use

**Symptom**: Backend fails to start, says "Address already in use"

**Solution**:
```powershell
# Find what's using port 8080
netstat -ano | findstr :8080

# Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>

# Then restart backend
.\run.ps1
```

### Issue 2: Firewall Blocking

**Symptom**: Backend starts but browser can't connect

**Solution**:
```powershell
# Allow backend through Windows Firewall
netsh advfirewall firewall add rule name="Backend Dev Server" dir=in action=allow protocol=TCP localport=8080
```

### Issue 3: Antivirus Blocking

**Symptom**: Backend starts but connections timeout

**Solution**: Temporarily disable antivirus and test

### Issue 4: Wrong Port

**Symptom**: Backend is on port 8443 but frontend expects 8080

**Check frontend/.env**:
```bash
VITE_API_URL=http://localhost:8080/api/v1  # Should match backend port
```

**Check backend/.env**:
```bash
PORT=8080  # Should match frontend expectation
```

### Issue 5: HTTPS vs HTTP Mismatch

**Symptom**: Backend uses HTTPS but frontend uses HTTP (or vice versa)

**Solution**: Make both use HTTP for development

**Backend .env**:
```bash
HTTPS_ENABLED=false  # or comment out TLS settings
```

**Frontend .env**:
```bash
VITE_API_URL=http://localhost:8080/api/v1  # Use http://, not https://
```

---

## 📝 Complete .env Template

Here's a working `.env` for local development:

```bash
# Server Configuration
HOST=0.0.0.0           # ← THIS IS CRITICAL!
PORT=8080
HTTPS_ENABLED=false    # Use HTTP for local dev

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/betting_db

# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRATION_HOURS=24

# Encryption
WALLET_ENCRYPTION_KEY=your-32-byte-key-here

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECS=60

# Logging
RUST_LOG=info
LOG_LEVEL=info

# Fraud Detection
FRAUD_ALERT_EMAIL=security@footballheritage.com

# Metrics
METRICS_ENABLED=true
```

---

## 🎯 Quick Checklist

Before testing:
- [ ] Backend .env has `HOST=0.0.0.0` (not 127.0.0.1)
- [ ] Backend .env has `PORT=8080`
- [ ] Backend .env has `ALLOWED_ORIGINS=http://localhost:5173`
- [ ] Backend .env has `HTTPS_ENABLED=false` (for local dev)
- [ ] Backend stopped (Ctrl+C)
- [ ] Backend restarted (`.\run.ps1`)
- [ ] Backend logs show "Starting server on 0.0.0.0:8080"
- [ ] `netstat` shows backend listening on 0.0.0.0:8080
- [ ] Health check works: `curl http://localhost:8080/health`
- [ ] Frontend .env has `VITE_API_URL=http://localhost:8080/api/v1`
- [ ] Browser cache cleared

After restart:
- [ ] No `net::ERR_FAILED` in console
- [ ] Network tab shows actual HTTP responses
- [ ] Login works or shows proper error (401, 400, etc.)
- [ ] CORS headers present in response

---

## 💡 Why This Happens

**Windows Networking Quirks**:
1. Windows treats `127.0.0.1` and `localhost` as potentially different interfaces
2. Some Windows network configurations have IPv6 enabled, making `localhost` resolve to `::1` (IPv6) instead of `127.0.0.1` (IPv4)
3. Browsers enforce stricter network isolation than command-line tools
4. CORS checks happen at a different network layer than simple TCP connections

**The Solution**:
- Binding to `0.0.0.0` tells the server to listen on **all** network interfaces
- This ensures the server is accessible via:
  - `localhost` (whatever it resolves to)
  - `127.0.0.1` (IPv4 loopback)
  - `::1` (IPv6 loopback)
  - Any other local network address

---

## 🚀 Expected Outcome

After fixing HOST to 0.0.0.0:

**Backend Logs**:
```
INFO  Server configuration loaded
INFO  CORS allowed origins: ["http://localhost:5173", "http://localhost:3000"]
INFO  Starting server on 0.0.0.0:8080
INFO  HTTPS disabled - running in insecure mode
```

**Browser Network Tab**:
```
POST http://localhost:8080/api/v1/auth/login
Status: 200 OK (or 401 if wrong credentials)
Response Headers:
  access-control-allow-origin: http://localhost:5173
  content-type: application/json
```

**No More Errors**:
- ❌ `net::ERR_FAILED` → ✅ Gone!
- ❌ CORS error → ✅ Fixed!
- ❌ Connection refused → ✅ Connected!

---

## 📞 Summary

**Problem**: `net::ERR_FAILED` - Backend not responding

**Root Cause**: Backend listening on `127.0.0.1` instead of `0.0.0.0`

**Solution**:
1. ✅ Update `backend/.env`: `HOST=0.0.0.0`
2. ✅ Run `.\fix_host.ps1` (or edit manually)
3. ✅ Restart backend: `.\run.ps1`
4. ✅ Verify logs show `0.0.0.0:8080`
5. ✅ Test in browser

**Result**: Login now works! 🎉

---

**Last Updated**: 2025-10-19  
**Status**: Host Configuration Fix  
**Action Required**: Update HOST in .env and restart backend

🚀 **Your backend will now accept browser connections!**