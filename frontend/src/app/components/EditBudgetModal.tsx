import { useState, useEffect } from "react";
import { X, DollarSign, Trash2, AlertTriangle } from "lucide-react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { calcSpentFromTransactions } from "../../lib/api";
import type { Budget } from "../../lib/api";

interface EditBudgetModalProps {
  isOpen: boolean;
  onClose: () => void;
  budget: Budget | null;
}

export function EditBudgetModal({ isOpen, onClose, budget }: EditBudgetModalProps) {
  const { categories, transactions, updateBudget, deleteBudget } = useData();
  const { selectedMonth } = useMonth();
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (isOpen && budget) {
      setAmount(String(budget.amount));
      setError("");
      setShowDeleteConfirm(false);
    }
  }, [isOpen, budget]);

  if (!isOpen) return null;
  if (!budget) return null;

  const category = categories.find((c) => c.id === budget.categoryId);
  const subcategory = budget.subcategoryId
    ? category?.subcategories?.find((s) => s.id === budget.subcategoryId)
    : null;
  const spent = calcSpentFromTransactions(budget, transactions, selectedMonth);
  const percentage = budget.amount > 0 ? (spent / budget.amount) * 100 : 0;
  const remaining = budget.amount - spent;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const amountValue = parseFloat(amount);
    if (!amount || isNaN(amountValue) || amountValue <= 0) {
      setError("Ingresa un monto válido mayor a 0");
      return;
    }
    setIsSubmitting(true);
    try {
      await updateBudget(budget.id, { amount: amountValue });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      return;
    }
    setIsDeleting(true);
    try {
      await deleteBudget(budget.id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleClose = () => {
    setError("");
    setShowDeleteConfirm(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl">
          <h2 className="text-xl font-semibold">Editar Presupuesto</h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Vista previa categoría/subcategoría */}
          {category && (
            <div className="flex justify-center">
              <div className="text-center">
                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center text-4xl mx-auto mb-3 shadow-lg"
                  style={{ backgroundColor: `${category.color}20` }}
                >
                  {category.icon}
                </div>
                <p className="font-medium text-gray-700">{category.name}</p>
                {subcategory && (
                  <p className="text-sm text-gray-500 mt-0.5">{subcategory.name}</p>
                )}
              </div>
            </div>
          )}

          {/* Gasto actual y porcentaje */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Gastado este mes</span>
              <span className="font-semibold">
                ${spent.toLocaleString("es-MX")}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Porcentaje</span>
              <span
                className={`font-semibold ${
                  percentage > 100
                    ? "text-red-600"
                    : percentage > 80
                    ? "text-yellow-600"
                    : "text-green-600"
                }`}
              >
                {percentage.toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">
                {remaining >= 0 ? "Disponible" : "Excedido"}
              </span>
              <span
                className={`font-semibold ${
                  remaining >= 0 ? "text-gray-700" : "text-red-600"
                }`}
              >
                ${Math.abs(remaining).toLocaleString("es-MX")}
              </span>
            </div>
          </div>

          {/* Monto */}
          <div>
            <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-2">
              Nuevo monto del presupuesto
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

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Botones */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg font-medium hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg shadow-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? "Guardando..." : "Guardar"}
            </button>
          </div>

          {/* Eliminar */}
          <div className="pt-4 border-t border-gray-200">
            {showDeleteConfirm ? (
              <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
                <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <p className="text-sm text-red-700 flex-1">
                  ¿Eliminar este presupuesto? Esta acción no se puede deshacer.
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowDeleteConfirm(false)}
                    className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={isDeleting}
                    className="px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
                  >
                    {isDeleting ? "Eliminando..." : "Sí, eliminar"}
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={handleDelete}
                className="flex items-center justify-center gap-2 w-full py-3 text-red-600 font-medium hover:bg-red-50 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Eliminar presupuesto
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
