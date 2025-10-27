import { useState, useEffect } from "react";
import useAuthStore from "../stores/authStore";

/**
 * Single Responsibility: Manage parlay data fetching (saved parlays & history)
 * Dependency Inversion: Depends on abstractions (hooks) not concrete implementations
 */
export const useParlayData = () => {
  const { token } = useAuthStore();
  const [savedParlays, setSavedParlays] = useState([]);
  const [history, setHistory] = useState([]);

  const fetchSavedParlays = async () => {
    try {
      const response = await fetch("http://localhost:8080/api/v1/parlay/saved", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setSavedParlays(data);
      }
    } catch (error) {
      console.error("Failed to fetch saved parlays:", error);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch("http://localhost:8080/api/v1/parlay/history?limit=10", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (error) {
      console.error("Failed to fetch history:", error);
    }
  };

  useEffect(() => {
    fetchSavedParlays();
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    savedParlays,
    history,
    refreshSavedParlays: fetchSavedParlays,
    refreshHistory: fetchHistory,
  };
};
