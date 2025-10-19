import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../utils/api";
import useAuthStore from "../stores/authStore";
import toast from "react-hot-toast";

// Hook for user data
export const useUser = () => {
  const { isAuthenticated, setUser, logout } = useAuthStore();

  return useQuery({
    queryKey: ["user"],
    queryFn: async () => {
      const userData = await api.getUser();
      setUser(userData);
      return userData;
    },
    enabled: isAuthenticated,
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
    retry: 1,
    onError: (error) => {
      if (error.message.includes("Unauthorized")) {
        logout();
      }
    },
  });
};

// Hook for registration
export const useRegister = () => {
  const { login } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      email,
      password,
      firstName,
      lastName,
      dateOfBirth,
    }) => {
      return await api.register(
        email,
        password,
        firstName,
        lastName,
        dateOfBirth,
      );
    },
    onSuccess: (data) => {
      if (data.token) {
        login(data.token, data.user);
        queryClient.invalidateQueries(["user"]);
        toast.success("Registration successful! Welcome aboard!");
      }
    },
    onError: (error) => {
      toast.error(error.message || "Registration failed");
    },
  });
};

// Hook for login
export const useLogin = () => {
  const { login } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ email, password }) => {
      return await api.login(email, password);
    },
    onSuccess: (data) => {
      if (data.token) {
        login(data.token, data.user);
        queryClient.invalidateQueries(["user"]);
        toast.success("Login successful!");
      }
    },
    onError: (error) => {
      toast.error(error.message || "Login failed");
    },
  });
};

// Hook for logout
export const useLogout = () => {
  const { logout } = useAuthStore();
  const queryClient = useQueryClient();

  return () => {
    api.logout();
    logout();
    queryClient.clear();
    toast.success("Logged out successfully");
  };
};

export default {
  useUser,
  useRegister,
  useLogin,
  useLogout,
};
