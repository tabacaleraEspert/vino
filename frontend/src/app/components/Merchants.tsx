import { useData } from "../context/DataContext";
import { Store, Plus, ChevronRight, Search } from "lucide-react";
import { Link } from "react-router";
import { useState, useMemo } from "react";
import { CreateMerchantModal } from "./CreateMerchantModal";
import { CreateRuleModal } from "./CreateRuleModal";

type SortOrder = "alfa" | "nuevo" | "viejo";

export function Merchants() {
  const { merchants, merchantRules, categories, transactions } = useData();
  const [showCreateMerchant, setShowCreateMerchant] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOrder, setSortOrder] = useState<SortOrder>("alfa");
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>("all");
  const [ruleModalMerchant, setRuleModalMerchant] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const merchantsWithStats = useMemo(() => {
    const withStats = merchants.map((merchant) => {
      const merchantTransactions = transactions.filter(
        (t) => t.merchantId === merchant.id
      );
      const totalSpent = merchantTransactions.reduce(
        (sum, t) => sum + Math.abs(t.amount),
        0
      );
      const lastTransactionDate =
        merchantTransactions.length > 0
          ? Math.max(
              ...merchantTransactions.map((t) =>
                new Date(t.date).getTime()
              )
            )
          : 0;
      const rule = merchantRules.find((r) => r.merchantId === merchant.id);
      const category = rule
        ? categories.find((c) => c.id === rule.categoryId)
        : null;
      const subcategory =
        rule?.subcategoryId && category
          ? category.subcategories?.find((s) => s.id === rule.subcategoryId)
          : null;

      return {
        ...merchant,
        totalSpent,
        transactionCount: merchantTransactions.length,
        lastTransactionDate,
        category,
        subcategory,
        hasRule: !!rule,
      };
    });

    const query = searchQuery.trim().toLowerCase();
    let filtered = withStats;

    if (query) {
      filtered = filtered.filter((m) =>
        m.name.toLowerCase().includes(query)
      );
    }

    if (selectedCategoryId !== "all") {
      filtered = filtered.filter(
        (m) => m.category?.id === selectedCategoryId
      );
    }

    filtered.sort((a, b) => {
      if (sortOrder === "alfa") {
        return a.name.localeCompare(b.name, "es", { sensitivity: "base" });
      }
      if (sortOrder === "nuevo") {
        return b.lastTransactionDate - a.lastTransactionDate;
      }
      return a.lastTransactionDate - b.lastTransactionDate;
    });
    return filtered;
  }, [merchants, merchantRules, categories, transactions, searchQuery, sortOrder, selectedCategoryId]);

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Comercios y Reglas</h2>
        <button
          className="flex items-center gap-1 text-sm text-blue-600 font-medium"
          onClick={() => setShowCreateMerchant(true)}
        >
          <Plus className="w-4 h-4" />
          Agregar
        </button>
      </div>

      {/* Información */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <p className="text-sm text-blue-800">
          Las reglas de comercio asignan automáticamente categorías a tus
          transacciones según el comercio.
        </p>
      </div>

      {/* Búsqueda y ordenamiento */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por nombre..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder:text-gray-400"
          />
        </div>
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value as SortOrder)}
          className="px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-700 min-w-[180px]"
        >
          <option value="alfa">Alfabético (A-Z)</option>
          <option value="nuevo">Más nuevo a más viejo</option>
          <option value="viejo">Más viejo a más nuevo</option>
        </select>
      </div>

      {/* Filtro por categoría */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        <button
          onClick={() => setSelectedCategoryId("all")}
          className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
            selectedCategoryId === "all"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-600"
          }`}
        >
          Todas
        </button>
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategoryId(cat.id)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              selectedCategoryId === cat.id
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {cat.icon} {cat.name}
          </button>
        ))}
      </div>

      {/* Lista de comercios */}
      <div className="space-y-3">
        {merchantsWithStats.length === 0 ? (
          <div className="bg-gray-50 rounded-xl p-8 text-center text-gray-500">
            <p className="text-sm">
              {searchQuery.trim()
                ? "No se encontraron comercios con ese nombre."
                : selectedCategoryId !== "all"
                  ? "No hay comercios con regla en esta categoría."
                  : "No hay comercios registrados."}
            </p>
          </div>
        ) : (
          merchantsWithStats.map((merchant) => (
          <div
            key={merchant.id}
            className="bg-white rounded-xl p-4 shadow-sm relative"
          >
            <Link
              to={`/merchants/${merchant.id}`}
              className="block"
            >
              <div className="flex items-start gap-3">
                {/* Icono */}
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                  <Store className="w-6 h-6 text-gray-600" />
                </div>

                {/* Información */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{merchant.name}</p>
                      {merchant.category && (
                        <div className="flex items-center gap-1.5 mt-1">
                          <span className="text-lg">{merchant.category.icon}</span>
                          <span className="text-xs text-gray-600">
                            {merchant.category.name}
                            {merchant.subcategory && ` - ${merchant.subcategory.name}`}
                          </span>
                        </div>
                      )}
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  </div>

                  {/* Estadísticas */}
                  <div className="flex items-center gap-4 mt-3">
                    <div>
                      <p className="text-xs text-gray-500">Total gastado</p>
                      <p className="text-sm font-semibold text-gray-900">
                        ${merchant.totalSpent.toLocaleString("es-MX")}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Transacciones</p>
                      <p className="text-sm font-semibold text-gray-900">
                        {merchant.transactionCount}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </Link>

            {/* Estado de regla */}
            <div className="mt-3 pt-3 border-t border-gray-100">
              {merchant.hasRule ? (
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-xs text-green-700 font-medium">
                    Regla activa
                  </span>
                </div>
              ) : (
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setRuleModalMerchant({ id: merchant.id, name: merchant.name });
                  }}
                  className="text-xs text-blue-600 font-medium hover:text-blue-700"
                >
                  + Crear regla de categorización
                </button>
              )}
            </div>
          </div>
        ))
        )}
      </div>

      {/* Información adicional */}
      <div className="bg-gray-50 rounded-xl p-4">
        <h3 className="font-medium mb-2 text-sm">¿Qué son las reglas?</h3>
        <p className="text-xs text-gray-600 leading-relaxed">
          Las reglas te permiten automatizar la categorización de transacciones.
          Cuando realizas una compra en un comercio con una regla activa, la
          transacción se categorizará automáticamente.
        </p>
      </div>

      {/* Modales */}
      <CreateMerchantModal
        show={showCreateMerchant}
        onClose={() => setShowCreateMerchant(false)}
      />
      <CreateRuleModal
        show={!!ruleModalMerchant}
        merchant={ruleModalMerchant}
        onClose={() => setRuleModalMerchant(null)}
      />
    </div>
  );
}