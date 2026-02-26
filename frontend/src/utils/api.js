// API utility for secure communication with the Rust betting backend
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8080/api/v1";

const STORAGE_KEY = "token";

// Token management
export const tokenManager = {
  setToken: (token) => {
    sessionStorage.setItem(STORAGE_KEY, token);
  },

  getToken: () => {
    return sessionStorage.getItem(STORAGE_KEY);
  },

  removeToken: () => {
    sessionStorage.removeItem(STORAGE_KEY);
  },
};

// Request helper with automatic auth headers
const makeRequest = async (endpoint, options = {}) => {
  const token = tokenManager.getToken();

  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
    mode: "cors",
    credentials: "omit",
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    // Handle 401 Unauthorized
    if (response.status === 401) {
      tokenManager.removeToken();
      window.location.href = "/login";
      throw new Error("Unauthorized - please login again");
    }

    // Parse response
    const contentType = response.headers.get("content-type");
    let data;

    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      throw new Error(
        data.message ||
          data.error ||
          `HTTP ${response.status}: ${response.statusText}`,
      );
    }

    return data;
  } catch (error) {
    // Network errors or other issues
    if (error.message.includes("Failed to fetch")) {
      throw new Error("Network error - please check your connection");
    }
    throw error;
  }
};

// API endpoints
export const api = {
  // Authentication
  register: async (email, password, firstName, lastName, dateOfBirth) => {
    const response = await makeRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        date_of_birth: dateOfBirth,
      }),
    });

    if (response.token) {
      tokenManager.setToken(response.token);
    }

    return response;
  },

  login: async (email, password) => {
    const response = await makeRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (response.token) {
      tokenManager.setToken(response.token);
    }

    return response;
  },

  logout: () => {
    tokenManager.removeToken();
  },

  // User data
  getUser: async () => {
    return await makeRequest("/user/profile", {
      method: "GET",
    });
  },

  // Wallet operations
  deposit: async (amount) => {
    return await makeRequest("/wallet/deposit", {
      method: "POST",
      body: JSON.stringify({ amount }),
    });
  },

  withdraw: async (amount) => {
    return await makeRequest("/wallet/withdraw", {
      method: "POST",
      body: JSON.stringify({ amount }),
    });
  },

  // Betting operations
  getOdds: async () => {
    return await makeRequest("/betting/events", {
      method: "GET",
    });
  },

  placeBet: async (eventId, amount, odds, type) => {
    return await makeRequest("/betting/bets", {
      method: "POST",
      body: JSON.stringify({
        event_id: eventId,
        amount,
        odds,
        type,
      }),
    });
  },

  getBetsHistory: async () => {
    return await makeRequest("/betting/bets", {
      method: "GET",
    });
  },

  // Sports data
  getSports: async () => {
    return await makeRequest("/sports", {
      method: "GET",
    });
  },

  getSportsCategories: async () => {
    return await makeRequest("/sports/categories", {
      method: "GET",
    });
  },

  getDeviggedOdds: async (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "") return;
      qs.set(k, String(v));
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return await makeRequest(`/intelligence/devigged-odds${suffix}`, {
      method: "GET",
    });
  },

  getEvBets: async (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "") return;
      qs.set(k, String(v));
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return await makeRequest(`/intelligence/ev-bets${suffix}`, {
      method: "GET",
    });
  },

  getArbitrage: async (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "") return;
      qs.set(k, String(v));
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return await makeRequest(`/intelligence/arbitrage${suffix}`, {
      method: "GET",
    });
  },

  refreshIntelligence: async () => {
    return await makeRequest("/intelligence/refresh", {
      method: "POST",
    });
  },
};

// Input sanitization utilities
export const sanitize = {
  email: (email) => {
    return email.trim().toLowerCase().replace(/[<>]/g, "");
  },

  amount: (amount) => {
    const parsed = parseFloat(amount);
    return isNaN(parsed) ? 0 : Math.max(0, Math.round(parsed * 100) / 100);
  },

  text: (text) => {
    return text.replace(/[<>'"]/g, "").trim();
  },
};

export default api;
