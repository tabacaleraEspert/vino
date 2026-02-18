import { useState } from "react";
import { useData } from "../context/DataContext";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";
import { TrendingUp, Award } from "lucide-react";

export function Stats() {
  const { categories, transactions } = useData();
  const [topN, setTopN] = useState(5);

  // Gastos por categoría
  const spendingByCategory = categories.map((cat) => {
    const catTransactions = transactions.filter((t) => t.categoryId === cat.id);
    const amount = catTransactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);
    return {
      name: cat.name,
      value: amount,
      color: cat.color,
      icon: cat.icon,
    };
  }).filter((item) => item.value > 0);

  // Top N gastos
  const topTransactions = [...transactions]
    .sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount))
    .slice(0, topN);

  // Gastos por día (últimos 7 días)
  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    return date.toISOString().split("T")[0];
  });

  const spendingByDay = last7Days.map((date) => {
    const dayTransactions = transactions.filter((t) => t.date === date);
    const total = dayTransactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);
    return {
      day: new Date(date).toLocaleDateString("es-MX", { weekday: "short" }),
      total,
    };
  });

  const totalSpent = transactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Estadísticas</h2>
        <div className="flex items-center gap-1 text-xs text-gray-600">
          <TrendingUp className="w-4 h-4" />
          Febrero 2026
        </div>
      </div>

      {/* Distribución por categoría - Gráfico de pastel */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h3 className="font-medium mb-4">Distribución por Categoría</h3>
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
                {((cat.value / totalSpent) * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
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
                formatter={(value) => `$${Number(value).toLocaleString("es-MX")}`}
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

        <div className="space-y-2">
          {topTransactions.map((transaction, index) => {
            const category = categories.find((c) => c.id === transaction.categoryId);
            const percentage = (Math.abs(transaction.amount) / totalSpent) * 100;

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
                    ${Math.abs(transaction.amount).toLocaleString("es-MX")}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Resumen total */}
      <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-2xl p-6 text-white shadow-lg">
        <p className="text-sm opacity-90 mb-1">Total Gastado (todos los registros)</p>
        <p className="text-3xl font-bold">
          ${totalSpent.toLocaleString("es-MX", { minimumFractionDigits: 2 })}
        </p>
        <div className="flex items-center gap-4 mt-4 text-sm">
          <div>
            <p className="opacity-75">Transacciones</p>
            <p className="font-semibold">{transactions.length}</p>
          </div>
          <div>
            <p className="opacity-75">Promedio</p>
            <p className="font-semibold">
              ${(totalSpent / transactions.length).toLocaleString("es-MX")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}