import { useState } from "react";
import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn, BackBtn } from "../primitives";
import { lime, ink, accent, muted, subtle } from "../theme";

const TIERS = [
  {
    pct: 50,
    label: "Necesidades",
    color: lime,
    fg: ink,
    tagline: "Lo esencial. Lo que NO podés no pagar.",
    examples: [
      { i: "🏠", n: "Vivienda" },
      { i: "🍴", n: "Comida" },
      { i: "💡", n: "Servicios" },
      { i: "🚗", n: "Transporte" },
      { i: "💊", n: "Salud" },
      { i: "🎓", n: "Educación" },
    ],
    hint: "Si superás el 50%, tus gastos fijos están altos. Mirá alquiler, deudas y servicios.",
  },
  {
    pct: 30,
    label: "Estilo de vida",
    color: "#FF7A45",
    fg: "#fff",
    tagline: "Lo que disfrutás. Mejorás tu vida, pero podrías recortar.",
    examples: [
      { i: "🎬", n: "Ocio" },
      { i: "👕", n: "Compras" },
      { i: "📺", n: "Streaming" },
      { i: "🎮", n: "Hobbies" },
    ],
    hint: "Acá es donde la mayoría se descuida. Si pasás del 30%, ya sabés dónde recortar.",
  },
  {
    pct: 20,
    label: "Tu futuro",
    color: accent,
    fg: "#fff",
    tagline: "Lo que sobra después de tus gastos. Se calcula solo.",
    examples: [
      { i: "💰", n: "Ahorro" },
      { i: "📈", n: "Inversion" },
      { i: "🆘", n: "Emergencia" },
    ],
    hint: "Empezá por un fondo de emergencia (3 a 6 meses de gastos). Después invertí.",
  },
];

interface Props {
  onNext: () => void;
  onBack?: () => void;
}

export function ScreenBudgetTheory({ onNext, onBack }: Props) {
  const [step, setStep] = useState(0);

  // Step 0: intro
  if (step === 0) {
    return (
      <Frame>
        {onBack && <BackBtn onClick={onBack} />}
        <Eyebrow>paso 2 · la regla</Eyebrow>
        <Display>
          Antes de seguir,
          <br />
          una <Italic>regla simple</Italic>.
        </Display>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", margin: "18px 0" }}>
          <div
            style={{
              fontFamily: '"SF Mono", monospace',
              fontSize: 76,
              fontWeight: 800,
              letterSpacing: -4,
              color: ink,
              lineHeight: 1,
              textAlign: "center",
              animation: "intro100 .9s cubic-bezier(.2,1.4,.4,1) both",
            }}
          >
            100%
          </div>
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: muted,
              textAlign: "center",
              marginTop: 6,
              letterSpacing: 1,
              textTransform: "uppercase" as const,
            }}
          >
            de tu ingreso
          </div>
          <div style={{ display: "flex", height: 38, borderRadius: 12, overflow: "hidden", marginTop: 26, position: "relative" }}>
            {TIERS.map((t, i) => (
              <div
                key={t.pct}
                style={{
                  width: 0,
                  height: "100%",
                  background: t.color,
                  color: t.fg,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                  fontSize: 13,
                  letterSpacing: -0.3,
                  animation: `splitGrow .55s cubic-bezier(.2,.8,.2,1) ${0.5 + i * 0.18}s forwards`,
                  ["--w" as string]: t.pct + "%",
                }}
              >
                {t.pct}%
              </div>
            ))}
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 10,
              fontSize: 11,
              fontWeight: 700,
              opacity: 0,
              animation: "fadeUp .5s ease 1.3s forwards",
            }}
          >
            <span>Necesidades</span>
            <span>Gustos</span>
            <span>Futuro</span>
          </div>
          <div style={{ marginTop: 22, opacity: 0, animation: "fadeUp .5s ease 1.5s forwards" }}>
            <Body>
              La <strong style={{ color: ink }}>regla 50/30/20</strong> es la teoría de presupuesto más usada del mundo.
              <br />
              Divide tu plata en tres usos. Te la enseñamos en 30 segundos.
            </Body>
          </div>
        </div>
        <PrimaryBtn onClick={() => setStep(1)}>Empezar lección →</PrimaryBtn>
      </Frame>
    );
  }

  // Steps 1-3: explain each tier
  const t = TIERS[step - 1];
  return (
    <Frame>
      {onBack && <BackBtn onClick={onBack} />}
      <div style={{ display: "flex", gap: 4, marginBottom: 18 }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ flex: 1, height: 3, borderRadius: 2, background: i < step ? ink : subtle }} />
        ))}
      </div>
      <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 1, color: muted, textTransform: "uppercase" as const }}>
        regla 50/30/20 · {step}/3
      </div>
      <div key={step} style={{ marginTop: 6 }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "baseline",
            gap: 4,
            background: t.color,
            color: t.fg,
            padding: "6px 18px",
            borderRadius: 12,
            animation: "pctIn .5s cubic-bezier(.2,1.4,.4,1)",
          }}
        >
          <div style={{ fontFamily: '"SF Mono", monospace', fontSize: 56, fontWeight: 800, letterSpacing: -3, lineHeight: 1 }}>
            {t.pct}
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: -1 }}>%</div>
        </div>
      </div>
      <div
        style={{
          fontFamily: '"Times New Roman", Georgia, serif',
          fontSize: 30,
          lineHeight: 1.05,
          fontWeight: 400,
          letterSpacing: -1,
          marginTop: 10,
          animation: "fadeUp2 .5s ease .15s both",
        }}
      >
        <Italic>{t.label}</Italic>
      </div>
      <div
        style={{
          marginTop: 8,
          fontSize: 14,
          color: ink,
          lineHeight: 1.4,
          fontWeight: 500,
          animation: "fadeUp2 .5s ease .25s both",
        }}
      >
        {t.tagline}
      </div>
      <div style={{ flex: 1, marginTop: 18, overflowY: "auto" }}>
        <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1, color: muted, textTransform: "uppercase" as const, marginBottom: 8 }}>
          Ejemplos
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {t.examples.map((e, i) => (
            <div
              key={e.n}
              style={{
                background: "#fff",
                border: `1px solid ${subtle}`,
                borderRadius: 12,
                padding: "8px 12px",
                display: "flex",
                alignItems: "center",
                gap: 7,
                opacity: 0,
                animation: `exIn .4s cubic-bezier(.2,1.6,.4,1) ${0.3 + i * 0.07}s forwards`,
              }}
            >
              <span style={{ fontSize: 16 }}>{e.i}</span>
              <span style={{ fontSize: 12, fontWeight: 700 }}>{e.n}</span>
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: 18,
            padding: "12px 14px",
            background: ink,
            color: "#fff",
            borderRadius: 14,
            opacity: 0,
            animation: "fadeUp2 .5s ease .8s forwards",
            display: "flex",
            gap: 10,
          }}
        >
          <div
            style={{
              width: 24,
              height: 24,
              flexShrink: 0,
              borderRadius: 12,
              background: t.color,
              color: t.fg,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 13,
              fontWeight: 800,
            }}
          >
            !
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.4, color: "rgba(255,255,255,0.85)" }}>{t.hint}</div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => setStep(step - 1)}
          style={{
            background: "#fff",
            color: ink,
            border: `1px solid ${subtle}`,
            borderRadius: 18,
            padding: "16px 18px",
            fontSize: 16,
            fontWeight: 700,
            cursor: "pointer",
            fontFamily: "-apple-system, system-ui, sans-serif",
          }}
        >
          ←
        </button>
        <button
          onClick={() => step === 3 ? onNext() : setStep(step + 1)}
          style={{
            flex: 1,
            background: ink,
            color: "#fff",
            border: "none",
            borderRadius: 18,
            padding: "16px 24px",
            fontSize: 16,
            fontWeight: 700,
            letterSpacing: -0.2,
            cursor: "pointer",
            boxShadow: "0 8px 24px rgba(10,10,10,0.18)",
            fontFamily: "-apple-system, system-ui, sans-serif",
          }}
        >
          {step === 3 ? "Elegir categorías →" : "Siguiente →"}
        </button>
      </div>
    </Frame>
  );
}
