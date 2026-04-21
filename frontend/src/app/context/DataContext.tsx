/**
 * DataContext: datos del período (movimientos, presupuestos, merchants, reglas).
 *
 * Cambios clave vs anterior:
 * - Bootstrap carga todo en 1 request al iniciar (no 5 paralelos)
 * - Solo movimientos se re-fetchan al cambiar de mes
 * - Mutaciones refrescan solo lo necesario (no full re-fetch)
 * - Sin refreshCatalog() redundante en cada pantalla
 */
import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from "react";
import { useAuth } from "./AuthContext";
import { useMonth } from "./MonthContext";
import { useCatalog } from "./CatalogContext";
import {
  api,
  mapCatalogToCategories,
  mapMovimientoItemToTransaction,
  mapReglasToMerchantRules,
  mapPresupuestosToBudgets,
  transactionToPatchPayload,
  type ReglaRaw,
  type Category,
  type Transaction,
  type Budget,
  type Merchant,
  type MerchantRule,
} from "../../lib/api";
import { fetchBootstrap, fetchMovimientos } from "../../lib/dataLayer";

interface DataContextType {
  categories: Category[];
  addCategory: (category: Omit<Category, "id">) => Promise<void>;
  updateCategory: (id: string, category: Partial<Category>) => Promise<void>;
  deleteCategory: (id: string) => Promise<void>;
  addSubcategory: (categoryId: string, subcategoryName: string) => Promise<void>;
  updateSubcategory: (categoryId: string, subcategoryId: string, newName: string) => Promise<void>;
  deleteSubcategory: (categoryId: string, subcategoryId: string) => Promise<void>;
  transactions: Transaction[];
  updateTransaction: (id: string, updates: Partial<Transaction>) => Promise<void>;
  deleteTransaction: (id: string) => Promise<void>;
  budgets: Budget[];
  addBudget: (budget: Omit<Budget, "id">) => Promise<void>;
  updateBudget: (id: string, budget: Partial<Budget>) => Promise<void>;
  deleteBudget: (id: string) => Promise<void>;
  merchants: Merchant[];
  addMerchant: (merchant: Omit<Merchant, "id">) => Promise<void>;
  updateMerchant: (id: string, merchant: Partial<Merchant>) => Promise<Merchant | undefined>;
  deleteMerchant: (id: string) => Promise<void>;
  merchantRules: MerchantRule[];
  addMerchantRule: (rule: Omit<MerchantRule, "id">) => Promise<void>;
  updateMerchantRule: (id: string, rule: Partial<MerchantRule>) => Promise<void>;
  deleteMerchantRule: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
  refreshTrigger: number;
  isLoading: boolean;
  error: string | null;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export function DataProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const { selectedMonth } = useMonth();
  const {
    categories, setRawCatalog,
    addCategory, updateCategory, deleteCategory,
    addSubcategory, updateSubcategory, deleteSubcategory,
    isLoading: catalogLoading, error: catalogError,
  } = useCatalog();

  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [merchantRules, setMerchantRules] = useState<MerchantRule[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const bootstrapDone = useRef(false);

  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;

  // --- Bootstrap: 1 request carga catálogo + presupuestos + reglas + comercios ---
  useEffect(() => {
    if (!token) {
      setBudgets([]);
      setMerchants([]);
      setMerchantRules([]);
      setTransactions([]);
      bootstrapDone.current = false;
      return;
    }

    let cancelled = false;
    (async () => {
      setIsLoading(true);
      try {
        const data = await fetchBootstrap(token);
        if (cancelled) return;

        // Catalog
        setRawCatalog(data.categorias, data.subcategorias);
        const cats = mapCatalogToCategories(data.categorias, data.subcategorias);

        // Budgets
        setBudgets(mapPresupuestosToBudgets(data.presupuestos as any[] ?? []));

        // Merchants + rules
        const mersList = data.comercios ?? [];
        const reglas = data.reglas ?? [];
        setMerchants(mersList);
        setMerchantRules(mapReglasToMerchantRules(reglas, mersList));

        // Movimientos for current period
        const movsRes = await fetchMovimientos(token, period);
        if (cancelled) return;
        const mapped = (movsRes?.items ?? []).map((m) =>
          mapMovimientoItemToTransaction(m, cats, mersList)
        );
        setTransactions(mapped);

        bootstrapDone.current = true;
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error al cargar datos");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [token]); // Solo al login, no al cambiar de mes

  // --- Cambio de mes: solo re-fetch movimientos ---
  useEffect(() => {
    if (!token || !bootstrapDone.current) return;

    let cancelled = false;
    (async () => {
      setIsLoading(true);
      try {
        const movsRes = await fetchMovimientos(token, period, { forceRefresh: true });
        if (cancelled) return;
        const mapped = (movsRes?.items ?? []).map((m) =>
          mapMovimientoItemToTransaction(m, categories, merchants)
        );
        setTransactions(mapped);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error al cargar movimientos");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [period]); // Solo period, no categories/merchants (evita loops)

  // --- Refresh completo (pull-to-refresh, botón refresh) ---
  const refresh = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const data = await fetchBootstrap(token);
      setRawCatalog(data.categorias, data.subcategorias);
      const cats = mapCatalogToCategories(data.categorias, data.subcategorias);
      setBudgets(mapPresupuestosToBudgets(data.presupuestos as any[] ?? []));
      const mersList = data.comercios ?? [];
      setMerchants(mersList);
      setMerchantRules(mapReglasToMerchantRules(data.reglas ?? [], mersList));

      const movsRes = await fetchMovimientos(token, period, { forceRefresh: true });
      setTransactions((movsRes?.items ?? []).map((m) =>
        mapMovimientoItemToTransaction(m, cats, mersList)
      ));
      setRefreshTrigger((t) => t + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al refrescar");
    } finally {
      setIsLoading(false);
    }
  }, [token, period, setRawCatalog]);

  // --- Refresh solo movimientos (tras mutaciones simples) ---
  const refreshMovimientos = useCallback(async () => {
    if (!token) return;
    const movsRes = await fetchMovimientos(token, period, { forceRefresh: true });
    const mapped = (movsRes?.items ?? []).map((m) =>
      mapMovimientoItemToTransaction(m, categories, merchants)
    );
    setTransactions(mapped);
  }, [token, period, categories, merchants]);

  // --- Mutations ---
  const addBudget = async (budget: Omit<Budget, "id">) => {
    if (!token) return;
    await api.budgets.create(budget);
    const rows = await api.budgets.list({ mes_anio: period });
    setBudgets(mapPresupuestosToBudgets(rows ?? []));
  };

  const updateBudget = async (id: string, updates: Partial<Budget>) => {
    if (!token) return;
    await api.budgets.update(id, updates);
    const rows = await api.budgets.list({ mes_anio: period });
    setBudgets(mapPresupuestosToBudgets(rows ?? []));
  };

  const deleteBudget = async (id: string) => {
    if (!token) return;
    await api.budgets.delete(id);
    setBudgets((prev) => prev.filter((b) => b.id !== id));
  };

  const addMerchant = async (merchant: Omit<Merchant, "id">) => {
    if (!token) return;
    const created = await api.merchants.create(merchant);
    setMerchants((prev) => [...prev, created]);
  };

  const updateMerchant = async (id: string, merchant: Partial<Merchant>) => {
    if (!token) return;
    const res = await api.merchants.update(id, merchant);
    setMerchants((prev) => prev.map((m) => (m.id === id ? { ...m, ...res } : m)));
    return res;
  };

  const deleteMerchant = async (id: string) => {
    if (!token) return;
    await api.merchants.delete(id);
    setMerchants((prev) => prev.filter((m) => m.id !== id));
  };

  const addMerchantRule = async (rule: Omit<MerchantRule, "id">) => {
    if (!token) return;
    await api.merchantRules.create(rule);
    await refresh();
  };

  const updateMerchantRule = async (id: string, rule: Partial<MerchantRule>) => {
    if (!token) return;
    await api.merchantRules.update(id, rule);
    await refresh();
  };

  const deleteMerchantRule = async (id: string) => {
    if (!token) return;
    await api.merchantRules.delete(id);
    setMerchantRules((prev) => prev.filter((r) => r.id !== id));
  };

  const updateTransaction = async (id: string, updates: Partial<Transaction>) => {
    if (!token) return;
    const payload = transactionToPatchPayload(updates, categories, merchants);
    if (Object.keys(payload).length === 0) return;
    await api.movimientos.update(id, payload);
    await refreshMovimientos();
  };

  const deleteTransaction = async (id: string) => {
    if (!token) return;
    await api.movimientos.delete(id);
    setTransactions((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <DataContext.Provider
      value={{
        categories, addCategory, updateCategory, deleteCategory,
        addSubcategory, updateSubcategory, deleteSubcategory,
        transactions, updateTransaction, deleteTransaction,
        budgets, addBudget, updateBudget, deleteBudget,
        merchants, addMerchant, updateMerchant, deleteMerchant,
        merchantRules, addMerchantRule, updateMerchantRule, deleteMerchantRule,
        refresh, refreshTrigger,
        isLoading: isLoading || catalogLoading,
        error: error || catalogError,
      }}
    >
      {children}
    </DataContext.Provider>
  );
}

export function useData() {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error("useData must be used within a DataProvider");
  }
  return context;
}
