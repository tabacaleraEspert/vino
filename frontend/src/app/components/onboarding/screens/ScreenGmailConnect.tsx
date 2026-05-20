import { useState } from "react";
import { Capacitor } from "@capacitor/core";
import { useGoogleLogin } from "@react-oauth/google";
import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn, BackBtn } from "../primitives";
import { lime, ink, muted, subtle } from "../theme";

const isNative = Capacitor.isNativePlatform();

interface Props {
  onNext: (authCode: string | null) => void;
  onBack?: () => void;
}

/** Inner component that uses useGoogleLogin — only rendered on web. */
function GmailConnectInner({
  onSuccess,
  onError,
}: {
  onSuccess: (code: string) => void;
  onError: () => void;
}) {
  const [connecting, setConnecting] = useState(false);

  const googleLogin = useGoogleLogin({
    flow: "auth-code",
    scope: "https://www.googleapis.com/auth/gmail.readonly",
    onSuccess: (response) => onSuccess(response.code),
    onError: () => onError(),
  });

  return (
    <PrimaryBtn
      onClick={() => {
        setConnecting(true);
        googleLogin();
      }}
      disabled={connecting}
    >
      {connecting ? (
        <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          <span
            style={{
              width: 18,
              height: 18,
              border: "2px solid rgba(255,255,255,0.3)",
              borderTopColor: "#fff",
              borderRadius: "50%",
              animation: "spin .8s linear infinite",
              display: "inline-block",
            }}
          />
          Conectando...
        </span>
      ) : (
        <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          <svg width="18" height="18" viewBox="0 0 48 48">
            <path fill="#4285f4" d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z" />
            <path fill="#34a853" d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z" />
            <path fill="#fbbc04" d="M11.69 28.18c-.44-1.32-.69-2.73-.69-4.18s.25-2.86.69-4.18v-5.7H4.34A21.99 21.99 0 002 24c0 3.55.85 6.91 2.34 9.88l7.35-5.7z" />
            <path fill="#ea4335" d="M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z" />
          </svg>
          Conectar Gmail
        </span>
      )}
    </PrimaryBtn>
  );
}

export function ScreenGmailConnect({ onNext, onBack }: Props) {
  const [status, setStatus] = useState<"idle" | "connecting" | "connected" | "error">("idle");

  return (
    <Frame>
      {onBack && <BackBtn onClick={onBack} />}
      <Eyebrow>paso 4 de 9</Eyebrow>
      <Display>
        Conecta tu <Italic>email</Italic>.
      </Display>
      <div style={{ marginTop: 12, marginBottom: 18 }}>
        <Body>
          Leemos tus notificaciones bancarias y registramos gastos automáticamente.
          Solo leemos emails de bancos, nada más.
        </Body>
      </div>

      {/* How it works preview */}
      <div
        style={{
          background: ink,
          borderRadius: 16,
          padding: "14px 14px 16px",
          marginBottom: 18,
        }}
      >
        <div
          style={{
            fontSize: 9,
            fontWeight: 800,
            letterSpacing: 1,
            color: "rgba(255,255,255,0.4)",
            textTransform: "uppercase" as const,
            marginBottom: 10,
          }}
        >
          así funciona
        </div>

        {/* Step 1 */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: 11,
              background: lime,
              color: ink,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 11,
              fontWeight: 900,
              flexShrink: 0,
            }}
          >
            1
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#fff" }}>
              Te llega un email del banco
            </div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>
              "Pagaste $8.000 en CAMINASA SRL"
            </div>
          </div>
        </div>

        {/* Step 2 */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: 11,
              background: lime,
              color: ink,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 11,
              fontWeight: 900,
              flexShrink: 0,
            }}
          >
            2
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#fff" }}>
              Lo detectamos automáticamente
            </div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>
              Extraemos monto, comercio y fecha
            </div>
          </div>
        </div>

        {/* Step 3 */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: 11,
              background: lime,
              color: ink,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 11,
              fontWeight: 900,
              flexShrink: 0,
            }}
          >
            3
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#fff" }}>
              Se registra en tu cuenta
            </div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>
              Categorizado y listo. Sin hacer nada.
            </div>
          </div>
        </div>
      </div>

      {/* Banks supported */}
      <div
        style={{
          background: "#fff",
          borderRadius: 14,
          padding: "10px 14px",
          border: `1px solid ${subtle}`,
          marginBottom: 18,
        }}
      >
        <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1, color: muted, textTransform: "uppercase" as const, marginBottom: 6 }}>
          Bancos soportados
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {["Santander", "BBVA", "Macro", "MercadoPago", "Galicia", "Brubank", "Uala"].map((b) => (
            <div
              key={b}
              style={{
                fontSize: 10,
                fontWeight: 700,
                padding: "4px 8px",
                borderRadius: 6,
                background: "rgba(10,10,10,0.05)",
                color: ink,
              }}
            >
              {b}
            </div>
          ))}
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Status feedback */}
      {status === "connected" && (
        <div
          style={{
            background: lime,
            color: ink,
            borderRadius: 14,
            padding: "12px 16px",
            marginBottom: 12,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontWeight: 700,
            fontSize: 14,
            animation: "fadeUp .4s cubic-bezier(.2,.7,.2,1)",
          }}
        >
          <span style={{ fontSize: 18 }}>✓</span>
          ¡Gmail conectado!
        </div>
      )}

      {status === "error" && (
        <div
          style={{
            background: "#FEF2F2",
            color: "#DC2626",
            borderRadius: 14,
            padding: "10px 14px",
            marginBottom: 12,
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          No se pudo conectar. Intentá de nuevo.
        </div>
      )}

      {/* Buttons */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {status !== "connected" && !isNative && (
          <GmailConnectInner
            onSuccess={(code) => {
              setStatus("connected");
              setTimeout(() => onNext(code), 1200);
            }}
            onError={() => setStatus("error")}
          />
        )}
        {status !== "connected" && isNative && (
          <Body>Podes conectar Gmail mas tarde desde Configuracion en la version web.</Body>
        )}
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
