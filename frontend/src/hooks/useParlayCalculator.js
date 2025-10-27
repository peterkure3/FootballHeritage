import { useState } from "react";
import { toast } from "react-hot-toast";
import useAuthStore from "../stores/authStore";

/**
 * Single Responsibility: Handle parlay calculation business logic
 * Open/Closed: Can be extended without modifying existing code
 */
export const useParlayCalculator = () => {
  const { token } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const calculateParlay = async (bets, stake) => {
    // Validate inputs
    const validBets = bets.filter(bet => bet.team && bet.odds);
    if (validBets.length < 2) {
      toast.error("Please add at least 2 valid bets");
      return null;
    }

    if (stake <= 0) {
      toast.error("Stake must be greater than 0");
      return null;
    }

    setLoading(true);
    try {
      const payload = {
        bets: validBets.map(bet => ({
          event_id: bet.event_id || "00000000-0000-0000-0000-000000000000",
          team: bet.team,
          odds: parseFloat(bet.odds),
          win_prob: bet.win_prob ? parseFloat(bet.win_prob) : null,
          bet_type: bet.bet_type,
          selection: bet.selection,
        })),
        stake: parseFloat(stake),
      };

      const response = await fetch("http://localhost:8080/api/v1/parlay/calculate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || "Calculation failed");
      }

      const data = await response.json();
      setResult(data);
      toast.success("Parlay calculated successfully!");
      return data;
    } catch (error) {
      console.error("Calculation error:", error);
      toast.error(error.message || "Failed to calculate parlay");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const saveParlay = async (bets, stake, name) => {
    if (!result) {
      toast.error("Calculate parlay first");
      return false;
    }

    try {
      const payload = {
        name,
        bets: bets.map(bet => ({
          event_id: bet.event_id || "00000000-0000-0000-0000-000000000000",
          team: bet.team,
          odds: parseFloat(bet.odds),
          win_prob: bet.win_prob ? parseFloat(bet.win_prob) : null,
          bet_type: bet.bet_type,
          selection: bet.selection,
        })),
        stake: parseFloat(stake),
      };

      const response = await fetch("http://localhost:8080/api/v1/parlay/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to save");

      toast.success("Parlay saved successfully!");
      return true;
    } catch {
      toast.error("Failed to save parlay");
      return false;
    }
  };

  return {
    loading,
    result,
    calculateParlay,
    saveParlay,
  };
};
