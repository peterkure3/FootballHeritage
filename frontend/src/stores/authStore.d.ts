import type { UseBoundStore, StoreApi } from "zustand";
export interface User {
  id: string | number;
  first_name?: string;
  last_name?: string;
  email?: string;
  username?: string;
  balance?: number;
  is_admin?: boolean;
  is_super_admin?: boolean;
}
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  logout: () => void;
  keepAlive: () => void;
}
declare const useAuthStore: UseBoundStore<StoreApi<AuthState>>;
export default useAuthStore;
