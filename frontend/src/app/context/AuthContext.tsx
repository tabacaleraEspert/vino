import { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from "react";
import { apiFetch, setApiToken, setOnUnauthorized } from "../../lib/api";
import { clearAllCacheOnLogout } from "../../lib/dataLayer";

interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  onboardingCompletado: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  loginWithGoogle: (credential: string) => Promise<{ ok: boolean; isNewUser: boolean; error?: string }>;
  loginWithApple: (idToken: string, givenName?: string, familyName?: string) => Promise<{ ok: boolean; isNewUser: boolean; error?: string }>;
  register: (username: string, password: string, apellido?: string, email?: string, whatsapp?: string) => Promise<{ ok: boolean; error?: string }>;
  markOnboardingDone: () => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "finanzas_token";
const USER_KEY = "finanzas_user";

// Restore token synchronously so it's available before any child renders
const savedTokenSync = localStorage.getItem(TOKEN_KEY);
const savedUserSync = (() => {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
})();
if (savedTokenSync) setApiToken(savedTokenSync);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(savedUserSync);
  const [token, setToken] = useState<string | null>(savedTokenSync);
  const [onboardingCompletado, setOnboardingCompletado] = useState(() => {
    return localStorage.getItem("finanzas_onboarding") === "true";
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setApiToken(token);
  }, [token]);

  const markOnboardingDone = useCallback(() => {
    setOnboardingCompletado(true);
    localStorage.setItem("finanzas_onboarding", "true");
  }, []);

  const logout = useCallback(() => {
    clearAllCacheOnLogout();
    setUser(null);
    setToken(null);
    setApiToken(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  useEffect(() => {
    setOnUnauthorized(() => logout());
    return () => setOnUnauthorized(null);
  }, [logout]);

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
      const obCompleted = res.onboarding_completado ?? true; // legacy users = completed
      setApiToken(accessToken);
      setToken(accessToken);
      setUser(newUser);
      setOnboardingCompletado(obCompleted);
      localStorage.setItem(TOKEN_KEY, accessToken);
      localStorage.setItem(USER_KEY, JSON.stringify(newUser));
      localStorage.setItem("finanzas_onboarding", String(obCompleted));
      return true;
    } catch (err) {
      console.error("Login error:", err);
      return false;
    }
  };

  const loginWithGoogle = async (credential: string): Promise<{ ok: boolean; isNewUser: boolean; error?: string }> => {
    try {
      const res = await apiFetch<{
        access_token: string;
        is_new_user: boolean;
        user: { id: string; nombre: string; apellido: string; gmail: string };
      }>("/auth/google", {
        method: "POST",
        body: JSON.stringify({ credential }),
      });
      const u = res.user;
      const newUser: User = {
        id: u.id,
        name: `${u.nombre} ${(u.apellido || "").trim()}`.trim(),
        email: u.gmail || "",
      };
      const obCompleted = (res as any).onboarding_completado ?? false;
      setApiToken(res.access_token);
      setToken(res.access_token);
      setUser(newUser);
      setOnboardingCompletado(obCompleted);
      localStorage.setItem(TOKEN_KEY, res.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(newUser));
      localStorage.setItem("finanzas_onboarding", String(obCompleted));
      return { ok: true, isNewUser: res.is_new_user };
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error con Google Sign-In";
      return { ok: false, isNewUser: false, error: msg };
    }
  };

  const loginWithApple = async (
    idToken: string,
    givenName?: string,
    familyName?: string,
  ): Promise<{ ok: boolean; isNewUser: boolean; error?: string }> => {
    try {
      const res = await apiFetch<{
        access_token: string;
        is_new_user: boolean;
        user: { id: string; nombre: string; apellido: string; gmail: string };
      }>("/auth/apple", {
        method: "POST",
        body: JSON.stringify({ id_token: idToken, given_name: givenName, family_name: familyName }),
      });
      const u = res.user;
      const newUser: User = {
        id: u.id,
        name: `${u.nombre} ${(u.apellido || "").trim()}`.trim(),
        email: u.gmail || "",
      };
      const obCompleted = (res as any).onboarding_completado ?? false;
      setApiToken(res.access_token);
      setToken(res.access_token);
      setUser(newUser);
      setOnboardingCompletado(obCompleted);
      localStorage.setItem(TOKEN_KEY, res.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(newUser));
      localStorage.setItem("finanzas_onboarding", String(obCompleted));
      return { ok: true, isNewUser: res.is_new_user };
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error con Apple Sign-In";
      return { ok: false, isNewUser: false, error: msg };
    }
  };

  const register = async (
    username: string,
    password: string,
    apellido?: string,
    email?: string,
    whatsapp?: string,
  ): Promise<{ ok: boolean; error?: string }> => {
    try {
      await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          username: username.trim(),
          password,
          apellido: apellido?.trim() || undefined,
          email: email?.trim() || undefined,
          whatsapp: whatsapp?.trim() || undefined,
        }),
      });
      // Auto-login after registration
      const loggedIn = await login(username.trim(), password);
      if (!loggedIn) {
        return { ok: true }; // Registered but auto-login failed — still success
      }
      return { ok: true };
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al crear la cuenta";
      return { ok: false, error: msg };
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, onboardingCompletado, login, loginWithGoogle, loginWithApple, register, markOnboardingDone, logout, isLoading }}>
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
