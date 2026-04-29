import { useState, useEffect } from "react";
import { Frame, Eyebrow, Display, Italic, PrimaryBtn } from "../primitives";
import { lime, ink, subtle, muted } from "../theme";

const CATS = [
  { i: "🏠", n: "Vivienda", subs: ["Alquiler", "Expensas", "Hipoteca", "Mantenimiento"] },
  { i: "🍴", n: "Comida", subs: ["Super", "Almacen", "Verduleria", "Carniceria", "Delivery"] },
  { i: "🚗", n: "Transporte", subs: ["Nafta", "SUBE", "Uber", "Peajes", "Auto"] },
  { i: "💡", n: "Servicios", subs: ["Luz", "Gas", "Agua", "Internet", "Celular"] },
  { i: "💊", n: "Salud", subs: ["Prepaga", "Farmacia", "Consultas", "Gimnasio"] },
  { i: "🍻", n: "Salidas", subs: ["Restaurantes", "Bar", "Cafe", "Eventos"] },
  { i: "🎬", n: "Ocio", subs: ["Cine", "Streaming", "Viajes", "Hobbies"] },
  { i: "👕", n: "Compras", subs: ["Ropa", "Calzado", "Hogar", "Tecnologia"] },
  { i: "🎓", n: "Educacion", subs: ["Cuotas", "Cursos", "Libros"] },
  { i: "💰", n: "Ahorro", subs: ["Caja", "Plazo fijo", "Emergencia", "Metas"] },
  { i: "📈", n: "Inversion", subs: ["Acciones", "FCI", "Cripto", "Dolar"] },
];

interface Props {
  onNext: () => void;
}

export function ScreenCategories({ onNext }: Props) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  const [revealed, setRevealed] = useState(0);
  const [counter, setCounter] = useState(0);

  useEffect(() => {
    if (revealed >= CATS.length) return;
    const t = setTimeout(() => setRevealed((r) => r + 1), revealed === 0 ? 200 : 70);
    return () => clearTimeout(t);
  }, [revealed]);

  const totalSubs = CATS.reduce((a, c) => a + c.subs.length, 0);
  useEffect(() => {
    if (revealed < CATS.length) return;
    let f: number;
    const s = Date.now();
    const tick = () => {
      const t = Math.min(1, (Date.now() - s) / 900);
      setCounter(Math.floor((1 - Math.pow(1 - t, 3)) * totalSubs));
      if (t < 1) f = requestAnimationFrame(tick);
    };
    f = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(f);
  }, [revealed, totalSubs]);

  return (
    <Frame>
      <Eyebrow>paso 2 · categorias</Eyebrow>
      <Display>
        <Italic>11 categorias</Italic>,<br />
        todo cubierto.
      </Display>

      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 8, marginBottom: 14 }}>
        <div
          style={{
            fontFamily: '"SF Mono", monospace',
            fontSize: 18,
            fontWeight: 800,
            letterSpacing: -0.5,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {counter}
        </div>
        <div style={{ fontSize: 13, color: muted }}>subcategorias · toca para ver</div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", marginRight: -8, paddingRight: 8 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
          {CATS.map((c, i) => {
            const visible = i < revealed;
            const open = openIdx === i;
            return (
              <button
                key={c.n}
                onClick={() => setOpenIdx(open ? null : i)}
                style={{
                  position: "relative",
                  background: open ? ink : "#fff",
                  color: open ? "#fff" : ink,
                  border: `1px solid ${open ? ink : subtle}`,
                  borderRadius: 14,
                  padding: "10px 6px 8px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  overflow: "hidden",
                  fontFamily: "-apple-system, system-ui, sans-serif",
                  opacity: visible ? 1 : 0,
                  transform: visible ? (open ? "scale(1.02)" : "scale(1)") : "translateY(12px) scale(.85)",
                  transition:
                    "opacity .35s cubic-bezier(.2,1.4,.4,1), transform .35s cubic-bezier(.2,1.4,.4,1), background .25s, color .25s, border-color .25s",
                  boxShadow: open ? "0 8px 20px rgba(10,10,10,0.22)" : "none",
                }}
              >
                <div
                  style={{
                    fontSize: 22,
                    animation: visible ? `bounceIn .5s cubic-bezier(.2,1.6,.4,1) ${i * 0.04}s both` : "none",
                  }}
                >
                  {c.i}
                </div>
                <div style={{ fontSize: 10.5, fontWeight: 700, marginTop: 2, letterSpacing: -0.2, whiteSpace: "nowrap" }}>
                  {c.n}
                </div>
                <div
                  style={{
                    fontSize: 8,
                    fontWeight: 800,
                    fontFamily: '"SF Mono", monospace',
                    opacity: 0.55,
                    marginTop: 1,
                  }}
                >
                  {c.subs.length}
                </div>
              </button>
            );
          })}
        </div>

        <div
          style={{
            marginTop: openIdx != null ? 14 : 0,
            maxHeight: openIdx != null ? 200 : 0,
            overflow: "hidden",
            transition: "max-height .35s cubic-bezier(.2,.7,.2,1), margin-top .35s",
          }}
        >
          {openIdx != null && (
            <div style={{ background: ink, color: "#fff", borderRadius: 16, padding: "14px 14px 12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 18 }}>{CATS[openIdx].i}</span>
                <span style={{ fontSize: 14, fontWeight: 800, letterSpacing: -0.3 }}>{CATS[openIdx].n}</span>
                <span
                  style={{
                    marginLeft: "auto",
                    fontSize: 9,
                    fontWeight: 800,
                    letterSpacing: 1,
                    background: lime,
                    color: ink,
                    padding: "2px 6px",
                    borderRadius: 4,
                    textTransform: "uppercase" as const,
                  }}
                >
                  {CATS[openIdx].subs.length} subs
                </span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {CATS[openIdx].subs.map((s, j) => (
                  <div
                    key={s}
                    style={{
                      background: "rgba(255,255,255,0.12)",
                      borderRadius: 8,
                      padding: "5px 9px",
                      fontSize: 11,
                      fontWeight: 600,
                      opacity: 0,
                      animation: `subPop .35s cubic-bezier(.2,1.6,.4,1) ${j * 0.05}s forwards`,
                    }}
                  >
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <PrimaryBtn onClick={onNext}>Continuar →</PrimaryBtn>
      </div>
    </Frame>
  );
}
