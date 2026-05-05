import { useState, useRef, useEffect } from "react";
import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn } from "../primitives";
import { lime, ink, muted, subtle } from "../theme";
import { OtpInput } from "../../OtpInput";
import { apiFetch } from "../../../../lib/api";

interface Props {
  onNext: (phoneNumber: string | null) => void;
}

export function ScreenWhatsAppConnect({ onNext }: Props) {
  const [digits, setDigits] = useState("");
  const [touched, setTouched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // OTP state
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [fullPhone, setFullPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

  const cleaned = digits.replace(/\D/g, "");
  const isValid = cleaned.length === 10 || cleaned.length === 11;

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  const formatted = (() => {
    const d = cleaned;
    if (d.length === 0) return "";
    let rest = d;
    let prefix = "";
    if (d.length === 11 && d[0] === "9") {
      prefix = "9 ";
      rest = d.slice(1);
    }
    if (rest.length <= 2) return prefix + rest;
    if (rest.length <= 6) return prefix + rest.slice(0, 2) + " " + rest.slice(2);
    return prefix + rest.slice(0, 2) + " " + rest.slice(2, 6) + "-" + rest.slice(6, 10);
  })();

  const sendCode = async (phone: string) => {
    setSending(true);
    setError("");
    try {
      await apiFetch("/auth/whatsapp/send-code", {
        method: "POST",
        body: JSON.stringify({ whatsapp: phone }),
      });
      setFullPhone(phone);
      setStep("otp");
      setOtp("");
      setResendCooldown(60);
    } catch (e: any) {
      setError(e?.message || "No se pudo enviar el codigo");
    }
    setSending(false);
  };

  const handleSubmit = () => {
    setTouched(true);
    if (!isValid) {
      inputRef.current?.focus();
      return;
    }
    const normalized = cleaned.startsWith("9") ? cleaned : "9" + cleaned;
    const phone = `+54${normalized}`;
    sendCode(phone);
  };

  const handleVerify = async () => {
    if (otp.length !== 6) return;
    setVerifying(true);
    setError("");
    try {
      await apiFetch("/auth/whatsapp/verify-code", {
        method: "POST",
        body: JSON.stringify({ whatsapp: fullPhone, code: otp }),
      });
      onNext(fullPhone);
    } catch (e: any) {
      setError(e?.message || "Codigo incorrecto o expirado");
      setOtp("");
    }
    setVerifying(false);
  };

  const handleResend = () => {
    if (resendCooldown > 0) return;
    sendCode(fullPhone);
  };

  const showError = touched && !isValid && cleaned.length > 0;

  if (step === "otp") {
    return (
      <Frame>
        <Eyebrow>paso 8 de 9</Eyebrow>
        <Display>
          Verifica tu <Italic>numero</Italic>.
        </Display>
        <div style={{ marginTop: 12, marginBottom: 24 }}>
          <Body>
            Enviamos un codigo de 6 digitos a{" "}
            <strong>{fullPhone}</strong> por WhatsApp.
          </Body>
        </div>

        <div style={{ marginBottom: 20 }}>
          <OtpInput value={otp} onChange={setOtp} disabled={verifying} />
        </div>

        {error && (
          <div style={{ color: "#DC2626", fontSize: 13, fontWeight: 600, textAlign: "center", marginBottom: 12 }}>
            {error}
          </div>
        )}

        <div style={{ flex: 1 }} />

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <PrimaryBtn onClick={handleVerify} disabled={otp.length !== 6 || verifying}>
            {verifying ? "Verificando..." : "Verificar →"}
          </PrimaryBtn>
          <div style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 4 }}>
            <button
              onClick={handleResend}
              disabled={resendCooldown > 0 || sending}
              style={{
                background: "transparent",
                border: "none",
                color: resendCooldown > 0 ? muted : ink,
                fontSize: 13,
                fontWeight: 600,
                cursor: resendCooldown > 0 ? "default" : "pointer",
                padding: "8px 0",
                fontFamily: "-apple-system, system-ui, sans-serif",
              }}
            >
              {sending ? "Enviando..." : resendCooldown > 0 ? `Reenviar (${resendCooldown}s)` : "Reenviar codigo"}
            </button>
            <button
              onClick={() => { setStep("phone"); setError(""); setOtp(""); }}
              style={{
                background: "transparent",
                border: "none",
                color: muted,
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                padding: "8px 0",
                fontFamily: "-apple-system, system-ui, sans-serif",
              }}
            >
              Cambiar numero
            </button>
          </div>
        </div>
      </Frame>
    );
  }

  return (
    <Frame>
      <Eyebrow>paso 8 de 9</Eyebrow>
      <Display>
        Conecta tu <Italic>WhatsApp</Italic>.
      </Display>
      <div style={{ marginTop: 12, marginBottom: 18 }}>
        <Body>
          Mandanos tus gastos por chat y los registramos automaticamente. Sin apps nuevas, sin formularios.
        </Body>
      </div>

      {/* Mini preview de chat */}
      <div
        style={{
          background: "#0A0A0A",
          borderRadius: 16,
          padding: "12px 12px 14px",
          marginBottom: 18,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            fontSize: 9,
            fontWeight: 800,
            letterSpacing: 1,
            color: "rgba(255,255,255,0.4)",
            textTransform: "uppercase" as const,
            marginBottom: 8,
          }}
        >
          asi se ve
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 6 }}>
          <div
            style={{
              background: "#25D366",
              color: "#0A0A0A",
              padding: "6px 10px",
              borderRadius: "12px 12px 4px 12px",
              fontSize: 12,
              fontWeight: 600,
              maxWidth: "75%",
            }}
          >
            gaste 4500 en cafe
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "flex-start" }}>
          <div
            style={{
              background: "rgba(255,255,255,0.1)",
              color: "#fff",
              padding: "6px 10px",
              borderRadius: "12px 12px 12px 4px",
              fontSize: 12,
              fontWeight: 500,
              maxWidth: "75%",
            }}
          >
            Anotado en <span style={{ color: lime, fontWeight: 700 }}>Comida</span>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ color: "#DC2626", fontSize: 13, fontWeight: 600, textAlign: "center", marginBottom: 8 }}>
          {error}
        </div>
      )}

      {/* Input de numero */}
      <div
        style={{
          background: "#fff",
          borderRadius: 18,
          padding: "14px 16px 12px",
          border: `1px solid ${showError ? "#DC2626" : subtle}`,
          marginBottom: 14,
          transition: "border-color .2s",
        }}
      >
        <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1, color: muted, textTransform: "uppercase" as const }}>
          Tu numero de WhatsApp
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 6,
            marginTop: 4,
            borderBottom: `2px solid ${ink}`,
            paddingBottom: 4,
          }}
        >
          <span style={{ fontFamily: '"SF Mono", monospace', fontSize: 22, fontWeight: 800, color: ink }}>+54</span>
          <input
            ref={inputRef}
            type="tel"
            inputMode="numeric"
            value={formatted}
            onChange={(e) => {
              const v = e.target.value.replace(/\D/g, "").slice(0, 11);
              setDigits(v);
            }}
            onBlur={() => setTouched(true)}
            placeholder="9 11 1234-5678"
            style={{
              flex: 1,
              minWidth: 0,
              fontFamily: '"SF Mono", monospace',
              fontSize: 22,
              fontWeight: 800,
              letterSpacing: -0.3,
              fontVariantNumeric: "tabular-nums",
              color: ink,
              background: "transparent",
              border: "none",
              outline: "none",
              padding: 0,
            }}
          />
        </div>
        <div style={{ fontSize: 10, color: showError ? "#DC2626" : muted, marginTop: 6, fontWeight: showError ? 700 : 400 }}>
          {showError ? "Ingresa un numero valido (10 u 11 digitos)" : "Inclui el 9 si tu numero es de celular argentino"}
        </div>
      </div>

      <div style={{ flex: 1 }} />

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <PrimaryBtn onClick={handleSubmit} disabled={!isValid || sending}>
          {sending ? "Enviando codigo..." : "Conectar WhatsApp →"}
        </PrimaryBtn>
        <button
          onClick={() => onNext(null)}
          style={{
            background: "transparent",
            border: "none",
            color: muted,
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            padding: "8px 0",
            fontFamily: "-apple-system, system-ui, sans-serif",
          }}
        >
          Ahora no
        </button>
      </div>
    </Frame>
  );
}
