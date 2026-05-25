import React, { type ReactNode, type RefObject, useState } from "react";

/* ─────────────────────────────────────────────
   Currency formatting
   ───────────────────────────────────────────── */

const CURRENCY_SYMBOLS: Record<string, string> = {
  ARS: "$",
  USD: "US$",
  BRL: "R$",
  MXN: "MX$",
};

interface FmtOpts {
  sign?: boolean;
  decimals?: number;
  currency?: string;
}

export function fmt(n: number, opts: FmtOpts = {}): string {
  const { sign = false, decimals = 0, currency = "ARS" } = opts;
  const abs = Math.abs(n);
  const intPart = Math.floor(abs);
  const decPart = decimals > 0 ? abs.toFixed(decimals).split(".")[1] : "";

  // Format integer with "." as thousands separator
  const intStr = intPart.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const formatted = decimals > 0 ? `${intStr},${decPart}` : intStr;

  const sym = CURRENCY_SYMBOLS[currency] ?? "$";
  const prefix = sign && n !== 0 ? (n > 0 ? "+" : "-") : n < 0 ? "-" : "";
  return `${prefix}${sym}${formatted}`;
}

export function fmtK(n: number): string {
  const abs = Math.abs(n);
  const prefix = n < 0 ? "-" : "";
  if (abs >= 1_000_000) {
    const v = abs / 1_000_000;
    return `${prefix}$${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}M`;
  }
  if (abs >= 1_000) {
    const v = abs / 1_000;
    return `${prefix}$${v % 1 === 0 ? v.toFixed(0) : v.toFixed(0)}K`;
  }
  return `${prefix}$${abs}`;
}

/* ─────────────────────────────────────────────
   NavIcons — inline SVG icon functions
   ───────────────────────────────────────────── */

export const NavIcons = {
  home: (c: string) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" />
      <path d="M9 21V12h6v9" />
    </svg>
  ),
  gastos: (c: string) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="5" width="20" height="15" rx="2" />
      <path d="M2 10h20" />
    </svg>
  ),
  cats: (c: string) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2v20M2 12h20" />
      <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10" />
      <path d="M12 2a15.3 15.3 0 00-4 10 15.3 15.3 0 004 10" />
    </svg>
  ),
  reglas: (c: string) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 113 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  ),
};

/* ─────────────────────────────────────────────
   FinaLogo
   ───────────────────────────────────────────── */

interface FinaLogoProps {
  size?: number;
  mark?: boolean;
}

export function FinaLogo({ size = 28, mark = false }: FinaLogoProps) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span
        style={{
          width: size,
          height: size,
          borderRadius: size * 0.28,
          background: "var(--lime)",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontSize: size * 0.6,
            lineHeight: 1,
            color: "var(--ink-stable)",
            fontWeight: 400,
          }}
        >
          F
        </span>
      </span>
      {!mark && (
        <span
          style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontSize: size * 0.82,
            lineHeight: 1,
            color: "var(--fg)",
          }}
        >
          Fina
        </span>
      )}
    </span>
  );
}

/* ─────────────────────────────────────────────
   TopBar
   ───────────────────────────────────────────── */

interface TopBarProps {
  onMenu?: () => void;
  onNotif?: () => void;
  onRefresh?: () => Promise<void>;
  balance?: number;
  label?: string;
}

export function TopBar({ onMenu, onNotif, onRefresh, balance, label = "Disponible" }: TopBarProps) {
  const [spinning, setSpinning] = useState(false);

  async function handleRefresh() {
    if (!onRefresh || spinning) return;
    setSpinning(true);
    try { await onRefresh(); } finally { setSpinning(false); }
  }
  const btnStyle: React.CSSProperties = {
    width: 40,
    height: 40,
    borderRadius: "var(--r-md)",
    border: "1px solid var(--hairline)",
    background: "var(--surface)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    color: "var(--fg)",
    padding: 0,
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 16px",
        background: "var(--surface)",
        borderBottom: "1px solid var(--hairline)",
      }}
    >
      {/* Hamburger */}
      <button style={btnStyle} onClick={onMenu} aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>

      {/* Balance pill */}
      {balance !== undefined && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 0,
          }}
        >
          <span
            style={{
              fontSize: 10,
              fontWeight: 500,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--fg-3)",
            }}
          >
            {label}
          </span>
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 16,
              fontWeight: 600,
              color: "var(--fg)",
              fontFeatureSettings: '"ss01","tnum"',
            }}
          >
            {fmt(balance)}
          </span>
        </div>
      )}

      {/* Right side: refresh + bell */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {onRefresh && (
          <button style={btnStyle} onClick={handleRefresh} aria-label="Actualizar" title="Actualizar datos">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
              style={{ transform: spinning ? 'rotate(360deg)' : 'rotate(0deg)', transition: spinning ? 'transform 0.6s linear' : 'none' }}>
              <path d="M23 4v6h-6" />
              <path d="M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
          </button>
        )}
      {/* Bell */}
      <button style={btnStyle} onClick={onNotif} aria-label="Notifications">
        <span style={{ position: "relative", display: "inline-flex" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 01-3.46 0" />
          </svg>
          <span
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--lime)",
              border: "1.5px solid var(--surface)",
            }}
          />
        </span>
      </button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   BottomBar
   ───────────────────────────────────────────── */

type TabId = "home" | "gastos" | "chat" | "cats" | "reglas";
const TAB_LABELS: Record<TabId, string> = {
  home: "Inicio",
  gastos: "Gastos",
  chat: "Fina",
  cats: "Presupuesto",
  reglas: "Reglas",
};

interface BottomBarProps {
  tab: TabId;
  onTab: (id: TabId) => void;
}

export function BottomBar({ tab, onTab }: BottomBarProps) {
  const tabs: TabId[] = ["home", "gastos", "chat", "cats", "reglas"];

  const renderIcon = (id: TabId, active: boolean) => {
    const c = active ? "var(--lime)" : "var(--fg-3)";
    if (id === "chat") return null; // handled separately
    const iconFn = NavIcons[id as keyof typeof NavIcons];
    return iconFn ? iconFn(c) : null;
  };

  return (
    <div
      style={{
        position: "fixed",
        bottom: 16,
        left: 16,
        right: 16,
        background: "var(--surface)",
        borderRadius: "var(--r-xl)",
        border: "1px solid var(--hairline)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-around",
        padding: "6px 4px",
        zIndex: 100,
        boxShadow: "0 4px 24px rgba(0,0,0,.08)",
      }}
    >
      {tabs.map((id) => {
        const active = tab === id;
        const isCenter = id === "chat";

        if (isCenter) {
          return (
            <button
              key={id}
              onClick={() => onTab(id)}
              style={{
                width: 52,
                height: 52,
                borderRadius: "50%",
                background: "var(--lime)",
                border: "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginTop: -20,
                cursor: "pointer",
                boxShadow: "0 2px 12px rgba(213,240,58,.35)",
                position: "relative",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--serif)",
                  fontStyle: "italic",
                  fontSize: 24,
                  color: "var(--ink-stable)",
                  lineHeight: 1,
                }}
              >
                F
              </span>
              {/* sparkle */}
              <span
                style={{
                  position: "absolute",
                  top: 2,
                  right: 2,
                  fontSize: 10,
                }}
              >
                ✦
              </span>
            </button>
          );
        }

        return (
          <button
            key={id}
            onClick={() => onTab(id)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 2,
              background: "none",
              border: "none",
              padding: "6px 12px",
              cursor: "pointer",
              position: "relative",
            }}
          >
            {renderIcon(id, active)}
            <span
              style={{
                fontSize: 10,
                fontWeight: 500,
                color: active ? "var(--lime)" : "var(--fg-3)",
              }}
            >
              {TAB_LABELS[id]}
            </span>
            {active && (
              <span
                style={{
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  background: "var(--lime)",
                  position: "absolute",
                  bottom: 0,
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Screen
   ───────────────────────────────────────────── */

interface ScreenProps {
  children: ReactNode;
  padBottom?: number;
  scrollRef?: RefObject<HTMLDivElement>;
}

export function Screen({ children, padBottom = 100, scrollRef }: ScreenProps) {
  return (
    <div
      ref={scrollRef as React.Ref<HTMLDivElement>}
      className="fina-scroll"
      style={{
        flex: 1,
        overflowY: "auto",
        paddingBottom: padBottom,
        minHeight: "100%",
        background: "var(--bg)",
        color: "var(--fg)",
      }}
    >
      {children}
    </div>
  );
}

/* ─────────────────────────────────────────────
   SectionHead
   ───────────────────────────────────────────── */

interface SectionHeadProps {
  title: string;
  trailing?: string;
  onTrailing?: () => void;
}

export function SectionHead({ title, trailing, onTrailing }: SectionHeadProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        padding: "16px 16px 8px",
      }}
    >
      <span
        style={{
          fontFamily: "var(--serif)",
          fontStyle: "italic",
          fontSize: 20,
          color: "var(--fg)",
        }}
      >
        {title}
      </span>
      {trailing && (
        <button
          onClick={onTrailing}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            fontSize: 13,
            fontWeight: 500,
            color: "var(--lime-deep)",
            cursor: "pointer",
          }}
        >
          {trailing}
        </button>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   CatTile
   ───────────────────────────────────────────── */

const TONE_COLORS: Record<string, { bg: string }> = {
  surface: { bg: "var(--surface)" },
  paper:   { bg: "var(--surface-2)" },
  lime:    { bg: "var(--lime-tint)" },
  soft:    { bg: "var(--surface-3)" },
};

interface CatTileProps {
  name: string;
  emoji?: string;
  size?: number;
  tone?: "surface" | "paper" | "lime" | "soft";
}

export function CatTile({ name, emoji, size = 36, tone = "surface" }: CatTileProps) {
  const t = TONE_COLORS[tone] ?? TONE_COLORS.surface;
  return (
    <div
      title={name}
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.28,
        background: t.bg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.5,
        lineHeight: 1,
        flexShrink: 0,
      }}
    >
      {emoji ?? name.charAt(0)}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Bar
   ───────────────────────────────────────────── */

interface BarProps {
  pct: number;
  color?: string;
  track?: string;
  height?: number;
}

export function Bar({
  pct,
  color = "var(--lime)",
  track = "var(--surface-2)",
  height = 6,
}: BarProps) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div
      style={{
        width: "100%",
        height,
        borderRadius: height / 2,
        background: track,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: `${clamped}%`,
          height: "100%",
          borderRadius: height / 2,
          background: color,
          transition: "width .3s ease",
        }}
      />
    </div>
  );
}

/* ─────────────────────────────────────────────
   Pill
   ───────────────────────────────────────────── */

type PillTone = "neutral" | "lime" | "limeSoft" | "warn" | "neg" | "pos" | "paper";

const PILL_TONES: Record<PillTone, React.CSSProperties> = {
  neutral: {
    background: "var(--surface-2)",
    color: "var(--fg-2)",
    border: "1px solid var(--hairline)",
  },
  lime: {
    background: "var(--pill-lime-bg)",
    color: "var(--pill-lime-fg)",
    border: "1px solid var(--pill-lime-bd)",
  },
  limeSoft: {
    background: "var(--lime-tint)",
    color: "var(--lime-deep)",
    border: "1px solid var(--lime-tint-2)",
  },
  warn: {
    background: "var(--pill-warn-bg)",
    color: "var(--pill-warn-fg)",
    border: "1px solid var(--pill-warn-bd)",
  },
  neg: {
    background: "var(--pill-neg-bg)",
    color: "var(--pill-neg-fg)",
    border: "1px solid var(--pill-neg-bd)",
  },
  pos: {
    background: "var(--pill-pos-bg)",
    color: "var(--pill-pos-fg)",
    border: "1px solid var(--pill-pos-bd)",
  },
  paper: {
    background: "var(--surface)",
    color: "var(--fg-2)",
    border: "1px solid var(--hairline)",
  },
};

interface PillProps {
  children: ReactNode;
  tone?: PillTone;
}

export function Pill({ children, tone = "neutral" }: PillProps) {
  const s = PILL_TONES[tone] ?? PILL_TONES.neutral;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.02em",
        whiteSpace: "nowrap",
        ...s,
      }}
    >
      {children}
    </span>
  );
}

/* ─────────────────────────────────────────────
   SourceBadge
   ───────────────────────────────────────────── */

const SOURCE_MAP: Record<string, { label: string; color: string }> = {
  bank:  { label: "Banco", color: "var(--fg-3)" },
  photo: { label: "Foto",  color: "#6BA3D6" },
  wpp:   { label: "WPP",   color: "#25D366" },
  audio: { label: "Audio", color: "#A78BFA" },
};

interface SourceBadgeProps {
  src: string;
}

export function SourceBadge({ src }: SourceBadgeProps) {
  const info = SOURCE_MAP[src] ?? { label: src, color: "var(--fg-3)" };
  return (
    <span
      style={{
        display: "inline-block",
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: info.color,
        lineHeight: 1,
      }}
    >
      {info.label}
    </span>
  );
}

/* ─────────────────────────────────────────────
   PaceRing
   ───────────────────────────────────────────── */

interface PaceRingProps {
  pct: number;
  pacePct: number;
  size?: number;
  stroke?: number;
}

export function PaceRing({ pct, pacePct, size = 100, stroke = 8 }: PaceRingProps) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  const clampedPct = Math.max(0, Math.min(100, pct));
  const progressOffset = circumference - (clampedPct / 100) * circumference;

  // Pace tick angle (0 = top, clockwise)
  const clampedPace = Math.max(0, Math.min(100, pacePct));
  const paceAngle = (clampedPace / 100) * 360 - 90; // -90 because SVG starts at 3 o'clock
  const paceRad = (paceAngle * Math.PI) / 180;
  const tickInner = radius - 4;
  const tickOuter = radius + 4;
  const x1 = center + tickInner * Math.cos(paceRad);
  const y1 = center + tickInner * Math.sin(paceRad);
  const x2 = center + tickOuter * Math.cos(paceRad);
  const y2 = center + tickOuter * Math.sin(paceRad);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Track */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="var(--surface-2)"
        strokeWidth={stroke}
      />
      {/* Progress */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="var(--lime)"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={progressOffset}
        transform={`rotate(-90 ${center} ${center})`}
        style={{ transition: "stroke-dashoffset .4s ease" }}
      />
      {/* Pace tick */}
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke="var(--fg-3)"
        strokeWidth={2}
        strokeLinecap="round"
      />
    </svg>
  );
}

/* ─────────────────────────────────────────────
   ConfirmDialog
   ───────────────────────────────────────────── */

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  body?: string;
  danger?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  body,
  danger = false,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0,0,0,.55)",
      }}
      onClick={onCancel}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--ink-stable)",
          color: "var(--paper-stable)",
          borderRadius: "var(--r-lg)",
          padding: "24px",
          width: "min(340px, calc(100vw - 48px))",
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div
          style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontSize: 20,
            lineHeight: 1.2,
          }}
        >
          {title}
        </div>

        {body && (
          <div style={{ fontSize: 14, lineHeight: 1.5, opacity: 0.8 }}>
            {body}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 4 }}>
          <button
            onClick={onCancel}
            style={{
              padding: "8px 18px",
              borderRadius: "var(--r-md)",
              border: "1px solid rgba(255,255,255,.15)",
              background: "transparent",
              color: "var(--paper-stable)",
              fontSize: 14,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            style={{
              padding: "8px 18px",
              borderRadius: "var(--r-md)",
              border: "none",
              background: danger ? "var(--neg)" : "var(--lime)",
              color: danger ? "#fff" : "var(--ink-stable)",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
