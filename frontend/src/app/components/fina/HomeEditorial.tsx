import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useData } from '../../context/DataContext';
import { useMonth, type MonthYear } from '../../context/MonthContext';

/* ── helpers ─────────────────────────────────────────── */

const MONTHS = [
  'Enero','Febrero','Marzo','Abril','Mayo','Junio',
  'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre',
];

const DAYS = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];

function fmt(n: number): string {
  return n.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtK(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 10_000) return `${Math.round(n / 1_000)}k`;
  return fmt(n);
}

function daysInMonth(month: number, year: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Buen día';
  if (h < 19) return 'Buenas tardes';
  return 'Buenas noches';
}

function monthPill(m: MonthYear): string {
  const now = new Date();
  const cur = now.getFullYear() * 12 + now.getMonth();
  const sel = m.year * 12 + m.month;
  if (sel === cur) return 'actual';
  return sel < cur ? 'pasado' : 'futuro';
}

/* ── SimpleTxRow ─────────────────────────────────────── */

function SimpleTxRow({
  emoji,
  color,
  merchant,
  categoryName,
  date,
  source,
  amount,
}: {
  emoji: string;
  color: string;
  merchant: string;
  categoryName: string;
  date: string;
  source?: string;
  amount: number;
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '10px 0',
        borderBottom: '1px solid var(--border, rgba(255,255,255,0.08))',
      }}
    >
      {/* emoji tile */}
      <div
        style={{
          width: 38,
          height: 38,
          borderRadius: 10,
          background: color || 'var(--surface, #1a1a1a)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 18,
          flexShrink: 0,
        }}
      >
        {emoji || '💰'}
      </div>

      {/* text block */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontWeight: 600,
            fontSize: 14,
            color: 'var(--fg, #fff)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {merchant || 'Sin descripción'}
        </div>
        <div
          style={{
            fontSize: 12,
            color: 'var(--fg-muted, #888)',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            marginTop: 2,
          }}
        >
          <span>{categoryName}</span>
          <span>·</span>
          <span>{date}</span>
          {source && (
            <>
              <span>·</span>
              <span
                style={{
                  background: 'var(--surface, #222)',
                  padding: '1px 6px',
                  borderRadius: 4,
                  fontSize: 10,
                  textTransform: 'uppercase',
                  letterSpacing: 0.5,
                }}
              >
                {source}
              </span>
            </>
          )}
        </div>
      </div>

      {/* amount */}
      <div
        style={{
          fontWeight: 600,
          fontSize: 14,
          color: amount < 0 ? 'var(--fg, #fff)' : 'var(--lime, #a3e635)',
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}
      >
        {amount < 0 ? `-$${fmt(Math.abs(amount))}` : `+$${fmt(amount)}`}
      </div>
    </div>
  );
}

/* ── PaceRing (local) ────────────────────────────────── */

function PaceRing({ pct, size = 72 }: { pct: number; size?: number }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const clamped = Math.min(Math.max(pct, 0), 100);
  const offset = circ - (clamped / 100) * circ;
  const color = pct > 100 ? '#ef4444' : pct > 85 ? '#f59e0b' : 'var(--lime, #a3e635)';

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="var(--border, rgba(255,255,255,0.08))"
        strokeWidth={6}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={6}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
      />
    </svg>
  );
}

/* ── HomeEditorial ───────────────────────────────────── */

export function HomeEditorial({ onTab }: { onTab: (tab: string) => void }) {
  const { user } = useAuth();
  const { categories, transactions, budgets, isLoading } = useData();
  const { selectedMonth, setSelectedMonth, isCurrentMonth } = useMonth();

  /* ── computed data ───────────────────────────────── */

  const { gastado, presupuesto, disponible, ingresos, usedPct, dayPct, pace, dailySafe, daysLeft } =
    useMemo(() => {
      const txs = transactions ?? [];
      const bds = budgets ?? [];

      const gastado = txs
        .filter((t) => t.amount < 0)
        .reduce((s, t) => s + Math.abs(t.amount), 0);

      const ingresos = txs
        .filter((t) => t.amount > 0)
        .reduce((s, t) => s + t.amount, 0);

      const presupuesto = bds.reduce((s, b) => s + (b.amount ?? 0), 0);
      const disponible = Math.max(presupuesto - gastado, 0);

      const totalDays = daysInMonth(selectedMonth.month, selectedMonth.year);
      const now = new Date();
      const elapsed =
        selectedMonth.year === now.getFullYear() && selectedMonth.month === now.getMonth()
          ? now.getDate()
          : totalDays;
      const daysLeft = Math.max(totalDays - elapsed, 1);

      const usedPct = presupuesto > 0 ? (gastado / presupuesto) * 100 : 0;
      const dayPct = elapsed / totalDays;
      const pace = usedPct / 100 - dayPct;
      const dailySafe = daysLeft > 0 ? disponible / daysLeft : 0;

      return { gastado, presupuesto, disponible, ingresos, usedPct, dayPct, pace, dailySafe, daysLeft };
    }, [transactions, budgets, selectedMonth]);

  /* ── date strings ────────────────────────────────── */

  const today = new Date();
  const totalDays = daysInMonth(selectedMonth.month, selectedMonth.year);
  const dayOfMonth = isCurrentMonth ? today.getDate() : totalDays;

  const dateLine = isCurrentMonth
    ? `${DAYS[today.getDay()]} ${today.getDate()}, ${MONTHS[today.getMonth()].toLowerCase()} · Día ${today.getDate()} de ${totalDays}`
    : `${MONTHS[selectedMonth.month]} ${selectedMonth.year}`;

  /* ── month nav ───────────────────────────────────── */

  function prevMonth() {
    const m = selectedMonth.month === 0 ? 11 : selectedMonth.month - 1;
    const y = selectedMonth.month === 0 ? selectedMonth.year - 1 : selectedMonth.year;
    setSelectedMonth({ month: m, year: y });
  }

  function nextMonth() {
    const m = selectedMonth.month === 11 ? 0 : selectedMonth.month + 1;
    const y = selectedMonth.month === 11 ? selectedMonth.year + 1 : selectedMonth.year;
    setSelectedMonth({ month: m, year: y });
  }

  /* ── pace label ──────────────────────────────────── */

  const paceLabel = pace > 0.05
    ? 'Por encima del ritmo'
    : pace < -0.05
      ? 'Por debajo del ritmo'
      : 'A buen ritmo';

  const paceColor = pace > 0.05
    ? '#ef4444'
    : pace < -0.05
      ? 'var(--lime, #a3e635)'
      : 'var(--fg-muted, #888)';

  /* ── category map ────────────────────────────────── */

  const catMap = useMemo(() => {
    const m = new Map<string, { name: string; icon: string; color: string }>();
    (categories ?? []).forEach((c) => m.set(c.id, { name: c.name, icon: c.icon, color: c.color }));
    return m;
  }, [categories]);

  /* ── recent transactions ─────────────────────────── */

  const recentTxs = useMemo(() => {
    return [...(transactions ?? [])]
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      .slice(0, 4);
  }, [transactions]);

  /* ── pill style ──────────────────────────────────── */

  const pill = monthPill(selectedMonth);
  const pillBg =
    pill === 'actual'
      ? 'var(--lime, #a3e635)'
      : pill === 'pasado'
        ? 'var(--fg-muted, #888)'
        : '#60a5fa';
  const pillFg = pill === 'actual' ? '#000' : '#fff';

  /* ── loading ─────────────────────────────────────── */

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100dvh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--fg-muted, #888)',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        Cargando...
      </div>
    );
  }

  /* ── render ──────────────────────────────────────── */

  return (
    <div
      style={{
        minHeight: '100dvh',
        background: 'var(--bg, #0a0a0a)',
        color: 'var(--fg, #fff)',
        fontFamily: 'system-ui, sans-serif',
        padding: '16px 20px 100px',
        maxWidth: 480,
        margin: '0 auto',
      }}
    >
      {/* ── Month Switcher ────────────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          marginBottom: 4,
        }}
      >
        <button
          onClick={prevMonth}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--fg-muted, #888)',
            fontSize: 20,
            cursor: 'pointer',
            padding: '4px 8px',
          }}
          aria-label="Mes anterior"
        >
          ‹
        </button>

        <div style={{ textAlign: 'center' }}>
          <span
            style={{
              fontFamily: 'Georgia, "Times New Roman", serif',
              fontStyle: 'italic',
              fontSize: 20,
              fontWeight: 400,
            }}
          >
            {MONTHS[selectedMonth.month]}
            {selectedMonth.year !== today.getFullYear() ? ` ${selectedMonth.year}` : ''}
          </span>

          <span
            style={{
              marginLeft: 8,
              fontSize: 11,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: 0.8,
              background: pillBg,
              color: pillFg,
              padding: '2px 8px',
              borderRadius: 20,
              verticalAlign: 'middle',
            }}
          >
            {pill}
          </span>
        </div>

        <button
          onClick={nextMonth}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--fg-muted, #888)',
            fontSize: 20,
            cursor: 'pointer',
            padding: '4px 8px',
          }}
          aria-label="Mes siguiente"
        >
          ›
        </button>
      </div>

      {/* ── Date line ─────────────────────────────── */}
      <div
        style={{
          textAlign: 'center',
          fontSize: 13,
          color: 'var(--fg-muted, #888)',
          marginBottom: 28,
        }}
      >
        {dateLine}
      </div>

      {/* ── Greeting ──────────────────────────────── */}
      <h1
        style={{
          fontFamily: 'Georgia, "Times New Roman", serif',
          fontStyle: 'italic',
          fontWeight: 400,
          fontSize: 28,
          lineHeight: 1.25,
          margin: '0 0 6px',
        }}
      >
        {greeting()}, {user?.name?.split(' ')[0] ?? 'ahí'}.
      </h1>

      {/* ── Daily safe amount ─────────────────────── */}
      <p
        style={{
          fontSize: 14,
          color: 'var(--fg-muted, #888)',
          margin: '0 0 28px',
          lineHeight: 1.5,
        }}
      >
        Hoy podés gastar hasta{' '}
        <span
          style={{
            color: 'var(--lime, #a3e635)',
            fontWeight: 700,
          }}
        >
          ${fmt(Math.round(dailySafe))}
        </span>{' '}
        sin pasarte del ritmo
      </p>

      {/* ── Pace card ─────────────────────────────── */}
      <div
        style={{
          background: 'var(--surface, #141414)',
          borderRadius: 16,
          padding: '20px 20px 18px',
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 18,
        }}
      >
        <PaceRing pct={usedPct} size={72} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, color: 'var(--fg-muted, #888)', marginBottom: 4 }}>
            Disponible este mes
          </div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>${fmtK(disponible)}</div>
          <div style={{ fontSize: 12, color: paceColor, marginTop: 2 }}>{paceLabel}</div>
        </div>
      </div>

      {/* ── Summary row ───────────────────────────── */}
      <div
        style={{
          display: 'flex',
          gap: 10,
          marginBottom: 16,
        }}
      >
        {[
          { label: 'Gastado', value: gastado, color: 'var(--fg, #fff)' },
          { label: 'Presupuesto', value: presupuesto, color: 'var(--fg-muted, #888)' },
          { label: 'Ingresos', value: ingresos, color: 'var(--lime, #a3e635)' },
        ].map((item) => (
          <div
            key={item.label}
            style={{
              flex: 1,
              background: 'var(--surface, #141414)',
              borderRadius: 12,
              padding: '12px 14px',
            }}
          >
            <div style={{ fontSize: 11, color: 'var(--fg-muted, #888)', marginBottom: 4 }}>
              {item.label}
            </div>
            <div style={{ fontSize: 16, fontWeight: 600, color: item.color }}>
              ${fmtK(item.value)}
            </div>
          </div>
        ))}
      </div>

      {/* ── CTA chat card ─────────────────────────── */}
      <button
        onClick={() => onTab('chat')}
        style={{
          width: '100%',
          background: 'var(--fg, #fff)',
          color: 'var(--bg, #0a0a0a)',
          border: 'none',
          borderRadius: 14,
          padding: '16px 20px',
          marginBottom: 24,
          cursor: 'pointer',
          textAlign: 'left',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 15 }}>
          ¿Puedo gastar algo hoy?
        </span>
        <span style={{ fontSize: 18 }}>→</span>
      </button>

      {/* ── Recent transactions ───────────────────── */}
      <div
        style={{
          background: 'var(--surface, #141414)',
          borderRadius: 16,
          padding: '16px 18px 8px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 8,
          }}
        >
          <span style={{ fontSize: 14, fontWeight: 600 }}>Últimos movimientos</span>
          <button
            onClick={() => onTab('gastos')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--lime, #a3e635)',
              fontSize: 13,
              cursor: 'pointer',
              padding: 0,
            }}
          >
            Ver todos →
          </button>
        </div>

        {recentTxs.length === 0 && (
          <div
            style={{
              padding: '20px 0',
              textAlign: 'center',
              color: 'var(--fg-muted, #888)',
              fontSize: 13,
            }}
          >
            Sin movimientos este mes
          </div>
        )}

        {recentTxs.map((tx) => {
          const cat = catMap.get(tx.categoryId);
          const dateStr = tx.date
            ? new Date(tx.date).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
            : '';

          return (
            <SimpleTxRow
              key={tx.id}
              emoji={cat?.icon ?? '💰'}
              color={cat?.color ?? '#333'}
              merchant={tx.description || tx.descripcion || 'Sin descripción'}
              categoryName={cat?.name ?? 'Sin categoría'}
              date={dateStr}
              amount={tx.amount}
            />
          );
        })}
      </div>
    </div>
  );
}

export default HomeEditorial;
