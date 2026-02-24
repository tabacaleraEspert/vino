import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { useAuth } from "./AuthContext";
import { useMonth } from "./MonthContext";
import { useCatalog } from "./CatalogContext";
import {
  api,
  mapMovimientoItemToTransaction,
  mapReglasToMerchantRules,
  mapPresupuestosToBudgets,
  transactionToPatchPayload,
  type MovimientosPaginatedResponse,
  type ReglaRaw,
  Category,
  Transaction,
  Budget,
  Merchant,
  MerchantRule,
} from "../../lib/api";
import { fetchDataForPeriod } from "../../lib/dataLayer";

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
    categories,
    addCategory,
    updateCategory,
    deleteCategory,
    addSubcategory,
    updateSubcategory,
    deleteSubcategory,
    refreshCatalog,
    isLoading: catalogLoading,
    error: catalogError,
  } = useCatalog();

  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [merchantRules, setMerchantRules] = useState<MerchantRule[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;

  const fetchData = useCallback(
    async (forceRefresh = false, categoriesOverride?: Category[]) => {
      if (!token) {
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const { movimientos: movsRes, presupuestos: presupuestosRaw, reglas: reglasRaw, comercios: mers } =
          await fetchDataForPeriod(token, period, { forceRefresh });

        const items = movsRes?.items ?? [];
        const mersList = mers ?? [];
        const reglas = reglasRaw ?? [];

        const comerciosFromReglas = reglas.map((r) => (r.comercio || "").trim()).filter(Boolean);
        const comerciosFromMovimientos = items
          .map((m) => (m.comercio || m.descripcion || (m as { Comercio?: string; Descripcion?: string }).Comercio || (m as { Comercio?: string; Descripcion?: string }).Descripcion || "").trim())
          .filter(Boolean);
        const allComercioNames = [...new Set([...comerciosFromReglas, ...comerciosFromMovimientos])];
        const virtualMerchants = allComercioNames
          .filter((nombre) => !mersList.some((m) => m.name.toLowerCase() === nombre.toLowerCase()))
          .map((nombre) => ({
            id: `comercio-${nombre.replace(/\s+/g, "_")}`,
            name: nombre,
          }));
        const merchantsEnhanced = [...mersList, ...virtualMerchants];
        const rules = mapReglasToMerchantRules(reglas, merchantsEnhanced);

        setBudgets(mapPresupuestosToBudgets(presupuestosRaw ?? []));
        setMerchants(merchantsEnhanced);
        setMerchantRules(rules);

        const catsToUse = categoriesOverride ?? categories;
        const mapped = items.map((m) =>
          mapMovimientoItemToTransaction(m, catsToUse, merchantsEnhanced)
        );
        setTransactions(mapped);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar datos");
        setBudgets([]);
        setMerchants([]);
        setMerchantRules([]);
        setTransactions([]);
      } finally {
        setIsLoading(false);
      }
    },
    [token, period, categories]
  );

  useEffect(() => {
    if (!token) {
      setBudgets([]);
      setMerchants([]);
      setMerchantRules([]);
      setTransactions([]);
      setIsLoading(false);
    }
  }, [token]);

  const addBudget = async (budget: Omit<Budget, "id">) => {
    if (!token) return;
    await api.budgets.create(budget, token);
    await fetchData(true);
  };

  const updateBudget = async (id: string, updates: Partial<Budget>) => {
    if (!token) return;
    await api.budgets.update(id, updates, token);
    await fetchData(true);
  };

  const deleteBudget = async (id: string) => {
    if (!token) return;
    await api.budgets.delete(id, token);
    await fetchData(true);
  };

  const addMerchant = async (merchant: Omit<Merchant, "id">) => {
    if (!token) return;
    await api.merchants.create(merchant, token);
    await fetchData(true);
  };

  const updateMerchant = async (id: string, merchant: Partial<Merchant>) => {
    if (!token) return;
    const res = await api.merchants.update(id, merchant, token);
    await fetchData(true);
    return res;
  };

  const deleteMerchant = async (id: string) => {
    if (!token) return;
    await api.merchants.delete(id, token);
    await fetchData(true);
  };

  const addMerchantRule = async (rule: Omit<MerchantRule, "id">) => {
    if (!token) return;
    await api.merchantRules.create(rule, token);
    await fetchData(true);
  };

  const updateMerchantRule = async (id: string, rule: Partial<MerchantRule>) => {
    if (!token) return;
    await api.merchantRules.update(id, rule, token);
    await fetchData(true);
  };

  const deleteMerchantRule = async (id: string) => {
    if (!token) return;
    await api.merchantRules.delete(id, token);
    await fetchData(true);
  };

  const updateTransaction = async (id: string, updates: Partial<Transaction>) => {
    if (!token) return;
    const payload = transactionToPatchPayload(updates, categories, merchants);
    if (Object.keys(payload).length === 0) return;
    await api.movimientos.update(id, payload, token);
    await fetchData(true);
  };

  const deleteTransaction = async (id: string) => {
    if (!token) return;
    await api.movimientos.delete(id, token);
    await fetchData(true);
  };

  const refresh = useCallback(async () => {
    const cats = await refreshCatalog(true);
    await fetchData(true, cats);
    setRefreshTrigger((t) => t + 1);
  }, [refreshCatalog, fetchData]);

  return (
    <DataContext.Provider
      value={{
        categories,
        addCategory,
        updateCategory,
        deleteCategory,
        addSubcategory,
        updateSubcategory,
        deleteSubcategory,
        transactions,
        updateTransaction,
        deleteTransaction,
        budgets,
        addBudget,
        updateBudget,
        deleteBudget,
        merchants,
        addMerchant,
        updateMerchant,
        deleteMerchant,
        merchantRules,
        addMerchantRule,
        updateMerchantRule,
        deleteMerchantRule,
        refresh,
        refreshTrigger,
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
