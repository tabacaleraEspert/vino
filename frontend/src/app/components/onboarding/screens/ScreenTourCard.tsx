import { useState, useEffect } from "react";
import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn } from "../primitives";
import { lime, ink, cream, subtle } from "../theme";

const movements = [
  { merchant: "Starbucks", cat: "Comida", amount: 4800, icon: "☕" },
  { merchant: "Uber", cat: "Transporte", amount: 3200, icon: "🚗" },
  { merchant: "Netflix", cat: "Ocio", amount: 6990, icon: "🎬" },
  { merchant: "YPF", cat: "Transporte", amount: 28500, icon: "⛽" },
];

interface Props { onNext: () => void }

export function ScreenTourCard({ onNext }: Props) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setShown((s) => (s + 1) % (movements.length + 1)), 700);
    return () => clearInterval(id);
  }, []);

  return (
    <Frame>
      <Eyebrow>tour · 2 de 3</Eyebrow>
      <Display>Tu tarjeta se <Italic>carga sola</Italic>.</Display>
      <div style={{ display: "flex", justifyContent: "center", margin: "18px 0 14px", perspective: 800 }}>
        <div style={{
          width: 220, height: 138, borderRadius: 16,
          background: `linear-gradient(135deg, ${ink} 0%, #2d2d2d 100%)`,
          color: "#fff", padding: 14, position: "relative", overflow: "hidden",
          transform: "rotateY(-8deg) rotateX(5deg)",
          boxShadow: "0 18px 36px rgba(0,0,0,0.22)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ width: 28, height: 22, borderRadius: 4, background: "linear-gradient(135deg,#FFD700,#B8860B)" }} />
            <div style={{ fontSize: 12, fontWeight: 800, fontStyle: "italic", color: lime }}>VISA</div>
          </div>
          <div style={{ fontFamily: '"SF Mono", monospace', fontSize: 13, letterSpacing: 2, marginTop: 22, fontWeight: 600 }}>•••• 4291</div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12, fontSize: 9, opacity: 0.7 }}>
            <span>USUARIO</span><span>12/27</span>
          </div>
          <div style={{
            position: "absolute", left: 0, right: 0, height: 2,
            background: `linear-gradient(90deg, transparent, ${lime}, transparent)`,
            boxShadow: `0 0 10px ${lime}`,
            animation: "cScan 1.6s ease-in-out infinite",
          }} />
        </div>
      </div>
      <div style={{ flex: 1, overflowY: "auto" }}>
        {movements.map((m, i) => (
          <div key={i} style={{
            opacity: i < shown ? 1 : 0,
            transform: i < shown ? "translateX(0)" : "translateX(16px)",
            transition: "all .4s cubic-bezier(.2,.7,.2,1)",
            background: "#fff", border: `1px solid ${subtle}`, borderRadius: 12, padding: "10px 12px",
            display: "flex", alignItems: "center", gap: 10, marginBottom: 6,
          }}>
            <div style={{ width: 30, height: 30, borderRadius: 9, background: cream, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15 }}>{m.icon}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 700 }}>{m.merchant}</div>
              <div style={{ fontSize: 10, fontWeight: 700, color: ink, background: lime, padding: "2px 6px", borderRadius: 4, display: "inline-block", marginTop: 2 }}>
                ✓ {m.cat}
              </div>
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, fontFamily: '"SF Mono", monospace' }}>
              −${m.amount.toLocaleString("es-AR")}
            </div>
          </div>
        ))}
      </div>
      <div style={{ margin: "12px 0" }}>
        <Body>Cada compra entra <strong style={{ color: ink }}>auto-categorizada</strong>. Cero planillas.</Body>
      </div>
      <PrimaryBtn onClick={onNext}>Siguiente →</PrimaryBtn>
    </Frame>
  );
}
