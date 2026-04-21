/**
 * CatalogContext: categorías + subcategorías.
 * Se carga UNA vez con bootstrap y solo se refresca tras mutaciones.
 */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { useAuth } from "./AuthContext";
import {
  api,
  mapCatalogToCategories,
  type Category,
  type CategoriaRaw,
  type SubcategoriaRaw,
} from "../../lib/api";
import { invalidateCatalog } from "../../lib/dataLayer";

interface CatalogContextType {
  categories: Category[];
  setRawCatalog: (cats: CategoriaRaw[], subs: SubcategoriaRaw[]) => void;
  addCategory: (category: Omit<Category, "id">) => Promise<void>;
  updateCategory: (id: string, category: Partial<Category>) => Promise<void>;
  deleteCategory: (id: string) => Promise<void>;
  addSubcategory: (categoryId: string, subcategoryName: string) => Promise<void>;
  updateSubcategory: (categoryId: string, subcategoryId: string, newName: string) => Promise<void>;
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

  const setRawCatalog = useCallback((cats: CategoriaRaw[], subs: SubcategoriaRaw[]) => {
    setCategories(mapCatalogToCategories(cats, subs));
  }, []);

  const reloadCatalog = useCallback(async (): Promise<Category[]> => {
    if (!token) return [];
    setIsLoading(true);
    try {
      const [cats, subs] = await Promise.all([
        api.categories.list(),
        api.subcategorias.list({}),
      ]);
      const mapped = mapCatalogToCategories(cats ?? [], subs ?? []);
      setCategories(mapped);
      return mapped;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar catálogo");
      return categories;
    } finally {
      setIsLoading(false);
    }
  }, [token, categories]);

  const refreshCatalog = useCallback(
    async (skipCache = false): Promise<Category[]> => {
      invalidateCatalog(user?.id ?? "", token ?? undefined);
      return reloadCatalog();
    },
    [reloadCatalog, user?.id, token]
  );

  const addCategory = useCallback(async (category: Omit<Category, "id">) => {
    if (!token) return;
    await api.categories.create(category);
    await reloadCatalog();
  }, [token, reloadCatalog]);

  const updateCategory = useCallback(async (id: string, updates: Partial<Category>) => {
    if (!token) return;
    await api.categories.update(id, updates);
    await reloadCatalog();
  }, [token, reloadCatalog]);

  const deleteCategory = useCallback(async (id: string) => {
    if (!token) return;
    await api.categories.delete(id);
    await reloadCatalog();
  }, [token, reloadCatalog]);

  const addSubcategory = useCallback(async (categoryId: string, subcategoryName: string) => {
    if (!token) return;
    await api.categories.addSubcategory(categoryId, subcategoryName);
    await reloadCatalog();
  }, [token, reloadCatalog]);

  const updateSubcategory = useCallback(async (_categoryId: string, subcategoryId: string, newName: string) => {
    if (!token) return;
    await api.subcategorias.update(subcategoryId, newName);
    await reloadCatalog();
  }, [token, reloadCatalog]);

  const deleteSubcategory = useCallback(async (_categoryId: string, subcategoryId: string) => {
    if (!token) return;
    await api.subcategorias.delete(subcategoryId);
    await reloadCatalog();
  }, [token, reloadCatalog]);

  return (
    <CatalogContext.Provider
      value={{
        categories,
        setRawCatalog,
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
