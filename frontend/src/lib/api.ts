import { apiFetch, getApiToken } from "./api/client";
import { resolveIcon } from "./categoryIcons";
export { apiFetch, setApiToken, setOnUnauthorized, getApiToken } from "./api/client";

// Tipos
export interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
  bucket?: string;
  tipo?: "Gasto" | "Ingreso";
  subcategories?: Subcategory[];
}

export interface Subcategory {
  id: string;
  name: string;
  categoryId: string;
}

export interface Budget {
  id: string;
  categoryId: string;
  subcategoryId?: string | null;
  mes_anio?: string;
  amount: number;
  period: "monthly" | "weekly" | "yearly";
  spent: number;
}

export interface Merchant {
  id: string;
  name: string;
  defaultCategoryId?: string;
  defaultSubcategoryId?: string;
}

export interface MerchantRule {
  id: string;
  merchantId: string;
  categoryId: string;
  subcategoryId?: string;
}

export interface Transaction {
  id: string;
  amount: number;
  tipo: "Gasto" | "Ingreso";
  currency: string;
  description: string;
  descripcion?: string;
  date: string;
  categoryId: string;
  subcategoryId?: string;
  merchantId: string;
  cuotaActual?: number | null;
  cuotaTotal?: number | null;
  montoTotalCompra?: number | null;
}

// Formatos de respuesta del backend (Sheets)
export interface CategoriaRaw {
  id: string;
  nombre: string;
  icon?: string;
  color?: string;
  tipo?: string;
}

export interface SubcategoriaRaw {
  id: string;
  categoria_id: string;
  nombre: string;
}

export interface ReglaRaw {
  id: string;
  comercio: string;
  categoria_id: string;
  categoria_nombre: string;
  subcategoria_id: string;
  subcategoria_nombre: string;
  timestamp?: string;
}

export interface HomeSummaryResponse {
  period: string;
  user_id: string | null;
  moneda: string;
  gasto_mes: number;
  ingreso_mes: number;
  balance_mes: number;
  presupuesto_mes: number;
}

export interface HomeBreakdownResponse {
  period: string;
  user_id: string | null;
  currency: string;
  gastos_por_categoria: Array<{ categoria: string; total: number; pct: number }>;
  transacciones_recientes: Array<{
    id: string;
    fecha: string;
    timestamp: string;
    titulo: string;
    descripcion: string;
    comercio: string;
    categoria: string;
    subcategoria: string;
    monto: number;
  }>;
  mayor_gasto: number;
  transacciones_count: number;
}

export interface MovimientoItem {
  id: string;
  fecha: string;
  timestamp: string;
  tipo: "Gasto" | "Ingreso";
  moneda: string;
  monto: number;
  comercio: string;
  comercioId?: string;
  descripcion: string;
  categoria: string;
  subcategoria: string;
  idCategoria?: string;
  idSubcategoria?: string;
  medio_pago: string;
  cuotaActual?: number | null;
  cuotaTotal?: number | null;
  montoTotalCompra?: number | null;
  CuotaActual?: number | null;
  CuotaTotal?: number | null;
  MontoTotalCompra?: number | null;
}

export interface MovimientosPaginatedResponse {
  items: MovimientoItem[];
  page: number;
  limit: number;
  total: number;
}

export interface PresupuestoRaw {
  id: string;
  mes_anio: string;
  categoria_id: string;
  categoria_nombre: string;
  subcategoria_id: string;
  subcategoria_nombre: string;
  monto: string;
}

// API calls
export const api = {
  health: () => apiFetch<{ ok: boolean; version: string }>("/health"),

  bootstrap: (token?: string) =>
    apiFetch<{
      categorias: CategoriaRaw[];
      subcategorias: SubcategoriaRaw[];
      reglas: ReglaRaw[];
      presupuestos: PresupuestoRaw[];
      comercios: Merchant[];
    }>("/bootstrap"),

  categories: {
    list: (token?: string) =>
      apiFetch<CategoriaRaw[]>("/categorias"),
    create: (data: Omit<Category, "id">) =>
      apiFetch<Category>("/categorias", {
        method: "POST",
        body: JSON.stringify({
          name: data.name,
          icon: data.icon || "📁",
          color: data.color || "#6b7280",
          bucket: data.bucket || "necesidades",
          tipo: data.tipo || "Gasto",
          subcategories: (data.subcategories ?? []).map((s) => ({ name: s.name })),
        }),
      }),
    update: (id: string, data: Partial<Category>) =>
      apiFetch<Category>(`/categorias/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...(data.name != null && { name: data.name }),
          ...(data.icon != null && { icon: data.icon }),
          ...(data.color != null && { color: data.color }),
          ...(data.bucket != null && { bucket: data.bucket }),
        }),
      }),
    delete: (id: string) =>
      apiFetch(`/categorias/${id}`, { method: "DELETE" }),
    addSubcategory: (categoryId: string, name: string) =>
      apiFetch<Category>(`/categorias/${categoryId}/subcategorias`, {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
  },

  subcategorias: {
    list: (params?: { categoria_id?: string }) => {
      const q = params?.categoria_id
        ? "?" + new URLSearchParams({ categoria_id: params.categoria_id }).toString()
        : "";
      return apiFetch<SubcategoriaRaw[]>(`/subcategorias${q}`);
    },
    update: (id: string, name: string) =>
      apiFetch<{ id: string; name: string; categoryId: string }>(`/subcategorias/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      }),
    delete: (id: string) =>
      apiFetch(`/subcategorias/${id}`, { method: "DELETE" }),
  },

  budgets: {
    list: (params?: { mes_anio?: string; categoria_id?: string; subcategoria_id?: string }) => {
      const p: Record<string, string> = {};
      if (params?.mes_anio) p["mesAño"] = params.mes_anio;
      if (params?.categoria_id) p["categoria_id"] = params.categoria_id;
      if (params?.subcategoria_id) p["subcategoria_id"] = params.subcategoria_id;
      const q = Object.keys(p).length ? "?" + new URLSearchParams(p).toString() : "";
      return apiFetch<PresupuestoRaw[]>(`/presupuestos${q}`);
    },
    create: (data: Omit<Budget, "id">) =>
      apiFetch<Budget>("/presupuestos", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Budget>) =>
      apiFetch<Budget>(`/presupuestos/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch(`/presupuestos/${id}`, { method: "DELETE" }),
    autoAssign: (total: number, mes_anio?: string) =>
      apiFetch<{
        total: number;
        regla: string;
        mes_anio: string;
        presupuestos_creados: number;
        distribucion: { categoria: string; bucket: string; pct_bucket: string; monto: number }[];
        presupuestos: PresupuestoRaw[];
      }>("/presupuestos/auto-assign", {
        method: "POST",
        body: JSON.stringify({ total, mes_anio }),
      }),
  },

  billeteras: {
    list: () => apiFetch<any[]>("/billeteras"),
    create: (data: { nombre: string; moneda: string; icono?: string; color?: string; saldo_inicial?: number }) =>
      apiFetch<any>("/billeteras", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: any) =>
      apiFetch<any>(`/billeteras/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: number) => apiFetch(`/billeteras/${id}`, { method: "DELETE" }),
  },

  deudas: {
    list: (pagado?: boolean) => {
      const q = pagado !== undefined ? `?pagado=${pagado}` : "";
      return apiFetch<any[]>(`/deudas${q}`);
    },
    summary: () => apiFetch<{ total_pendiente: number; personas: any[] }>("/deudas/summary"),
    pagar: (id: number) => apiFetch<any>(`/deudas/${id}/pagar`, { method: "PATCH" }),
    delete: (id: number) => apiFetch(`/deudas/${id}`, { method: "DELETE" }),
  },

  statement: {
    extract: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const token = getApiToken();
      const API_BASE =
        import.meta.env.VITE_API_URL ||
        "https://vino-backend-bkbge8cwfffsdrhc.brazilsouth-01.azurewebsites.net/api/v1";
      const res = await fetch(`${API_BASE}/statement/extract`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error desconocido" }));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      return res.json();
    },
    confirm: (data: { transactions: any[]; origen_label?: string }) =>
      apiFetch<{ status: string; total: number; creados: number; duplicados: number; errores: number }>(
        "/statement/confirm",
        { method: "POST", body: JSON.stringify(data) }
      ),
  },

  merchants: {
    smart: {
      identify: (merchant_name: string) =>
        apiFetch<any>("/merchants/smart/identify", {
          method: "POST",
          body: JSON.stringify({ merchant_name }),
        }),
      identifyBatch: (merchant_names: string[]) =>
        apiFetch<{ results: any[] }>("/merchants/smart/identify/batch", {
          method: "POST",
          body: JSON.stringify({ merchant_names }),
        }),
      uncategorized: (period?: string) => {
        const q = period ? `?period=${period}` : "";
        return apiFetch<{ total_uncategorized: number; unique_merchants: number; merchants: any[] }>(
          `/merchants/smart/uncategorized${q}`
        );
      },
      categorize: (data: { comercio: string; categoria_id: number; subcategoria_id: number | null; create_rule: boolean }) =>
        apiFetch<any>("/merchants/smart/categorize", {
          method: "POST",
          body: JSON.stringify(data),
        }),
      bulkCategorize: (items: any[]) =>
        apiFetch<any>("/merchants/smart/categorize/bulk", {
          method: "POST",
          body: JSON.stringify({ items }),
        }),
    },
    list: () => apiFetch<Merchant[]>("/comercios"),
    create: (data: Omit<Merchant, "id">) =>
      apiFetch<Merchant>("/comercios", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Merchant>) =>
      apiFetch<Merchant>(`/comercios/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch(`/comercios/${id}`, { method: "DELETE" }),
  },

  merchantRules: {
    list: (params?: { comercio?: string; categoria_id?: string; subcategoria_id?: string }) => {
      const q = params?.comercio || params?.categoria_id || params?.subcategoria_id
        ? "?" + new URLSearchParams(
            Object.fromEntries(
              Object.entries(params || {}).filter(([, v]) => v != null && v !== "")
            )
          ).toString()
        : "";
      return apiFetch<ReglaRaw[]>(`/reglas${q}`);
    },
    create: (data: Omit<MerchantRule, "id">) =>
      apiFetch<MerchantRule>("/reglas", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<MerchantRule>) =>
      apiFetch<MerchantRule>(`/reglas/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch(`/reglas/${id}`, { method: "DELETE" }),
  },

  views: {
    homeSummary: (
      params: { period: string; moneda?: string },
      token?: string
    ) => {
      const q = new URLSearchParams({ period: params.period });
      if (params.moneda) q.set("moneda", params.moneda);
      return apiFetch<HomeSummaryResponse>(`/views/home/summary?${q}`);
    },
    homeBreakdown: (
      params: {
        period: string;
        currency?: string;
        top_categories?: number;
        recent_limit?: number;
        include_zeros?: boolean;
      },
      token?: string
    ) => {
      const q = new URLSearchParams({ period: params.period });
      if (params.currency) q.set("currency", params.currency);
      if (params.top_categories != null) q.set("top_categories", String(params.top_categories));
      if (params.recent_limit != null) q.set("recent_limit", String(params.recent_limit));
      if (params.include_zeros != null) q.set("include_zeros", String(params.include_zeros));
      return apiFetch<HomeBreakdownResponse>(`/views/home/breakdown?${q}`);
    },
  },

  movimientos: {
    list: (
      params?: Record<string, string | number | boolean | undefined>,
      token?: string
    ) => {
      const filtered = params
        ? (Object.fromEntries(
            Object.entries(params).filter(([, v]) => v != null && v !== "")
          ) as Record<string, string>)
        : {};
      const q = Object.keys(filtered).length
        ? "?" + new URLSearchParams(filtered as Record<string, string>).toString()
        : "";
      return apiFetch<MovimientosPaginatedResponse>(`/movimientos${q}`);
    },
    invalidateCache: (token?: string) =>
      apiFetch<{ ok: boolean }>("/movimientos/invalidate-cache", {
        method: "POST",
      }),
    create: (data: Record<string, unknown>) =>
      apiFetch<MovimientoRaw>("/movimientos", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Record<string, unknown>) =>
      apiFetch<MovimientoRaw>(`/movimientos/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch(`/movimientos/${id}`, { method: "DELETE" }),
  },
};

// Formato raw del backend (Sheets)
export interface MovimientoRaw {
  Id?: string;
  Fecha?: string;
  Monto?: string | number;
  Comercio?: string;
  Nombre_Categoria?: string;
  Nombre_SubCategoria?: string;
  "Tipo de Movimiento"?: string;
  Moneda?: string;
  [key: string]: unknown;
}

/** Convierte fecha DD/MM/YYYY a YYYY-MM-DD */
function parseFecha(s: string | undefined): string {
  if (!s) return "";
  const parts = String(s).trim().split("/");
  if (parts.length === 3) {
    const [d, m, y] = parts;
    return `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }
  return String(s);
}

/** Parsea YYYY-MM-DD como fecha local (evita shift UTC→local en zonas negativas) */
export function parseDateLocal(dateStr: string): Date {
  if (!dateStr || !dateStr.includes("-")) return new Date(NaN);
  const parts = dateStr.trim().split("-");
  if (parts.length !== 3) return new Date(NaN);
  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10) - 1;
  const d = parseInt(parts[2], 10);
  if (isNaN(y) || isNaN(m) || isNaN(d)) return new Date(NaN);
  return new Date(y, m, d);
}

/** Parsea monto (puede tener comas) */
function parseMonto(v: string | number | undefined): number {
  if (v === undefined || v === null) return 0;
  const s = String(v).replace(/,/g, "").replace(/[^\d.-]/g, "");
  const n = parseFloat(s);
  return isNaN(n) ? 0 : n;
}

/** Normaliza id para comparación (backend puede devolver int o string) */
function normId(v: unknown): string {
  if (v == null || v === "") return "";
  const s = String(v).trim();
  const n = Number(s);
  return !Number.isNaN(n) && Number.isInteger(n) ? String(n) : s;
}

/** Extrae categoria_id de subcategoría (backend puede usar categoria_id, Id_Categoria o categoryId) */
function getSubCategoriaId(s: Record<string, unknown>): string {
  const v = s.categoria_id ?? s.Id_Categoria ?? s.categoryId;
  return normId(v);
}

/** Extrae nombre de subcategoría (backend puede usar nombre, name o Nombre_SubCategoria) */
function getSubNombre(s: Record<string, unknown>): string {
  const v = s.nombre ?? s.name ?? s.Nombre_SubCategoria;
  return String(v ?? "").trim() || "";
}

/** Extrae id de subcategoría */
function getSubId(s: Record<string, unknown>): string {
  return normId(s.id ?? s.Id);
}

/** Convierte subcategorias a array (puede venir como array, objeto con índices, o { data: [...] }) */
function toSubcategoriasArray(subcategorias: unknown): Record<string, unknown>[] {
  if (Array.isArray(subcategorias)) {
    return subcategorias.filter((s) => s && typeof s === "object") as Record<string, unknown>[];
  }
  if (subcategorias && typeof subcategorias === "object") {
    const obj = subcategorias as Record<string, unknown>;
    if (Array.isArray(obj.data)) return toSubcategoriasArray(obj.data);
    if (Array.isArray(obj.subcategorias)) return toSubcategoriasArray(obj.subcategorias);
    const vals = Object.values(obj);
    if (vals.every((v) => v && typeof v === "object" && !Array.isArray(v))) {
      return vals as Record<string, unknown>[];
    }
  }
  return [];
}

/** Mapea CategoriaRaw[] + SubcategoriaRaw[] a Category[] */
export function mapCatalogToCategories(
  categorias: CategoriaRaw[],
  subcategorias: SubcategoriaRaw[] | unknown
): Category[] {
  const subs = toSubcategoriasArray(subcategorias);
  const cats = Array.isArray(categorias) ? categorias : [];
  const catIds = cats.map((c) => normId(c.id));
  const subCatIds = [...new Set(subs.map((s) => getSubCategoriaId(s)))];
  console.log("[mapCatalogToCategories] input:", {
    categoriasCount: cats.length,
    subcategoriasCount: subs.length,
    catIds,
    subCatIdsUnicos: subCatIds,
    match: catIds.some((cid) => subCatIds.includes(cid)) ? "SÍ hay coincidencias" : "NO hay coincidencias - categoria_id de subs no matchea con id de cats",
  });
  return cats.map((cat) => {
    const catId = normId(cat.id);
    const subcats = subs.filter((s) => getSubCategoriaId(s) === catId);
    if (subcats.length > 0) {
      console.log("[mapCatalogToCategories] ✓", cat.nombre, "id:", cat.id, "→", subcats.length, "subcategorías");
    }
    return {
      id: cat.id,
      name: cat.nombre,
      icon: resolveIcon(cat.icon, cat.nombre),
      color: cat.color || "#6b7280",
      bucket: cat.bucket || "",
      tipo: (cat.tipo as "Gasto" | "Ingreso") || "Gasto",
      subcategories: subcats.map((s) => ({
        id: getSubId(s),
        name: getSubNombre(s),
        categoryId: cat.id,
      })),
    };
  });
}

/** Mapea ReglaRaw[] a MerchantRule[] usando merchants para resolver merchantId */
export function mapReglasToMerchantRules(
  reglas: ReglaRaw[],
  merchants: Merchant[]
): MerchantRule[] {
  return reglas.map((r) => {
    const merchant = merchants.find(
      (m) => m.name.toLowerCase() === r.comercio.toLowerCase()
    );
    return {
      id: r.id,
      merchantId: merchant?.id ?? "unknown",
      categoryId: r.categoria_id,
      subcategoryId: r.subcategoria_id || undefined,
    };
  });
}

/** Normaliza mes_anio a YYYY-MM para comparación */
export function normalizeMesAnio(s: string | undefined): string {
  if (!s || !String(s).trim()) return "";
  const t = String(s).trim();
  const m = /^(\d{4})-(\d{1,2})$/.exec(t);
  if (m) return `${m[1]}-${m[2].padStart(2, "0")}`;
  const m2 = /^(\d{1,2})\/(\d{4})$/.exec(t);
  if (m2) return `${m2[2]}-${m2[1].padStart(2, "0")}`;
  const m3 = /^(\d{1,2})\/(\d{2})$/.exec(t);
  if (m3) {
    const yy = parseInt(m3[2], 10);
    const y = yy < 50 ? 2000 + yy : 1900 + yy;
    return `${y}-${m3[1].padStart(2, "0")}`;
  }
  return t;
}

/** Mapea PresupuestoRaw[] a Budget[] */
export function mapPresupuestosToBudgets(presupuestos: PresupuestoRaw[]): Budget[] {
  return presupuestos.map((p) => {
    const monto = parseFloat(String(p.monto).replace(/,/g, "")) || 0;
    return {
      id: p.id,
      categoryId: p.categoria_id,
      subcategoryId: p.subcategoria_id?.trim() || undefined,
      mes_anio: normalizeMesAnio(p.mes_anio) || p.mes_anio,
      amount: monto,
      period: "monthly" as const,
      spent: 0,
    };
  });
}

/** Calcula gasto desde transacciones de un mes dado */
export function calcSpentFromTransactions(
  budget: Budget,
  transactions: Transaction[],
  monthYear?: { month: number; year: number }
): number {
  const ref = monthYear ?? { month: new Date().getMonth(), year: new Date().getFullYear() };

  return transactions
    .filter((t) => {
      const d = parseDateLocal(t.date);
      if (d.getMonth() !== ref.month || d.getFullYear() !== ref.year) return false;
      if (t.amount === 0) return false;
      if (String(t.categoryId) !== String(budget.categoryId)) return false;
      if (budget.subcategoryId) {
        return String(t.subcategoryId) === String(budget.subcategoryId);
      }
      return true;
    })
    .reduce((sum, t) => sum + Math.abs(t.amount), 0);
}

/** Mapea MovimientoRaw a Transaction usando categorías y comercios para resolver IDs */
export function mapMovimientoToTransaction(
  m: MovimientoRaw,
  categories: Category[],
  merchants: Merchant[]
): Transaction {
  const catName = (m.Nombre_Categoria || "").trim();
  const subName = (m.Nombre_SubCategoria || "").trim();
  const comercio = (m.Comercio || "").trim();
  const tipo = (m["Tipo de Movimiento"] || "gasto").toString().toLowerCase();
  const monto = parseMonto(m.Monto);
  const amount = tipo === "ingreso" ? monto : -monto;

  const category = categories.find(
    (c) => c.name.toLowerCase() === catName.toLowerCase()
  );
  const subcategory = category?.subcategories?.find(
    (s) => s.name.toLowerCase() === subName.toLowerCase()
  );
  const merchant = merchants.find(
    (mr) => mr.name.toLowerCase() === comercio.toLowerCase()
  );

  return {
    id: String(m.Id || ""),
    amount,
    description: comercio || "Sin descripción",
    date: parseFecha(m.Fecha),
    categoryId: category?.id || "unknown",
    subcategoryId: subcategory?.id,
    merchantId: merchant?.id || "unknown",
  };
}

/** Convierte YYYY-MM-DD a DD/MM/YYYY para el backend */
export function formatDateToBackend(dateStr: string): string {
  if (!dateStr || !dateStr.trim()) return "";
  const parts = String(dateStr).trim().split("-");
  if (parts.length === 3) {
    const [y, m, d] = parts;
    return `${d.padStart(2, "0")}/${m.padStart(2, "0")}/${y}`;
  }
  return dateStr;
}

/** Convierte Transaction a payload para PATCH /movimientos (formato Sheets) */
export function transactionToPatchPayload(
  t: Partial<Transaction>,
  categories: Category[],
  merchants: Merchant[]
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  if (t.description != null) payload.Descripcion = t.description;
  if (t.amount != null) payload.Monto = Math.abs(t.amount);
  if (t.date != null) payload.Fecha = formatDateToBackend(t.date);
  if (t.merchantId != null) {
    const m = merchants.find((mr) => mr.id === t.merchantId);
    if (m) {
      // Si es id numérico (comercio de la base), enviar comercioId; si no, Comercio (nombre)
      if (/^\d+$/.test(String(t.merchantId))) {
        payload.comercioId = t.merchantId;
      } else {
        payload.Comercio = m.name;
      }
    }
  } else if (t.merchantId === "") {
    payload.comercioId = "";
  }
  if (t.categoryId != null) {
    const c = categories.find((cat) => cat.id === t.categoryId);
    if (c) payload.Nombre_Categoria = c.name;
  }
  if (t.subcategoryId != null) {
    const c = categories.find((cat) => cat.id === t.categoryId);
    const s = c?.subcategories?.find((sub) => sub.id === t.subcategoryId);
    if (s) payload.Nombre_SubCategoria = s.name;
  } else if (t.categoryId != null) {
    payload.Nombre_SubCategoria = "";
  }
  return payload;
}

/** Mapea MovimientoItem (formato paginado API) a Transaction */
export function mapMovimientoItemToTransaction(
  item: MovimientoItem,
  categories: Category[],
  merchants: Merchant[]
): Transaction {
  const amount = item.tipo === "Gasto" ? -Math.abs(item.monto) : item.monto;
  let category = categories.find(
    (c) => c.name.toLowerCase() === (item.categoria || "").toLowerCase()
  );
  let subcategory = category?.subcategories?.find(
    (s) => s.name.toLowerCase() === (item.subcategoria || "").toLowerCase()
  );
  const merchant = merchants.find(
    (m) => m.id === item.comercioId || m.name.toLowerCase() === (item.comercio || "").toLowerCase()
  );
  const merchantById = item.comercioId
    ? merchants.find((m) => m.id === item.comercioId)
    : null;
  // Fallback: si no tiene cat/subcat pero tiene comercio, usar las del comercio
  if ((!category || !subcategory) && (merchantById ?? merchant)) {
    const m = merchantById ?? merchant;
    const catId = m?.defaultCategoryId ?? item.idCategoria;
    const subId = m?.defaultSubcategoryId ?? item.idSubcategoria;
    if (catId) {
      const cat = categories.find((c) => c.id === catId);
      if (cat) {
        category = cat;
        subcategory = subId
          ? cat.subcategories?.find((s) => s.id === subId)
          : cat.subcategories?.find(
              (s) => s.name.toLowerCase() === (item.subcategoria || "").toLowerCase()
            );
      }
    }
  }

  return {
    id: item.id,
    amount,
    tipo: item.tipo,
    currency: (item.moneda || "ARS").trim().toUpperCase() || "ARS",
    description: item.comercio || item.descripcion || "Sin descripción",
    descripcion: item.descripcion?.trim() || undefined,
    date: item.fecha,
    categoryId: category?.id || "unknown",
    subcategoryId: subcategory?.id,
    merchantId: item.comercioId || merchant?.id || "",
    cuotaActual: item.cuotaActual ?? item.CuotaActual ?? null,
    cuotaTotal: item.cuotaTotal ?? item.CuotaTotal ?? null,
    montoTotalCompra: item.montoTotalCompra ?? item.MontoTotalCompra ?? null,
  };
}
