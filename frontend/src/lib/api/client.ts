/**
 * Cliente API con token automático e interceptor 401.
 */
const API_BASE =
  import.meta.env.VITE_API_URL ||
  "https://vino-backend-bkbge8cwfffsdrhc.brazilsouth-01.azurewebsites.net/api/v1";

let _token: string | null = null;
let _onUnauthorized: (() => void) | null = null;

export function setApiToken(token: string | null): void {
  _token = token;
}

export function setOnUnauthorized(cb: (() => void) | null): void {
  _onUnauthorized = cb;
}

export function getApiToken(): string | null {
  return _token;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token: explicitToken, ...init } = options;
  const token = explicitToken ?? _token;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }
  const method = (init.method || "GET").toUpperCase();
  const cacheOpt = method === "GET" ? { cache: "no-store" as RequestCache } : {};
  const res = await fetch(`${API_BASE}${path}`, { ...init, ...cacheOpt, headers });

  if (res.status === 401 && _onUnauthorized) {
    _onUnauthorized();
    const err = await res.json().catch(() => ({ detail: "Sesión expirada" }));
    throw new Error(err.detail || "Sesión expirada");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Error en la petición");
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return {} as T;
  }
  return res.json();
}
