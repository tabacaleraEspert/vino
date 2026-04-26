import { useState, useEffect, useCallback } from "react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { useAuth } from "../context/AuthContext";
import { MonthSelector } from "./MonthSelector";
import { api } from "../../lib/api";
import { TrendingDown, TrendingUp, Receipt, RefreshCw } from "lucide-react";

export function Dashboard() {
  const { categories, budgets, refresh, refreshTrigger } = useData();
  const { selectedMonth } = useMonth();
  const { token } = useAuth();
  const [summary, setSummary] = useState<{ gasto_mes: number; presupuesto_mes: number } | null>(null);
  const [breakdown, setBreakdown] = useState<{
    gastos_por_categoria: Array<{ categoria: string; total: number; pct: number }>;
    transacciones_recientes: Array<{ id: string; fecha: string; titulo: string; descripcion: string; monto: number; categoria: string }>;
    mayor_gasto: number;
    transacciones_count: number;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;

  const fetchDashboard = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      // Parallel: summary + breakdown en 1 batch
      const [summaryRes, breakdownRes] = await Promise.all([
        api.views.homeSummary({ period, moneda: "ARS" }),
        api.views.homeBreakdown({ period, currency: "ARS", top_categories: 6, recent_limit: 5 }),
      ]);
      setSummary({ gasto_mes: summaryRes.gasto_mes, presupuesto_mes: summaryRes.presupuesto_mes });
      setBreakdown({
        gastos_por_categoria: breakdownRes.gastos_por_categoria,
        transacciones_recientes: breakdownRes.transacciones_recientes,
        mayor_gasto: breakdownRes.mayor_gasto,
        transacciones_count: breakdownRes.transacciones_count,
      });
    } catch {
      setSummary(null);
      setBreakdown(null);
    } finally {
      setIsLoading(false);
    }
  }, [period, token]);

  useEffect(() => {
    if (!token) {
      setSummary(null);
      setBreakdown(null);
      return;
    }
    fetchDashboard();
  }, [token, period, refreshTrigger, fetchDashboard]);

  const monthSpent = summary?.gasto_mes ?? 0;
  const totalBudget = summary?.presupuesto_mes ?? 0;
  const percentageUsed = totalBudget > 0 ? (monthSpent / totalBudget) * 100 : 0;

  const spendingByCategory = (breakdown?.gastos_por_categoria ?? []).slice(0, 6).map((g) => {
    const cat = categories.find((c) => c.name.toLowerCase() === g.categoria.toLowerCase());
    return { ...g, ...cat, amount: g.total };
  });

  const totalSpent = spendingByCategory.reduce((sum, g) => sum + g.amount, 0);
  const maxPctOfTotal =
    totalSpent > 0
      ? Math.max(...spendingByCategory.map((g) => (g.amount / totalSpent) * 100), 0)
      : 0;

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
          onClick={refresh}
          disabled={isLoading}
          className="p-2.5 rounded-xl bg-white shadow-sm text-gray-600 hover:bg-gray-50 hover:text-blue-600 transition-colors disabled:opacity-50"
          title="Actualizar"
        >
          <RefreshCw className={`w-5 h-5 ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>
      {/* Resumen total */}
      <div
        className={`bg-gradient-to-br ${getCardGradient(percentageUsed)} rounded-2xl p-6 text-white shadow-lg transition-colors duration-500 min-h-[140px]`}
      >
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-24 bg-white/30 rounded" />
            <div className="h-9 w-32 bg-white/40 rounded" />
            <div className="h-4 w-full bg-white/20 rounded" />
            <div className="h-2 w-full bg-white/20 rounded-full" />
          </div>
        ) : (
          <>
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
          </>
        )}
      </div>

      {/* Gastos por categoría */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h2 className="font-semibold mb-3">Gastos por Categoría</h2>
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            <div className="h-3 w-full bg-gray-200 rounded-full" />
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-8 w-8 bg-gray-200 rounded" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4" />
                  <div className="h-2 bg-gray-100 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <>
        {totalSpent > 0 && spendingByCategory.length > 0 && (
          <div className="mb-4">
            <div className="h-3 rounded-full overflow-hidden flex">
              {spendingByCategory.map((item) => {
                const pct = (item.amount / totalSpent) * 100;
                return (
                  <div
                    key={item.categoria}
                    className="h-full transition-all min-w-[2px]"
                    style={{
                      width: `${Math.max(pct, 0.5)}%`,
                      backgroundColor: item.color ?? "#6b7280",
                    }}
                    title={`${item.categoria}: ${pct.toFixed(1)}%`}
                  />
                );
              })}
            </div>
          </div>
        )}
        <div className="space-y-3">
          {spendingByCategory.map((item) => {
            const pctOfTotal = totalSpent > 0 ? (item.amount / totalSpent) * 100 : 0;
            const barWidth = maxPctOfTotal > 0 ? (pctOfTotal / maxPctOfTotal) * 100 : 0;
            return (
              <div key={item.categoria} className="flex items-center gap-3">
                <div className="text-2xl flex-shrink-0">{item.icon ?? "📁"}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium truncate">{item.categoria}</span>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-xs text-gray-500 tabular-nums">
                        {pctOfTotal.toFixed(1)}%
                      </span>
                      <span className="text-sm font-semibold text-gray-900">
                        ${item.amount.toLocaleString("es-MX")}
                      </span>
                    </div>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500 min-w-[4px]"
                      style={{
                        width: `${Math.max(barWidth, 2)}%`,
                        backgroundColor: item.color ?? "#6b7280",
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
          </>
        )}
      </div>

      {/* Transacciones recientes */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h2 className="font-semibold mb-3">Transacciones Recientes</h2>
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-8 w-8 bg-gray-200 rounded" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-2/3" />
                  <div className="h-3 bg-gray-100 rounded w-1/4" />
                </div>
                <div className="h-4 bg-gray-200 rounded w-16" />
              </div>
            ))}
          </div>
        ) : (
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
        )}
      </div>

      {/* Insights rápidos */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-xl p-4 shadow-sm">
          {isLoading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-4 w-20 bg-gray-200 rounded" />
              <div className="h-5 w-16 bg-gray-200 rounded" />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown className="w-4 h-4 text-red-500" />
                <p className="text-xs text-gray-600">Mayor gasto</p>
              </div>
              <p className="font-semibold text-sm">
                ${(breakdown?.mayor_gasto ?? 0).toLocaleString("es-MX")}
              </p>
            </>
          )}
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm">
          {isLoading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-4 w-24 bg-gray-200 rounded" />
              <div className="h-5 w-8 bg-gray-200 rounded" />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <Receipt className="w-4 h-4 text-blue-500" />
                <p className="text-xs text-gray-600">Transacciones</p>
              </div>
              <p className="font-semibold text-sm">{breakdown?.transacciones_count ?? 0}</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
