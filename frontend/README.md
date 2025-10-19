# SportsBet Frontend - React + Vite + Tailwind CSS v4

A modern, secure, and high-performance sports betting frontend built with React 18, Vite, and Tailwind CSS v4. This application integrates with a Rust-based backend API for NFL sports betting.

## 🚀 Features

### Security
- **JWT Authentication** with encrypted localStorage
- **CSRF Token Protection** on all requests
- **Auto-logout** after 15 minutes of inactivity
- **Age Verification** (21+ only) with modal confirmation
- **Input Sanitization** on all form submissions
- **HTTPS-only** communication with backend

### Performance
- **React Query Caching** for optimized data fetching
- **Real-time Odds Updates** every 15 seconds
- **Optimistic UI Updates** for instant feedback
- **Memoized Components** to prevent unnecessary re-renders
- **Infinite Scroll** for betting history
- **Loading Skeletons** for better UX
- **<100ms Bet Placement** with optimized mutations

### Responsible Gambling
- **Session Limits** ($100 per session)
- **Warning Thresholds** at 80% of limit
- **Bet Limits** ($1 min, $100 max per event)
- **Real-time Budget Tracking** with progress bars
- **Problem Gambling Resources** prominently displayed
- **Helpline Information** (1-800-522-4700)

### User Experience
- **Dark Theme** with Tailwind CSS v4
- **Mobile Responsive** design
- **Smooth Animations** and transitions
- **Toast Notifications** for user feedback
- **Live Bet Counters** and statistics
- **Clean Bet365-style** interface

## 📋 Tech Stack

- **React 18.3+** - Modern React with hooks and context
- **Vite 7.1+** - Lightning-fast build tool
- **React Router v6** - Client-side routing
- **TanStack Query (React Query)** - Server state management
- **Zustand** - Lightweight state management for auth & betting
- **Zod** - TypeScript-first schema validation
- **React Hot Toast** - Beautiful toast notifications
- **Tailwind CSS v4** - Utility-first CSS framework
- **JavaScript (ES6+)** - Pure JavaScript, no TypeScript

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── BetCard.jsx
│   │   ├── OddsRow.jsx
│   │   ├── WalletModal.jsx
│   │   ├── BetConfirmationModal.jsx
│   │   ├── AgeVerificationModal.jsx
│   │   ├── LoadingSkeleton.jsx
│   │   └── Navbar.jsx
│   ├── pages/               # Page components
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Odds.jsx
│   │   └── BetHistory.jsx
│   ├── stores/              # Zustand stores
│   │   ├── authStore.js
│   │   └── bettingStore.js
│   ├── hooks/               # Custom React hooks
│   │   ├── useAuth.js
│   │   └── useBetting.js
│   ├── utils/               # Utility functions
│   │   ├── api.js
│   │   └── validation.js
│   ├── App.jsx              # Main app component with routing
│   ├── main.jsx             # App entry point
│   └── index.css            # Tailwind imports
├── public/                  # Static assets
├── .env                     # Environment variables
├── .env.example             # Environment variables template
├── package.json             # Dependencies
├── vite.config.js           # Vite configuration
└── README.md                # This file
```

## 🛠️ Installation & Setup

### Prerequisites
- **Node.js 18+** and npm/yarn
- **Backend API** running (Rust backend on https://localhost:8443)

### Step 1: Install Dependencies
```bash
cd frontend
npm install
```

### Step 2: Configure Environment
```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your backend API URL
# Default: VITE_API_URL=https://localhost:8443/api
```

### Step 3: Run Development Server
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Step 4: Build for Production
```bash
npm run build
```

Build output will be in the `dist/` folder.

### Step 5: Preview Production Build
```bash
npm run preview
```

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `https://localhost:8443/api` |
| `VITE_ENV` | Environment name | `development` |
| `VITE_SESSION_TIMEOUT` | Session timeout in minutes | `15` |
| `VITE_ENABLE_ANALYTICS` | Enable analytics tracking | `false` |
| `VITE_ENABLE_DEBUG` | Enable debug logging | `true` |

## 📡 API Integration

The frontend communicates with the Rust backend via these endpoints:

### Authentication
- `POST /api/register` - Register new user (email, password, dob)
- `POST /api/login` - Login user (returns JWT token)

### User Operations
- `GET /api/user` - Get user data (balance, bets history)

### Wallet Operations
- `POST /api/deposit` - Deposit funds
- `POST /api/withdraw` - Withdraw funds

### Betting Operations
- `GET /api/odds` - Get NFL game odds (auto-refreshes every 15s)
- `POST /api/bets` - Place a bet (event_id, amount, odds, type)

## 🎨 Component Guide

### Pages

#### Login (`/login`)
- Email/password authentication
- Password visibility toggle
- Form validation with Zod
- Redirects to dashboard on success

#### Register (`/register`)
- Email, password, DOB, terms acceptance
- Age verification modal (21+)
- Strong password requirements
- Age calculation and validation

#### Dashboard (`/dashboard`)
- User balance display
- Session limit progress bar
- Active bets overview
- Recent betting history
- Quick action buttons
- Statistics cards

#### Odds (`/odds`)
- Real-time NFL odds (updates every 15s)
- Filter by status (all, live, upcoming)
- Moneyline, spread, and over/under betting
- Click to place bet with confirmation modal

#### Bet History (`/bets`)
- Complete betting history
- Filter by status (all, pending, won, lost)
- Search functionality
- Infinite scroll (load more)
- Financial summary statistics

### Components

#### BetCard
Displays individual bet information:
- Event name and date
- Bet type and odds
- Stake and potential payout
- Status badge (pending, won, lost)

#### OddsRow
Displays betting odds for a game:
- Team names and scores (if live)
- Moneyline, spread, over/under options
- Click handlers for bet placement
- Live indicator

#### WalletModal
Deposit/withdraw interface:
- Tabbed interface (deposit/withdraw)
- Amount input with validation
- Quick amount buttons ($10, $25, $50, $100)
- Balance display and limits

#### BetConfirmationModal
Confirms bet placement:
- Event details summary
- Amount input with validation
- Potential payout calculation
- Session limit warning
- Responsible gambling notices

#### AgeVerificationModal
Age verification (21+):
- DOB validation
- Legal disclaimers
- Responsible gambling resources
- Confirmation/rejection flows

#### Navbar
Main navigation:
- Logo and branding
- Balance display
- Navigation links (Dashboard, Odds, Bets)
- Deposit/withdraw buttons
- Logout button
- Mobile-responsive menu

#### LoadingSkeleton
Loading state placeholders:
- Card skeleton
- Odds skeleton
- List skeleton
- Stats skeleton

## 🔐 Security Features

### Token Management
- JWT tokens stored encrypted in localStorage
- XOR encryption with secret key (basic obfuscation)
- Auto-logout on token expiration
- Session timeout tracking with activity detection

### CSRF Protection
- CSRF token generated on app load
- Sent with every API request
- Token rotation on security events

### Input Validation
- Zod schemas for all form inputs
- Email sanitization
- Amount validation (2 decimal places max)
- Text sanitization (remove HTML/script tags)

### Age Verification
- DOB validation (must be 21+)
- Age calculation with edge case handling
- Modal confirmation with legal notices

## 🎰 Responsible Gambling

### Session Limits
- $100 maximum per session
- Real-time tracking of session total
- Warning at 80% ($80)
- Hard stop at 100% ($100)
- Progress bar visualization

### Bet Limits
- Minimum: $1 per bet
- Maximum: $100 per bet per event
- Validation on both frontend and backend

### Resources
- National Problem Gambling Helpline: 1-800-522-4700
- Links to ncpgambling.org
- Prominent placement throughout app
- Help section on dashboard

## 🧪 Testing the Frontend

### Manual Testing Checklist

#### Authentication Flow
- [ ] Register with valid email/password/DOB (21+)
- [ ] Age verification modal appears
- [ ] Register with underage DOB (rejected)
- [ ] Login with correct credentials
- [ ] Login with incorrect credentials (error)
- [ ] Auto-logout after 15 minutes

#### Betting Flow
- [ ] View odds page with games
- [ ] Odds refresh every 15 seconds
- [ ] Click to place bet opens modal
- [ ] Enter bet amount with validation
- [ ] Session limit warnings appear
- [ ] Cannot exceed $100 session limit
- [ ] Bet appears in history after placement

#### Wallet Operations
- [ ] Open wallet modal
- [ ] Deposit funds (min $10, max $10,000)
- [ ] Withdraw funds (min $10, max balance)
- [ ] Balance updates after transaction

#### Responsive Design
- [ ] Test on mobile (320px+)
- [ ] Test on tablet (768px+)
- [ ] Test on desktop (1024px+)
- [ ] Mobile menu works correctly

## 🚧 Known Limitations

1. **Mock Data**: If backend is not running, odds may not load
2. **TLS Certificates**: Dev TLS cert may show browser warnings
3. **Real-time Updates**: WebSocket not implemented (polling only)
4. **Payment Processing**: Mock deposit/withdrawal (no real payment gateway)
5. **Multi-currency**: USD only

## 🐛 Troubleshooting

### CORS Errors
Ensure backend allows requests from `http://localhost:5173`:
```rust
// In backend Actix CORS config
.allowed_origin("http://localhost:5173")
```

### TLS Certificate Errors
Accept the self-signed cert in browser or use HTTP for development:
```bash
# In .env
VITE_API_URL=http://localhost:8080/api
```

### Token Expired Errors
Clear localStorage and login again:
```javascript
// In browser console
localStorage.clear()
```

### Odds Not Updating
Check backend is running and `/api/odds` endpoint is accessible.

### Build Errors
Clear node_modules and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```

## 📚 Development Guide

### Adding a New Page
1. Create page component in `src/pages/`
2. Add route in `App.jsx`
3. Add navigation link in `Navbar.jsx`
4. Wrap with `<ProtectedRoute>` if auth required

### Adding a New API Call
1. Add function in `src/utils/api.js`
2. Create custom hook in `src/hooks/`
3. Use React Query for caching
4. Handle loading/error states

### Adding a New Component
1. Create in `src/components/`
2. Use memo() for optimization
3. Add PropTypes or JSDoc comments
4. Use Tailwind classes for styling

### State Management
- **Auth State**: `authStore.js` (Zustand)
- **Betting State**: `bettingStore.js` (Zustand)
- **Server State**: React Query hooks
- **Local State**: useState/useReducer

## 🎯 Performance Optimization

### React Query Settings
- `staleTime`: 30s (data considered fresh)
- `cacheTime`: 5m (cache kept in memory)
- `refetchInterval`: 15s for odds (real-time)
- `retry`: 2 attempts on failure

### Component Optimization
- Use `memo()` for expensive components
- Lazy load routes with React.lazy()
- Virtualize long lists (betting history)
- Debounce search inputs

### Bundle Size
- Tailwind CSS v4 with purge (production)
- Tree-shaking enabled in Vite
- Code splitting by route
- Compress images and assets

## 📞 Support

For issues or questions:
- Backend Issues: Check backend README
- Frontend Issues: Create GitHub issue
- Security Concerns: Email security@sportsbet.com

## 📄 License

MIT License - See LICENSE file for details

## ⚠️ Legal Disclaimer

This is a demonstration sports betting platform. Real gambling involves risk. Only users 21 years or older may participate. If you have a gambling problem, call 1-800-522-4700.

---

**Built with ⚡ by the SportsBet Team**