import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { apiFetch } from "../../lib/api";
import { clearAllCacheOnLogout } from "../../lib/dataLayer";

interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, password: string, apellido?: string, email?: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "finanzas_token";
const USER_KEY = "finanzas_user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    const savedUser = localStorage.getItem(USER_KEY);
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setIsLoading(false);
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const res = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const accessToken = res.access_token;
      const u = res.user || {};
      const newUser: User = {
        id: u.id || username,
        name: u.nombre ? `${u.nombre} ${(u.apellido || "").trim()}`.trim() : username,
        email: u.gmail || "",
      };
      setToken(accessToken);
      setUser(newUser);
      localStorage.setItem(TOKEN_KEY, accessToken);
      localStorage.setItem(USER_KEY, JSON.stringify(newUser));
      return true;
    } catch (err) {
      console.error("Login error:", err);
      return false;
    }
  };

  const register = async (
    username: string,
    password: string,
    apellido?: string,
    email?: string
  ): Promise<{ ok: boolean; error?: string }> => {
    try {
      await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          username: username.trim(),
          password,
          apellido: apellido?.trim() || undefined,
          email: email?.trim() || undefined,
        }),
      });
      return { ok: true };
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al crear la cuenta";
      return { ok: false, error: msg };
    }
  };

  const logout = () => {
    clearAllCacheOnLogout();
    setUser(null);
    setToken(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
