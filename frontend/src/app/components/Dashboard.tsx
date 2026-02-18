import { useState, useEffect, useCallback } from "react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { useAuth } from "../context/AuthContext";
import { MonthSelector } from "./MonthSelector";
import { api } from "../../lib/api";
import { TrendingDown, TrendingUp, Receipt, RefreshCw } from "lucide-react";

const summaryCache: Record<string, { gasto_mes: number; presupuesto_mes: number }> = {};
const breakdownCache: Record<
  string,
  {
    gastos_por_categoria: Array<{ categoria: string; total: number; pct: number }>;
    transacciones_recientes: Array<{
      id: string;
      fecha: string;
      titulo: string;
      descripcion: string;
      monto: number;
      categoria: string;
    }>;
    mayor_gasto: number;
    transacciones_count: number;
  }
> = {};

export function Dashboard() {
  const { categories, budgets } = useData();
  const { selectedMonth } = useMonth();
  const { token } = useAuth();
  const [summary, setSummary] = useState<{ gasto_mes: number; presupuesto_mes: number } | null>(null);
  const [breakdown, setBreakdown] = useState<{
    gastos_por_categoria: Array<{ categoria: string; total: number; pct: number }>;
    transacciones_recientes: Array<{ id: string; fecha: string; titulo: string; descripcion: string; monto: number; categoria: string }>;
    mayor_gasto: number;
    transacciones_count: number;
  } | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);
  const [isLoadingBreakdown, setIsLoadingBreakdown] = useState(false);

  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;

  const fetchSummary = useCallback(async () => {
    if (!token) return;
    setIsLoadingSummary(true);
    try {
      const res = await api.views.homeSummary(
        { period, moneda: "ARS" },
        token
      );
      const data = { gasto_mes: res.gasto_mes, presupuesto_mes: res.presupuesto_mes };
      summaryCache[period] = data;
      setSummary(data);
    } catch {
      setSummary(null);
    } finally {
      setIsLoadingSummary(false);
    }
  }, [period, token]);

  const fetchBreakdown = useCallback(async () => {
    if (!token) return;
    setIsLoadingBreakdown(true);
    try {
      const res = await api.views.homeBreakdown(
        { period, currency: "ARS", top_categories: 6, recent_limit: 5 },
        token
      );
      const data = {
        gastos_por_categoria: res.gastos_por_categoria,
        transacciones_recientes: res.transacciones_recientes,
        mayor_gasto: res.mayor_gasto,
        transacciones_count: res.transacciones_count,
      };
      breakdownCache[period] = data;
      setBreakdown(data);
    } catch {
      setBreakdown(null);
    } finally {
      setIsLoadingBreakdown(false);
    }
  }, [period, token]);

  const fetchAll = useCallback(() => {
    fetchSummary();
    fetchBreakdown();
  }, [fetchSummary, fetchBreakdown]);

  useEffect(() => {
    if (!token) {
      setSummary(null);
      setBreakdown(null);
      setIsLoadingSummary(false);
      setIsLoadingBreakdown(false);
      return;
    }
    if (summaryCache[period]) {
      setSummary(summaryCache[period]);
    } else {
      fetchSummary();
    }
    if (breakdownCache[period]) {
      setBreakdown(breakdownCache[period]);
    } else {
      fetchBreakdown();
    }
  }, [period, token, fetchSummary, fetchBreakdown]);

  useEffect(() => {
    Object.keys(summaryCache).forEach((k) => delete summaryCache[k]);
    Object.keys(breakdownCache).forEach((k) => delete breakdownCache[k]);
  }, [token]);

  const monthSpent = summary?.gasto_mes ?? 0;
  const totalBudget = summary?.presupuesto_mes ?? budgets.reduce((sum, b) => sum + b.amount, 0);
  const percentageUsed = totalBudget > 0 ? (monthSpent / totalBudget) * 100 : 0;

  const spendingByCategory = (breakdown?.gastos_por_categoria ?? []).slice(0, 4).map((g) => {
    const cat = categories.find((c) => c.name.toLowerCase() === g.categoria.toLowerCase());
    return { ...g, ...cat, amount: g.total };
  });

  const recentTransactions = breakdown?.transacciones_recientes ?? [];

  const getCardGradient = (pct: number) => {
    if (pct <= 40) return "from-green-600 to-green-700";
    if (pct <= 80) return "from-blue-600 to-blue-700";
    return "from-red-600 to-red-700";
  };

  return (
    <div className="p-4 space-y-4 relative">
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <MonthSelector />
        </div>
        <button
          onClick={fetchAll}
          disabled={isLoadingSummary || isLoadingBreakdown}
          className="p-2.5 rounded-xl bg-white shadow-sm text-gray-600 hover:bg-gray-50 hover:text-blue-600 transition-colors disabled:opacity-50"
          title="Actualizar"
        >
          <RefreshCw className={`w-5 h-5 ${(isLoadingSummary || isLoadingBreakdown) ? "animate-spin" : ""}`} />
        </button>
      </div>
      {(isLoadingSummary || isLoadingBreakdown) && (
        <div className="absolute inset-0 top-14 left-0 right-0 bottom-0 flex items-start justify-center pt-8 bg-gray-50/80 backdrop-blur-sm z-10 rounded-2xl">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-600 font-medium">Cargando datos del mes...</p>
          </div>
        </div>
      )}
      {/* Resumen total */}
      <div
        className={`bg-gradient-to-br ${getCardGradient(percentageUsed)} rounded-2xl p-6 text-white shadow-lg transition-colors duration-500`}
      >
        <p className="text-sm opacity-90 mb-1">Balance del mes</p>
        <p className="text-3xl font-bold mb-4">
          ${monthSpent.toLocaleString("es-MX", { minimumFractionDigits: 2 })}
        </p>
        <div className="flex items-center justify-between text-sm">
          <div>
            <p className="opacity-75">Presupuesto</p>
            <p className="font-semibold">${totalBudget.toLocaleString("es-MX")}</p>
          </div>
          <div className="text-right">
            <p className="opacity-75">Usado</p>
            <p className="font-semibold">{percentageUsed.toFixed(1)}%</p>
          </div>
        </div>
        <div className="mt-3 bg-white/20 rounded-full h-2 overflow-hidden">
          <div
            className="bg-white h-full rounded-full transition-all"
            style={{ width: `${Math.min(percentageUsed, 100)}%` }}
          />
        </div>
      </div>

      {/* Gastos por categoría */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h2 className="font-semibold mb-3">Gastos por Categoría</h2>
        <div className="space-y-2">
          {spendingByCategory.map((item) => {
            const budget = item.id ? budgets.find((b) => b.categoryId === item.id) : null;
            const percentage = budget ? (item.amount / budget.amount) * 100 : (item.pct ?? 0) * 100;
            return (
              <div key={item.categoria} className="flex items-center gap-3">
                <div className="text-2xl">{item.icon ?? "📁"}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium truncate">{item.categoria}</span>
                    <span className="text-sm font-semibold text-gray-900">
                      ${item.amount.toLocaleString("es-MX")}
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.min(percentage, 100)}%`,
                        backgroundColor: item.color ?? "#6b7280",
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Transacciones recientes */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h2 className="font-semibold mb-3">Transacciones Recientes</h2>
        <div className="space-y-3">
          {recentTransactions.map((t) => {
            const category = categories.find((c) => c.name.toLowerCase() === (t.categoria || "").toLowerCase());
            return (
              <div key={t.id} className="flex items-center gap-3">
                <div className="text-2xl">{category?.icon ?? "📁"}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{t.titulo}</p>
                  <p className="text-xs text-gray-500">
                    {new Date(t.fecha).toLocaleDateString("es-MX", {
                      day: "numeric",
                      month: "short",
                    })}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-red-600">
                    ${Math.abs(t.monto).toLocaleString("es-MX")}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Insights rápidos */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-500" />
            <p className="text-xs text-gray-600">Mayor gasto</p>
          </div>
          <p className="font-semibold text-sm">
            ${(breakdown?.mayor_gasto ?? 0).toLocaleString("es-MX")}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Receipt className="w-4 h-4 text-blue-500" />
            <p className="text-xs text-gray-600">Transacciones</p>
          </div>
          <p className="font-semibold text-sm">{breakdown?.transacciones_count ?? 0}</p>
        </div>
      </div>
    </div>
  );
}