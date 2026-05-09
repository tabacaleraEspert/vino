import { useState, useEffect } from "react";
import { Frame, Eyebrow, Display, Italic, PrimaryBtn, BackBtn } from "../primitives";
import { lime } from "../theme";

const sequence = [
  { side: "out" as const, text: "gasté 5500 en café" },
  { side: "typing" as const },
  { side: "in" as const, kind: "card" as const },
  { side: "out" as const, text: "cuánto en comida este mes?" },
  { side: "typing" as const },
  { side: "in" as const, kind: "summary" as const },
];

interface Props { onNext: () => void; onBack?: () => void }

export function ScreenTourWhatsApp({ onNext, onBack }: Props) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const delays = [400, 600, 700, 900, 600, 700];
    if (step >= sequence.length) return;
    const t = setTimeout(() => setStep(step + 1), delays[step]);
    return () => clearTimeout(t);
  }, [step]);
  const visible = sequence.slice(0, step);

  return (
    <Frame>
      {onBack && <BackBtn onClick={onBack} />}
      <Eyebrow>tour · 3 de 3</Eyebrow>
      <Display>Carga y consulta<br />por <Italic>WhatsApp</Italic>.</Display>
      <div style={{
        flex: 1, marginTop: 18, marginBottom: 14,
        background: "#0B141A", borderRadius: 18, overflow: "hidden",
        display: "flex", flexDirection: "column",
      }}>
        <div style={{ background: "#1F2C34", padding: "10px 14px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 26, height: 26, borderRadius: 13, background: "#25D366", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 800, fontSize: 12 }}>V</div>
          <div style={{ flex: 1, color: "#fff" }}>
            <div style={{ fontSize: 12, fontWeight: 700 }}>Fina Bot</div>
            <div style={{ fontSize: 9, color: "#25D366" }}>● en línea</div>
          </div>
        </div>
        <div style={{ flex: 1, padding: 10, overflowY: "auto" }}>
          {visible.map((m, i) => {
            if (m.side === "typing") return (
              <div key={i} style={{ background: "#1F2C34", padding: "6px 12px", borderRadius: 12, display: "inline-flex", gap: 4, marginBottom: 6 }}>
                {[0, 1, 2].map(d => <div key={d} style={{ width: 5, height: 5, borderRadius: 3, background: "rgba(255,255,255,0.5)", animation: `td 1s infinite ${d * 0.15}s` }} />)}
              </div>
            );
            if (m.side === "out") return (
              <div key={i} style={{ display: "flex", justifyContent: "flex-end", marginBottom: 6 }}>
                <div style={{ background: "#005C4B", color: "#fff", padding: "6px 10px", borderRadius: 10, fontSize: 12, maxWidth: "75%" }}>{m.text}</div>
              </div>
            );
            return (
              <div key={i} style={{ display: "flex", marginBottom: 6 }}>
                <div style={{ background: "#1F2C34", color: "#fff", padding: "8px 10px", borderRadius: 10, fontSize: 11, maxWidth: "82%" }}>
                  {m.kind === "card" && (<>
                    <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 5 }}>
                      <span>☕</span><strong>Registrado</strong>
                      <span style={{ fontSize: 9, background: "rgba(216,255,60,0.18)", color: lime, padding: "1px 5px", borderRadius: 3, fontWeight: 700 }}>✓ Comida</span>
                    </div>
                    <div style={{ fontSize: 16, fontWeight: 800, fontFamily: '"SF Mono", monospace' }}>−$5.500</div>
                  </>)}
                  {m.kind === "summary" && (<>
                    <div style={{ marginBottom: 5 }}>📊 <strong>Comida · octubre</strong></div>
                    <div style={{ fontSize: 18, fontWeight: 800, fontFamily: '"SF Mono", monospace' }}>$92.800</div>
                    <div style={{ fontSize: 9, color: "rgba(255,255,255,0.6)", marginTop: 3 }}>de $150k · 47 mov</div>
                  </>)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <PrimaryBtn onClick={onNext}>Siguiente →</PrimaryBtn>
    </Frame>
  );
}
