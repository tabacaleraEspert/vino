import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { useAuth } from "./AuthContext";
import {
  api,
  mapMovimientoItemToTransaction,
  mapCatalogToCategories,
  mapReglasToMerchantRules,
  mapPresupuestosToBudgets,
  type MovimientosPaginatedResponse,
  Category,
  Subcategory,
  Transaction,
  Budget,
  Merchant,
  MerchantRule,
} from "../../lib/api";

interface DataContextType {
  categories: Category[];
  addCategory: (category: Omit<Category, "id">) => Promise<void>;
  updateCategory: (id: string, category: Partial<Category>) => Promise<void>;
  deleteCategory: (id: string) => Promise<void>;
  addSubcategory: (categoryId: string, subcategoryName: string) => Promise<void>;
  updateSubcategory: (categoryId: string, subcategoryId: string, newName: string) => Promise<void>;
  deleteSubcategory: (categoryId: string, subcategoryId: string) => Promise<void>;
  transactions: Transaction[];
  budgets: Budget[];
  addBudget: (budget: Omit<Budget, "id">) => Promise<void>;
  updateBudget: (id: string, budget: Partial<Budget>) => Promise<void>;
  deleteBudget: (id: string) => Promise<void>;
  merchants: Merchant[];
  addMerchant: (merchant: Omit<Merchant, "id">) => Promise<void>;
  updateMerchant: (id: string, merchant: Partial<Merchant>) => Promise<void>;
  deleteMerchant: (id: string) => Promise<void>;
  merchantRules: MerchantRule[];
  addMerchantRule: (rule: Omit<MerchantRule, "id">) => Promise<void>;
  updateMerchantRule: (id: string, rule: Partial<MerchantRule>) => Promise<void>;
  deleteMerchantRule: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export function DataProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [merchantRules, setMerchantRules] = useState<MerchantRule[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const [
        categoriasRaw,
        subcategoriasRaw,
        presupuestosRaw,
        reglasRaw,
        mers,
        movs,
      ] = await Promise.all([
        api.categories.list(token).catch(() => []),
        api.subcategorias.list({}, token).catch(() => []),
        api.budgets.list({}, token).catch(() => []),
        api.merchantRules.list({}, token).catch(() => []),
        api.merchants.list(token).catch(() => []),
        api.movimientos.list({ limit: "5000" }, token).catch((): MovimientosPaginatedResponse => ({ items: [], page: 1, limit: 50, total: 0 })),
      ]);

      const cats = mapCatalogToCategories(
        categoriasRaw || [],
        subcategoriasRaw || []
      );
      const buds = mapPresupuestosToBudgets(presupuestosRaw || []);

      const mersList = mers || [];
      const comerciosFromReglas = [
        ...new Set(
          (reglasRaw || [])
            .map((r) => (r.comercio || "").trim())
            .filter(Boolean)
        ),
      ];
      const virtualMerchants = comerciosFromReglas
        .filter(
          (nombre) =>
            !mersList.some(
              (m) => m.name.toLowerCase() === nombre.toLowerCase()
            )
        )
        .map((nombre) => ({
          id: `comercio-${nombre.replace(/\s+/g, "_")}`,
          name: nombre,
        }));
      const merchantsEnhanced = [...mersList, ...virtualMerchants];
      const rules = mapReglasToMerchantRules(
        reglasRaw || [],
        merchantsEnhanced
      );

      setCategories(cats);
      setBudgets(buds);
      setMerchants(merchantsEnhanced);
      setMerchantRules(rules);

      const movsRes = movs as MovimientosPaginatedResponse;
      const items = movsRes?.items ?? [];
      const mapped = items.map((m) =>
        mapMovimientoItemToTransaction(m, cats, merchantsEnhanced)
      );
      setTransactions(mapped);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar datos");
      setCategories([]);
      setBudgets([]);
      setMerchants([]);
      setMerchantRules([]);
      setTransactions([]);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const addCategory = async (category: Omit<Category, "id">) => {
    if (!token) return;
    await api.categories.create(category, token);
    await fetchData();
  };

  const updateCategory = async (id: string, updates: Partial<Category>) => {
    if (!token) return;
    await api.categories.update(id, updates, token);
    await fetchData();
  };

  const deleteCategory = async (id: string) => {
    if (!token) return;
    await api.categories.delete(id, token);
    await fetchData();
  };

  const addSubcategory = async (categoryId: string, subcategoryName: string) => {
    if (!token) return;
    await api.categories.addSubcategory(categoryId, subcategoryName, token);
    await fetchData();
  };

  const updateSubcategory = async (
    categoryId: string,
    subcategoryId: string,
    newName: string
  ) => {
    if (!token) return;
    await api.subcategorias.update(subcategoryId, newName, token);
    await fetchData();
  };

  const deleteSubcategory = async (categoryId: string, subcategoryId: string) => {
    if (!token) return;
    await api.subcategorias.delete(subcategoryId, token);
    await fetchData();
  };

  const addBudget = async (budget: Omit<Budget, "id">) => {
    if (!token) return;
    await api.budgets.create(budget, token);
    await fetchData();
  };

  const updateBudget = async (id: string, updates: Partial<Budget>) => {
    if (!token) return;
    await api.budgets.update(id, updates, token);
    await fetchData();
  };

  const deleteBudget = async (id: string) => {
    if (!token) return;
    await api.budgets.delete(id, token);
    await fetchData();
  };

  const addMerchant = async (merchant: Omit<Merchant, "id">) => {
    if (!token) return;
    await api.merchants.create(merchant, token);
    await fetchData();
  };

  const updateMerchant = async (id: string, updates: Partial<Merchant>) => {
    if (!token) return;
    await api.merchants.update(id, updates, token);
    await fetchData();
  };

  const deleteMerchant = async (id: string) => {
    if (!token) return;
    await api.merchants.delete(id, token);
    await fetchData();
  };

  const addMerchantRule = async (rule: Omit<MerchantRule, "id">) => {
    if (!token) return;
    await api.merchantRules.create(rule, token);
    await fetchData();
  };

  const updateMerchantRule = async (id: string, updates: Partial<MerchantRule>) => {
    if (!token) return;
    await api.merchantRules.update(id, updates, token);
    await fetchData();
  };

  const deleteMerchantRule = async (id: string) => {
    if (!token) return;
    await api.merchantRules.delete(id, token);
    await fetchData();
  };

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
        refresh: fetchData,
        isLoading,
        error,
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
