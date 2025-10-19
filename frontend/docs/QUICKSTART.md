# 🚀 SportsBet Frontend - Quick Start

## ⚡ 30-Second Setup

```bash
cd frontend
npm install
npm run dev
```

Open: **http://localhost:5173**

## 📋 Prerequisites

- ✅ Node.js 18+
- ✅ Backend running at https://localhost:8443
- ✅ Accept TLS certificate in browser

## 🎯 First-Time Setup

```bash
# 1. Install dependencies
npm install

# 2. Copy environment config (optional - defaults work)
cp .env.example .env

# 3. Start dev server
npm run dev

# 4. Open browser
# http://localhost:5173
```

## 🔑 Test Account

**Create via Registration Page**:
- Email: test@test.com
- Password: Test123!
- DOB: 21+ years ago (e.g., 2000-01-01)
- Accept terms → Age verification → Register

## 📁 Key Files

```
src/
├── App.jsx              # Main app + routing
├── pages/               # Login, Register, Dashboard, Odds, BetHistory
├── components/          # BetCard, OddsRow, Modals, Navbar
├── stores/              # authStore, bettingStore
├── hooks/               # useAuth, useBetting
└── utils/               # api.js, validation.js
```

## 🛠️ Common Commands

```bash
npm run dev        # Start dev server (http://localhost:5173)
npm run build      # Build for production (→ dist/)
npm run preview    # Preview production build
npm run lint       # Run ESLint
```

## 🔧 Configuration

### Backend URL
**File**: `.env`
```bash
# For HTTPS (dev TLS)
VITE_API_URL=https://localhost:8443/api

# For HTTP (TLS disabled)
VITE_API_URL=http://localhost:8080/api
```

## 🧪 Quick Test Flow

1. **Register** → http://localhost:5173/register
   - Fill form with 21+ DOB
   - Accept age verification

2. **Dashboard** → Auto-redirect after registration
   - View balance (starts at $0)

3. **Deposit** → Click "Deposit" button in navbar
   - Enter $100
   - Balance updates

4. **Place Bet** → Navigate to "Odds"
   - Click any bet button
   - Enter $25
   - Confirm

5. **View History** → Navigate to "My Bets"
   - See your bet in history

## 🚨 Troubleshooting

### Backend Not Running
```bash
cd ../backend
.\run.ps1  # Windows
./run.sh   # Linux/Mac
```

### TLS Certificate Error
**Option 1**: Visit https://localhost:8443 → "Advanced" → "Proceed"  
**Option 2**: Use HTTP (see Configuration above)

### CORS Error
Check backend `config.toml`:
```toml
allowed_origins = ["http://localhost:5173"]
```

### Cannot Login
- Clear localStorage: `localStorage.clear()` in console
- Restart backend and frontend

### Odds Not Loading
- Check backend is running: `curl https://localhost:8443/api/odds -k`
- Check backend logs for errors

## 📚 Documentation

- **README.md** - Complete project documentation
- **INTEGRATION_GUIDE.md** - Backend integration details
- **COMPLETE_GUIDE.md** - Full implementation guide

## 🎨 Tech Stack

- React 18 (JavaScript, NO TypeScript)
- Vite 7.1+ (Build tool)
- Tailwind CSS v4 (Styling)
- React Router v6 (Routing)
- TanStack Query (Data fetching)
- Zustand (State management)
- Zod (Validation)
- React Hot Toast (Notifications)

## 🔐 Security Features

- ✅ JWT authentication (encrypted in localStorage)
- ✅ CSRF token protection
- ✅ Auto-logout after 15 minutes
- ✅ Age verification (21+)
- ✅ Input sanitization
- ✅ Session timeouts

## 🎰 Responsible Gambling

- **Session Limit**: $100 per session
- **Bet Limits**: $1 min, $100 max per event
- **Warnings**: At 80% of session limit
- **Helpline**: 1-800-522-4700
- **Resources**: ncpgambling.org

## 📱 Features

✅ User Authentication (Login/Register)  
✅ Dashboard with Stats  
✅ Live Odds Display (15s refresh)  
✅ Bet Placement (Moneyline/Spread/O-U)  
✅ Wallet (Deposit/Withdraw)  
✅ Bet History with Filters  
✅ Mobile Responsive  
✅ Dark Theme (Bet365-style)  
✅ Loading Skeletons  
✅ Toast Notifications  

## 🌐 URLs

- **Frontend**: http://localhost:5173
- **Backend**: https://localhost:8443
- **API Docs**: https://localhost:8443/api
- **GitHub**: (your repo URL here)

## 💡 Quick Tips

1. **Hot Reload**: Edit files → auto-refresh
2. **React DevTools**: Install browser extension
3. **Network Tab**: Monitor API calls
4. **Console Errors**: Check browser console
5. **Backend Logs**: Check backend terminal

## 🐛 Debug Commands

```javascript
// In browser console

// Check auth state
useAuthStore.getState()

// Check betting state
useBettingStore.getState()

// Clear all data
localStorage.clear()

// Check token
localStorage.getItem('betting_auth_token')
```

## 📞 Need Help?

1. Check **README.md** for detailed docs
2. Check **INTEGRATION_GUIDE.md** for backend setup
3. Check browser console for errors
4. Check backend logs for API errors
5. Clear cache and localStorage

## ⚡ Performance

- **Bundle Size**: ~500KB (gzipped)
- **First Load**: ~1-2 seconds
- **Bet Placement**: <100ms
- **Odds Refresh**: Every 15 seconds
- **React Query Cache**: 5 minutes

## 🎯 Development Workflow

```bash
# 1. Pull latest changes
git pull

# 2. Install any new dependencies
npm install

# 3. Start dev server
npm run dev

# 4. Make changes (hot reload enabled)
# Edit src/pages/Dashboard.jsx

# 5. Build for production
npm run build

# 6. Test production build
npm run preview
```

## 🚢 Deployment

```bash
# Build
npm run build

# Deploy to Vercel
vercel deploy

# Deploy to Netlify
netlify deploy --prod

# Deploy to custom server
# Upload dist/ folder to web server
```

## 📝 Environment Variables

```bash
VITE_API_URL=https://localhost:8443/api    # Backend URL
VITE_ENV=development                        # Environment
VITE_SESSION_TIMEOUT=15                     # Minutes
VITE_ENABLE_DEBUG=true                      # Debug mode
```

## 🎓 Learning Resources

- **React**: https://react.dev
- **Vite**: https://vitejs.dev
- **Tailwind**: https://tailwindcss.com
- **React Router**: https://reactrouter.com
- **TanStack Query**: https://tanstack.com/query

---

## ✨ You're All Set!

```bash
npm run dev
```

**Frontend**: http://localhost:5173  
**Backend**: https://localhost:8443

**Test User**: Register at /register (21+ DOB)  
**Default Balance**: $0 (use Deposit to add funds)  
**Session Limit**: $100

🎰 **Gamble Responsibly • 21+ Only • Call 1-800-522-4700**

---

**Built with ⚡ by the SportsBet Team**