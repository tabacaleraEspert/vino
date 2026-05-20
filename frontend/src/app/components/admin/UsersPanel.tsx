import { useState, useEffect } from "react";
import { apiFetch } from "../../../lib/api";
import {
  Mail,
  MessageCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Receipt,
  Clock,
} from "lucide-react";

interface UserInfo {
  id: number;
  nombre: string;
  apellido: string;
  gmail: string;
  whatsapp: string;
  wpp_vinculado: boolean;
  gmail_conectado: boolean;
  gmail_last_polled: string | null;
  onboarding: boolean;
  movimientos: number;
  created_at: string | null;
}

export function UsersPanel() {
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await apiFetch<{ users: UserInfo[] }>("/admin/users");
      setUsers(res.users);
    } catch {
      // silent
    }
    setLoading(false);
  };

  useEffect(() => {
    fetch();
  }, []);

  const fmtDate = (iso: string | null) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleDateString("es-AR", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const fmtTime = (iso: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleTimeString("es-AR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">{users.length} usuarios</p>
        <button
          onClick={fetch}
          disabled={loading}
          className="p-2 rounded-lg bg-white shadow-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="space-y-2">
        {users.map((u) => (
          <div
            key={u.id}
            className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden"
          >
            <div className="p-3">
              {/* Name + ID */}
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="font-semibold text-sm text-gray-900">
                    {u.nombre} {u.apellido}
                  </span>
                  <span className="ml-2 text-[10px] text-gray-400 font-mono">
                    #{u.id}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Receipt className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-xs font-bold text-gray-700">
                    {u.movimientos}
                  </span>
                </div>
              </div>

              {/* Email */}
              {u.gmail && (
                <p className="text-xs text-gray-500 mb-2 truncate">
                  {u.gmail}
                </p>
              )}

              {/* Status badges */}
              <div className="flex flex-wrap gap-1.5">
                {/* Gmail */}
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    u.gmail_conectado
                      ? "bg-blue-50 text-blue-700"
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  <Mail className="w-3 h-3" />
                  Gmail {u.gmail_conectado ? "ON" : "OFF"}
                </span>

                {/* WhatsApp */}
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    u.wpp_vinculado
                      ? "bg-green-50 text-green-700"
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  <MessageCircle className="w-3 h-3" />
                  WPP {u.wpp_vinculado ? "ON" : "OFF"}
                </span>

                {/* Onboarding */}
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    u.onboarding
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-yellow-50 text-yellow-700"
                  }`}
                >
                  {u.onboarding ? (
                    <CheckCircle className="w-3 h-3" />
                  ) : (
                    <XCircle className="w-3 h-3" />
                  )}
                  {u.onboarding ? "Activo" : "Pendiente"}
                </span>
              </div>

              {/* Last poll + creation */}
              <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
                {u.gmail_last_polled && (
                  <span className="flex items-center gap-0.5">
                    <Clock className="w-3 h-3" />
                    Poll: {fmtDate(u.gmail_last_polled)} {fmtTime(u.gmail_last_polled)}
                  </span>
                )}
                {u.created_at && (
                  <span>
                    Creado: {fmtDate(u.created_at)}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
