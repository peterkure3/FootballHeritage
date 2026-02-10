import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
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

// Create React Query client with optimized settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 2,
      staleTime: 30000, // 30 seconds
      cacheTime: 300000, // 5 minutes
    },
    mutations: {
      retry: 1,
    },
  },
});

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Public Route Component (redirect to dashboard if already logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <div className="min-h-screen bg-gray-900">
          <Routes>
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
                <ProtectedRoute>
                  <AdminLayout />
                </ProtectedRoute>
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
            <Route path="/" element={<Navigate to="/login" replace />} />

            {/* 404 Route */}
            <Route
              path="*"
              element={
                <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center p-4">
                  <div className="text-center">
                    <h1 className="text-6xl font-bold text-white mb-4">404</h1>
                    <p className="text-gray-400 text-xl mb-8">Page not found</p>
                    <a
                      href="/dashboard"
                      className="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors inline-block"
                    >
                      Go to Dashboard
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
              background: "#1f2937",
              color: "#fff",
              border: "1px solid #374151",
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
