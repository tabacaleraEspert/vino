import { useState, useEffect, lazy, Suspense } from "react";
import { Capacitor } from "@capacitor/core";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../../lib/api";
import { Mail, MessageCircle, User, LogOut, CheckCircle, Loader2, Shield } from "lucide-react";
import { OtpInput } from "./OtpInput";

const isNative = Capacitor.isNativePlatform();

// Lazy-load the Gmail connect button — only loaded on web, avoids importing
// @react-oauth/google on native where GoogleOAuthProvider is not available
const GmailConnectButtonWeb = isNative
  ? null
  : lazy(() => import("./GmailConnectButton"));

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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [message, setMessage] = useState("");

  // OTP state
  const [otpStep, setOtpStep] = useState<"idle" | "sent" | "verifying">("idle");
  const [otpCode, setOtpCode] = useState("");
  const [otpPhone, setOtpPhone] = useState("");
  const [otpError, setOtpError] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

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

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  // Send OTP code
  const sendCode = async () => {
    const raw = whatsapp.trim();
    if (!raw) return;
    setSaving(true);
    setOtpError("");
    // Normalize: add +54 if no country code
    let phone = raw.replace(/[\s-]/g, "");
    if (!phone.startsWith("+")) phone = "+54" + phone;
    setOtpPhone(phone);
    try {
      await apiFetch("/auth/whatsapp/send-code", {
        method: "POST",
        body: JSON.stringify({ whatsapp: phone }),
      });
      setOtpStep("sent");
      setOtpCode("");
      setResendCooldown(60);
    } catch (e: any) {
      setOtpError(e?.message || "No se pudo enviar el codigo");
    }
    setSaving(false);
  };

  // Verify OTP code
  const verifyCode = async () => {
    if (otpCode.length !== 6) return;
    setOtpStep("verifying");
    setOtpError("");
    try {
      await apiFetch("/auth/whatsapp/verify-code", {
        method: "POST",
        body: JSON.stringify({ whatsapp: otpPhone, code: otpCode }),
      });
      setWhatsappSaved(whatsapp.trim());
      setOtpStep("idle");
      setOtpCode("");
      setMessage("WhatsApp verificado");
      setTimeout(() => setMessage(""), 3000);
    } catch (e: any) {
      setOtpError(e?.message || "Codigo incorrecto o expirado");
      setOtpCode("");
      setOtpStep("sent");
    }
  };

  const handleResend = () => {
    if (resendCooldown > 0) return;
    sendCode();
  };

  const [confirmDisconnectWpp, setConfirmDisconnectWpp] = useState(false);
  const disconnectWhatsapp = async () => {
    if (!confirmDisconnectWpp) {
      setConfirmDisconnectWpp(true);
      setTimeout(() => setConfirmDisconnectWpp(false), 4000);
      return;
    }
    setConfirmDisconnectWpp(false);
    setSaving(true);
    try {
      await apiFetch("/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({ whatsapp: "" }),
      });
      setWhatsapp("");
      setWhatsappSaved("");
      setMessage("WhatsApp desconectado");
      setTimeout(() => setMessage(""), 3000);
    } catch {
      setMessage("Error al desconectar");
    }
    setSaving(false);
  };

  const cancelOtp = () => {
    setOtpStep("idle");
    setOtpCode("");
    setOtpError("");
  };


  // Gmail disconnect
  const [confirmDisconnectGmail, setConfirmDisconnectGmail] = useState(false);
  const disconnectGmail = async () => {
    if (!confirmDisconnectGmail) {
      setConfirmDisconnectGmail(true);
      setTimeout(() => setConfirmDisconnectGmail(false), 4000);
      return;
    }
    setConfirmDisconnectGmail(false);
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

  const missingGmail = gmailStatus !== null && !gmailStatus.connected;
  const missingWhatsapp = !whatsappSaved;
  const hasPending = missingGmail || missingWhatsapp;

  return (
    <div className="p-4 space-y-6 max-w-lg mx-auto">
      <h2 className="text-lg font-semibold">Configuracion</h2>

      {message && (
        <div className={`rounded-lg p-3 text-sm font-medium ${message.includes("Error") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
          {message}
        </div>
      )}

      {/* Pending setup banner */}
      {hasPending && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
          <p className="text-sm font-semibold text-amber-900">Te falta configurar:</p>
          <ul className="space-y-1.5">
            {missingGmail && (
              <li className="flex items-center gap-2 text-sm text-amber-800">
                <span className="w-2 h-2 bg-red-500 rounded-full flex-shrink-0" />
                <Mail className="w-4 h-4" />
                <span><strong>Gmail</strong> — Para detectar gastos automaticamente desde tu banco</span>
              </li>
            )}
            {missingWhatsapp && (
              <li className="flex items-center gap-2 text-sm text-amber-800">
                <span className="w-2 h-2 bg-red-500 rounded-full flex-shrink-0" />
                <MessageCircle className="w-4 h-4" />
                <span><strong>WhatsApp</strong> — Para registrar gastos y consultar tu balance por mensaje</span>
              </li>
            )}
          </ul>
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
              {gmailLoading ? "Desconectando..." : confirmDisconnectGmail ? "Toca de nuevo para confirmar" : "Desconectar Gmail"}
            </button>
          </div>
        ) : isNative || !GmailConnectButtonWeb ? (
          <p className="text-sm text-gray-400 italic">
            Conecta Gmail desde la version web de la app.
          </p>
        ) : (
          <Suspense fallback={<Loader2 className="w-4 h-4 animate-spin mx-auto" />}>
            <GmailConnectButtonWeb
              onConnected={(status) => {
                setGmailStatus(status);
                setMessage("Gmail conectado");
                setTimeout(() => setMessage(""), 3000);
              }}
              onError={(msg) => {
                setMessage(msg);
                setTimeout(() => setMessage(""), 3000);
              }}
            />
          </Suspense>
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

        {otpStep === "idle" ? (
          <>
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
                onClick={sendCode}
                disabled={saving || !whatsappChanged || !whatsapp.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? "..." : whatsappSaved ? "Cambiar" : "Verificar"}
              </button>
            </div>
            {whatsappSaved && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-sm text-green-700">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Verificado
                </div>
                <button
                  onClick={disconnectWhatsapp}
                  disabled={saving}
                  className="text-sm text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
                >
                  {confirmDisconnectWpp ? "Toca para confirmar" : "Desconectar"}
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Ingresa el codigo de 6 digitos que enviamos a <strong>{otpPhone}</strong>
            </p>
            <OtpInput value={otpCode} onChange={setOtpCode} disabled={otpStep === "verifying"} />
            {otpError && (
              <p className="text-sm text-red-600 font-medium text-center">{otpError}</p>
            )}
            <div className="flex items-center justify-between">
              <button
                onClick={cancelOtp}
                className="text-sm text-gray-500 hover:text-gray-700 font-medium"
              >
                Cancelar
              </button>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleResend}
                  disabled={resendCooldown > 0 || saving}
                  className="text-sm text-gray-500 hover:text-gray-700 font-medium disabled:opacity-50"
                >
                  {resendCooldown > 0 ? `Reenviar (${resendCooldown}s)` : "Reenviar"}
                </button>
                <button
                  onClick={verifyCode}
                  disabled={otpCode.length !== 6 || otpStep === "verifying"}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {otpStep === "verifying" ? "..." : "Verificar"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Account */}
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
        <hr className="border-gray-100" />
        <button
          onClick={async () => {
            if (!showDeleteConfirm) {
              setShowDeleteConfirm(true);
              return;
            }
            try {
              await apiFetch("/auth/account", { method: "DELETE" });
              logout();
            } catch {
              setMessage("Error al eliminar la cuenta");
              setTimeout(() => setMessage(""), 3000);
              setShowDeleteConfirm(false);
            }
          }}
          className="text-sm text-gray-400 hover:text-red-600 font-medium transition-colors"
        >
          {showDeleteConfirm ? "Toca de nuevo para confirmar" : "Eliminar cuenta y datos"}
        </button>
        {showDeleteConfirm && (
          <p className="text-xs text-red-500">
            Se eliminaran todos tus movimientos, categorias y datos. Esta accion no se puede deshacer.
          </p>
        )}
      </div>

      <p className="text-center text-xs text-gray-400 pt-2">
        Fina v0.1.0
      </p>
    </div>
  );
}
