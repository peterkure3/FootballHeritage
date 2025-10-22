import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import useAuthStore from "./stores/authStore";

// Pages
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Odds from "./pages/Odds";
import BetHistory from "./pages/BetHistory";
import Chat from "./pages/Chat";

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
                  <Chat />
                </ProtectedRoute>
              }
            />

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
  );
}

export default App;
