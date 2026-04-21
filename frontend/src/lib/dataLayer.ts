/**
 * Capa de datos: fetch con coalescing y cache inteligente.
 * - Coalescing: dedup requests idénticos en vuelo
 * - Cache localStorage para catálogo (24h TTL)
 * - Sin console.log en producción
 */
import { api } from "./api";
import type { CategoriaRaw, SubcategoriaRaw, ReglaRaw } from "./api";
import type { MovimientosPaginatedResponse } from "./api";

const CACHE_KEY_CATALOG = (userId: string) => `vino_catalog_${userId}`;
const CATALOG_TTL_MS = 24 * 60 * 60 * 1000;

const inFlight = new Map<string, Promise<unknown>>();

function getUserIdFromToken(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.sub != null ? String(payload.sub) : null;
  } catch {
    return null;
  }
}

function coalesce<T>(key: string, fn: () => Promise<T>, forceRefresh = false): Promise<T> {
  if (forceRefresh) inFlight.delete(key);
  const existing = inFlight.get(key);
  if (existing) return existing as Promise<T>;
  const p = fn().finally(() => inFlight.delete(key));
  inFlight.set(key, p);
  return p;
}

// --- Catalog ---

export interface CatalogData {
  categorias: CategoriaRaw[];
  subcategorias: SubcategoriaRaw[];
}

export async function fetchCatalog(
  token: string,
  userId: string,
  options?: { skipCache?: boolean }
): Promise<CatalogData> {
  const effectiveUserId = userId || getUserIdFromToken(token) || "anon";
  const cacheKey = CACHE_KEY_CATALOG(effectiveUserId);

  if (!options?.skipCache) {
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const { data, lastFetchTs } = JSON.parse(cached);
        const cats = Array.isArray(data?.categorias) ? data.categorias : [];
        let subs = Array.isArray(data?.subcategorias) ? data.subcategorias : [];
        if (subs.length === 0 && data?.subcategorias && typeof data.subcategorias === "object") {
          subs = Object.values(data.subcategorias) as SubcategoriaRaw[];
        }
        if (Date.now() - lastFetchTs < CATALOG_TTL_MS && cats.length > 0 && subs.length > 0) {
          return { categorias: cats, subcategorias: subs };
        }
      }
    } catch { /* ignore */ }
  }

  return coalesce(`catalog_${effectiveUserId}`, async () => {
    const [categorias, subcategorias] = await Promise.all([
      api.categories.list(),
      api.subcategorias.list({}),
    ]);
    const data: CatalogData = {
      categorias: categorias ?? [],
      subcategorias: Array.isArray(subcategorias) ? subcategorias : [],
    };
    try {
      localStorage.setItem(cacheKey, JSON.stringify({ data, lastFetchTs: Date.now() }));
    } catch { /* localStorage full */ }
    return data;
  }, options?.skipCache);
}

export function invalidateCatalog(userId: string, token?: string): void {
  try {
    const effective = userId || (token ? getUserIdFromToken(token) : null) || "anon";
    localStorage.removeItem(CACHE_KEY_CATALOG(effective));
  } catch { /* ignore */ }
}

// --- Bootstrap (1 request en vez de 5) ---

export interface BootstrapData {
  categorias: CategoriaRaw[];
  subcategorias: SubcategoriaRaw[];
  reglas: ReglaRaw[];
  presupuestos: unknown[];
  comercios: { id: string; name: string }[];
}

export async function fetchBootstrap(token: string): Promise<BootstrapData> {
  return coalesce("bootstrap", async () => {
    const res = await api.bootstrap();
    return {
      categorias: res.categorias ?? [],
      subcategorias: res.subcategorias ?? [],
      reglas: res.reglas ?? [],
      presupuestos: res.presupuestos ?? [],
      comercios: res.comercios ?? [],
    };
  });
}

// --- Data for period (movimientos only - budgets come from bootstrap) ---

export async function fetchMovimientos(
  token: string,
  period: string,
  options?: { forceRefresh?: boolean }
): Promise<MovimientosPaginatedResponse> {
  const key = `movimientos_${period}`;
  return coalesce(
    key,
    () => api.movimientos
      .list({ limit: "1000", period })
      .catch((): MovimientosPaginatedResponse => ({ items: [], page: 1, limit: 100, total: 0 })),
    options?.forceRefresh,
  );
}

// --- Cleanup ---

export function clearAllCacheOnLogout(): void {
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith("vino_")) keysToRemove.push(key);
    }
    keysToRemove.forEach((k) => localStorage.removeItem(k));
    inFlight.clear();
  } catch { /* ignore */ }
}
