const API_BASE =
  import.meta.env.VITE_API_URL ||
  "https://vino-backend-bkbge8cwfffsdrhc.brazilsouth-01.azurewebsites.net/api/v1";

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...init } = options;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Error en la petición");
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return {} as T;
  }
  return res.json();
}

// Tipos
export interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
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
  description: string;
  date: string;
  categoryId: string;
  subcategoryId?: string;
  merchantId: string;
}

// Formatos de respuesta del backend (Sheets)
export interface CategoriaRaw {
  id: string;
  nombre: string;
  icon?: string;
  color?: string;
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
  descripcion: string;
  categoria: string;
  subcategoria: string;
  medio_pago: string;
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
  categories: {
    list: (token?: string) =>
      apiFetch<CategoriaRaw[]>("/categorias", { token }),
    create: (data: Omit<Category, "id">, token?: string) =>
      apiFetch<Category>("/categorias", {
        method: "POST",
        body: JSON.stringify({
          name: data.name,
          icon: data.icon || "📁",
          color: data.color || "#6b7280",
          subcategories: (data.subcategories ?? []).map((s) => ({ name: s.name })),
        }),
        token,
      }),
    update: (id: string, data: Partial<Category>, token?: string) =>
      apiFetch<Category>(`/categorias/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...(data.name != null && { name: data.name }),
          ...(data.icon != null && { icon: data.icon }),
          ...(data.color != null && { color: data.color }),
        }),
        token,
      }),
    delete: (id: string, token?: string) =>
      apiFetch(`/categorias/${id}`, { method: "DELETE", token }),
    addSubcategory: (categoryId: string, name: string, token?: string) =>
      apiFetch<Category>(`/categorias/${categoryId}/subcategorias`, {
        method: "POST",
        body: JSON.stringify({ name }),
        token,
      }),
  },

  subcategorias: {
    list: (params?: { categoria_id?: string }, token?: string) => {
      const q = params?.categoria_id
        ? "?" + new URLSearchParams({ categoria_id: params.categoria_id }).toString()
        : "";
      return apiFetch<SubcategoriaRaw[]>(`/subcategorias${q}`, { token });
    },
    update: (id: string, name: string, token?: string) =>
      apiFetch<{ id: string; name: string; categoryId: string }>(`/subcategorias/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
        token,
      }),
    delete: (id: string, token?: string) =>
      apiFetch(`/subcategorias/${id}`, { method: "DELETE", token }),
  },

  budgets: {
    list: (params?: { mes_anio?: string; categoria_id?: string; subcategoria_id?: string }, token?: string) => {
      const q = params?.mes_anio || params?.categoria_id || params?.subcategoria_id
        ? "?" + new URLSearchParams(
            Object.fromEntries(
              Object.entries(params || {}).filter(([, v]) => v != null && v !== "")
            )
          ).toString()
        : "";
      return apiFetch<PresupuestoRaw[]>(`/presupuestos${q}`, { token });
    },
    create: (data: Omit<Budget, "id">, token?: string) =>
      apiFetch<Budget>("/presupuestos", {
        method: "POST",
        body: JSON.stringify(data),
        token,
      }),
    update: (id: string, data: Partial<Budget>, token?: string) =>
      apiFetch<Budget>(`/presupuestos/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
        token,
      }),
    delete: (id: string, token?: string) =>
      apiFetch(`/presupuestos/${id}`, { method: "DELETE", token }),
  },

  merchants: {
    list: (token?: string) =>
      apiFetch<Merchant[]>("/comercios", { token }),
    create: (data: Omit<Merchant, "id">, token?: string) =>
      apiFetch<Merchant>("/comercios", {
        method: "POST",
        body: JSON.stringify(data),
        token,
      }),
    update: (id: string, data: Partial<Merchant>, token?: string) =>
      apiFetch<Merchant>(`/comercios/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
        token,
      }),
    delete: (id: string, token?: string) =>
      apiFetch(`/comercios/${id}`, { method: "DELETE", token }),
  },

  merchantRules: {
    list: (params?: { comercio?: string; categoria_id?: string; subcategoria_id?: string }, token?: string) => {
      const q = params?.comercio || params?.categoria_id || params?.subcategoria_id
        ? "?" + new URLSearchParams(
            Object.fromEntries(
              Object.entries(params || {}).filter(([, v]) => v != null && v !== "")
            )
          ).toString()
        : "";
      return apiFetch<ReglaRaw[]>(`/reglas${q}`, { token });
    },
    create: (data: Omit<MerchantRule, "id">, token?: string) =>
      apiFetch<MerchantRule>("/reglas", {
        method: "POST",
        body: JSON.stringify(data),
        token,
      }),
    update: (id: string, data: Partial<MerchantRule>, token?: string) =>
      apiFetch<MerchantRule>(`/reglas/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
        token,
      }),
    delete: (id: string, token?: string) =>
      apiFetch(`/reglas/${id}`, { method: "DELETE", token }),
  },

  views: {
    homeSummary: (
      params: { period: string; moneda?: string },
      token?: string
    ) => {
      const q = new URLSearchParams({ period: params.period });
      if (params.moneda) q.set("moneda", params.moneda);
      return apiFetch<HomeSummaryResponse>(`/views/home/summary?${q}`, { token });
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
      return apiFetch<HomeBreakdownResponse>(`/views/home/breakdown?${q}`, { token });
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
      return apiFetch<MovimientosPaginatedResponse>(`/movimientos${q}`, { token });
    },
    create: (data: Record<string, unknown>, token?: string) =>
      apiFetch<MovimientoRaw>("/movimientos", {
        method: "POST",
        body: JSON.stringify(data),
        token,
      }),
    update: (id: string, data: Record<string, unknown>, token?: string) =>
      apiFetch<MovimientoRaw>(`/movimientos/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
        token,
      }),
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

/** Parsea monto (puede tener comas) */
function parseMonto(v: string | number | undefined): number {
  if (v === undefined || v === null) return 0;
  const s = String(v).replace(/,/g, "").replace(/[^\d.-]/g, "");
  const n = parseFloat(s);
  return isNaN(n) ? 0 : n;
}

/** Mapea CategoriaRaw[] + SubcategoriaRaw[] a Category[] */
export function mapCatalogToCategories(
  categorias: CategoriaRaw[],
  subcategorias: SubcategoriaRaw[]
): Category[] {
  return categorias.map((cat) => ({
    id: cat.id,
    name: cat.nombre,
    icon: cat.icon || "📁",
    color: cat.color || "#6b7280",
    subcategories: subcategorias
      .filter((s) => s.categoria_id === cat.id)
      .map((s) => ({
        id: s.id,
        name: s.nombre,
        categoryId: cat.id,
      })),
  }));
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
      const d = new Date(t.date);
      if (d.getMonth() !== ref.month || d.getFullYear() !== ref.year) return false;
      if (t.amount >= 0) return false; // solo gastos (negativos)
      if (t.categoryId !== budget.categoryId) return false;
      if (budget.subcategoryId) {
        return t.subcategoryId === budget.subcategoryId;
      }
      return true; // presupuesto de categoría completa
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

/** Mapea MovimientoItem (formato paginado API) a Transaction */
export function mapMovimientoItemToTransaction(
  item: MovimientoItem,
  categories: Category[],
  merchants: Merchant[]
): Transaction {
  const amount = item.tipo === "Gasto" ? -Math.abs(item.monto) : item.monto;
  const category = categories.find(
    (c) => c.name.toLowerCase() === (item.categoria || "").toLowerCase()
  );
  const subcategory = category?.subcategories?.find(
    (s) => s.name.toLowerCase() === (item.subcategoria || "").toLowerCase()
  );
  const merchant = merchants.find(
    (m) => m.name.toLowerCase() === (item.comercio || "").toLowerCase()
  );

  return {
    id: item.id,
    amount,
    description: item.comercio || item.descripcion || "Sin descripción",
    date: item.fecha,
    categoryId: category?.id || "unknown",
    subcategoryId: subcategory?.id,
    merchantId: merchant?.id || "unknown",
  };
}
