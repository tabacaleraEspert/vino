import { useState, useEffect } from "react";
import { X, TrendingUp, TrendingDown, Award, AlertTriangle, Target, ArrowRight } from "lucide-react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { calcSpentFromTransactions, normalizeMesAnio } from "../../lib/api";
import type { Budget } from "../../lib/api";

const DISMISSED_KEY = "vino_month_summary_dismissed";

function getPreviousMonth(): { month: number; year: number; period: string } {
  const now = new Date();
  const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return {
    month: prev.getMonth(),
    year: prev.getFullYear(),
    period: `${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, "0")}`,
  };
}

interface CategoryResult {
  name: string;
  budgeted: number;
  spent: number;
  pct: number;
  status: "under" | "on-track" | "over";
}

export function MonthSummary() {
  const { budgets, transactions, categories } = useData();
  const { selectedMonth } = useMonth();
  const [isOpen, setIsOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const prev = getPreviousMonth();
  const currentPeriod = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;

  // Show only if we're in the current month and haven't dismissed
  useEffect(() => {
    const now = new Date();
    const isCurrentMonth =
      selectedMonth.year === now.getFullYear() && selectedMonth.month === now.getMonth();
    const dayOfMonth = now.getDate();

    // Show in the first 5 days of the month
    if (!isCurrentMonth || dayOfMonth > 5) return;

    const dismissedMonths = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");
    if (dismissedMonths.includes(prev.period)) return;

    // Only show if there were budgets last month
    const prevBudgets = budgets.filter(
      (b) => b.mes_anio && normalizeMesAnio(b.mes_anio) === prev.period
    );
    if (prevBudgets.length === 0) return;

    setIsOpen(true);
  }, [budgets, selectedMonth]);

  const handleDismiss = () => {
    setIsOpen(false);
    setDismissed(true);
    const dismissedMonths = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");
    if (!dismissedMonths.includes(prev.period)) {
      dismissedMonths.push(prev.period);
      // Keep only last 6 months
      while (dismissedMonths.length > 6) dismissedMonths.shift();
      localStorage.setItem(DISMISSED_KEY, JSON.stringify(dismissedMonths));
    }
  };

  if (!isOpen || dismissed) return null;

  // Calculate last month's results
  const prevMonth = { month: prev.month, year: prev.year };
  const prevBudgets = budgets.filter(
    (b) => b.mes_anio && normalizeMesAnio(b.mes_anio) === prev.period && b.amount > 0
  );

  const results: CategoryResult[] = prevBudgets.map((b) => {
    const spent = calcSpentFromTransactions(b, transactions, prevMonth);
    const pct = b.amount > 0 ? (spent / b.amount) * 100 : 0;
    const cat = categories.find((c) => c.id === b.categoryId);
    return {
      name: cat?.name || "Sin categoria",
      budgeted: b.amount,
      spent,
      pct,
      status: pct > 100 ? "over" : pct > 80 ? "on-track" : "under",
    };
  });

  const totalBudgeted = results.reduce((s, r) => s + r.budgeted, 0);
  const totalSpent = results.reduce((s, r) => s + r.spent, 0);
  const totalPct = totalBudgeted > 0 ? (totalSpent / totalBudgeted) * 100 : 0;
  const overCount = results.filter((r) => r.status === "over").length;
  const underCount = results.filter((r) => r.status === "under").length;

  const monthLabel = new Date(prev.year, prev.month).toLocaleDateString("es-AR", {
    month: "long",
    year: "numeric",
  });

  // Score: simple grade based on how many categories stayed under budget
  const score = results.length > 0 ? Math.round((underCount / results.length) * 100) : 0;
  const grade = score >= 80 ? "A" : score >= 60 ? "B" : score >= 40 ? "C" : "D";
  const gradeColor =
    grade === "A" ? "from-green-400 to-green-500" :
    grade === "B" ? "from-blue-400 to-blue-500" :
    grade === "C" ? "from-yellow-400 to-yellow-500" :
    "from-red-400 to-red-500";
  const gradeMessage =
    grade === "A" ? "Excelente! Controlaste muy bien tus gastos" :
    grade === "B" ? "Bien! La mayoria de categorias estuvieron en rango" :
    grade === "C" ? "Regular. Algunas categorias se pasaron" :
    "Hay que mejorar. Varias categorias se excedieron";

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-md rounded-2xl max-h-[85vh] overflow-y-auto shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="relative bg-gradient-to-br from-indigo-600 to-purple-700 p-6 rounded-t-2xl text-white text-center">
          <button
            onClick={handleDismiss}
            className="absolute top-4 right-4 p-1.5 hover:bg-white/20 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <p className="text-sm opacity-80 mb-1">Resumen de</p>
          <h3 className="text-xl font-bold capitalize mb-4">{monthLabel}</h3>

          {/* Grade */}
          <div className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${gradeColor} flex items-center justify-center mx-auto shadow-lg mb-3`}>
            <span className="text-4xl font-black text-white">{grade}</span>
          </div>
          <p className="text-sm opacity-90">{gradeMessage}</p>
        </div>

        <div className="p-5 space-y-4">
          {/* Totals */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className="text-xs text-gray-500">Presupuestado</p>
              <p className="text-lg font-bold text-gray-800">${totalBudgeted.toLocaleString("es-AR")}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className="text-xs text-gray-500">Gastado</p>
              <p className={`text-lg font-bold ${totalPct > 100 ? "text-red-600" : "text-gray-800"}`}>
                ${totalSpent.toLocaleString("es-AR")}
              </p>
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center justify-center gap-6 py-2">
            <div className="flex items-center gap-1.5">
              <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                <TrendingDown className="w-3.5 h-3.5 text-green-600" />
              </div>
              <span className="text-sm text-gray-600">{underCount} bajo presup.</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center">
                <TrendingUp className="w-3.5 h-3.5 text-red-600" />
              </div>
              <span className="text-sm text-gray-600">{overCount} excedidas</span>
            </div>
          </div>

          {/* Per category */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-500 uppercase">Por categoria</p>
            {results
              .sort((a, b) => b.pct - a.pct)
              .map((r, i) => (
                <div key={i} className="flex items-center gap-3 py-1.5">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700 truncate">{r.name}</span>
                      <span
                        className={`text-xs font-semibold ${
                          r.status === "over" ? "text-red-600" : r.status === "on-track" ? "text-yellow-600" : "text-green-600"
                        }`}
                      >
                        {r.pct.toFixed(0)}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          r.status === "over" ? "bg-red-500" : r.status === "on-track" ? "bg-yellow-500" : "bg-green-500"
                        }`}
                        style={{ width: `${Math.min(r.pct, 100)}%` }}
                      />
                    </div>
                  </div>
                  {r.status === "over" ? (
                    <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                  ) : r.status === "under" ? (
                    <Award className="w-4 h-4 text-green-400 flex-shrink-0" />
                  ) : (
                    <Target className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                  )}
                </div>
              ))}
          </div>

          {/* CTA */}
          <button
            onClick={handleDismiss}
            className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-medium rounded-xl hover:from-indigo-700 hover:to-purple-700 transition-all flex items-center justify-center gap-2"
          >
            Seguir al nuevo mes
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
