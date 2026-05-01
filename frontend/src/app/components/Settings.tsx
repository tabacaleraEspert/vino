import { useState, useEffect, useCallback } from "react";
import { useGoogleLogin } from "@react-oauth/google";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../../lib/api";
import { Mail, MessageCircle, User, LogOut, CheckCircle, XCircle, Loader2, Shield } from "lucide-react";

interface GmailStatus {
  connected: boolean;
  connected_at: string | null;
  last_polled_at: string | null;
}

export function Settings() {
  const { user, logout } = useAuth();
  const [whatsapp, setWhatsapp] = useState("");
  const [whatsappSaved, setWhatsappSaved] = useState("");
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [gmailLoading, setGmailLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Load current profile + gmail status
  useEffect(() => {
    (async () => {
      try {
        const profile = await apiFetch("/auth/profile");
        setWhatsapp(profile.whatsapp || "");
        setWhatsappSaved(profile.whatsapp || "");
      } catch {}
      try {
        const status = await apiFetch<GmailStatus>("/gmail/status");
        setGmailStatus(status);
      } catch {}
    })();
  }, []);

  // Save WhatsApp
  const saveWhatsapp = async () => {
    setSaving(true);
    setMessage("");
    try {
      await apiFetch("/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({ whatsapp: whatsapp.trim() || "" }),
      });
      setWhatsappSaved(whatsapp.trim());
      setMessage("WhatsApp actualizado");
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage("Error al guardar");
    }
    setSaving(false);
  };

  // Gmail connect
  const googleLogin = useGoogleLogin({
    flow: "auth-code",
    scope: "https://www.googleapis.com/auth/gmail.readonly",
    onSuccess: async (response) => {
      setGmailLoading(true);
      try {
        await apiFetch("/gmail/connect", {
          method: "POST",
          body: JSON.stringify({ code: response.code }),
        });
        const status = await apiFetch<GmailStatus>("/gmail/status");
        setGmailStatus(status);
        setMessage("Gmail conectado");
        setTimeout(() => setMessage(""), 3000);
      } catch (e) {
        setMessage("Error al conectar Gmail");
      }
      setGmailLoading(false);
    },
    onError: () => {
      setMessage("Error al conectar con Google");
    },
  });

  // Gmail disconnect
  const disconnectGmail = async () => {
    if (!confirm("Desconectar Gmail? No se detectaran mas gastos automaticamente.")) return;
    setGmailLoading(true);
    try {
      await apiFetch("/gmail/connect", { method: "DELETE" });
      setGmailStatus({ connected: false, connected_at: null, last_polled_at: null });
      setMessage("Gmail desconectado");
      setTimeout(() => setMessage(""), 3000);
    } catch {}
    setGmailLoading(false);
  };

  const whatsappChanged = whatsapp.trim() !== whatsappSaved;

  return (
    <div className="p-4 space-y-6 max-w-lg mx-auto">
      <h2 className="text-lg font-semibold">Configuracion</h2>

      {message && (
        <div className={`rounded-lg p-3 text-sm font-medium ${message.includes("Error") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
          {message}
        </div>
      )}

      {/* Profile */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
            <User className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <p className="font-medium text-gray-900">{user?.name}</p>
            <p className="text-sm text-gray-500">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* Gmail */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <Mail className="w-4 h-4 text-gray-600" />
          <h3 className="font-medium text-gray-900">Gmail</h3>
        </div>
        <p className="text-sm text-gray-500">
          Detectamos gastos automaticamente desde las notificaciones de tu banco.
        </p>

        {gmailStatus?.connected ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="text-green-700 font-medium">Conectado</span>
              {gmailStatus.last_polled_at && (
                <span className="text-gray-400 text-xs">
                  · Ultima lectura: {new Date(gmailStatus.last_polled_at).toLocaleString("es-AR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
            </div>
            <button
              onClick={disconnectGmail}
              disabled={gmailLoading}
              className="text-sm text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
            >
              {gmailLoading ? "Desconectando..." : "Desconectar Gmail"}
            </button>
          </div>
        ) : (
          <button
            onClick={() => googleLogin()}
            disabled={gmailLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {gmailLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <svg width="16" height="16" viewBox="0 0 48 48">
                <path fill="#4285f4" d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z" />
                <path fill="#34a853" d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z" />
                <path fill="#fbbc04" d="M11.69 28.18c-.44-1.32-.69-2.73-.69-4.18s.25-2.86.69-4.18v-5.7H4.34A21.99 21.99 0 002 24c0 3.55.85 6.91 2.34 9.88l7.35-5.7z" />
                <path fill="#ea4335" d="M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z" />
              </svg>
            )}
            Conectar Gmail
          </button>
        )}

        <div className="flex flex-wrap gap-1.5 pt-1">
          {["Santander", "BBVA", "Macro", "MercadoPago", "Galicia", "Brubank"].map((b) => (
            <span key={b} className="text-[10px] font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
              {b}
            </span>
          ))}
        </div>
      </div>

      {/* WhatsApp */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <MessageCircle className="w-4 h-4 text-green-600" />
          <h3 className="font-medium text-gray-900">WhatsApp</h3>
        </div>
        <p className="text-sm text-gray-500">
          Registra gastos y consulta tu balance por mensaje.
        </p>
        <div className="flex gap-2">
          <div className="flex items-center gap-1 flex-1">
            <span className="text-sm font-medium text-gray-500 pl-1">+54</span>
            <input
              type="tel"
              value={whatsapp}
              onChange={(e) => setWhatsapp(e.target.value)}
              placeholder="9 11 1234-5678"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>
          <button
            onClick={saveWhatsapp}
            disabled={saving || !whatsappChanged}
            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? "..." : "Guardar"}
          </button>
        </div>
        {whatsappSaved && (
          <div className="flex items-center gap-1.5 text-sm text-green-700">
            <CheckCircle className="w-3.5 h-3.5" />
            Vinculado
          </div>
        )}
      </div>

      {/* Security */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <Shield className="w-4 h-4 text-gray-600" />
          <h3 className="font-medium text-gray-900">Cuenta</h3>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-sm text-red-600 hover:text-red-700 font-medium"
        >
          <LogOut className="w-4 h-4" />
          Cerrar sesion
        </button>
      </div>

      <p className="text-center text-xs text-gray-400 pt-2">
        Vino v0.1.0
      </p>
    </div>
  );
}
