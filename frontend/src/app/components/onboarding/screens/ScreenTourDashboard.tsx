import { useState, useEffect } from "react";
import { Frame, Eyebrow, Italic, PrimaryBtn, BackBtn } from "../primitives";
import { lime, ink, accent, muted, subtle } from "../theme";

const HL_LABELS = [
  { label: "BALANCE DEL MES", text: "Lo que gastaste y cuánto del presupuesto te queda." },
  { label: "GASTOS POR CATEGORÍA", text: "Dónde se va tu plata, ordenado de mayor a menor." },
  { label: "TRANSACCIONES RECIENTES", text: "Las últimas compras, auto-categorizadas." },
  { label: "INSIGHTS RÁPIDOS", text: "El gasto más alto y cuántos movimientos hubo." },
];

const cats = [
  { n: "Comida", i: "🍴", v: 248500, c: "#FF7A45" },
  { n: "Vivienda", i: "🏠", v: 195000, c: lime },
  { n: "Transporte", i: "🚗", v: 142800, c: "#3B82F6" },
  { n: "Servicios", i: "💡", v: 98400, c: "#FBBF24" },
];
const totalCats = cats.reduce((a, c) => a + c.v, 0);

const txs = [
  { i: "☕", t: "Starbucks Palermo", d: "23 oct", a: 4800 },
  { i: "⛽", t: "YPF Av. Libertador", d: "22 oct", a: 28500 },
  { i: "🍴", t: "Carrefour Express", d: "21 oct", a: 18420 },
  { i: "🎬", t: "Netflix", d: "20 oct", a: 6990 },
];

interface Props { onNext: () => void; onBack?: () => void }

export function ScreenTourDashboard({ onNext, onBack }: Props) {
  const [highlight, setHighlight] = useState(0);
  const [balance, setBalance] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setHighlight((h) => (h + 1) % HL_LABELS.length), 2400);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let f: number; const s = Date.now();
    const tick = () => {
      const t = Math.min(1, (Date.now() - s) / 1400);
      setBalance(Math.floor((1 - Math.pow(1 - t, 3)) * 847230));
      if (t < 1) f = requestAnimationFrame(tick);
    };
    f = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(f);
  }, []);

  const pctUsed = (balance / 1500000) * 100;
  const ring = (i: number) => ({
    outline: highlight === i ? `3px solid ${ink}` : "3px solid transparent",
    outlineOffset: 4, borderRadius: 16, transition: "outline-color .35s", position: "relative" as const,
  });

  return (
    <Frame>
      {onBack && <BackBtn onClick={onBack} />}
      <Eyebrow>tour · 1 de 3</Eyebrow>
      <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 22, lineHeight: 1.05, fontWeight: 400, letterSpacing: -0.6 }}>
        Tu <Italic>inicio</Italic>, todo en una pantalla.
      </div>
      <div style={{ flex: 1, marginTop: 14, marginBottom: 12, background: "#F4F1EA", borderRadius: 18, padding: "10px 10px 12px", border: `1px solid ${subtle}`, overflowY: "auto", scrollbarWidth: "none" as const }}>
        {/* Balance card */}
        <div style={ring(0)}>
          <div style={{ background: "linear-gradient(135deg, #2563eb, #1e40af)", color: "#fff", borderRadius: 14, padding: "12px 14px", boxShadow: "0 6px 14px rgba(37,99,235,0.25)" }}>
            <div style={{ fontSize: 9, opacity: 0.85, fontWeight: 700, marginBottom: 2 }}>Balance del mes</div>
            <div style={{ fontFamily: '"SF Mono", monospace', fontSize: 22, fontWeight: 800, letterSpacing: -1, marginBottom: 8, fontVariantNumeric: "tabular-nums" }}>
              ${balance.toLocaleString("es-AR")}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9 }}>
              <div><div style={{ opacity: 0.7 }}>Presupuesto</div><div style={{ fontWeight: 700, fontFamily: '"SF Mono", monospace' }}>$1.500.000</div></div>
              <div style={{ textAlign: "right" }}><div style={{ opacity: 0.7 }}>Usado</div><div style={{ fontWeight: 700, fontFamily: '"SF Mono", monospace' }}>{pctUsed.toFixed(1)}%</div></div>
            </div>
            <div style={{ marginTop: 7, height: 4, background: "rgba(255,255,255,0.2)", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", background: "#fff", borderRadius: 2, width: `${Math.min(pctUsed, 100)}%`, transition: "width .4s" }} />
            </div>
          </div>
        </div>
        {/* Categories */}
        <div style={{ marginTop: 8, ...ring(1) }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "10px 12px", boxShadow: "0 1px 2px rgba(0,0,0,0.04)" }}>
            <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 8 }}>Gastos por Categoría</div>
            {cats.slice(0, 4).map((c, i) => (
              <div key={c.n} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 6, opacity: 0, animation: `dRow .4s cubic-bezier(.2,.7,.2,1) ${0.7 + i * 0.08}s forwards` }}>
                <span style={{ fontSize: 13 }}>{c.i}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                    <span style={{ fontSize: 10, fontWeight: 600 }}>{c.n}</span>
                    <span style={{ fontSize: 9.5, fontWeight: 700, fontFamily: '"SF Mono", monospace' }}>${(c.v / 1000).toFixed(0)}k</span>
                  </div>
                  <div style={{ height: 3, background: "#F4F1EA", borderRadius: 2, overflow: "hidden" }}>
                    <div style={{ height: "100%", background: c.c, borderRadius: 2, width: 0, animation: `dBar .7s cubic-bezier(.2,.7,.2,1) ${0.9 + i * 0.08}s forwards`, ["--w" as string]: ((c.v / totalCats) * 100) + "%" }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        {/* Transactions */}
        <div style={{ marginTop: 8, ...ring(2) }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "10px 12px", boxShadow: "0 1px 2px rgba(0,0,0,0.04)" }}>
            <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 8 }}>Transacciones Recientes</div>
            {txs.map((t, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7, opacity: 0, animation: `dRow .4s cubic-bezier(.2,.7,.2,1) ${1.1 + i * 0.07}s forwards` }}>
                <span style={{ fontSize: 13 }}>{t.i}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{t.t}</div>
                  <div style={{ fontSize: 8.5, color: muted }}>{t.d}</div>
                </div>
                <div style={{ fontSize: 10, fontWeight: 700, color: "#dc2626", fontFamily: '"SF Mono", monospace' }}>${t.a.toLocaleString("es-AR")}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* Highlight label */}
      <div key={highlight} style={{ background: ink, color: "#fff", borderRadius: 12, padding: "10px 14px", marginBottom: 12, animation: "hlIn .35s cubic-bezier(.2,.7,.2,1)", display: "flex", gap: 10, alignItems: "flex-start" }}>
        <div style={{ fontSize: 9, fontWeight: 800, letterSpacing: 1, color: lime, background: "rgba(216,255,60,0.15)", padding: "3px 7px", borderRadius: 5, textTransform: "uppercase" as const, flexShrink: 0 }}>
          {HL_LABELS[highlight].label}
        </div>
        <div style={{ fontSize: 11, lineHeight: 1.4, color: "rgba(255,255,255,0.9)" }}>{HL_LABELS[highlight].text}</div>
      </div>
      <div style={{ display: "flex", justifyContent: "center", gap: 5, marginBottom: 12 }}>
        {HL_LABELS.map((_, i) => (
          <button key={i} onClick={() => setHighlight(i)} style={{ border: "none", padding: 0, background: "transparent", cursor: "pointer" }}>
            <div style={{ width: i === highlight ? 18 : 5, height: 5, borderRadius: 3, background: ink, opacity: i === highlight ? 1 : 0.25, transition: "all .25s" }} />
          </button>
        ))}
      </div>
      <PrimaryBtn onClick={onNext}>Siguiente →</PrimaryBtn>
    </Frame>
  );
}
