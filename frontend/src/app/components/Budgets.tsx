import { useState } from "react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { MonthSelector } from "./MonthSelector";
import { AlertCircle, CheckCircle2, Plus, ChevronDown, ChevronRight, Pencil, Sparkles, Trash2 } from "lucide-react";
import { CreateBudgetModal } from "./CreateBudgetModal";
import { EditBudgetModal } from "./EditBudgetModal";
import { BudgetOnboarding } from "./BudgetOnboarding";
import { MonthSummary } from "./MonthSummary";
import { calcSpentFromTransactions, normalizeMesAnio } from "../../lib/api";
import type { Budget } from "../../lib/api";

function getStatus(percentage: number) {
  if (percentage > 100) return "over";
  if (percentage > 80) return "near";
  return "ok";
}

function BudgetCard({
  budget,
  spent,
  isSubcategory,
  onEdit,
}: {
  budget: Budget;
  spent: number;
  isSubcategory: boolean;
  onEdit: () => void;
}) {
  const percentage = budget.amount > 0 ? (spent / budget.amount) * 100 : 0;
  const remaining = budget.amount - spent;
  const status = getStatus(percentage);

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm space-y-3 group">
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="font-medium text-gray-800">
              ${spent.toLocaleString("es-AR")} de $
              {budget.amount.toLocaleString("es-AR")}
            </p>
            <button
              onClick={onEdit}
              className={`p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${
                isSubcategory
                  ? "hover:bg-purple-100 text-purple-600"
                  : "hover:bg-blue-100 text-blue-600"
              }`}
            >
              <Pencil className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-gray-500">
            {remaining >= 0 ? "Disponible" : "Excedido"}{" "}
            <span
              className={remaining >= 0 ? "text-gray-700 font-medium" : "text-red-600 font-medium"}
            >
              ${Math.abs(remaining).toLocaleString("es-AR")}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {status === "over" ? (
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          ) : status === "near" ? (
            <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
          )}
          <span
            className={`text-sm font-semibold ${
              status === "over"
                ? "text-red-600"
                : status === "near"
                ? "text-yellow-600"
                : "text-green-600"
            }`}
          >
            {percentage.toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            status === "over" ? "bg-red-500" : status === "near" ? "bg-yellow-500" : "bg-green-500"
          }`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}

export function Budgets() {
  const { budgets, categories, transactions, deleteBudget } = useData();
  const { selectedMonth } = useMonth();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editingTotal, setEditingTotal] = useState(false);
  const [newTotal, setNewTotal] = useState("");

  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;
  const budgetsForMonth = budgets.filter((b) => {
    if (!b.mes_anio) return false;
    return normalizeMesAnio(b.mes_anio) === period;
  });

  const budgetsWithSpent = budgetsForMonth
    .filter((b) => b.amount > 0)
    .map((b) => ({
      budget: b,
      spent: calcSpentFromTransactions(b, transactions, selectedMonth),
    }));

  // Debug: log IDs to find mismatch
  if (budgetsWithSpent.length > 0 && categories.length > 0) {
    console.log("[Budgets] budgetCategoryIds:", budgetsWithSpent.map(b => ({ id: b.budget.categoryId, type: typeof b.budget.categoryId })));
    console.log("[Budgets] categoriesIds:", categories.map(c => ({ id: c.id, type: typeof c.id, name: c.name })));
  }

  const grouped = categories
    .filter((cat) => budgetsWithSpent.some(({ budget }) => String(budget.categoryId) === String(cat.id)))
    .map((cat) => {
      const categoryBudgets = budgetsWithSpent.filter(
        ({ budget }) => String(budget.categoryId) === String(cat.id) && !budget.subcategoryId
      );
      const subcategoryBudgets = budgetsWithSpent.filter(
        ({ budget }) => String(budget.categoryId) === String(cat.id) && budget.subcategoryId
      );
      const catTotalAmount = budgetsWithSpent
        .filter(({ budget }) => String(budget.categoryId) === String(cat.id))
        .reduce((s, { budget }) => s + budget.amount, 0);
      const catTotalSpent = budgetsWithSpent
        .filter(({ budget }) => String(budget.categoryId) === String(cat.id))
        .reduce((s, { spent }) => s + spent, 0);
      const catPercentage = catTotalAmount > 0 ? (catTotalSpent / catTotalAmount) * 100 : 0;
      const catStatus = getStatus(catPercentage);

      return {
        category: cat,
        categoryBudgets,
        subcategoryBudgets,
        catTotalAmount,
        catTotalSpent,
        catPercentage,
        catStatus,
      };
    });

  const totalAmount = budgetsWithSpent.reduce((s, { budget }) => s + budget.amount, 0);
  const totalSpent = budgetsWithSpent.reduce((s, { spent }) => s + spent, 0);
  const totalPercentage = totalAmount > 0 ? (totalSpent / totalAmount) * 100 : 0;
  const totalStatus = getStatus(totalPercentage);

  const toggleExpand = (catId: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(catId)) next.delete(catId);
      else next.add(catId);
      return next;
    });
  };

  const handleDeleteAll = async () => {
    setIsDeleting(true);
    try {
      for (const { budget } of budgetsWithSpent) {
        await deleteBudget(budget.id);
      }
      setConfirmDeleteAll(false);
    } catch (e) {
      console.error("Delete all failed:", e);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleEditTotal = () => {
    setNewTotal(String(totalAmount));
    setEditingTotal(true);
  };

  const handleSaveTotal = async () => {
    const parsed = parseInt(newTotal.replace(/[^\d]/g, ""), 10);
    if (!parsed || parsed <= 0) return;
    const ratio = parsed / totalAmount;
    // Redistribute proportionally
    for (const { budget } of budgetsWithSpent) {
      const newAmount = Math.round(budget.amount * ratio);
      await updateBudget(budget.id, { amount: newAmount });
    }
    setEditingTotal(false);
  };

  const hasBudgets = budgetsWithSpent.length > 0;

  return (
    <div className="p-4 space-y-4">
      <MonthSelector />
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Presupuestos Mensuales</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsOnboardingOpen(true)}
            className="flex items-center gap-1 text-sm text-purple-600 font-medium"
          >
            <Sparkles className="w-4 h-4" />
            50/30/20
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-1 text-sm text-blue-600 font-medium"
          >
            <Plus className="w-4 h-4" />
            Nuevo
          </button>
        </div>
      </div>

      {!hasBudgets ? (
        <div className="bg-white rounded-2xl p-8 shadow-sm text-center">
          <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-purple-500" />
          </div>
          <p className="text-gray-600 font-medium mb-2">Sin presupuestos para este mes</p>
          <p className="text-sm text-gray-500 mb-6">
            Configura tus presupuestos para controlar cuánto gastás en cada categoría.
            Podés hacerlo manualmente o dejar que te ayudemos con la regla 50/30/20.
          </p>
          <button
            onClick={() => setIsOnboardingOpen(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white font-medium rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all"
          >
            <Sparkles className="w-5 h-5" />
            Configurar presupuestos
          </button>
        </div>
      ) : (
        <>
      {/* Resumen general */}
      <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-2xl p-6 text-white shadow-lg relative">
        <button
          onClick={() => setConfirmDeleteAll(true)}
          className="absolute top-3 right-3 p-2 hover:bg-white/20 rounded-lg transition-colors"
          title="Eliminar todos los presupuestos del mes"
        >
          <Trash2 className="w-4 h-4" />
        </button>
        <p className="text-sm opacity-90 mb-1">Presupuesto Total</p>
        {editingTotal ? (
          <div className="flex items-center gap-2 mb-4">
            <span className="text-3xl font-bold">$</span>
            <input
              autoFocus
              type="text"
              inputMode="numeric"
              value={parseInt(newTotal.replace(/[^\d]/g, "") || "0", 10).toLocaleString("es-AR")}
              onChange={(e) => setNewTotal(e.target.value.replace(/[^\d]/g, ""))}
              onKeyDown={(e) => e.key === "Enter" && handleSaveTotal()}
              className="text-3xl font-bold bg-white/20 border-b-2 border-white rounded-lg px-2 py-1 outline-none w-48 text-white placeholder:text-white/50"
            />
            <button onClick={handleSaveTotal} className="p-2 bg-white/20 rounded-lg hover:bg-white/30">
              <CheckCircle2 className="w-5 h-5" />
            </button>
          </div>
        ) : (
          <button onClick={handleEditTotal} className="text-3xl font-bold mb-4 flex items-center gap-2 hover:opacity-80 transition-opacity">
            ${totalAmount.toLocaleString("es-AR")}
            <Pencil className="w-4 h-4 opacity-60" />
          </button>
        )}
        <div className="flex items-center justify-between text-sm">
          <div>
            <p className="opacity-75">Gastado</p>
            <p className="font-semibold">
              ${totalSpent.toLocaleString("es-AR")}
            </p>
          </div>
          <div className="text-right">
            <p className="opacity-75">Disponible</p>
            <p className="font-semibold">
              ${(totalAmount - totalSpent).toLocaleString("es-AR")}
            </p>
          </div>
        </div>
        <div className="mt-3 h-2 bg-white/20 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${
              totalStatus === "over" ? "bg-red-400" : totalStatus === "near" ? "bg-yellow-400" : "bg-green-400"
            }`}
            style={{ width: `${Math.min(totalPercentage, 100)}%` }}
          />
        </div>
      </div>

      {/* Desglose por categoría — agrupado por bucket */}
      {[
        { key: "necesidades", label: "Necesidades", pct: "50%" },
        { key: "estilo_vida", label: "Estilo de vida", pct: "30%" },
        { key: "", label: "Otras", pct: "" },
      ].map((bucket) => {
        const bucketGroups = grouped.filter(({ category }) =>
          bucket.key ? category.bucket === bucket.key : !category.bucket || !["necesidades", "estilo_vida", "futuro"].includes(category.bucket)
        );
        if (bucketGroups.length === 0) return null;
        return (
      <div key={bucket.key} className="bg-white rounded-xl shadow-sm p-4">
        <div className="flex items-center gap-2 mb-4">
          <h3 className="font-medium text-gray-800">{bucket.label}</h3>
          {bucket.pct && (
            <span className="text-[10px] font-bold bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">{bucket.pct}</span>
          )}
        </div>
        <div className="space-y-4">
          {bucketGroups.map(({ category, categoryBudgets, subcategoryBudgets, catTotalAmount, catTotalSpent, catPercentage, catStatus }) => {
            const remaining = catTotalAmount - catTotalSpent;
            return (
              <div key={category.id} className="space-y-1.5">
                <div className="flex items-center gap-3">
                  <div className="text-2xl flex-shrink-0">{category.icon}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-800">{category.name}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">{catPercentage.toFixed(0)}%</span>
                        <span className="text-sm font-semibold text-gray-900">
                          ${catTotalSpent.toLocaleString("es-AR")}
                          <span className="text-xs font-normal text-gray-400"> / ${catTotalAmount.toLocaleString("es-AR")}</span>
                        </span>
                        {categoryBudgets.length > 0 && (
                          <button
                            onClick={() => setEditingBudget(categoryBudgets[0].budget)}
                            className="p-1 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden mt-1">
                      <div
                        className={`h-full rounded-full transition-all ${
                          catStatus === "over" ? "bg-red-500" : catStatus === "near" ? "bg-yellow-500" : "bg-green-500"
                        }`}
                        style={{ width: `${Math.min(catPercentage, 100)}%` }}
                      />
                    </div>
                    <p className={`text-xs mt-0.5 ${remaining >= 0 ? "text-gray-400" : "text-red-500"}`}>
                      {remaining >= 0 ? `Quedan $${remaining.toLocaleString("es-AR")}` : `Excedido por $${Math.abs(remaining).toLocaleString("es-AR")}`}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
        );
      })}

      {/* Botón para agregar presupuesto */}
      <button
        onClick={() => setIsCreateOpen(true)}
        className="w-full py-4 bg-white rounded-xl shadow-sm text-blue-600 font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
      >
        <Plus className="w-5 h-5" />
        Crear Nuevo Presupuesto
      </button>
        </>
      )}

      {/* Confirm delete all */}
      {confirmDeleteAll && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl space-y-4">
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6 text-red-600" />
            </div>
            <div className="text-center">
              <h3 className="font-semibold text-lg">Eliminar presupuestos</h3>
              <p className="text-sm text-gray-500 mt-1">
                Se van a eliminar los {budgetsWithSpent.length} presupuestos de este mes. Esta accion no se puede deshacer.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDeleteAll(false)}
                className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleDeleteAll}
                disabled={isDeleting}
                className="flex-1 py-2.5 bg-red-600 text-white rounded-xl text-sm font-medium hover:bg-red-700 disabled:opacity-50 flex items-center justify-center gap-1"
              >
                {isDeleting ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Eliminar todos
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <MonthSummary />
      <BudgetOnboarding
        isOpen={isOnboardingOpen}
        onClose={() => setIsOnboardingOpen(false)}
        mesAnio={period}
      />
      <CreateBudgetModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        mesAnio={period}
      />
      <EditBudgetModal
        isOpen={!!editingBudget}
        onClose={() => setEditingBudget(null)}
        budget={editingBudget}
      />
    </div>
  );
}
