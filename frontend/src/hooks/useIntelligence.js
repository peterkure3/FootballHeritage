import { useQuery } from "@tanstack/react-query";
import { api } from "../utils/api";

export const useDeviggedOdds = (params) => {
  return useQuery({
    queryKey: ["intelligence", "devigged-odds", params],
    queryFn: async () => {
      return await api.getDeviggedOdds(params);
    },
    staleTime: 15000,
    refetchInterval: 30000,
    retry: 2,
  });
};

export const useEvBets = (params) => {
  return useQuery({
    queryKey: ["intelligence", "ev-bets", params],
    queryFn: async () => {
      return await api.getEvBets(params);
    },
    staleTime: 15000,
    refetchInterval: 30000,
    retry: 2,
  });
};

export const useArbitrage = (params) => {
  return useQuery({
    queryKey: ["intelligence", "arbitrage", params],
    queryFn: async () => {
      return await api.getArbitrage(params);
    },
    staleTime: 15000,
    refetchInterval: 30000,
    retry: 2,
  });
};

export default {
  useDeviggedOdds,
  useEvBets,
  useArbitrage,
};
