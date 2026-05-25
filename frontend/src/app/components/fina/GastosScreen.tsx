import { useState, useMemo, useRef, useCallback } from 'react';
import { useData } from '../../context/DataContext';
import { useCatalog } from '../../context/CatalogContext';
import { Screen, fmt, fmtK, Pill, Bar, SourceBadge } from './shared';
import type { Transaction, Category } from '../../../lib/api';

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const MONTHS = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
];

const DAYS = ['Dom', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab'];

function dayLabel(dateStr: string): string {
  const today = new Date();
  const d = new Date(dateStr + 'T12:00:00');
  const todayStr = today.toISOString().slice(0, 10);
  const yesterdayDate = new Date(today);
  yesterdayDate.setDate(yesterdayDate.getDate() - 1);
  const yesterdayStr = yesterdayDate.toISOString().slice(0, 10);

  if (dateStr === todayStr) return 'Hoy';
  if (dateStr === yesterdayStr) return 'Ayer';

  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

function groupByDay(txs: Transaction[]): { date: string; label: string; total: number; items: Transaction[] }[] {
  const map = new Map<string, Transaction[]>();
  for (const t of txs) {
    const key = t.date;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(t);
  }
  const groups = Array.from(map.entries())
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([date, items]) => ({
      date,
      label: dayLabel(date),
      total: items.reduce((s, t) => s + Math.abs(t.amount), 0),
      items: items.sort((a, b) => b.id.localeCompare(a.id)),
    }));
  return groups;
}

function lookupCategory(categories: Category[], categoryId: string) {
  return categories.find((c) => c.id === categoryId);
}

function lookupSubcategory(categories: Category[], categoryId: string, subcategoryId?: string) {
  if (!subcategoryId) return undefined;
  const cat = lookupCategory(categories, categoryId);
  return cat?.subcategories?.find((s) => s.id === subcategoryId);
}

/* ------------------------------------------------------------------ */
/*  TxRow                                                              */
/* ------------------------------------------------------------------ */

const SWIPE_THRESHOLD = 50;   // px to trigger snap
const SWIPE_MAX      = 152;  // width of both action buttons combined (76 each)
const BTN_W          = 76;

export function TxRow({
  t,
  categories,
  onTap,
  onDelete,
}: {
  t: Transaction;
  categories?: Category[];
  onTap?: (t: Transaction) => void;
  onDelete?: (t: Transaction) => void;
}) {
  const cats = categories ?? [];
  const cat = lookupCategory(cats, t.categoryId);
  const sub = lookupSubcategory(cats, t.categoryId, t.subcategoryId);

  const [offset, setOffset] = useState(0);
  const [snapped, setSnapped] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const startX = useRef(0);
  const dragging = useRef(false);

  const snapBack = useCallback(() => { setOffset(0); setSnapped(false); }, []);

  function onTouchStart(e: React.TouchEvent) {
    startX.current = e.touches[0].clientX;
    dragging.current = true;
  }
  function onTouchMove(e: React.TouchEvent) {
    if (!dragging.current) return;
    const dx = e.touches[0].clientX - startX.current;
    // only allow swipe left (negative dx)
    setOffset(Math.max(-SWIPE_MAX, Math.min(0, dx)));
  }
  function onTouchEnd() {
    dragging.current = false;
    if (offset < -SWIPE_THRESHOLD) {
      setOffset(-SWIPE_MAX);
      setSnapped(true);
    } else {
      snapBack();
    }
  }

  function handleTap() {
    if (snapped) { snapBack(); return; }
    onTap?.(t);
  }

  function handleDelete() {
    snapBack();
    setConfirmDelete(true);
  }

  function handleEdit() {
    snapBack();
    onTap?.(t);
  }

  return (
    <>
      {/* Inline confirm */}
      {confirmDelete && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px',
          borderRadius: 14,
          background: '#fff',
          border: '1px solid var(--border,#f0f0f0)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}>
          <span style={{ fontSize: 13, color: 'var(--text-secondary,#555)', flex: 1 }}>
            ¿Eliminar <strong>{t.description || 'este movimiento'}</strong>?
          </span>
          <button onClick={() => setConfirmDelete(false)} style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--border,#ddd)', background: 'transparent', fontSize: 13, cursor: 'pointer', color: 'var(--text-secondary,#666)', whiteSpace: 'nowrap' }}>
            No
          </button>
          <button onClick={() => { setConfirmDelete(false); onDelete?.(t); }} style={{ padding: '6px 12px', borderRadius: 8, border: 'none', background: '#ef4444', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' }}>
            Eliminar
          </button>
        </div>
      )}

      {!confirmDelete && (
        <div style={{
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 14,
          background: '#fff',
          border: '1px solid var(--border,#f0f0f0)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}>
          {/* Action buttons — revealed on the right when swiping left */}
          <div style={{
            position: 'absolute', right: 0, top: 0, bottom: 0,
            width: SWIPE_MAX,
            display: 'flex',
          }}>
            {/* Editar — lime */}
            <button
              onClick={handleEdit}
              style={{
                width: BTN_W, border: 'none', cursor: 'pointer',
                background: 'var(--lime, #a3e635)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1a2e05" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
              <span style={{ fontSize: 10, fontWeight: 700, color: '#1a2e05' }}>Editar</span>
            </button>

            {/* Eliminar — rojo */}
            <button
              onClick={handleDelete}
              style={{
                width: BTN_W, border: 'none', cursor: 'pointer',
                background: '#ef4444',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
                <path d="M10 11v6M14 11v6"/>
                <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
              </svg>
              <span style={{ fontSize: 10, fontWeight: 700, color: '#fff' }}>Eliminar</span>
            </button>
          </div>

          {/* Row */}
          <div
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
            onClick={handleTap}
            style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
              cursor: 'pointer',
              transform: `translateX(${offset}px)`,
              transition: dragging.current ? 'none' : 'transform 0.22s ease',
              background: '#fff',
              position: 'relative', zIndex: 1,
              userSelect: 'none', WebkitUserSelect: 'none',
            }}
          >
            <div style={{ width: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, flexShrink: 0 }}>
              {cat?.icon ?? ''}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-primary,#1a1a1a)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {t.description || 'Sin descripcion'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary,#999)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>{cat?.name ?? 'Sin cat.'}{sub ? ` / ${sub.name}` : ''}</span>
                <SourceBadge source={(t as any).medioCarga ?? (t as any).origen ?? ''} />
              </div>
            </div>
            <div style={{ fontFamily: 'var(--font-mono,"SF Mono",monospace)', fontSize: 15, fontWeight: 600, color: t.amount < 0 ? 'var(--text-primary,#1a1a1a)' : '#34C759', whiteSpace: 'nowrap', textAlign: 'right' }}>
              {t.amount < 0 ? `-${fmt(Math.abs(t.amount))}` : `+${fmt(t.amount)}`}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Segmented Control                                                  */
/* ------------------------------------------------------------------ */

function SegmentedControl({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div
      style={{
        display: 'flex',
        background: 'var(--surface-secondary, #f0f0f0)',
        borderRadius: 10,
        padding: 3,
        gap: 2,
      }}
    >
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          style={{
            flex: 1,
            padding: '7px 0',
            fontSize: 13,
            fontWeight: value === o.value ? 600 : 400,
            color: value === o.value ? 'var(--text-primary, #1a1a1a)' : 'var(--text-secondary, #666)',
            background: value === o.value ? 'var(--surface-primary, #fff)' : 'transparent',
            border: 'none',
            borderRadius: 8,
            cursor: 'pointer',
            transition: 'all 0.2s',
            boxShadow: value === o.value ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Search Bar                                                         */
/* ------------------------------------------------------------------ */

function SearchBar({
  value,
  onChange,
  expanded,
  onToggle,
}: {
  value: string;
  onChange: (v: string) => void;
  expanded: boolean;
  onToggle: () => void;
}) {
  if (!expanded) {
    return (
      <button
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 14px',
          fontSize: 14,
          color: 'var(--text-tertiary, #999)',
          background: 'var(--surface-secondary, #f5f5f5)',
          border: 'none',
          borderRadius: 10,
          cursor: 'pointer',
          width: '100%',
        }}
      >
        <span style={{ fontSize: 16 }}>&#x1F50D;</span>
        Buscar movimiento...
      </button>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <input
        autoFocus
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Buscar por comercio o categoria..."
        style={{
          width: '100%',
          padding: '10px 36px 10px 14px',
          fontSize: 15,
          border: '1.5px solid var(--border-active, #ccc)',
          borderRadius: 10,
          outline: 'none',
          background: 'var(--surface-primary, #fff)',
          color: 'var(--text-primary, #1a1a1a)',
          boxSizing: 'border-box',
        }}
      />
      <button
        onClick={() => {
          onChange('');
          onToggle();
        }}
        style={{
          position: 'absolute',
          right: 8,
          top: '50%',
          transform: 'translateY(-50%)',
          background: 'none',
          border: 'none',
          fontSize: 18,
          color: 'var(--text-tertiary, #999)',
          cursor: 'pointer',
          padding: 4,
        }}
      >
        &times;
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Filter Chips                                                       */
/* ------------------------------------------------------------------ */

function FilterChips({
  categories,
  selected,
  onSelect,
}: {
  categories: Category[];
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        overflowX: 'auto',
        paddingBottom: 4,
        WebkitOverflowScrolling: 'touch',
        scrollbarWidth: 'none',
      }}
    >
      <button
        onClick={() => onSelect(null)}
        style={{
          padding: '6px 14px',
          fontSize: 13,
          fontWeight: selected === null ? 600 : 400,
          color: selected === null ? '#fff' : 'var(--text-secondary, #666)',
          background: selected === null ? 'var(--color-primary, #007AFF)' : 'var(--surface-secondary, #f0f0f0)',
          border: 'none',
          borderRadius: 20,
          cursor: 'pointer',
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}
      >
        Todas
      </button>
      {categories.map((c) => (
        <button
          key={c.id}
          onClick={() => onSelect(c.id)}
          style={{
            padding: '6px 14px',
            fontSize: 13,
            fontWeight: selected === c.id ? 600 : 400,
            color: selected === c.id ? '#fff' : 'var(--text-secondary, #666)',
            background: selected === c.id ? (c.color || 'var(--color-primary, #007AFF)') : 'var(--surface-secondary, #f0f0f0)',
            border: 'none',
            borderRadius: 20,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          {c.icon} {c.name}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Category Breakdown View                                            */
/* ------------------------------------------------------------------ */

function CategoryView({
  categories,
  transactions,
  budgets,
}: {
  categories: Category[];
  transactions: Transaction[];
  budgets: { categoryId: string; amount: number; spent: number }[];
}) {
  const breakdown = useMemo(() => {
    const map = new Map<string, { spent: number; count: number }>();
    for (const t of transactions) {
      if (t.amount >= 0) continue;
      const entry = map.get(t.categoryId) ?? { spent: 0, count: 0 };
      entry.spent += Math.abs(t.amount);
      entry.count += 1;
      map.set(t.categoryId, entry);
    }

    const totalSpent = Array.from(map.values()).reduce((s, e) => s + e.spent, 0);

    return categories
      .map((c) => {
        const data = map.get(c.id) ?? { spent: 0, count: 0 };
        const budget = budgets.find((b) => b.categoryId === c.id);
        const budgetAmt = budget?.amount ?? 0;
        const pct = budgetAmt > 0 ? Math.round((data.spent / budgetAmt) * 100) : 0;
        const barPct = totalSpent > 0 ? (data.spent / totalSpent) * 100 : 0;
        return { ...c, spent: data.spent, count: data.count, budgetAmt, pct, barPct };
      })
      .filter((c) => c.spent > 0)
      .sort((a, b) => b.spent - a.spent);
  }, [categories, transactions, budgets]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Stacked bar chart */}
      <div style={{ borderRadius: 8, overflow: 'hidden', height: 10, display: 'flex' }}>
        {breakdown.map((c) => (
          <div
            key={c.id}
            style={{
              width: `${c.barPct}%`,
              background: c.color || '#ccc',
              opacity: 0.75,
              minWidth: c.barPct > 0 ? 3 : 0,
              transition: 'width 0.3s',
            }}
            title={`${c.name}: ${fmt(c.spent)}`}
          />
        ))}
      </div>

      {/* Category list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {breakdown.map((c) => {
          // Bar = % of assigned budget; fallback to % of total if no budget set
          const barPct = c.budgetAmt > 0 ? c.pct : c.barPct;
          const isOver = c.budgetAmt > 0 && c.pct > 100;

          return (
            <div
              key={c.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '10px 0',
                borderBottom: '1px solid var(--border, #f0f0f0)',
              }}
            >
              <div
                style={{
                  width: 32,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 20,
                  flexShrink: 0,
                }}
              >
                {c.icon}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 5 }}>
                  <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary, #1a1a1a)' }}>
                    {c.name}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                    <span
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        fontFamily: 'var(--font-mono, "SF Mono", monospace)',
                        color: isOver ? '#ef4444' : 'var(--text-primary, #1a1a1a)',
                      }}
                    >
                      {fmtK(c.spent)}
                    </span>
                    {c.budgetAmt > 0 && (
                      <span style={{ fontSize: 11, color: 'var(--text-tertiary, #999)' }}>
                        / {fmtK(c.budgetAmt)}
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <Bar
                      pct={barPct}
                      color={c.color || '#ccc'}
                      fillOpacity={0.65}
                      overColor="#ef4444"
                      height={5}
                    />
                  </div>
                  <span style={{ fontSize: 11, color: isOver ? '#ef4444' : 'var(--text-tertiary, #999)', whiteSpace: 'nowrap', minWidth: 36, textAlign: 'right' }}>
                    {c.budgetAmt > 0 ? `${c.pct}%` : `${c.count} mov${c.count !== 1 ? 's' : ''}`}
                  </span>
                </div>
                {c.budgetAmt === 0 && (
                  <span style={{ fontSize: 10, color: 'var(--text-tertiary, #aaa)', marginTop: 1, display: 'block' }}>
                    {c.count} mov{c.count !== 1 ? 's' : ''} · sin presupuesto
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  GastosScreen                                                       */
/* ------------------------------------------------------------------ */

export function GastosScreen({
  onTab,
  onEditTx,
  onDeleteTx,
}: {
  onTab?: (tab: string) => void;
  onEditTx?: (t: Transaction) => void;
  onDeleteTx?: (t: Transaction) => void;
}) {
  const { transactions, budgets } = useData();
  const { categories } = useCatalog();

  const [view, setView] = useState<'movimientos' | 'categoria'>('movimientos');
  const [search, setSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [filterCat, setFilterCat] = useState<string | null>(null);

  // Only expenses (negative amounts)
  const expenses = useMemo(
    () => transactions.filter((t) => t.amount < 0),
    [transactions],
  );

  // Totals
  const totalGastado = useMemo(
    () => expenses.reduce((s, t) => s + Math.abs(t.amount), 0),
    [expenses],
  );

  const totalPresupuesto = useMemo(
    () => budgets.reduce((s, b) => s + b.amount, 0),
    [budgets],
  );

  const pctPresupuesto = totalPresupuesto > 0 ? Math.round((totalGastado / totalPresupuesto) * 100) : 0;

  // Filtered expenses
  const filtered = useMemo(() => {
    let result = expenses;
    if (filterCat) {
      result = result.filter((t) => t.categoryId === filterCat);
    }
    if (search.trim()) {
      const q = search.toLowerCase().trim();
      result = result.filter((t) => {
        const cat = lookupCategory(categories, t.categoryId);
        return (
          t.description?.toLowerCase().includes(q) ||
          cat?.name?.toLowerCase().includes(q)
        );
      });
    }
    return result;
  }, [expenses, filterCat, search, categories]);

  // Day groups
  const groups = useMemo(() => groupByDay(filtered), [filtered]);

  // Current month label
  const now = new Date();
  const monthLabel = `${MONTHS[now.getMonth()]} ${now.getFullYear()}`;

  // Categories that have expenses (for filter chips)
  const activeCategories = useMemo(() => {
    const ids = new Set(expenses.map((t) => t.categoryId));
    return categories.filter((c) => ids.has(c.id));
  }, [expenses, categories]);

  return (
    <Screen onTab={onTab}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '0 16px 24px' }}>
        {/* --- Header --- */}
        <div style={{ textAlign: 'center', padding: '8px 0 0' }}>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: 1,
              color: 'var(--text-tertiary, #999)',
              marginBottom: 4,
            }}
          >
            Gastos del mes
          </div>
          <div
            style={{
              fontSize: 34,
              fontWeight: 700,
              fontFamily: 'var(--font-mono, "SF Mono", monospace)',
              color: 'var(--text-primary, #1a1a1a)',
              lineHeight: 1.1,
            }}
          >
            {fmt(totalGastado)}
          </div>
          <div style={{ marginTop: 8, display: 'flex', justifyContent: 'center', gap: 8, alignItems: 'center' }}>
            {totalPresupuesto > 0 && (
              <Pill
                label={`${pctPresupuesto}% del presup.`}
                variant={pctPresupuesto > 100 ? 'danger' : pctPresupuesto > 80 ? 'warning' : 'default'}
              />
            )}
          </div>
          <div
            style={{
              fontSize: 13,
              color: 'var(--text-tertiary, #999)',
              marginTop: 6,
            }}
          >
            {monthLabel} &middot; {expenses.length} movimiento{expenses.length !== 1 ? 's' : ''}
          </div>
        </div>

        {/* --- Segmented control --- */}
        <SegmentedControl
          options={[
            { label: 'Movimientos', value: 'movimientos' },
            { label: 'Por categoria', value: 'categoria' },
          ]}
          value={view}
          onChange={(v) => setView(v as any)}
        />

        {/* --- Search + Filters (only in movimientos view) --- */}
        {view === 'movimientos' && (
          <>
            <SearchBar
              value={search}
              onChange={setSearch}
              expanded={searchOpen}
              onToggle={() => setSearchOpen((p) => !p)}
            />
            <FilterChips categories={activeCategories} selected={filterCat} onSelect={setFilterCat} />
          </>
        )}

        {/* --- Content --- */}
        {view === 'movimientos' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {groups.length === 0 && (
              <div
                style={{
                  textAlign: 'center',
                  padding: '40px 0',
                  color: 'var(--text-tertiary, #999)',
                  fontSize: 14,
                }}
              >
                No hay gastos{search || filterCat ? ' con estos filtros' : ''}
              </div>
            )}
            {groups.map((g) => (
              <div key={g.date}>
                {/* Day header */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    marginBottom: 8,
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary, #666)' }}>
                    {g.label}
                  </span>
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      fontFamily: 'var(--font-mono, "SF Mono", monospace)',
                      color: 'var(--text-tertiary, #999)',
                    }}
                  >
                    {fmtK(g.total)}
                  </span>
                </div>
                {/* Transactions card */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {g.items.map((t) => (
                    <TxRow
                      key={t.id}
                      t={t}
                      categories={categories}
                      onTap={onEditTx}
                      onDelete={onDeleteTx}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <CategoryView categories={categories} transactions={expenses} budgets={budgets} />
        )}
      </div>
    </Screen>
  );
}
