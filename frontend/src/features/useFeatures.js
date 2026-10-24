import { useQuery } from "@tanstack/react-query";
import useAuthStore from "../stores/authStore";
import { makeRequest } from "../utils/api";

export function useFeatures({ poll = false } = {}) {
  const user = useAuthStore((state) => state.user);
  const authenticated = useAuthStore((state) => state.isAuthenticated);
  return useQuery({
    queryKey: ["feature-access", authenticated, user?.id],
    queryFn: () => makeRequest("/me/features"),
    staleTime: 15000,
    // The application boundary owns polling; navigation consumers share its cache.
    refetchInterval: poll ? 15000 : false,
    refetchOnWindowFocus: true,
    retry: false,
  });
}
