import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../../lib/api";
import {
  Activity,
  Users,
  Receipt,
  Zap,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
  LayoutDashboard,
  Radio,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useNavigate } from "react-router";
import { PipelineLog } from "./admin/PipelineLog";
import { UsersPanel } from "./admin/UsersPanel";

interface AdminDashboardResponse {
  system: { status: string; timestamp: string };
  counts: {
    usuarios: number;
    movimientos_total: number;
    movimientos_hoy: number;
    movimientos_semana: number;
    reglas_total: number;
    reglas_auto: number;
  };
  ingest_recientes: Array<{
    id: number;
    fecha: string;
    timestamp: string;
    descripcion: string;
    monto: number;
    moneda: string;
    categoria: string;
    subcategoria: string;
    regla_confianza: string;
  }>;
  reglas_recientes: Array<{
    id: number;
    patron: string;
    categoria: string;
    subcategoria: string;
    confianza: string;
    creado_en: string;
  }>;
  movimientos_por_dia: Array<{
    fecha: string;
    count: number;
    total: number;
  }>;
}

type Tab = "dashboard" | "pipeline" | "users";

export function AdminPanel() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("pipeline");
  const [data, setData] = useState<AdminDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch<AdminDashboardResponse>("/views/admin/dashboard");
      setData(res);
    } catch (e) {
      setError("No se pudo cargar el panel");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const chartData = (data?.movimientos_por_dia ?? []).map((d) => ({
    dia: new Date(d.fecha + "T12:00:00").toLocaleDateString("es-AR", {
      weekday: "short",
    }),
    movimientos: d.count,
    total: d.total,
  }));

  const confianzaBadge = (c: string) => {
    if (c === "MANUAL")
      return (
        <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">
          MANUAL
        </span>
      );
    if (c === "AUTO")
      return (
        <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700">
          AUTO
        </span>
      );
    return (
      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">
        SIN REGLA
      </span>
    );
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="p-2 rounded-xl bg-white shadow-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-lg font-bold flex-1">Monitor</h1>
        {tab === "dashboard" && (
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-white shadow-sm text-gray-600 hover:bg-gray-50 hover:text-blue-600 transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`w-5 h-5 ${isLoading ? "animate-spin" : ""}`}
            />
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
        <button
          onClick={() => setTab("pipeline")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            tab === "pipeline"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <Radio className="w-3.5 h-3.5" />
          Pipeline
        </button>
        <button
          onClick={() => setTab("users")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            tab === "users"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          Usuarios
        </button>
        <button
          onClick={() => { setTab("dashboard"); if (!data) fetchData(); }}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            tab === "dashboard"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <LayoutDashboard className="w-3.5 h-3.5" />
          Dashboard
        </button>
      </div>

      {/* Pipeline Tab */}
      {tab === "pipeline" && <PipelineLog />}

      {/* Users Tab */}
      {tab === "users" && <UsersPanel />}

      {/* Dashboard Tab */}
      {tab === "dashboard" && (
        <>
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* System Status */}
      <div
        className={`bg-gradient-to-br ${
          data?.system.status === "ok"
            ? "from-emerald-600 to-emerald-700"
            : "from-red-600 to-red-700"
        } rounded-2xl p-6 text-white shadow-lg`}
      >
        {isLoading && !data ? (
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-32 bg-white/30 rounded" />
            <div className="h-6 w-48 bg-white/40 rounded" />
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-2">
              {data?.system.status === "ok" ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              <p className="text-sm font-medium opacity-90">Estado del Sistema</p>
            </div>
            <p className="text-2xl font-bold">
              {data?.system.status === "ok"
                ? "Sistema Operando"
                : "Error"}
            </p>
            <p className="text-xs opacity-75 mt-2">
              {data?.system.timestamp
                ? new Date(data.system.timestamp).toLocaleString("es-AR")
                : ""}
            </p>
          </>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        {isLoading && !data
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-white rounded-xl p-4 shadow-sm">
                <div className="animate-pulse space-y-2">
                  <div className="h-4 w-20 bg-gray-200 rounded" />
                  <div className="h-6 w-12 bg-gray-200 rounded" />
                </div>
              </div>
            ))
          : [
              {
                icon: <Receipt className="w-4 h-4 text-blue-500" />,
                label: "Total Movimientos",
                value: data?.counts.movimientos_total ?? 0,
              },
              {
                icon: <Activity className="w-4 h-4 text-green-500" />,
                label: "Hoy",
                value: data?.counts.movimientos_hoy ?? 0,
              },
              {
                icon: <Activity className="w-4 h-4 text-indigo-500" />,
                label: "Semana",
                value: data?.counts.movimientos_semana ?? 0,
              },
              {
                icon: <Zap className="w-4 h-4 text-yellow-500" />,
                label: "Total Reglas",
                value: data?.counts.reglas_total ?? 0,
              },
              {
                icon: <Zap className="w-4 h-4 text-orange-500" />,
                label: "Reglas AUTO",
                value: data?.counts.reglas_auto ?? 0,
              },
              {
                icon: <Users className="w-4 h-4 text-purple-500" />,
                label: "Usuarios",
                value: data?.counts.usuarios ?? 0,
              },
            ].map((m) => (
              <div key={m.label} className="bg-white rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  {m.icon}
                  <p className="text-xs text-gray-600">{m.label}</p>
                </div>
                <p className="text-xl font-bold text-gray-900">
                  {m.value.toLocaleString("es-AR")}
                </p>
              </div>
            ))}
      </div>

      {/* Activity Chart */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h3 className="font-medium mb-4">Actividad (7 dias)</h3>
        {isLoading && !data ? (
          <div className="h-48 animate-pulse bg-gray-100 rounded" />
        ) : (
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis
                  dataKey="dia"
                  tick={{ fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  formatter={(value: number, name: string) =>
                    name === "total"
                      ? `$${value.toLocaleString("es-AR")}`
                      : value
                  }
                  contentStyle={{
                    backgroundColor: "white",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar
                  dataKey="movimientos"
                  fill="#3b82f6"
                  radius={[8, 8, 0, 0]}
                  name="Movimientos"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Recent Ingestions */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h3 className="font-medium mb-3">Ingestas Recientes (Gmail)</h3>
        {isLoading && !data ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-8 w-8 bg-gray-200 rounded" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-2/3" />
                  <div className="h-3 bg-gray-100 rounded w-1/3" />
                </div>
              </div>
            ))}
          </div>
        ) : data?.ingest_recientes.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">
            Sin ingestas recientes
          </p>
        ) : (
          <div className="space-y-3">
            {data?.ingest_recientes.map((item) => (
              <div key={item.id} className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-sm font-medium truncate flex-1">
                      {item.descripcion}
                    </p>
                    {confianzaBadge(item.regla_confianza)}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>{item.categoria}</span>
                    {item.subcategoria && (
                      <>
                        <span className="text-gray-300">|</span>
                        <span>{item.subcategoria}</span>
                      </>
                    )}
                    <span className="text-gray-300">|</span>
                    <span>
                      {item.timestamp
                        ? new Date(item.timestamp).toLocaleDateString("es-AR", {
                            day: "numeric",
                            month: "short",
                          })
                        : item.fecha}
                    </span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-gray-900">
                    ${item.monto.toLocaleString("es-AR")}
                  </p>
                  <p className="text-xs text-gray-400">{item.moneda}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent AUTO Rules */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="w-4 h-4 text-yellow-500" />
          <h3 className="font-medium">Reglas AUTO Recientes</h3>
        </div>
        {isLoading && !data ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-gray-100 rounded" />
            ))}
          </div>
        ) : data?.reglas_recientes.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">
            Sin reglas AUTO recientes
          </p>
        ) : (
          <div className="space-y-2">
            {data?.reglas_recientes.map((regla) => (
              <div
                key={regla.id}
                className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{regla.patron}</p>
                  <p className="text-xs text-gray-500">
                    {regla.categoria}
                    {regla.subcategoria && ` / ${regla.subcategoria}`}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700">
                    AUTO
                  </span>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {regla.creado_en
                      ? new Date(regla.creado_en).toLocaleDateString("es-AR", {
                          day: "numeric",
                          month: "short",
                        })
                      : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
        </>
      )}
    </div>
  );
}
