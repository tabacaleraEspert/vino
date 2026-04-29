import { useState, useRef } from "react";
import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn } from "../primitives";
import { lime, ink, muted, subtle } from "../theme";

interface Props {
  onNext: (phoneNumber: string | null) => void;
}

export function ScreenWhatsAppConnect({ onNext }: Props) {
  const [digits, setDigits] = useState("");
  const [touched, setTouched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const cleaned = digits.replace(/\D/g, "");
  const isValid = cleaned.length === 10 || cleaned.length === 11;

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

  const handleSubmit = () => {
    setTouched(true);
    if (!isValid) {
      inputRef.current?.focus();
      return;
    }
    // Normalize: ensure starts with 9
    const normalized = cleaned.startsWith("9") ? cleaned : "9" + cleaned;
    const full = `+54${normalized}`;
    onNext(full);
  };

  const showError = touched && !isValid && cleaned.length > 0;

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
            gaste 4500 en cafe ☕
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
            ✓ Anotado en <span style={{ color: lime, fontWeight: 700 }}>Comida</span>
          </div>
        </div>
      </div>

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
        <PrimaryBtn onClick={handleSubmit} disabled={!isValid}>
          Conectar WhatsApp →
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
