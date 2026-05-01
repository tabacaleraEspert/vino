import { useState, useEffect } from "react";
import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn } from "../primitives";
import { lime, ink, accent, muted, subtle } from "../theme";

const TIERS = [
  {
    pct: 50,
    label: "Necesidades",
    color: lime,
    fg: ink,
    tagline: "Lo esencial. Lo que NO podes no pagar.",
    examples: [
      { i: "🏠", n: "Vivienda" },
      { i: "🍴", n: "Comida" },
      { i: "💡", n: "Servicios" },
      { i: "🚗", n: "Transporte" },
      { i: "💊", n: "Salud" },
      { i: "🎓", n: "Educacion" },
    ],
    hint: "Si superas el 50%, tus gastos fijos estan altos. Mira alquiler, deudas y servicios.",
  },
  {
    pct: 30,
    label: "Estilo de vida",
    color: "#FF7A45",
    fg: "#fff",
    tagline: "Lo que disfrutas. Mejoras tu vida, pero podrias recortar.",
    examples: [
      { i: "🍻", n: "Salidas" },
      { i: "🎬", n: "Ocio" },
      { i: "👕", n: "Compras" },
      { i: "📺", n: "Streaming" },
      { i: "🎮", n: "Hobbies" },
    ],
    hint: "Aca es donde la mayoria se descuida. Si pasas del 30%, ya sabes donde recortar.",
  },
  {
    pct: 20,
    label: "Tu futuro",
    color: accent,
    fg: "#fff",
    tagline: "Pagate primero a vos. Sin esto, el sistema no funciona.",
    examples: [
      { i: "💰", n: "Ahorro" },
      { i: "📈", n: "Inversion" },
      { i: "🆘", n: "Emergencia" },
      { i: "💳", n: "Pago deudas" },
    ],
    hint: "Empeza por un fondo de emergencia (3 a 6 meses de gastos). Despues inverti.",
  },
];

interface Props {
  onNext: (income: number) => void;
  isLoading?: boolean;
}

export function ScreenBudget({ onNext, isLoading = false }: Props) {
  const [step, setStep] = useState(0);
  const [income, setIncome] = useState(1500000);
  const [animIncome, setAnimIncome] = useState(income);

  useEffect(() => {
    if (step !== 4) return;
    let f: number;
    const s = Date.now();
    const from = animIncome;
    const delta = income - from;
    const tick = () => {
      const t = Math.min(1, (Date.now() - s) / 350);
      setAnimIncome(Math.round(from + delta * (1 - Math.pow(1 - t, 3))));
      if (t < 1) f = requestAnimationFrame(tick);
    };
    f = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(f);
  }, [income, step]);

  // Step 0: intro
  if (step === 0) {
    return (
      <Frame>
        <Eyebrow>paso 3 · presupuesto</Eyebrow>
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
              La <strong style={{ color: ink }}>regla 50/30/20</strong> es la teoria de presupuesto mas usada del mundo.
              <br />
              Divide tu plata en tres usos. Te la ensenamos en 30 segundos.
            </Body>
          </div>
        </div>
        <PrimaryBtn onClick={() => setStep(1)}>Empezar leccion →</PrimaryBtn>
      </Frame>
    );
  }

  // Steps 1-3: explain each tier
  if (step >= 1 && step <= 3) {
    const t = TIERS[step - 1];
    return (
      <Frame>
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
            onClick={() => setStep(step + 1)}
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
            {step === 3 ? "Aplicalo a tu plata →" : "Siguiente →"}
          </button>
        </div>
      </Frame>
    );
  }

  // Step 4: calculator
  return (
    <Frame>
      <Eyebrow>tu presupuesto</Eyebrow>
      <Display>
        Tu plata, <Italic>repartida</Italic>.
      </Display>
      <div style={{ marginTop: 8 }}>
        <Body>Edita el monto y ve como se divide.</Body>
      </div>
      <div style={{ flex: 1, overflowY: "auto", marginTop: 14, marginRight: -8, paddingRight: 8 }}>
        <div style={{ background: "#fff", borderRadius: 18, padding: "16px 16px 14px", border: `1px solid ${subtle}`, marginBottom: 12 }}>
          <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1, color: muted, textTransform: "uppercase" as const }}>
            Presupuesto mensual
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginTop: 4, borderBottom: `2px solid ${ink}`, paddingBottom: 4 }}>
            <span style={{ fontFamily: '"SF Mono", monospace', fontSize: 30, fontWeight: 800, letterSpacing: -1.5, color: ink }}>$</span>
            <input
              type="text"
              inputMode="numeric"
              value={income.toLocaleString("es-AR")}
              onChange={(e) => {
                const raw = e.target.value.replace(/[^\d]/g, "");
                const n = raw === "" ? 0 : parseInt(raw, 10);
                setIncome(Math.min(99999999, n));
              }}
              onFocus={(e) => e.target.select()}
              placeholder="1.500.000"
              style={{
                flex: 1,
                minWidth: 0,
                fontFamily: '"SF Mono", monospace',
                fontSize: 30,
                fontWeight: 800,
                letterSpacing: -1.5,
                fontVariantNumeric: "tabular-nums",
                color: ink,
                background: "transparent",
                border: "none",
                outline: "none",
                padding: 0,
              }}
            />
          </div>
          <div style={{ fontSize: 10, color: muted, marginTop: 6 }}>Tu ingreso o el monto que queres presupuestar este mes.</div>
        </div>
        <div style={{ background: ink, color: "#fff", borderRadius: 18, padding: "14px 14px 12px" }}>
          <div
            style={{
              fontSize: 10,
              color: "rgba(255,255,255,0.55)",
              letterSpacing: 1,
              fontWeight: 800,
              marginBottom: 10,
              textTransform: "uppercase" as const,
            }}
          >
            Asi te queda
          </div>
          <div style={{ display: "flex", height: 12, borderRadius: 6, overflow: "hidden", marginBottom: 14 }}>
            {TIERS.map((t) => (
              <div key={t.pct} style={{ width: t.pct + "%", height: "100%", background: t.color, transition: "width .4s ease" }} />
            ))}
          </div>
          {TIERS.map((t, i) => (
            <div
              key={t.label}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "7px 0",
                borderTop: i === 0 ? "none" : "1px solid rgba(255,255,255,0.08)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, background: t.color }} />
                <div style={{ fontSize: 13, fontWeight: 700 }}>{t.label}</div>
                <div style={{ fontSize: 9, fontWeight: 800, color: "rgba(255,255,255,0.5)", fontFamily: '"SF Mono", monospace' }}>{t.pct}%</div>
              </div>
              <div style={{ fontSize: 14, fontWeight: 800, fontFamily: '"SF Mono", monospace', fontVariantNumeric: "tabular-nums" }}>
                ${Math.round(animIncome * (t.pct / 100)).toLocaleString("es-AR")}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => setStep(3)}
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
          onClick={() => !isLoading && onNext(income)}
          disabled={isLoading}
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
            cursor: isLoading ? "not-allowed" : "pointer",
            opacity: isLoading ? 0.5 : 1,
            boxShadow: isLoading ? "none" : "0 8px 24px rgba(10,10,10,0.18)",
            fontFamily: "-apple-system, system-ui, sans-serif",
            transition: "opacity .2s",
          }}
        >
          {isLoading ? (
            <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <span style={{ width: 18, height: 18, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin .8s linear infinite", display: "inline-block" }} />
              Creando presupuesto...
            </span>
          ) : (
            "Crear presupuesto →"
          )}
        </button>
      </div>
    </Frame>
  );
}
