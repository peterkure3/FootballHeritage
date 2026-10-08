import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import useAuthStore from "./stores/authStore";
import ErrorBoundary from "./components/ErrorBoundary";

// Pages
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Odds from "./pages/Odds";
import BetHistory from "./pages/BetHistory";
import Chat from "./pages/Chat";
import Sports from './pages/Sports';
import ParlayCalculator from './pages/ParlayCalculator';
import AdminDashboard from './pages/AdminDashboard';
import AdminBets from './pages/AdminBets';
import AdminEvents from './pages/AdminEvents';
import AdminUsers from './pages/AdminUsers';
import AdminAnalytics from './pages/AdminAnalytics';
import AdminRevenue from './pages/AdminRevenue';
import AdminSettings from './pages/AdminSettings';
import AdminLogs from './pages/AdminLogs';
import AdminSportsGPT from './pages/AdminSportsGPT';
import AdminLayout from './components/admin/AdminLayout';
import Predictions from "./pages/Predictions";
import DeviggedOdds from "./pages/DeviggedOdds";
import EVBets from "./pages/EVBets";
import Arbitrage from "./pages/Arbitrage";
import BestBets from "./pages/BestBets";
import SmartAssistant from "./pages/SmartAssistant";
import CollegeSports from "./pages/CollegeSports";
import MarchMadnessBracket from "./pages/MarchMadnessBracket";
import FPLAdvisor from "./pages/FPLAdvisor";
import PlayerProps from "./pages/PlayerProps";
import HomePage, { StoryPage } from './heritage/HomePage';
import SportPage, { TeamsPage } from './heritage/SportPage';
import { BestPicksPage, AiChatPage } from './heritage/AiPages';
import MainNavbar from './heritage/MainNavbar';
import Landing from './landing/Landing';
import LandingNavbar from './landing/LandingNavbar';
import { safeReturnTo } from './utils/authRedirect';

// Create React Query client with optimized settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 2,
      staleTime: 30000, // 30 seconds
      gcTime: 300000, // 5 minutes (React Query v5)
    },
    mutations: {
      retry: 0, // Never automatically replay money-moving requests.
    },
  },
});

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: `${location.pathname}${location.search}${location.hash}` }} replace />;
  }

  return children;
};

// Admin Route Component (requires authenticated user with admin/superadmin role)
const AdminRoute = ({ children }) => {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: `${location.pathname}${location.search}${location.hash}` }} replace />;
  }

  if (!user?.is_admin && !user?.is_super_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// Public Route Component (redirect to dashboard if already logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();
  const requested = new URLSearchParams(location.search).get('returnTo') ?? location.state?.from;

  if (isAuthenticated) {
    return <Navigate to={safeReturnTo(requested)} replace />;
  }

  return children;
};

function ApplicationNavbar() {
  const { pathname } = useLocation();
  if (pathname === '/') return null;
  if (/^\/(login|register)\/?$/.test(pathname)) {
    return <div className="fh-landing landing-auth-header"><LandingNavbar /></div>;
  }
  return <MainNavbar />;
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <div className="min-h-screen heritage-app" style={{ background: 'var(--color-surface, #f0f2ef)' }}>
          <ApplicationNavbar />
          <Routes>
            <Route path="/app" element={<HomePage />} />
            <Route path="/sport/:sport" element={<SportPage />} />
            <Route path="/sport/:sport/:section" element={<SportPage />} />
            <Route path="/stories/:id" element={<StoryPage />} />
            <Route path="/saved" element={<HomePage savedOnly />} />
            <Route path="/followed-teams" element={<TeamsPage followedOnly />} />
            {/* Public Routes */}
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <Login />
                </PublicRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicRoute>
                  <Register />
                </PublicRoute>
              }
            />

            {/* Protected Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/odds"
              element={
                <ProtectedRoute>
                  <Odds />
                </ProtectedRoute>
              }
            />
            <Route
              path="/bets"
              element={
                <ProtectedRoute>
                  <BetHistory />
                </ProtectedRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <ProtectedRoute>
                  <SmartAssistant />
                </ProtectedRoute>
              }
            />
            <Route
              path="/assistant"
              element={
                <ProtectedRoute>
                  <SmartAssistant />
                </ProtectedRoute>
              }
            />

            <Route
              path="/sports"
              element={
                <ProtectedRoute>
                  <Sports />
                </ProtectedRoute>
              }
            />

            <Route
              path="/predictions"
              element={
                <ProtectedRoute>
                  <Predictions />
                </ProtectedRoute>
              }
            />

            <Route
              path="/intelligence/devigged-odds"
              element={
                <ProtectedRoute>
                  <DeviggedOdds />
                </ProtectedRoute>
              }
            />
            <Route
              path="/intelligence/ev-bets"
              element={
                <ProtectedRoute>
                  <EVBets />
                </ProtectedRoute>
              }
            />
            <Route
              path="/intelligence/arbitrage"
              element={
                <ProtectedRoute>
                  <Arbitrage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/best-bets"
              element={
                <ProtectedRoute>
                  <BestBets />
                </ProtectedRoute>
              }
            />
            <Route
              path="/ai-picks"
              element={<BestPicksPage />}
            />
            <Route
              path="/ai-picks/chat"
              element={<AiChatPage />}
            />
            <Route
              path="/player-props"
              element={
                <ProtectedRoute>
                  <PlayerProps />
                </ProtectedRoute>
              }
            />
            <Route
              path="/parlay-calculator"
              element={
                <ProtectedRoute>
                  <ParlayCalculator />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
            <Route
              path="/college"
              element={
                <ProtectedRoute>
                  <CollegeSports />
                </ProtectedRoute>
              }
            />
            <Route
              path="/college/bracket"
              element={
                <ProtectedRoute>
                  <MarchMadnessBracket />
                </ProtectedRoute>
              }
            />
            <Route
              path="/fpl-advisor"
              element={
                <ProtectedRoute>
                  <FPLAdvisor />
                </ProtectedRoute>
              }
            />
            {/* Admin Routes - Nested under AdminLayout */}
            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <AdminLayout />
                </AdminRoute>
              }
            >
              <Route index element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="dashboard" element={<AdminDashboard />} />
              <Route path="events" element={<AdminEvents />} />
              <Route path="bets" element={<AdminBets />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="analytics" element={<AdminAnalytics />} />
              <Route path="revenue" element={<AdminRevenue />} />
              <Route path="sportsgpt" element={<AdminSportsGPT />} />
              <Route path="settings" element={<AdminSettings />} />
              <Route path="logs" element={<AdminLogs />} />
            </Route>

            {/* Default Route */}
            <Route path="/" element={<Landing />} />

            {/* 404 Route */}
            <Route
              path="*"
              element={
                <div className="min-h-screen bg-surface flex items-center justify-center p-4">
                  <div className="text-center">
                    <h1 className="text-6xl font-normal text-heritage-ink mb-4">404</h1>
                    <p className="text-heritage-muted text-xl mb-8">Page not found</p>
                    <a
                      href="/"
                      className="fh-button"
                    >
                      Return home
                    </a>
                  </div>
                </div>
              }
            />
          </Routes>
        </div>

        {/* Toast Notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: "#fff",
              color: "#202723",
              border: "1px solid #e1e6dd",
            },
            success: {
              iconTheme: {
                primary: "#10b981",
                secondary: "#fff",
              },
            },
            error: {
              iconTheme: {
                primary: "#ef4444",
                secondary: "#fff",
              },
            },
          }}
        />
      </Router>
    </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
