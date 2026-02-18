import { useState } from "react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { MonthSelector } from "./MonthSelector";
import { EditTransactionModal } from "./EditTransactionModal";
import { Search, Filter, X, Calendar, DollarSign, Store, Edit2 } from "lucide-react";
import type { Transaction } from "../../lib/api";

export function Transactions() {
  const { categories, merchants, transactions } = useData();
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const { selectedMonth } = useMonth();

  const transactionsInMonth = transactions.filter((t) => {
    const d = new Date(t.date);
    return d.getMonth() === selectedMonth.month && d.getFullYear() === selectedMonth.year;
  });
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  
  // Filtros avanzados
  const [selectedMerchant, setSelectedMerchant] = useState<string>("all");
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [amountMin, setAmountMin] = useState("");
  const [amountMax, setAmountMax] = useState("");

  const filteredTransactions = transactionsInMonth.filter((t) => {
    // Filtro de búsqueda
    const matchesSearch = t.description
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    
    // Filtro de categoría
    const matchesCategory =
      selectedCategory === "all" || t.categoryId === selectedCategory;
    
    // Filtro de comercio
    const matchesMerchant =
      selectedMerchant === "all" || t.merchantId === selectedMerchant;
    
    // Filtro de subcategoría
    const matchesSubcategory =
      selectedSubcategory === "all" || t.subcategoryId === selectedSubcategory;
    
    // Filtro de fecha desde
    const matchesDateFrom = !dateFrom || t.date >= dateFrom;
    
    // Filtro de fecha hasta
    const matchesDateTo = !dateTo || t.date <= dateTo;
    
    // Filtro de monto mínimo
    const matchesAmountMin =
      !amountMin || Math.abs(t.amount) >= parseFloat(amountMin);
    
    // Filtro de monto máximo
    const matchesAmountMax =
      !amountMax || Math.abs(t.amount) <= parseFloat(amountMax);

    return (
      matchesSearch &&
      matchesCategory &&
      matchesMerchant &&
      matchesSubcategory &&
      matchesDateFrom &&
      matchesDateTo &&
      matchesAmountMin &&
      matchesAmountMax
    );
  });

  // Obtener subcategorías disponibles según la categoría seleccionada
  const availableSubcategories =
    selectedCategory === "all"
      ? []
      : categories.find((c) => c.id === selectedCategory)?.subcategories || [];

  const hasActiveFilters =
    selectedMerchant !== "all" ||
    selectedSubcategory !== "all" ||
    dateFrom ||
    dateTo ||
    amountMin ||
    amountMax;

  const clearAllFilters = () => {
    setSearchTerm("");
    setSelectedCategory("all");
    setSelectedMerchant("all");
    setSelectedSubcategory("all");
    setDateFrom("");
    setDateTo("");
    setAmountMin("");
    setAmountMax("");
  };

  const groupedByDate = filteredTransactions.reduce((acc, t) => {
    const date = new Date(t.date).toLocaleDateString("es-MX", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    if (!acc[date]) acc[date] = [];
    acc[date].push(t);
    return acc;
  }, {} as Record<string, typeof transactions>);

  return (
    <div className="p-4 space-y-4">
      <MonthSelector />
      {/* Búsqueda */}
      <div className="bg-white rounded-xl p-3 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex-1 flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar transacciones..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 bg-transparent outline-none text-sm"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <button
            onClick={() => setShowAdvancedFilters(true)}
            className={`p-2 rounded-lg transition-colors relative ${
              hasActiveFilters
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            <Filter className="w-4 h-4" />
            {hasActiveFilters && (
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full border-2 border-white" />
            )}
          </button>
        </div>

        {/* Filtro por categoría */}
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-3 px-3 scrollbar-hide">
          <button
            onClick={() => {
              setSelectedCategory("all");
              setSelectedSubcategory("all");
            }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              selectedCategory === "all"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            Todas
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => {
                setSelectedCategory(cat.id);
                setSelectedSubcategory("all");
              }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {cat.icon} {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Indicador de filtros activos */}
      {hasActiveFilters && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-blue-600" />
            <span className="text-sm text-blue-800 font-medium">
              Filtros activos aplicados
            </span>
          </div>
          <button
            onClick={clearAllFilters}
            className="text-xs text-blue-600 font-medium hover:text-blue-700"
          >
            Limpiar todo
          </button>
        </div>
      )}

      {/* Resultados */}
      {filteredTransactions.length === 0 ? (
        <div className="bg-white rounded-xl p-8 text-center shadow-sm">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <Search className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-600 font-medium mb-1">No hay resultados</p>
          <p className="text-sm text-gray-500">
            Intenta ajustar los filtros de búsqueda
          </p>
        </div>
      ) : (
        <div className="flex items-center justify-between px-1">
          <p className="text-sm text-gray-600">
            {filteredTransactions.length} transacción
            {filteredTransactions.length !== 1 ? "es" : ""}
          </p>
          <p className="text-sm font-semibold text-gray-900">
            Total: $
            {filteredTransactions
              .reduce((sum, t) => sum + Math.abs(t.amount), 0)
              .toLocaleString("es-MX")}
          </p>
        </div>
      )}

      {/* Lista de transacciones agrupadas */}
      {filteredTransactions.length > 0 && (
        <div className="space-y-4">
          {Object.entries(groupedByDate).map(([date, dateTransactions]) => {
            const dayTotal = dateTransactions.reduce(
              (sum, t) => sum + Math.abs(t.amount),
              0
            );

            return (
              <div key={date} className="space-y-2">
                <div className="flex items-center justify-between px-1">
                  <h3 className="text-sm font-semibold text-gray-700 capitalize">
                    {date}
                  </h3>
                  <span className="text-sm font-semibold text-gray-900">
                    ${dayTotal.toLocaleString("es-MX")}
                  </span>
                </div>

                <div className="bg-white rounded-xl overflow-hidden shadow-sm">
                  {dateTransactions.map((transaction, idx) => {
                    const category = categories.find(
                      (c) => c.id === transaction.categoryId
                    );
                    const merchant = merchants.find(
                      (m) => m.id === transaction.merchantId
                    );
                    const subcategory = category?.subcategories?.find(
                      (s) => s.id === transaction.subcategoryId
                    );

                    return (
                      <div
                        key={transaction.id}
                        className={`flex items-center gap-3 p-4 ${
                          idx !== dateTransactions.length - 1
                            ? "border-b border-gray-100"
                            : ""
                        }`}
                      >
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
                          style={{ backgroundColor: `${category?.color}20` }}
                        >
                          {category?.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">
                            {merchant?.name || transaction.description}
                          </p>
                          <p className="text-xs text-gray-500 truncate">
                            {[
                              transaction.descripcion?.trim() || null,
                              subcategory?.name,
                            ]
                              .filter(Boolean)
                              .join(" • ")}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-red-600">
                            -${Math.abs(transaction.amount).toLocaleString("es-MX")}
                          </p>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setEditingTransaction(transaction);
                            }}
                            className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-blue-600 transition-colors"
                            aria-label="Editar transacción"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal Editar Transacción */}
      <EditTransactionModal
        show={!!editingTransaction}
        transaction={editingTransaction}
        onClose={() => setEditingTransaction(null)}
      />

      {/* Modal de Filtros Avanzados */}
      {showAdvancedFilters && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up max-h-[85vh] overflow-y-auto">
            {/* Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl">
              <h2 className="text-xl font-semibold">Filtros Avanzados</h2>
              <button
                onClick={() => setShowAdvancedFilters(false)}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-gray-600" />
              </button>
            </div>

            {/* Contenido */}
            <div className="p-6 space-y-6">
              {/* Filtro por comercio */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <Store className="w-4 h-4" />
                  Comercio
                </label>
                <select
                  value={selectedMerchant}
                  onChange={(e) => setSelectedMerchant(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                >
                  <option value="all">Todos los comercios</option>
                  {merchants.map((merchant) => (
                    <option key={merchant.id} value={merchant.id}>
                      {merchant.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Filtro por subcategoría */}
              {selectedCategory !== "all" && availableSubcategories.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Subcategoría
                  </label>
                  <select
                    value={selectedSubcategory}
                    onChange={(e) => setSelectedSubcategory(e.target.value)}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  >
                    <option value="all">Todas las subcategorías</option>
                    {availableSubcategories.map((sub) => (
                      <option key={sub.id} value={sub.id}>
                        {sub.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Filtros de fecha */}
              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <Calendar className="w-4 h-4" />
                  Rango de Fechas
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Desde</label>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => setDateFrom(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Hasta</label>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => setDateTo(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Filtros de monto */}
              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <DollarSign className="w-4 h-4" />
                  Rango de Monto
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Mínimo</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={amountMin}
                      onChange={(e) => setAmountMin(e.target.value)}
                      placeholder="0.00"
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Máximo</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={amountMax}
                      onChange={(e) => setAmountMax(e.target.value)}
                      placeholder="0.00"
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Botones */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => {
                    setSelectedMerchant("all");
                    setSelectedSubcategory("all");
                    setDateFrom("");
                    setDateTo("");
                    setAmountMin("");
                    setAmountMax("");
                  }}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
                >
                  Limpiar
                </button>
                <button
                  onClick={() => setShowAdvancedFilters(false)}
                  className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                >
                  Aplicar Filtros
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}