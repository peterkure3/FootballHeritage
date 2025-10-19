# 🔧 CORS Fix - Browser Login Issue

## ❌ The Problem

**Error in Browser Console**:
```
Access to fetch at 'http://localhost:8080/api/v1/auth/login' from origin 'http://localhost:5173' 
has been blocked by CORS policy: Response to preflight request doesn't pass access control check: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Why it works in Postman but not Browser**:
- Postman doesn't enforce CORS (it's a development tool)
- Browsers enforce CORS for security (cross-origin requests)
- The backend needs to explicitly allow requests from `http://localhost:5173`

---

## ✅ The Solution

### Step 1: Check Backend .env File

**File**: `backend/.env`

Make sure this line exists and includes `http://localhost:5173`:

```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://yourdomain.com
```

### Step 2: Verify Backend CORS Configuration

**File**: `backend/src/main.rs` (around line 128-142)

Should look like this:

```rust
let cors = Cors::default()
    .allowed_origin_fn(move |origin, _req_head| {
        let origin_str = origin.to_str().unwrap_or("");
        allowed_origins_clone.contains(&origin_str.to_string())
    })
    .allowed_methods(vec!["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    .allowed_headers(vec![
        header::AUTHORIZATION,
        header::CONTENT_TYPE,
        header::ACCEPT,
    ])
    .supports_credentials()
    .max_age(3600);
```

### Step 3: Restart Backend Server

**IMPORTANT**: The backend must be restarted to pick up the new ALLOWED_ORIGINS!

```bash
# Stop backend (Ctrl+C)

# Restart backend
cd backend
.\run.ps1  # Windows PowerShell
# OR
./run.sh   # Linux/Mac
```

### Step 4: Verify CORS Headers

Test that the backend returns correct CORS headers:

```bash
curl -X OPTIONS http://localhost:8080/api/v1/auth/login \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

**Expected Response Headers**:
```
< HTTP/1.1 200 OK
< access-control-allow-origin: http://localhost:5173
< access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS
< access-control-allow-headers: authorization, content-type, accept
< access-control-max-age: 3600
< access-control-allow-credentials: true
```

---

## 🚀 Quick Fix (Step-by-Step)

### 1. Update Backend .env

```bash
cd backend
nano .env  # or your preferred editor
```

Add or update:
```bash
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

Save and exit.

### 2. Restart Backend

```bash
# Stop current backend process (Ctrl+C)

# Restart
.\run.ps1  # Windows
# OR
./run.sh   # Linux/Mac
```

Wait for this message:
```
✓ Server started successfully
  Listening on http://0.0.0.0:8080
  Allowed origins: http://localhost:5173, http://localhost:3000
```

### 3. Test in Browser

1. Open http://localhost:5173
2. Go to Login page
3. Try to login
4. Open DevTools (F12) → Network tab
5. Look for the OPTIONS request (preflight)
6. Check Response Headers for `access-control-allow-origin`

---

## 🔍 Debugging CORS Issues

### Check 1: Verify Backend is Reading .env

Look at backend startup logs. Should see:
```
INFO  Allowed origins: http://localhost:5173, http://localhost:3000
```

If not, the .env file isn't being read.

### Check 2: Browser Network Tab

1. Open DevTools (F12)
2. Go to Network tab
3. Try to login
4. Look for TWO requests:
   - `OPTIONS /api/v1/auth/login` (preflight)
   - `POST /api/v1/auth/login` (actual request)

The OPTIONS request must return:
- Status: **200 OK** or **204 No Content**
- Header: `access-control-allow-origin: http://localhost:5173`

### Check 3: Test with curl

```bash
# Test OPTIONS preflight
curl -X OPTIONS http://localhost:8080/api/v1/auth/login \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i

# Should return 200 OK with CORS headers
```

### Check 4: Common Mistakes

❌ **Mistake 1**: Backend not restarted after .env change
- **Fix**: Always restart backend after changing .env

❌ **Mistake 2**: Wrong origin format
- **Wrong**: `http://localhost:5173/` (trailing slash)
- **Right**: `http://localhost:5173` (no trailing slash)

❌ **Mistake 3**: Using HTTPS when backend is HTTP
- **Check**: Frontend .env should use `http://` if backend uses HTTP

❌ **Mistake 4**: Port mismatch
- **Check**: Frontend runs on 5173, backend on 8080

---

## 🛠️ Alternative Solutions

### Solution 1: Temporary - Allow All Origins (DEV ONLY!)

**⚠️ WARNING: Only for local development testing!**

In `backend/src/main.rs`, temporarily change:

```rust
let cors = Cors::permissive(); // Allows all origins
```

Then restart backend. This is **NOT** for production!

### Solution 2: Use Vite Proxy (Frontend)

If backend CORS is hard to configure, use Vite's proxy feature.

**File**: `frontend/vite.config.js`

```javascript
export default {
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      }
    }
  }
}
```

Then update frontend .env:
```bash
VITE_API_URL=/api/v1
```

This makes the frontend send requests to itself, and Vite proxies to backend.

### Solution 3: Run Backend and Frontend on Same Port

Use a reverse proxy (nginx, Apache) to serve both on same origin.

**Not recommended for development** - too complex.

---

## ✅ Verification Steps

After applying the fix:

1. **Backend Logs** - Should show:
   ```
   INFO Allowed origins: http://localhost:5173
   ```

2. **OPTIONS Request** - Should return:
   ```
   HTTP/1.1 200 OK
   access-control-allow-origin: http://localhost:5173
   ```

3. **POST Request** - Should work:
   ```
   HTTP/1.1 200 OK
   access-control-allow-origin: http://localhost:5173
   {"token":"eyJ..."}
   ```

4. **Browser Console** - No CORS errors

5. **Login Works** - Redirects to dashboard

---

## 📝 Complete Example

### Backend .env
```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/betting_db

# JWT
JWT_SECRET=your-secret-key-here

# Server
HOST=0.0.0.0
PORT=8080

# CORS - Add your frontend origin here!
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Other settings...
```

### Start Backend
```bash
cd backend
.\run.ps1
```

### Check Backend Logs
```
INFO  Server configuration loaded
INFO  Allowed origins: http://localhost:5173, http://localhost:3000
INFO  Starting HTTP server
INFO  Listening on http://0.0.0.0:8080
```

### Test from Browser
```javascript
// Open console at http://localhost:5173
fetch('http://localhost:8080/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'test@test.com',
    password: 'Test123!'
  })
})
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
```

Should return token, not CORS error.

---

## 🚨 Still Not Working?

### Nuclear Option: Reset Everything

```bash
# 1. Stop both servers

# 2. Backend - Clear and restart
cd backend
rm -rf target/  # Clear build cache
.\run.ps1

# 3. Frontend - Clear and restart
cd frontend
rm -rf node_modules/ .vite/
npm install
npm run dev

# 4. Browser - Clear cache
# Ctrl+Shift+Delete → Clear cache
# Or use Incognito mode

# 5. Try again
```

### Check Firewall

Windows Firewall might block cross-origin requests:

```powershell
# Allow backend through firewall
netsh advfirewall firewall add rule name="Backend Dev Server" dir=in action=allow protocol=TCP localport=8080
```

### Check Antivirus

Some antivirus software blocks localhost cross-origin requests. Try temporarily disabling it.

---

## 📞 Final Checklist

Before asking for more help, verify:

- [ ] Backend .env has `ALLOWED_ORIGINS=http://localhost:5173`
- [ ] Backend was **restarted** after changing .env
- [ ] Backend logs show correct allowed origins
- [ ] Backend is listening on port 8080
- [ ] Frontend is running on port 5173
- [ ] Frontend .env has `VITE_API_URL=http://localhost:8080/api/v1`
- [ ] Browser DevTools shows OPTIONS request
- [ ] OPTIONS request returns 200 OK
- [ ] OPTIONS response has `access-control-allow-origin` header
- [ ] Browser cache cleared (or use Incognito)
- [ ] No firewall blocking localhost:8080
- [ ] No antivirus blocking requests

---

## 🎯 TL;DR - Quick Fix

```bash
# 1. Add to backend/.env
ALLOWED_ORIGINS=http://localhost:5173

# 2. Restart backend
cd backend
.\run.ps1

# 3. Check backend logs for "Allowed origins"

# 4. Try login again in browser

# Done! ✅
```

---

**Last Updated**: 2025-10-19  
**Status**: CORS Configuration Guide  
**Next**: After fixing CORS, login should work in browser!

🎉 **Once CORS is fixed, your login will work perfectly!**