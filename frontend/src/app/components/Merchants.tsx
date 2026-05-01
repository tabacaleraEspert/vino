import { useData } from "../context/DataContext";
import { parseDateLocal } from "../../lib/api";
import { Store, Plus, ChevronRight, Search, Calendar, Trash2 } from "lucide-react";
import { Link } from "react-router";
import { useState, useMemo, useEffect } from "react";
import { toast } from "sonner";
import { CreateMerchantModal } from "./CreateMerchantModal";
import { CreateRuleModal } from "./CreateRuleModal";
import { ComerciosExplainerModal, CEHelpButton } from "./ComerciosExplainerModal";

type SortOrder = "alfa" | "nuevo" | "viejo";
type CreatedFilter = "all" | "7" | "15" | "30";

/** Extrae timestamp de id tipo mer_1234567890_1234 (store) */
function getCreatedAtFromId(id: string): number | null {
  const m = /^mer_(\d+)_\d+$/.exec(id);
  if (m) return parseInt(m[1], 10);
  return null;
}

export function Merchants() {
  const { merchants, merchantRules, categories, transactions, deleteMerchant, refresh } = useData();
  const [showCreateMerchant, setShowCreateMerchant] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOrder, setSortOrder] = useState<SortOrder>("alfa");
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>("all");
  const [createdFilter, setCreatedFilter] = useState<CreatedFilter>("all");
  const [ruleModalMerchant, setRuleModalMerchant] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [helpSeen, setHelpSeen] = useState(() => localStorage.getItem("comercios_explainer_seen") === "1");

  // Auto-show on first visit
  useEffect(() => {
    if (!helpSeen) setShowHelp(true);
  }, [helpSeen]);

  const closeHelp = () => {
    setShowHelp(false);
    if (!helpSeen) {
      localStorage.setItem("comercios_explainer_seen", "1");
      setHelpSeen(true);
    }
  };
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeletingEmpty, setIsDeletingEmpty] = useState(false);

  // Expensive computation: stats per merchant. Only recalculates when merchants/transactions change.
  const merchantStats = useMemo(() => {
    const now = Date.now();
    return merchants.map((merchant) => {
      const merchantTransactions = transactions.filter(
        (t) => t.merchantId === merchant.id
      );
      const totalSpent = merchantTransactions.reduce(
        (sum, t) => sum + Math.abs(t.amount),
        0
      );
      const lastTransactionDate =
        merchantTransactions.length > 0
          ? Math.max(...merchantTransactions.map((t) => parseDateLocal(t.date).getTime()))
          : 0;
      const firstTransactionDate =
        merchantTransactions.length > 0
          ? Math.min(...merchantTransactions.map((t) => parseDateLocal(t.date).getTime()))
          : 0;
      const storeCreatedAt = getCreatedAtFromId(merchant.id);
      const createdAt = storeCreatedAt ?? (firstTransactionDate || now);
      const rule = merchantRules.find((r) => r.merchantId === merchant.id);
      const category = rule ? categories.find((c) => c.id === rule.categoryId) : null;
      const subcategory =
        rule?.subcategoryId && category
          ? category.subcategories?.find((s) => s.id === rule.subcategoryId)
          : null;

      return {
        ...merchant,
        totalSpent,
        transactionCount: merchantTransactions.length,
        lastTransactionDate,
        createdAt,
        category,
        subcategory,
        hasRule: !!rule,
      };
    });
  }, [merchants, merchantRules, categories, transactions]);

  // Cheap: filtering and sorting on the precomputed stats
  const merchantsWithStats = useMemo(() => {
    const now = Date.now();
    const query = searchQuery.trim().toLowerCase();
    let filtered = merchantStats;

    if (query) {
      filtered = filtered.filter((m) => m.name.toLowerCase().includes(query));
    }
    if (selectedCategoryId !== "all") {
      filtered = filtered.filter((m) => m.category?.id === selectedCategoryId);
    }
    if (createdFilter !== "all") {
      const days = parseInt(createdFilter, 10);
      const cutoff = now - days * 24 * 60 * 60 * 1000;
      filtered = filtered.filter((m) => m.createdAt >= cutoff);
    }

    return [...filtered].sort((a, b) => {
      if (sortOrder === "alfa") return a.name.localeCompare(b.name, "es", { sensitivity: "base" });
      if (sortOrder === "nuevo") return b.lastTransactionDate - a.lastTransactionDate;
      return a.lastTransactionDate - b.lastTransactionDate;
    });
  }, [merchantStats, searchQuery, sortOrder, selectedCategoryId, createdFilter]);

  const groupedByDate = useMemo(() => {
    const acc = merchantsWithStats.reduce((a, m) => {
      const d = new Date(m.createdAt);
      const dateKey = d.toLocaleDateString("es-MX", {
        weekday: "long",
        day: "numeric",
        month: "long",
      });
      if (!a[dateKey]) a[dateKey] = [];
      a[dateKey].push(m);
      return a;
    }, {} as Record<string, typeof merchantsWithStats>);
    return Object.fromEntries(
      Object.entries(acc).sort(([_, a], [__, b]) => {
        const tA = a[0]?.createdAt ?? 0;
        const tB = b[0]?.createdAt ?? 0;
        return tB - tA;
      })
    );
  }, [merchantsWithStats]);

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold">Comercios y Reglas</h2>
          <CEHelpButton onClick={() => setShowHelp(true)} pulse={!helpSeen} />
        </div>
        <div className="flex items-center gap-2">
          {merchantStats.filter((m) => m.transactionCount === 0).length > 0 && (
            <button
              className="flex items-center gap-1 text-sm text-red-600 font-medium"
              disabled={isDeletingEmpty}
              onClick={async () => {
                const empty = merchantStats.filter((m) => m.transactionCount === 0);
                if (!confirm(`Borrar ${empty.length} comercios sin transacciones?`)) return;
                setIsDeletingEmpty(true);
                let deleted = 0;
                for (const m of empty) {
                  try { await deleteMerchant(m.id); deleted++; } catch {}
                }
                setIsDeletingEmpty(false);
                toast.success(`${deleted} comercios eliminados`);
              }}
            >
              <Trash2 className="w-4 h-4" />
              {isDeletingEmpty ? "Borrando..." : "Limpiar vacíos"}
            </button>
          )}
          <button
            className="flex items-center gap-1 text-sm text-blue-600 font-medium"
            onClick={() => setShowCreateMerchant(true)}
          >
            <Plus className="w-4 h-4" />
            Agregar
          </button>
        </div>
      </div>

      {/* Explainer modal */}
      <ComerciosExplainerModal open={showHelp} onClose={closeHelp} />

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

      {/* Filtro por fecha de creación */}
      <div className="flex items-center gap-2 flex-wrap">
        <Calendar className="w-4 h-4 text-gray-500" />
        <span className="text-xs text-gray-600">Creados en:</span>
        <div className="flex gap-2">
          {(["all", "7", "15", "30"] as const).map((opt) => (
            <button
              key={opt}
              onClick={() => setCreatedFilter(opt)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                createdFilter === opt
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {opt === "all" ? "Todos" : `Últimos ${opt} días`}
            </button>
          ))}
        </div>
      </div>

      {/* Lista de comercios agrupados por día */}
      <div className="space-y-4">
        {merchantsWithStats.length === 0 ? (
          <div className="bg-gray-50 rounded-xl p-8 text-center text-gray-500">
            <p className="text-sm">
              {searchQuery.trim()
                ? "No se encontraron comercios con ese nombre."
                : selectedCategoryId !== "all"
                  ? "No hay comercios con regla en esta categoría."
                  : createdFilter !== "all"
                    ? "No hay comercios creados en ese período."
                    : "No hay comercios registrados."}
            </p>
          </div>
        ) : (
          Object.entries(groupedByDate).map(([date, dateMerchants]) => (
            <div key={date} className="space-y-2">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-sm font-semibold text-gray-700 capitalize">
                  {date}
                </h3>
                <span className="text-xs text-gray-500">
                  {dateMerchants.length} comercio{dateMerchants.length !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="space-y-3">
                {dateMerchants.map((merchant) => (
                  <div
                    key={merchant.id}
                    className="bg-white rounded-xl p-4 shadow-sm relative"
                  >
                    <Link
                      to={`/merchants/${merchant.id}`}
                      className="block"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                          <Store className="w-6 h-6 text-gray-600" />
                        </div>
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
                    <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                      <div>
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
                      <button
                        onClick={async (e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          if (deletingId === merchant.id) {
                            // Second click = confirm
                            try {
                              await deleteMerchant(merchant.id);
                              toast.success(`${merchant.name} eliminado`);
                            } catch { toast.error("Error al eliminar"); }
                            setDeletingId(null);
                          } else {
                            setDeletingId(merchant.id);
                            setTimeout(() => setDeletingId((prev) => prev === merchant.id ? null : prev), 3000);
                          }
                        }}
                        className={`p-1.5 rounded-lg transition-colors ${
                          deletingId === merchant.id
                            ? "bg-red-100 text-red-600"
                            : "hover:bg-red-50 text-gray-400 hover:text-red-500"
                        }`}
                        title={deletingId === merchant.id ? "Click para confirmar" : "Eliminar comercio"}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
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