import { useState, useEffect, type ReactNode, type CSSProperties } from "react";
import { ink, cream, muted } from "./theme";

// ─── Hooks ────────────────────────────────────────────────

export function useDelay(ms: number) {
  const [v, setV] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setV(true), ms);
    return () => clearTimeout(t);
  }, [ms]);
  return v;
}

// ─── Layout ───────────────────────────────────────────────

export function Frame({
  children,
  dark = false,
}: {
  children: ReactNode;
  dark?: boolean;
}) {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        minHeight: "100dvh",
        background: dark ? ink : cream,
        color: dark ? "#fff" : ink,
        display: "flex",
        flexDirection: "column",
        padding: "60px 24px 28px",
        fontFamily: "-apple-system, system-ui, sans-serif",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

// ─── Typography ───────────────────────────────────────────

export function Eyebrow({
  children,
  dark = false,
}: {
  children: ReactNode;
  dark?: boolean;
}) {
  return (
    <div
      style={{
        fontSize: 11,
        fontWeight: 800,
        letterSpacing: 1.5,
        color: dark ? "rgba(255,255,255,0.55)" : "rgba(10,10,10,0.45)",
        textTransform: "uppercase" as const,
        marginBottom: 8,
      }}
    >
      {children}
    </div>
  );
}

export function Display({
  children,
  dark = false,
}: {
  children: ReactNode;
  dark?: boolean;
}) {
  return (
    <div
      style={{
        fontFamily: '"Times New Roman", Georgia, serif',
        fontSize: 30,
        lineHeight: 1.05,
        fontWeight: 400,
        letterSpacing: -1,
        color: dark ? "#fff" : ink,
      }}
    >
      {children}
    </div>
  );
}

export function Italic({ children }: { children: ReactNode }) {
  return <span style={{ fontStyle: "italic" }}>{children}</span>;
}

export function Body({
  children,
  dark = false,
}: {
  children: ReactNode;
  dark?: boolean;
}) {
  return (
    <div
      style={{
        fontSize: 15,
        lineHeight: 1.45,
        color: dark ? "rgba(255,255,255,0.7)" : muted,
      }}
    >
      {children}
    </div>
  );
}

// ─── Buttons ──────────────────────────────────────────────

export function PrimaryBtn({
  children,
  onClick,
  disabled = false,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        width: "100%",
        background: ink,
        color: "#fff",
        border: "none",
        borderRadius: 18,
        padding: "16px 24px",
        fontSize: 16,
        fontWeight: 700,
        letterSpacing: -0.2,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.4 : 1,
        boxShadow: disabled ? "none" : "0 8px 24px rgba(10,10,10,0.18)",
        fontFamily: "-apple-system, system-ui, sans-serif",
        transition: "opacity .2s, box-shadow .2s",
      }}
    >
      {children}
    </button>
  );
}

export function BackBtn({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        position: "absolute",
        top: 20,
        left: 16,
        background: "transparent",
        border: "none",
        color: muted,
        fontSize: 15,
        fontWeight: 600,
        cursor: "pointer",
        padding: "8px 12px",
        fontFamily: "-apple-system, system-ui, sans-serif",
        minHeight: 44,
        minWidth: 44,
        display: "flex",
        alignItems: "center",
        gap: 4,
        zIndex: 10,
      }}
    >
      ← Volver
    </button>
  );
}

// ─── Keyframes (injected once) ────────────────────────────

export function OnboardingStyles() {
  return (
    <style>{`
      @keyframes bounceIn { 0%{transform:scale(0) rotate(-25deg)} 60%{transform:scale(1.2) rotate(8deg)} 100%{transform:scale(1) rotate(0)} }
      @keyframes subPop { from{opacity:0;transform:translateY(6px) scale(.85)} to{opacity:1;transform:translateY(0) scale(1)} }
      @keyframes pctIn { from{opacity:0;transform:scale(.5) rotate(-4deg)} to{opacity:1;transform:scale(1) rotate(0)} }
      @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
      @keyframes fadeUp2 { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
      @keyframes exIn { from{opacity:0;transform:translateY(8px) scale(.85)} to{opacity:1;transform:translateY(0) scale(1)} }
      @keyframes intro100 { from{opacity:0;transform:scale(.6)} to{opacity:1;transform:scale(1)} }
      @keyframes splitGrow { to { width: var(--w); } }
      @keyframes spin { to { transform: rotate(360deg); } }
      @keyframes dBar { to { width: var(--w); } }
      @keyframes dRow { to { opacity: 1; } }
      @keyframes hlIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
      @keyframes cScan { 0%,100%{top:0} 50%{top:calc(100% - 2px)} }
      @keyframes td { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-3px)} }
    `}</style>
  );
}
