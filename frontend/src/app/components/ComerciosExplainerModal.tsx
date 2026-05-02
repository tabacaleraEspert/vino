import { useState, useEffect, type ReactNode } from "react";

// ─── Theme ────────────────────────────────────────────────
const CE = {
  lime: "#D8FF3C",
  ink: "#0A0A0A",
  cream: "#FAF6EF",
  terracotta: "#FF7A45",
  muted: "rgba(10,10,10,0.55)",
  subtle: "rgba(10,10,10,0.08)",
};

const CEItalic = ({ children }: { children: ReactNode }) => (
  <span style={{ fontFamily: '"Times New Roman", Georgia, serif', fontStyle: "italic", fontWeight: 400 }}>
    {children}
  </span>
);

// ─── Step 1: El problema ─────────────────────────────────
function StepProblem({ active }: { active: boolean }) {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    if (!active) { setPhase(0); return; }
    const t1 = setTimeout(() => setPhase(1), 200);
    const t2 = setTimeout(() => setPhase(2), 1200);
    const t3 = setTimeout(() => setPhase(3), 1900);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [active]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="text-[11px] font-extrabold tracking-[1.5px] uppercase mb-1.5" style={{ color: CE.muted }}>El problema</div>
      <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 26, lineHeight: 1.05, fontWeight: 400, letterSpacing: -0.8, color: CE.ink, marginBottom: 18 }}>
        Los nombres no <CEItalic>siempre coinciden</CEItalic>.
      </div>
      <div style={{ flex: 1, background: "#F4F1EA", borderRadius: 18, border: `1px solid ${CE.subtle}`, padding: "16px 14px", display: "flex", flexDirection: "column", position: "relative", overflow: "hidden" }}>
        <div className="text-[9px] font-bold tracking-[1px] mb-2.5" style={{ color: "rgba(10,10,10,0.35)" }}>
          ○ ○ ○  · NOTIFICACIONES
        </div>
        {/* Notification card */}
        <div style={{
          background: "#fff", borderRadius: 14, padding: "11px 12px", boxShadow: "0 8px 18px rgba(10,10,10,0.10)", border: `1px solid ${CE.subtle}`,
          display: "flex", alignItems: "center", gap: 10,
          opacity: phase >= 1 ? 1 : 0, transform: phase >= 1 ? "translateY(0)" : "translateY(-30px)", transition: "all .55s cubic-bezier(.2,1.2,.3,1)",
        }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #1e40af, #2563eb)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>💳</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="text-[10px] font-bold" style={{ color: CE.muted }}>BANCO · ahora</div>
            <div className="text-[11.5px] font-semibold mt-0.5" style={{ color: CE.ink }}>
              Nuevo gasto: <span style={{ fontFamily: '"SF Mono", monospace', fontWeight: 800 }}>$8.000</span>
            </div>
            <div style={{ fontSize: 10.5, color: CE.muted, fontFamily: '"SF Mono", monospace', marginTop: 2, letterSpacing: 0.3 }}>en CAMINASA SRL</div>
          </div>
        </div>
        {/* Dotted line */}
        <div style={{ width: 2, height: 28, margin: "10px auto 4px", background: `repeating-linear-gradient(to bottom, ${CE.muted} 0 3px, transparent 3px 6px)`, opacity: phase >= 2 ? 0.4 : 0, transition: "opacity .4s" }} />
        {/* Question */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
          <div style={{ fontSize: 56, fontWeight: 800, color: CE.ink, lineHeight: 1, opacity: phase >= 2 ? 1 : 0, transform: phase >= 2 ? "scale(1)" : "scale(0.5)", transition: "all .5s cubic-bezier(.2,1.4,.3,1)", animation: phase >= 2 ? "cePulse 1.6s ease-in-out infinite" : "none" }}>?</div>
          <div style={{ marginTop: 8, fontFamily: '"Times New Roman", Georgia, serif', fontSize: 17, fontStyle: "italic", color: CE.ink, opacity: phase >= 2 ? 1 : 0, transform: phase >= 2 ? "translateY(0)" : "translateY(8px)", transition: "all .5s .15s cubic-bezier(.2,.7,.2,1)" }}>
            ¿Que es <span style={{ fontFamily: '"SF Mono", monospace', fontStyle: "normal", fontSize: 14, fontWeight: 700 }}>CAMINASA SRL</span>?
          </div>
        </div>
      </div>
      <div style={{ marginTop: 14, fontSize: 13, lineHeight: 1.45, color: CE.muted, opacity: phase >= 3 ? 1 : 0, transform: phase >= 3 ? "translateY(0)" : "translateY(8px)", transition: "all .5s cubic-bezier(.2,.7,.2,1)" }}>
        Cuando pagas con tarjeta, el comercio aparece con su <strong style={{ color: CE.ink }}>razon social</strong>, no el nombre del local. No podemos categorizar automaticamente.
      </div>
    </div>
  );
}

// ─── Step 2: La solucion ─────────────────────────────────
function StepSolution({ active }: { active: boolean }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (!active) { setStep(0); return; }
    const ts = [
      setTimeout(() => setStep(1), 350),
      setTimeout(() => setStep(2), 1500),
      setTimeout(() => setStep(3), 2200),
      setTimeout(() => setStep(4), 3300),
    ];
    return () => ts.forEach(clearTimeout);
  }, [active]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="text-[11px] font-extrabold tracking-[1.5px] uppercase mb-1.5" style={{ color: CE.muted }}>La solucion</div>
      <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 26, lineHeight: 1.05, fontWeight: 400, letterSpacing: -0.8, color: CE.ink, marginBottom: 14 }}>
        Lo categorizas <CEItalic>una vez</CEItalic>.
      </div>
      <div style={{ flex: 1, background: "#0B141A", borderRadius: 18, overflow: "hidden", display: "flex", flexDirection: "column", boxShadow: "0 8px 24px rgba(10,10,10,0.18)" }}>
        <div style={{ background: "#1F2C34", padding: "10px 14px", display: "flex", alignItems: "center", gap: 9 }}>
          <div style={{ width: 26, height: 26, borderRadius: 13, background: CE.lime, color: CE.ink, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 800 }}>V</div>
          <div style={{ flex: 1, color: "#fff" }}>
            <div className="text-xs font-bold">Fina Bot</div>
            <div className="text-[9px]" style={{ color: "#25D366" }}>● en linea</div>
          </div>
        </div>
        <div style={{ flex: 1, padding: "10px 10px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
          {step >= 1 && (
            <div style={{ alignSelf: "flex-start", maxWidth: "82%", background: "#1F2C34", color: "#fff", padding: "8px 11px", borderRadius: 12, borderBottomLeftRadius: 3, animation: "ceMsgIn .35s cubic-bezier(.2,1.2,.3,1) both" }}>
              <div className="text-[11px] leading-snug">
                🔔 <strong>Nuevo gasto:</strong> <span style={{ fontFamily: '"SF Mono", monospace' }}>$8.000</span> en <span style={{ fontFamily: '"SF Mono", monospace' }}>CAMINASA SRL</span>.
                <br /><span style={{ color: "rgba(255,255,255,0.65)" }}>No reconozco este comercio.</span>
              </div>
            </div>
          )}
          {step === 2 && (
            <div style={{ alignSelf: "flex-end", background: "#005C4B", color: "#fff", padding: "7px 12px", borderRadius: 12, borderBottomRightRadius: 3, display: "inline-flex", gap: 4, animation: "ceMsgIn .35s cubic-bezier(.2,1.2,.3,1) both" }}>
              {[0, 1, 2].map(d => <div key={d} style={{ width: 5, height: 5, borderRadius: 3, background: "rgba(255,255,255,0.7)", animation: `ceTyping 1s infinite ${d * 0.15}s` }} />)}
            </div>
          )}
          {step >= 3 && (
            <div style={{ alignSelf: "flex-end", maxWidth: "75%", background: "#005C4B", color: "#fff", padding: "8px 11px", borderRadius: 12, borderBottomRightRadius: 3, fontSize: 12, animation: "ceMsgIn .35s cubic-bezier(.2,1.2,.3,1) both" }}>
              Es una cafeteria ☕
            </div>
          )}
          {step >= 4 && (
            <div style={{ alignSelf: "flex-start", maxWidth: "88%", background: "#1F2C34", color: "#fff", padding: "10px 12px", borderRadius: 12, borderBottomLeftRadius: 3, animation: "ceMsgIn .4s cubic-bezier(.2,1.2,.3,1) both" }}>
              <div className="flex items-center gap-1.5 text-[11px] font-bold mb-1.5">
                <span style={{ width: 16, height: 16, borderRadius: 8, background: CE.lime, color: CE.ink, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 900 }}>✓</span>
                Listo!
              </div>
              <div style={{ fontSize: 11, lineHeight: 1.4, fontFamily: '"SF Mono", monospace', background: "rgba(255,255,255,0.06)", padding: "6px 9px", borderRadius: 8, marginBottom: 7 }}>
                CAMINASA SRL → ☕ Comida / Cafe
              </div>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 4, background: CE.lime, color: CE.ink, fontSize: 9, fontWeight: 800, letterSpacing: 1, padding: "3px 7px", borderRadius: 4, textTransform: "uppercase" as const }}>
                <span style={{ fontSize: 10 }}>★</span> Regla creada
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Step 3: El resultado ────────────────────────────────
function StepResult({ active }: { active: boolean }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (!active) { setShown(0); return; }
    const ts = [400, 1200, 2000].map((d, i) => setTimeout(() => setShown(i + 1), d));
    return () => ts.forEach(clearTimeout);
  }, [active]);

  const expenses = [
    { amt: "4.500", date: "12 ABR" },
    { amt: "6.200", date: "18 ABR" },
    { amt: "3.800", date: "24 ABR" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="text-[11px] font-extrabold tracking-[1.5px] uppercase mb-1.5" style={{ color: CE.muted }}>El resultado</div>
      <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 26, lineHeight: 1.05, fontWeight: 400, letterSpacing: -0.8, color: CE.ink, marginBottom: 14 }}>
        Las proximas, <CEItalic>automaticas</CEItalic>.
      </div>
      <div style={{ flex: 1, background: "#F4F1EA", borderRadius: 18, border: `1px solid ${CE.subtle}`, padding: "12px 12px", display: "flex", flexDirection: "column", gap: 7, position: "relative", overflow: "hidden" }}>
        {/* Rule banner */}
        <div style={{ background: CE.ink, color: "#fff", borderRadius: 12, padding: "8px 11px", display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <div style={{ width: 20, height: 20, borderRadius: 10, background: CE.lime, color: CE.ink, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 900 }}>★</div>
          <div style={{ flex: 1 }}>
            <div className="text-[9px] font-extrabold tracking-[1px] uppercase" style={{ color: "rgba(255,255,255,0.55)" }}>regla activa</div>
            <div className="text-[11px] font-bold" style={{ fontFamily: '"SF Mono", monospace' }}>CAMINASA SRL → ☕ Cafe</div>
          </div>
        </div>
        {expenses.map((e, i) => {
          const visible = i < shown;
          return (
            <div key={i} style={{ background: "#fff", borderRadius: 12, padding: "10px 11px", border: `1px solid ${CE.subtle}`, boxShadow: "0 2px 6px rgba(10,10,10,0.04)", display: "flex", alignItems: "center", gap: 10, opacity: visible ? 1 : 0, transform: visible ? "translateY(0) scale(1)" : "translateY(-14px) scale(.96)", transition: "all .45s cubic-bezier(.2,1.2,.3,1)" }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: "linear-gradient(135deg, #1e40af, #2563eb)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13 }}>💳</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, fontFamily: '"SF Mono", monospace', color: CE.muted, fontWeight: 700 }}>CAMINASA SRL · {e.date}</div>
                <div style={{ fontSize: 13, fontWeight: 800, fontFamily: '"SF Mono", monospace', fontVariantNumeric: "tabular-nums", color: CE.ink, marginTop: 1 }}>${e.amt}</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 3, opacity: visible ? 1 : 0, transform: visible ? "translateX(0)" : "translateX(8px)", transition: `all .45s cubic-bezier(.2,1.6,.3,1) ${visible ? ".18s" : "0s"}` }}>
                <div style={{ display: "inline-flex", alignItems: "center", gap: 4, background: CE.lime, color: CE.ink, fontSize: 10, fontWeight: 800, padding: "3px 7px", borderRadius: 5, whiteSpace: "nowrap" }}>
                  <span style={{ fontSize: 11 }}>☕</span> Comida
                </div>
                <div style={{ fontSize: 8.5, fontWeight: 800, letterSpacing: 0.5, color: "#10B981", display: "flex", alignItems: "center", gap: 3 }}>
                  <span style={{ width: 11, height: 11, borderRadius: 6, background: "#10B981", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 8, fontWeight: 900 }}>✓</span>
                  AUTO
                </div>
              </div>
            </div>
          );
        })}
        {shown >= 3 && (
          <div className="text-center text-[10px] font-bold tracking-[1px] uppercase mt-auto pt-2" style={{ color: CE.muted, opacity: 0, animation: "ceFadeIn .5s ease .3s forwards" }}>
            · · ·  y todos los proximos tambien
          </div>
        )}
      </div>
      <div style={{ marginTop: 14, fontSize: 13, lineHeight: 1.45, color: CE.muted, opacity: shown >= 3 ? 1 : 0, transform: shown >= 3 ? "translateY(0)" : "translateY(8px)", transition: "all .5s cubic-bezier(.2,.7,.2,1)" }}>
        Una vez creada la regla, <strong style={{ color: CE.ink }}>todos los gastos futuros</strong> en ese comercio se categorizan solos. Cero trabajo manual.
      </div>
    </div>
  );
}

// ─── Modal ───────────────────────────────────────────────
const STEPS = ["El problema", "La solucion", "El resultado"];

export function ComerciosExplainerModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [step, setStep] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => { if (open) { setStep(0); setPaused(false); } }, [open]);

  // Auto-advance
  useEffect(() => {
    if (paused || !open || step >= STEPS.length - 1) return;
    const t = setTimeout(() => setStep(s => s + 1), 5400);
    return () => clearTimeout(t);
  }, [step, paused, open]);

  // ESC closes
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  const isLast = step === STEPS.length - 1;

  return (
    <div onClick={onClose} className="fixed inset-0 z-50" style={{ background: "rgba(10,10,10,0.45)", backdropFilter: "blur(14px) saturate(140%)", WebkitBackdropFilter: "blur(14px) saturate(140%)", animation: "ceBackdropIn .3s ease" }}>
      <div onClick={e => e.stopPropagation()} style={{ position: "absolute", bottom: 0, left: 0, right: 0, background: CE.cream, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: "12px 22px 22px", maxHeight: "92%", display: "flex", flexDirection: "column", boxShadow: "0 -20px 60px rgba(10,10,10,0.25)", animation: "ceSheetIn .45s cubic-bezier(.2,1.1,.3,1) both", fontFamily: "-apple-system, system-ui, sans-serif" }}>
        {/* Drag handle */}
        <div className="w-[38px] h-1 rounded-sm mx-auto mb-3.5" style={{ background: "rgba(10,10,10,0.18)" }} />
        {/* Progress + close */}
        <div className="flex items-center gap-2.5 mb-4">
          <div className="flex gap-1.5 flex-1">
            {STEPS.map((_, i) => (
              <button key={i} onClick={() => { setStep(i); setPaused(true); }} className="h-[3px] rounded-sm flex-1 border-0 p-0 cursor-pointer transition-colors" style={{ background: i <= step ? CE.ink : CE.subtle }} />
            ))}
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer text-sm font-semibold p-0" style={{ border: `1px solid ${CE.subtle}`, background: "#fff", color: CE.ink }}>×</button>
        </div>
        {/* Step counter */}
        <div className="text-[10px] font-extrabold tracking-[1.5px] uppercase mb-1" style={{ color: CE.muted }}>
          {String(step + 1).padStart(2, "0")} / 03
        </div>
        {/* Step body */}
        <div style={{ height: 480, display: "flex", flexDirection: "column" }}>
          {step === 0 && <StepProblem active />}
          {step === 1 && <StepSolution active />}
          {step === 2 && <StepResult active />}
        </div>
        {/* Footer */}
        <div className="flex gap-2 mt-4">
          {step > 0 && (
            <button onClick={() => { setStep(step - 1); setPaused(true); }} className="rounded-2xl px-4 py-3.5 text-[15px] font-bold cursor-pointer" style={{ background: "#fff", color: CE.ink, border: `1px solid ${CE.subtle}`, fontFamily: "-apple-system, system-ui, sans-serif" }}>←</button>
          )}
          <button onClick={() => { if (isLast) onClose(); else { setStep(step + 1); setPaused(true); } }} className="flex-1 rounded-2xl px-5 py-3.5 text-[15px] font-extrabold border-0 cursor-pointer" style={{ background: isLast ? CE.lime : CE.ink, color: isLast ? CE.ink : "#fff", boxShadow: isLast ? "0 8px 22px rgba(216,255,60,0.45)" : "0 8px 22px rgba(10,10,10,0.18)", fontFamily: "-apple-system, system-ui, sans-serif", letterSpacing: -0.2 }}>
            {isLast ? "Entendido ✓" : "Siguiente →"}
          </button>
        </div>
      </div>
      <style>{`
        @keyframes ceBackdropIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes ceSheetIn { from { transform: translateY(100%); } to { transform: translateY(0); } }
        @keyframes cePulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.08); } }
        @keyframes ceMsgIn { from { opacity: 0; transform: translateY(8px) scale(.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes ceTyping { 0%, 60%, 100% { transform: translateY(0); opacity: 0.5; } 30% { transform: translateY(-3px); opacity: 1; } }
        @keyframes ceFadeIn { to { opacity: 0.6; } }
      `}</style>
    </div>
  );
}

// ─── Help Button ─────────────────────────────────────────
export function CEHelpButton({ onClick, pulse = false }: { onClick: () => void; pulse?: boolean }) {
  return (
    <button
      onClick={onClick}
      aria-label="Como funciona?"
      className="relative inline-flex items-center justify-center w-6 h-6 rounded-full border-[1.5px] border-gray-900 bg-transparent text-gray-900 text-xs font-extrabold cursor-pointer p-0 hover:bg-gray-900 hover:text-white transition-colors"
      style={{ fontFamily: '"Times New Roman", Georgia, serif', fontStyle: "italic" }}
    >
      ?
      {pulse && (
        <span className="absolute -inset-0.5 rounded-full border-[1.5px] border-gray-900 pointer-events-none" style={{ animation: "cePulseRing 1.8s ease-out infinite" }} />
      )}
      <style>{`@keyframes cePulseRing { 0% { transform: scale(1); opacity: 0.7; } 100% { transform: scale(1.7); opacity: 0; } }`}</style>
    </button>
  );
}
