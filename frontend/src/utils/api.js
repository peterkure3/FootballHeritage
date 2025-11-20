// API utility for secure communication with the Rust betting backend
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8080/api/v1";

// Encryption key for localStorage (in production, use a more robust solution)
const STORAGE_KEY = "token";
const CSRF_TOKEN_KEY = "betting_csrf_token";

// Simple XOR encryption for localStorage (basic obfuscation)
const encryptToken = (token) => {
  const key = "BettingSecureKey2024";
  let encrypted = "";
  for (let i = 0; i < token.length; i++) {
    encrypted += String.fromCharCode(
      token.charCodeAt(i) ^ key.charCodeAt(i % key.length),
    );
  }
  return btoa(encrypted);
};

const decryptToken = (encrypted) => {
  try {
    const key = "BettingSecureKey2024";
    const decoded = atob(encrypted);
    let decrypted = "";
    for (let i = 0; i < decoded.length; i++) {
      decrypted += String.fromCharCode(
        decoded.charCodeAt(i) ^ key.charCodeAt(i % key.length),
      );
    }
    return decrypted;
  } catch {
    return null;
  }
};

// Token management
export const tokenManager = {
  setToken: (token) => {
    const encrypted = encryptToken(token);
    localStorage.setItem(STORAGE_KEY, encrypted);
  },

  getToken: () => {
    const encrypted = localStorage.getItem(STORAGE_KEY);
    if (!encrypted) return null;
    return decryptToken(encrypted);
  },

  removeToken: () => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(CSRF_TOKEN_KEY);
  },

  setCsrfToken: (token) => {
    localStorage.setItem(CSRF_TOKEN_KEY, token);
  },

  getCsrfToken: () => {
    return localStorage.getItem(CSRF_TOKEN_KEY);
  },
};

// Generate CSRF token
const generateCsrfToken = () => {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(16).padStart(2, "0")).join(
    "",
  );
};

// Initialize CSRF token
if (!tokenManager.getCsrfToken()) {
  tokenManager.setCsrfToken(generateCsrfToken());
}

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
