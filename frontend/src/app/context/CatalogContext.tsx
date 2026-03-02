/**
 * CatalogContext: categorías + subcategorías con cache (bootstrap slim).
 * Usa dataLayer para fetch con coalescing y localStorage.
 */
import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { useAuth } from "./AuthContext";
import {
  api,
  mapCatalogToCategories,
  type Category,
} from "../../lib/api";
import { fetchCatalog, invalidateCatalog } from "../../lib/dataLayer";

interface CatalogContextType {
  categories: Category[];
  addCategory: (category: Omit<Category, "id">) => Promise<void>;
  updateCategory: (id: string, category: Partial<Category>) => Promise<void>;
  deleteCategory: (id: string) => Promise<void>;
  addSubcategory: (categoryId: string, subcategoryName: string) => Promise<void>;
  updateSubcategory: (
    categoryId: string,
    subcategoryId: string,
    newName: string
  ) => Promise<void>;
  deleteSubcategory: (categoryId: string, subcategoryId: string) => Promise<void>;
  refreshCatalog: (skipCache?: boolean) => Promise<Category[]>;
  isLoading: boolean;
  error: string | null;
}

const CatalogContext = createContext<CatalogContextType | undefined>(undefined);

export function CatalogProvider({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCatalog = useCallback(
    async (skipCache = false): Promise<Category[]> => {
      if (!token) {
        setIsLoading(false);
        return [];
      }
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchCatalog(token, user?.id ?? "", { skipCache });
        const cats = mapCatalogToCategories(
          data.categorias ?? [],
          data.subcategorias ?? []
        );
        setCategories(cats);
        return cats;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar catálogo");
        setCategories([]);
        return [];
      } finally {
        setIsLoading(false);
      }
    },
    [token, user?.id]
  );

  useEffect(() => {
    if (!token) {
      setCategories([]);
      setIsLoading(false);
      setError(null);
    }
  }, [token]);

  const refreshCatalog = useCallback(
    async (skipCache = false): Promise<Category[]> => {
      invalidateCatalog(user?.id ?? "", token ?? undefined);
      return loadCatalog(skipCache);
    },
    [loadCatalog, user?.id, token]
  );

  const addCategory = useCallback(
    async (category: Omit<Category, "id">) => {
      if (!token) return;
      await api.categories.create(category);
      invalidateCatalog(user?.id ?? "", token);
      await loadCatalog(true);
    },
    [token, user?.id, loadCatalog]
  );

  const updateCategory = useCallback(
    async (id: string, updates: Partial<Category>) => {
      if (!token) return;
      await api.categories.update(id, updates);
      invalidateCatalog(user?.id ?? "", token);
      await loadCatalog(true);
    },
    [token, user?.id, loadCatalog]
  );

  const deleteCategory = useCallback(
    async (id: string) => {
      if (!token) return;
      await api.categories.delete(id);
      invalidateCatalog(user?.id ?? "", token);
      await loadCatalog(true);
    },
    [token, user?.id, loadCatalog]
  );

  const addSubcategory = useCallback(
    async (categoryId: string, subcategoryName: string) => {
      if (!token) return;
      await api.categories.addSubcategory(categoryId, subcategoryName);
      invalidateCatalog(user?.id ?? "", token);
      await loadCatalog(true);
    },
    [token, user?.id, loadCatalog]
  );

  const updateSubcategory = useCallback(
    async (
      _categoryId: string,
      subcategoryId: string,
      newName: string
    ) => {
      if (!token) return;
      await api.subcategorias.update(subcategoryId, newName);
      invalidateCatalog(user?.id ?? "", token);
      await loadCatalog(true);
    },
    [token, user?.id, loadCatalog]
  );

  const deleteSubcategory = useCallback(
    async (_categoryId: string, subcategoryId: string) => {
      if (!token) return;
      await api.subcategorias.delete(subcategoryId);
      invalidateCatalog(user?.id ?? "", token);
      await loadCatalog(true);
    },
    [token, user?.id, loadCatalog]
  );

  return (
    <CatalogContext.Provider
      value={{
        categories,
        addCategory,
        updateCategory,
        deleteCategory,
        addSubcategory,
        updateSubcategory,
        deleteSubcategory,
        refreshCatalog,
        isLoading,
        error,
      }}
    >
      {children}
    </CatalogContext.Provider>
  );
}

export function useCatalog() {
  const context = useContext(CatalogContext);
  if (context === undefined) {
    throw new Error("useCatalog must be used within a CatalogProvider");
  }
  return context;
}
