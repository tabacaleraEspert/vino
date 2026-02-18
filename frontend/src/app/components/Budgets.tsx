import { useState } from "react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { MonthSelector } from "./MonthSelector";
import { AlertCircle, CheckCircle2, Plus, ChevronDown, ChevronRight, Pencil } from "lucide-react";
import { CreateBudgetModal } from "./CreateBudgetModal";
import { EditBudgetModal } from "./EditBudgetModal";
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
              ${spent.toLocaleString("es-MX")} de $
              {budget.amount.toLocaleString("es-MX")}
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
              ${Math.abs(remaining).toLocaleString("es-MX")}
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
  const { budgets, categories, transactions } = useData();
  const { selectedMonth } = useMonth();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

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

  const grouped = categories
    .filter((cat) => budgetsWithSpent.some(({ budget }) => budget.categoryId === cat.id))
    .map((cat) => {
      const categoryBudgets = budgetsWithSpent.filter(
        ({ budget }) => budget.categoryId === cat.id && !budget.subcategoryId
      );
      const subcategoryBudgets = budgetsWithSpent.filter(
        ({ budget }) => budget.categoryId === cat.id && budget.subcategoryId
      );
      const catTotalAmount = budgetsWithSpent
        .filter(({ budget }) => budget.categoryId === cat.id)
        .reduce((s, { budget }) => s + budget.amount, 0);
      const catTotalSpent = budgetsWithSpent
        .filter(({ budget }) => budget.categoryId === cat.id)
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

  const hasBudgets = budgetsWithSpent.length > 0;

  return (
    <div className="p-4 space-y-4">
      <MonthSelector />
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Presupuestos Mensuales</h2>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-1 text-sm text-blue-600 font-medium"
        >
          <Plus className="w-4 h-4" />
          Nuevo
        </button>
      </div>

      {!hasBudgets ? (
        <div className="bg-white rounded-2xl p-8 shadow-sm text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Plus className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-600 font-medium mb-2">Sin presupuestos para este mes</p>
          <p className="text-sm text-gray-500 mb-6">
            No tienes presupuestos asignados para{" "}
            {new Date(selectedMonth.year, selectedMonth.month).toLocaleDateString("es-MX", {
              month: "long",
              year: "numeric",
            })}
            . Agrega uno para comenzar a controlar tus gastos.
          </p>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-5 h-5" />
            Agregar presupuesto
          </button>
        </div>
      ) : (
        <>
      {/* Resumen general */}
      <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-2xl p-6 text-white shadow-lg">
        <p className="text-sm opacity-90 mb-1">Presupuesto Total</p>
        <p className="text-3xl font-bold mb-4">
          ${totalAmount.toLocaleString("es-MX")}
        </p>
        <div className="flex items-center justify-between text-sm">
          <div>
            <p className="opacity-75">Gastado</p>
            <p className="font-semibold">
              ${totalSpent.toLocaleString("es-MX")}
            </p>
          </div>
          <div className="text-right">
            <p className="opacity-75">Disponible</p>
            <p className="font-semibold">
              ${(totalAmount - totalSpent).toLocaleString("es-MX")}
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

      {/* Lista agrupada por categoría */}
      <div className="space-y-3">
        {grouped.map(({ category, categoryBudgets, subcategoryBudgets, catTotalAmount, catTotalSpent, catPercentage, catStatus }) => {
          const hasSub = subcategoryBudgets.length > 0;
          const isExpanded = expandedCategories.has(category.id);

          return (
            <div
              key={category.id}
              className="bg-white rounded-xl shadow-sm overflow-hidden"
            >
              {/* Header de categoría */}
              <div
                className={`flex items-center gap-3 p-4 group cursor-pointer ${
                  hasSub ? "hover:bg-gray-50" : ""
                }`}
                onClick={() => hasSub && toggleExpand(category.id)}
              >
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-2xl flex-shrink-0"
                  style={{ backgroundColor: `${category.color}20` }}
                >
                  {category.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">{category.name}</p>
                  <p className="text-xs text-gray-500">
                    ${catTotalSpent.toLocaleString("es-MX")} de $
                    {catTotalAmount.toLocaleString("es-MX")}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {catStatus === "over" ? (
                    <AlertCircle className="w-5 h-5 text-red-500" />
                  ) : catStatus === "near" ? (
                    <AlertCircle className="w-5 h-5 text-yellow-500" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  )}
                  <span
                    className={`text-sm font-semibold ${
                      catStatus === "over" ? "text-red-600" : catStatus === "near" ? "text-yellow-600" : "text-green-600"
                    }`}
                  >
                    {catPercentage.toFixed(0)}%
                  </span>
                  {hasSub && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpand(category.id);
                      }}
                      className="p-1 hover:bg-gray-200 rounded transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-gray-600" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-600" />
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Progreso total categoría */}
              <div className="px-4 pb-3">
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      catStatus === "over" ? "bg-red-500" : catStatus === "near" ? "bg-yellow-500" : "bg-green-500"
                    }`}
                    style={{ width: `${Math.min(catPercentage, 100)}%` }}
                  />
                </div>
              </div>

              {/* Presupuestos de categoría (sin subcategoría) */}
              {categoryBudgets.map(({ budget, spent }) => (
                <div key={budget.id} className="px-4 pb-3">
                  <BudgetCard
                    budget={budget}
                    spent={spent}
                    isSubcategory={false}
                    onEdit={() => setEditingBudget(budget)}
                  />
                </div>
              ))}

              {/* Subcategorías expandibles */}
              {hasSub && (
                <div className="border-t border-gray-100">
                  {isExpanded && (
                    <div className="p-4 pt-2 space-y-3">
                      {subcategoryBudgets.map(({ budget, spent }) => {
                        const sub = category.subcategories?.find((s) => s.id === budget.subcategoryId);
                        return (
                          <div key={budget.id} className="pl-4 border-l-2 border-purple-200">
                            <p className="text-xs font-medium text-purple-600 mb-2">
                              {sub?.name ?? "Subcategoría"}
                            </p>
                            <BudgetCard
                              budget={budget}
                              spent={spent}
                              isSubcategory={true}
                              onEdit={() => setEditingBudget(budget)}
                            />
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

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
