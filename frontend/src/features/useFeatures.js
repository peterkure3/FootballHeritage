import { useQuery } from "@tanstack/react-query";
import useAuthStore from "../stores/authStore";
import { makeRequest } from "../utils/api";

export function useFeatures() {
  const user = useAuthStore((state) => state.user);
  const authenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ["feature-access", authenticated, user?.id],
    queryFn: () => makeRequest("/me/features"),
    staleTime: 0,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
    retry: false,
  });
}
