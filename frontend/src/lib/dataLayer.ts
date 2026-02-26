/**
 * Capa de datos: fetch, cache y coalescing.
 * Reemplaza bootstrap gigante por endpoints separados.
 */
import { api } from "./api";
import type { CategoriaRaw, SubcategoriaRaw, ReglaRaw } from "./api";
import type { MovimientosPaginatedResponse } from "./api";

const CACHE_KEY_CATALOG = (userId: string) => `vino_catalog_${userId}`;
const CATALOG_TTL_MS = 24 * 60 * 60 * 1000; // 24h

const inFlight = new Map<string, Promise<unknown>>();

/** Extrae sub (user id) del JWT para usar como fallback cuando user?.id no está disponible */
function getUserIdFromToken(token: string): string | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
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
  const coalesceKey = `catalog_${effectiveUserId}`;

  if (!options?.skipCache) {
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const { data, lastFetchTs } = JSON.parse(cached) as {
          data: { categorias?: unknown[]; subcategorias?: unknown[] };
          lastFetchTs: number;
        };
        let subs = Array.isArray(data?.subcategorias) ? data.subcategorias : [];
        if (subs.length === 0 && data?.subcategorias && typeof data.subcategorias === "object") {
          subs = Object.values(data.subcategorias) as SubcategoriaRaw[];
        }
        const cats = Array.isArray(data?.categorias) ? data.categorias : [];
        const cacheValid = Date.now() - lastFetchTs < CATALOG_TTL_MS;
        // Si cache tiene categorías pero subcategorías vacías, puede ser stale (usuario añadió en DB)
        const subsMaybeStale = cats.length > 0 && subs.length === 0;
        if (cacheValid && !subsMaybeStale) {
          return { categorias: cats, subcategorias: subs };
        }
      }
    } catch {
      // Ignorar errores de parse
    }
  }

  return coalesce(coalesceKey, async () => {
    const [categoriasRaw, subcategoriasRaw] = await Promise.all([
      api.categories.list(token),
      api.subcategorias.list({}, token),
    ]);
    const categorias = categoriasRaw ?? [];
    let subcategorias: SubcategoriaRaw[] = [];
    if (Array.isArray(subcategoriasRaw)) {
      subcategorias = subcategoriasRaw;
    } else if (subcategoriasRaw && typeof subcategoriasRaw === "object") {
      const obj = subcategoriasRaw as Record<string, unknown>;
      if (Array.isArray(obj.data)) subcategorias = obj.data as SubcategoriaRaw[];
      else if (Array.isArray(obj.subcategorias)) subcategorias = obj.subcategorias as SubcategoriaRaw[];
      else subcategorias = Object.values(obj).filter((v) => v && typeof v === "object" && !Array.isArray(v)) as SubcategoriaRaw[];
    }
    console.log("[fetchCatalog] /categorias + /subcategorias OK:", {
      categoriasCount: categorias.length,
      subcategoriasCount: subcategorias.length,
      categorias,
      subcategorias,
    });
    const data: CatalogData = {
      categorias,
      subcategorias,
    };
    try {
      localStorage.setItem(
        cacheKey,
        JSON.stringify({ data, lastFetchTs: Date.now() })
      );
    } catch {
      // localStorage lleno o no disponible
    }
    return data;
  }, options?.skipCache);
}

export function invalidateCatalog(userId: string, token?: string): void {
  try {
    const effective = userId || (token ? getUserIdFromToken(token) : null) || "anon";
    localStorage.removeItem(CACHE_KEY_CATALOG(effective));
  } catch {
    // Ignorar
  }
}

/** Caches del Dashboard (summary, breakdown) - se limpian en logout */
export const dashboardSummaryCache: Record<string, { gasto_mes: number; presupuesto_mes: number }> = {};
export const dashboardBreakdownCache: Record<
  string,
  {
    gastos_por_categoria: Array<{ categoria: string; total: number; pct: number }>;
    transacciones_recientes: Array<{
      id: string;
      fecha: string;
      titulo: string;
      descripcion: string;
      monto: number;
      categoria: string;
    }>;
    mayor_gasto: number;
    transacciones_count: number;
  }
> = {};

/**
 * Limpia TODO el cache al hacer logout.
 * localStorage (vino_*), inFlight, Dashboard caches.
 */
export function clearAllCacheOnLogout(): void {
  try {
    // localStorage: vino_catalog_*, etc.
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith("vino_")) keysToRemove.push(key);
    }
    keysToRemove.forEach((k) => localStorage.removeItem(k));

    // inFlight: catalog_*, data_period_*
    for (const key of inFlight.keys()) {
      if (key.startsWith("catalog_") || key.startsWith("data_period_")) {
        inFlight.delete(key);
      }
    }

    // Dashboard caches
    Object.keys(dashboardSummaryCache).forEach((k) => delete dashboardSummaryCache[k]);
    Object.keys(dashboardBreakdownCache).forEach((k) => delete dashboardBreakdownCache[k]);
  } catch {
    // Ignorar errores
  }
}

/** Datos crudos para DataContext: movimientos, presupuestos, reglas, comercios */
export interface DataForPeriodRaw {
  movimientos: MovimientosPaginatedResponse;
  presupuestos: unknown[];
  reglas: ReglaRaw[];
  comercios: { id: string; name: string }[];
}

const DATA_COALESCE_PREFIX = "data_period_";

/**
 * Fetch coalescido de movimientos, presupuestos, reglas y comercios.
 * Evita duplicados por StrictMode, dependencias o re-renders.
 */
export async function fetchDataForPeriod(
  token: string,
  period: string,
  options?: { forceRefresh?: boolean }
): Promise<DataForPeriodRaw> {
  const key = `${DATA_COALESCE_PREFIX}${token.slice(-24)}_${period}`;
  return coalesce(
    key,
    async () => {
      const [movsRes, presupuestosRaw, reglasRaw, mers] = await Promise.all([
        api.movimientos
          .list({ limit: "1000", period }, token)
          .catch((): MovimientosPaginatedResponse => ({ items: [], page: 1, limit: 100, total: 0 })),
        api.budgets.list({ mes_anio: period }, token).catch(() => []),
        api.merchantRules.list({}, token).catch(() => [] as ReglaRaw[]),
        api.merchants.list(token).catch(() => []),
      ]);
      return {
        movimientos: movsRes as MovimientosPaginatedResponse,
        presupuestos: presupuestosRaw ?? [],
        reglas: (reglasRaw ?? []) as ReglaRaw[],
        comercios: (mers ?? []) as { id: string; name: string }[],
      };
    },
    options?.forceRefresh
  ) as Promise<DataForPeriodRaw>;
}
