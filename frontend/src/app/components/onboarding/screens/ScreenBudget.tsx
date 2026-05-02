import { useState, useEffect, useRef } from "react";
import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn } from "../primitives";
import { lime, ink, accent, muted, subtle } from "../theme";

const TIERS = [
  { label: "Necesidades", color: lime, fg: ink },
  { label: "Estilo de vida", color: "#FF7A45", fg: "#fff" },
  { label: "Tu futuro", color: accent, fg: "#fff" },
];

interface Props {
  onNext: (income: number) => void;
  isLoading?: boolean;
}

export function ScreenBudget({ onNext, isLoading = false }: Props) {
  const [income, setIncome] = useState(1500000);
  const [animIncome, setAnimIncome] = useState(income);
  const [edited, setEdited] = useState(false);
  const [pcts, setPcts] = useState([50, 30, 20]);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
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
  }, [income]);

  return (
    <Frame>
      <Eyebrow>paso 4 · tu presupuesto</Eyebrow>
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
            <span style={{ fontFamily: '"SF Mono", monospace', fontSize: 30, fontWeight: 800, letterSpacing: -1.5, color: edited ? ink : muted }}>$</span>
            <input
              type="text"
              inputMode="numeric"
              value={income.toLocaleString("es-AR")}
              onChange={(e) => {
                const raw = e.target.value.replace(/[^\d]/g, "");
                const n = raw === "" ? 0 : parseInt(raw, 10);
                setIncome(Math.min(99999999, n));
                if (!edited) setEdited(true);
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
                color: edited ? ink : muted,
                background: "transparent",
                border: "none",
                outline: "none",
                padding: 0,
                transition: "color .2s",
              }}
            />
          </div>
          <div style={{ fontSize: 10, color: muted, marginTop: 6 }}>Tu ingreso o el monto que queres presupuestar este mes.</div>
        </div>

        {/* Recommendation note */}
        <div style={{ fontSize: 12, color: muted, lineHeight: 1.5, marginBottom: 10, padding: "0 2px" }}>
          Recomendamos <strong style={{ color: ink }}>50 / 30 / 20</strong>, pero podes ajustarlo
          moviendo las barritas. Siempre tiene que sumar 100%.
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

          {/* Draggable bar */}
          <div
            ref={barRef}
            style={{ position: "relative", height: 38, borderRadius: 10, overflow: "visible", marginBottom: 14, display: "flex", touchAction: "none" }}
            onPointerDown={(e) => {
              const bar = barRef.current;
              if (!bar) return;
              const rect = bar.getBoundingClientRect();
              const x = e.clientX - rect.left;
              const totalW = rect.width;
              const p1 = (pcts[0] / 100) * totalW;
              const p2 = ((pcts[0] + pcts[1]) / 100) * totalW;
              const handle = Math.abs(x - p1) < Math.abs(x - p2) ? 0 : 1;

              const onMove = (ev: PointerEvent) => {
                const mx = ev.clientX - rect.left;
                const pct = Math.round(Math.max(5, Math.min(95, (mx / totalW) * 100)));
                setPcts((prev) => {
                  const next = [...prev];
                  if (handle === 0) {
                    const clamped = Math.max(5, Math.min(pct, 90));
                    next[0] = clamped;
                    const remaining = 100 - next[0];
                    next[1] = Math.max(5, remaining - next[2]);
                    if (next[1] + next[2] !== remaining) {
                      next[2] = remaining - next[1];
                    }
                  } else {
                    const dividerPct = Math.max(next[0] + 5, Math.min(95, pct));
                    next[1] = dividerPct - next[0];
                    next[2] = 100 - dividerPct;
                    if (next[1] < 5) { next[1] = 5; next[2] = 100 - next[0] - 5; }
                    if (next[2] < 5) { next[2] = 5; next[1] = 100 - next[0] - 5; }
                  }
                  return next;
                });
              };

              const onUp = () => {
                window.removeEventListener("pointermove", onMove);
                window.removeEventListener("pointerup", onUp);
              };
              window.addEventListener("pointermove", onMove);
              window.addEventListener("pointerup", onUp);
            }}
          >
            {TIERS.map((t, i) => (
              <div
                key={t.label}
                style={{
                  width: pcts[i] + "%",
                  height: "100%",
                  background: t.color,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "width .05s",
                  borderRadius: i === 0 ? "10px 0 0 10px" : i === 2 ? "0 10px 10px 0" : 0,
                  position: "relative",
                  cursor: "ew-resize",
                }}
              >
                <span style={{ fontFamily: '"SF Mono", monospace', fontSize: 13, fontWeight: 800, color: t.fg, pointerEvents: "none" }}>
                  {pcts[i]}%
                </span>
              </div>
            ))}
            {[0, 1].map((h) => {
              const pos = h === 0 ? pcts[0] : pcts[0] + pcts[1];
              return (
                <div
                  key={h}
                  style={{
                    position: "absolute",
                    left: pos + "%",
                    top: -4,
                    width: 4,
                    height: 46,
                    background: "#fff",
                    borderRadius: 2,
                    transform: "translateX(-50%)",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
                    cursor: "ew-resize",
                    pointerEvents: "none",
                  }}
                />
              );
            })}
          </div>

          {/* Tier rows */}
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
                <div style={{ fontSize: 9, fontWeight: 800, color: "rgba(255,255,255,0.5)", fontFamily: '"SF Mono", monospace' }}>{pcts[i]}%</div>
              </div>
              <div style={{ fontSize: 14, fontWeight: 800, fontFamily: '"SF Mono", monospace', fontVariantNumeric: "tabular-nums" }}>
                ${Math.round(animIncome * (pcts[i] / 100)).toLocaleString("es-AR")}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button
          onClick={() => !isLoading && pcts[0] + pcts[1] + pcts[2] === 100 && onNext(income)}
          disabled={isLoading || pcts[0] + pcts[1] + pcts[2] !== 100}
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
