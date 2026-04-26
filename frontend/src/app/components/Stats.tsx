import { useState, useMemo } from "react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { MonthSelector } from "./MonthSelector";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";
import { TrendingUp, Award } from "lucide-react";

export function Stats() {
  const { categories, transactions } = useData();
  const { selectedMonth } = useMonth();
  const [topN, setTopN] = useState(5);

  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;
  const monthLabel = new Date(selectedMonth.year, selectedMonth.month).toLocaleDateString("es-AR", {
    month: "long",
    year: "numeric",
  });

  // Gastos por categoría
  const spendingByCategory = useMemo(() =>
    categories.map((cat) => {
      const catTransactions = transactions.filter((t) => t.categoryId === cat.id);
      const amount = catTransactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);
      return { name: cat.name, value: amount, color: cat.color, icon: cat.icon };
    }).filter((item) => item.value > 0),
    [categories, transactions]
  );

  const totalSpent = useMemo(() =>
    transactions.reduce((sum, t) => sum + Math.abs(t.amount), 0),
    [transactions]
  );

  // Top N gastos
  const topTransactions = useMemo(() =>
    [...transactions].sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount)).slice(0, topN),
    [transactions, topN]
  );

  // Gastos por día del mes seleccionado
  const spendingByDay = useMemo(() => {
    const year = selectedMonth.year;
    const month = selectedMonth.month;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;
    const lastDay = isCurrentMonth ? today.getDate() : daysInMonth;

    // Show last 7 days of activity within the month
    const startDay = Math.max(1, lastDay - 6);
    const days: { day: string; date: string; total: number }[] = [];

    for (let d = startDay; d <= lastDay; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const dayTransactions = transactions.filter((t) => t.date === dateStr);
      const total = dayTransactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);
      days.push({
        day: new Date(year, month, d).toLocaleDateString("es-AR", { weekday: "short" }),
        date: dateStr,
        total,
      });
    }
    return days;
  }, [transactions, selectedMonth]);

  return (
    <div className="p-4 space-y-4">
      <MonthSelector />
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Estadísticas</h2>
        <div className="flex items-center gap-1 text-xs text-gray-600 capitalize">
          <TrendingUp className="w-4 h-4" />
          {monthLabel}
        </div>
      </div>

      {/* Distribución por categoría - Gráfico de pastel */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h3 className="font-medium mb-4">Distribución por Categoría</h3>
        {spendingByCategory.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">Sin gastos este mes</p>
        ) : (
          <>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={spendingByCategory}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              >
                {spendingByCategory.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-2 gap-2 mt-4">
          {spendingByCategory.map((cat) => (
            <div key={cat.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: cat.color }}
              />
              <span className="text-xs text-gray-600 truncate">{cat.name}</span>
              <span className="text-xs font-semibold text-gray-900 ml-auto">
                {totalSpent > 0 ? ((cat.value / totalSpent) * 100).toFixed(0) : 0}%
              </span>
            </div>
          ))}
        </div>
          </>
        )}
      </div>

      {/* Gastos por día - Gráfico de barras */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h3 className="font-medium mb-4">Últimos 7 Días</h3>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={spendingByDay}>
              <XAxis
                dataKey="day"
                tick={{ fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value) => `$${Number(value).toLocaleString("es-AR")}`}
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="total" fill="#3b82f6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top N gastos */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium flex items-center gap-2">
            <Award className="w-5 h-5 text-yellow-500" />
            Top Gastos
          </h3>
          <select
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
            className="text-sm border border-gray-200 rounded-lg px-2 py-1 outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={3}>Top 3</option>
            <option value={5}>Top 5</option>
            <option value={10}>Top 10</option>
          </select>
        </div>

        {topTransactions.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">Sin transacciones</p>
        ) : (
        <div className="space-y-2">
          {topTransactions.map((transaction, index) => {
            const category = categories.find((c) => c.id === transaction.categoryId);
            const percentage = totalSpent > 0 ? (Math.abs(transaction.amount) / totalSpent) * 100 : 0;

            return (
              <div key={transaction.id} className="flex items-center gap-3">
                <div className="flex items-center justify-center w-6 h-6 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-500 text-white text-xs font-bold flex-shrink-0">
                  {index + 1}
                </div>
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-lg flex-shrink-0"
                  style={{ backgroundColor: `${category?.color}20` }}
                >
                  {category?.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {transaction.description}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${percentage}%`,
                          backgroundColor: category?.color,
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 flex-shrink-0">
                      {percentage.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-gray-900">
                    ${Math.abs(transaction.amount).toLocaleString("es-AR")}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
        )}
      </div>

      {/* Resumen total */}
      <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-2xl p-6 text-white shadow-lg">
        <p className="text-sm opacity-90 mb-1">Total Gastado</p>
        <p className="text-3xl font-bold">
          ${totalSpent.toLocaleString("es-AR", { minimumFractionDigits: 2 })}
        </p>
        <div className="flex items-center gap-4 mt-4 text-sm">
          <div>
            <p className="opacity-75">Transacciones</p>
            <p className="font-semibold">{transactions.length}</p>
          </div>
          <div>
            <p className="opacity-75">Promedio</p>
            <p className="font-semibold">
              ${transactions.length > 0
                ? (totalSpent / transactions.length).toLocaleString("es-AR")
                : "0"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
