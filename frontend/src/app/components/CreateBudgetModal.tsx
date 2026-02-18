import { useState, useEffect } from "react";
import { X, DollarSign } from "lucide-react";
import { useData } from "../context/DataContext";
import { normalizeMesAnio } from "../../lib/api";

interface CreateBudgetModalProps {
  isOpen: boolean;
  onClose: () => void;
  mesAnio?: string;
}

export function CreateBudgetModal({ isOpen, onClose, mesAnio }: CreateBudgetModalProps) {
  const { categories, budgets, addBudget } = useData();
  const [selectedCategoryId, setSelectedCategoryId] = useState("");
  const [selectedSubcategoryId, setSelectedSubcategoryId] = useState("");
  const [amount, setAmount] = useState("");
  const [period, setPeriod] = useState<"monthly" | "weekly" | "yearly">("monthly");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const budgetsForMonth = mesAnio
    ? budgets.filter((b) => !b.mes_anio || normalizeMesAnio(b.mes_anio) === mesAnio)
    : budgets;

  const hasCategoryLevelBudget = (catId: string) =>
    budgetsForMonth.some((b) => b.categoryId === catId && !b.subcategoryId);
  const hasSubcategoryBudget = (subId: string) =>
    budgetsForMonth.some((b) => b.subcategoryId === subId);

  const selectedCategory = categories.find((c) => c.id === selectedCategoryId);
  const subcategoryOptions = selectedCategory?.subcategories ?? [];
  const availableSubcategoryOptions = [
    { id: "", name: "Toda la categoría" },
    ...subcategoryOptions.map((s) => ({ id: s.id, name: s.name })),
  ].filter(
    (opt) =>
      opt.id === "" ? !hasCategoryLevelBudget(selectedCategoryId) : !hasSubcategoryBudget(opt.id)
  );

  useEffect(() => {
    if (isOpen && selectedCategoryId && availableSubcategoryOptions.length > 0) {
      const isValid = availableSubcategoryOptions.some((o) => o.id === selectedSubcategoryId);
      if (!isValid) {
        setSelectedSubcategoryId(availableSubcategoryOptions[0].id);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, selectedCategoryId]);

  const availableCategories = categories.filter(
    (cat) =>
      !hasCategoryLevelBudget(cat.id) ||
      (cat.subcategories ?? []).some((s) => !hasSubcategoryBudget(s.id))
  );

  if (!isOpen) return null;

  const isDuplicate = () => {
    if (!selectedCategoryId) return false;
    if (selectedSubcategoryId) {
      return budgetsForMonth.some(
        (b) =>
          b.categoryId === selectedCategoryId &&
          b.subcategoryId === selectedSubcategoryId
      );
    }
    return hasCategoryLevelBudget(selectedCategoryId);
  };

  const effectiveMesAnio =
    mesAnio ||
    `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!selectedCategoryId) {
      setError("Por favor selecciona una categoría");
      return;
    }
    const amountValue = parseFloat(amount);
    if (!amount || isNaN(amountValue) || amountValue <= 0) {
      setError("Por favor ingresa un monto válido mayor a 0");
      return;
    }
    if (isDuplicate()) {
      setError("Ya existe un presupuesto para esta categoría o subcategoría");
      return;
    }
    setIsSubmitting(true);
    try {
      await addBudget({
        categoryId: selectedCategoryId,
        subcategoryId: selectedSubcategoryId || null,
        mes_anio: effectiveMesAnio,
        amount: amountValue,
        period: period,
        spent: 0,
      });
      setSelectedCategoryId("");
      setSelectedSubcategoryId("");
      setAmount("");
      setPeriod("monthly");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setSelectedCategoryId("");
    setSelectedSubcategoryId("");
    setAmount("");
    setPeriod("monthly");
    setError("");
    onClose();
  };

  const handleCategoryChange = (catId: string) => {
    setSelectedCategoryId(catId);
    setSelectedSubcategoryId("");
  };

  const selectedSubcategory = selectedCategory?.subcategories?.find(
    (s) => s.id === selectedSubcategoryId
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl">
          <h2 className="text-xl font-semibold">Nuevo Presupuesto</h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Contenido */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Vista previa */}
          {selectedCategory && (
            <div className="flex justify-center">
              <div className="text-center">
                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center text-4xl mx-auto mb-3 shadow-lg"
                  style={{ backgroundColor: `${selectedCategory.color}20` }}
                >
                  {selectedCategory.icon}
                </div>
                <p className="font-medium text-gray-700">{selectedCategory.name}</p>
                {selectedSubcategory && (
                  <p className="text-sm text-gray-500 mt-0.5">{selectedSubcategory.name}</p>
                )}
              </div>
            </div>
          )}

          {/* Selector de categoría */}
          <div>
            <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
              Categoría
            </label>
            {availableCategories.length === 0 ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                <p className="text-sm text-yellow-800">
                  ¡Todas tus categorías ya tienen presupuesto asignado!
                </p>
                <p className="text-xs text-yellow-700 mt-1">
                  Crea una nueva categoría para agregar más presupuestos.
                </p>
              </div>
            ) : (
              <select
                id="category"
                value={selectedCategoryId}
                onChange={(e) => handleCategoryChange(e.target.value)}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              >
                <option value="">Selecciona una categoría</option>
                {availableCategories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.icon} {cat.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Selector de subcategoría (opcional) */}
          {selectedCategoryId && availableSubcategoryOptions.length > 0 && (
            <div>
              <label htmlFor="subcategory" className="block text-sm font-medium text-gray-700 mb-2">
                Subcategoría (opcional)
              </label>
              <select
                id="subcategory"
                value={selectedSubcategoryId}
                onChange={(e) => setSelectedSubcategoryId(e.target.value)}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              >
                {availableSubcategoryOptions.map((opt) => (
                  <option key={opt.id || "all"} value={opt.id}>
                    {opt.id === "" ? "📂 " : "📁 "}{opt.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Monto */}
          <div>
            <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-2">
              Monto del presupuesto
            </label>
            <div className="relative">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">
                <DollarSign className="w-5 h-5" />
              </div>
              <input
                id="amount"
                type="number"
                step="0.01"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full pl-12 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-lg font-semibold"
              />
            </div>
          </div>

          {/* Período */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Período
            </label>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setPeriod("weekly")}
                className={`py-3 px-4 rounded-lg font-medium transition-all ${
                  period === "weekly"
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                Semanal
              </button>
              <button
                type="button"
                onClick={() => setPeriod("monthly")}
                className={`py-3 px-4 rounded-lg font-medium transition-all ${
                  period === "monthly"
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                Mensual
              </button>
              <button
                type="button"
                onClick={() => setPeriod("yearly")}
                className={`py-3 px-4 rounded-lg font-medium transition-all ${
                  period === "yearly"
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                Anual
              </button>
            </div>
          </div>

          {/* Información adicional */}
          {amount && parseFloat(amount) > 0 && selectedCategory && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800 font-medium mb-2">
                📊 Resumen del presupuesto
              </p>
              <div className="space-y-1 text-sm text-blue-700">
                <p>
                  <span className="font-semibold">{selectedCategory.icon}</span>{" "}
                  {selectedCategory.name}
                  {selectedSubcategory && (
                    <span className="text-blue-600"> → {selectedSubcategory.name}</span>
                  )}
                </p>
                <p>
                  <span className="font-semibold">
                    ${parseFloat(amount).toLocaleString("es-MX")}
                  </span>{" "}
                  {period === "weekly" && "por semana"}
                  {period === "monthly" && "por mes"}
                  {period === "yearly" && "por año"}
                </p>
                {period === "weekly" && (
                  <p className="text-xs">
                    ≈ ${(parseFloat(amount) * 4.33).toLocaleString("es-MX")} mensuales
                  </p>
                )}
                {period === "yearly" && (
                  <p className="text-xs">
                    ≈ ${(parseFloat(amount) / 12).toLocaleString("es-MX")} mensuales
                  </p>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Botones */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={
                availableCategories.length === 0 ||
                !selectedCategoryId ||
                availableSubcategoryOptions.length === 0 ||
                isSubmitting
              }
              className="flex-1 px-4 py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg font-medium hover:from-purple-700 hover:to-purple-800 transition-all shadow-lg shadow-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? "Creando..." : "Crear Presupuesto"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
