import { useState, useMemo } from 'react';
import { useData } from '../../context/DataContext';
import { useCatalog } from '../../context/CatalogContext';
import { useMonth } from '../../context/MonthContext';
import { Screen, SectionHead, Bar, Pill, fmt, fmtK } from './shared';

const GROUPS = [
  { id: 'necesidades', label: 'Necesidades', pct: 50, desc: 'Lo que necesitás sí o sí: vivienda, comida, transporte, salud' },
  { id: 'deseos', label: 'Deseos', pct: 30, desc: 'Lo que te hace bien pero podés cortar: ocio, gustos, compras' },
  { id: 'ahorro', label: 'Ahorro', pct: 20, desc: 'Lo que separás antes de gastar — emergencia, metas, inversiones' },
];

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

interface CatsScreenProps {
  onEditCat: (categoryId: string) => void;
  onCreateCat: () => void;
  onEditBudget: () => void;
}

export function CatsScreen({ onEditCat, onCreateCat, onEditBudget }: CatsScreenProps) {
  const { categories } = useCatalog();
  const { budgets } = useData();
  const { selectedMonth } = useMonth();

  const [expandedCat, setExpandedCat] = useState<string | null>(null);
  const [showTheory, setShowTheory] = useState(false);

  // Month navigation
  const [localMonth, setLocalMonth] = useState(selectedMonth);

  const goLeft = () => {
    setLocalMonth((prev) => {
      if (prev.month === 0) return { month: 11, year: prev.year - 1 };
      return { month: prev.month - 1, year: prev.year };
    });
  };

  const goRight = () => {
    setLocalMonth((prev) => {
      if (prev.month === 11) return { month: 0, year: prev.year + 1 };
      return { month: prev.month + 1, year: prev.year };
    });
  };

  // Total budget amount
  const totalBudget = useMemo(
    () => budgets.reduce((sum, b) => sum + b.amount, 0),
    [budgets]
  );

  // Ingresos approximation: sum of all budget amounts (used as income proxy for 50/30/20)
  const ingresos = totalBudget;

  // Group categories by bucket
  const groupedCategories = useMemo(() => {
    const map: Record<string, typeof categories> = {
      necesidades: [],
      deseos: [],
      ahorro: [],
    };
    categories.forEach((cat) => {
      const bucket = cat.bucket || 'deseos';
      if (map[bucket]) {
        map[bucket].push(cat);
      } else {
        map.deseos.push(cat);
      }
    });
    return map;
  }, [categories]);

  // Spending per group
  const groupStats = useMemo(() => {
    return GROUPS.map((g) => {
      const cats = groupedCategories[g.id] || [];
      const spent = cats.reduce((sum, cat) => {
        const b = budgets.find((bgt) => bgt.categoryId === cat.id);
        return sum + (b?.spent || 0);
      }, 0);
      const target = (ingresos * g.pct) / 100;
      return { ...g, spent, target };
    });
  }, [groupedCategories, budgets, ingresos]);

  return (
    <Screen>
      {/* Month switcher */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginBottom: 24 }}>
        <button
          onClick={goLeft}
          style={{ background: 'none', border: 'none', fontSize: 20, color: 'var(--color-text)', cursor: 'pointer' }}
        >
          ‹
        </button>
        <span style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600 }}>
          {MONTH_NAMES[localMonth.month]} {localMonth.year}
        </span>
        <button
          onClick={goRight}
          style={{ background: 'none', border: 'none', fontSize: 20, color: 'var(--color-text)', cursor: 'pointer' }}
        >
          ›
        </button>
      </div>

      {/* Budget total */}
      <div
        style={{ textAlign: 'center', marginBottom: 28, cursor: 'pointer' }}
        onClick={onEditBudget}
      >
        <p style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--color-muted)', marginBottom: 4 }}>
          Presupuesto del mes
        </p>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 700, color: 'var(--color-text)' }}>
          {fmt(totalBudget)}
        </p>
      </div>

      {/* 50/30/20 distribution */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
        {groupStats.map((g) => {
          const pct = g.target > 0 ? Math.min((g.spent / g.target) * 100, 100) : 0;
          return (
            <div key={g.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)' }}>{g.label}</span>
                <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>
                  Gastado {fmtK(g.spent)} / {fmtK(g.target)}
                </span>
              </div>
              <Bar value={pct} />
            </div>
          );
        })}
      </div>

      {/* 50/30/20 theory card */}
      <div
        style={{
          background: 'var(--color-surface-dark, #1a1a2e)',
          borderRadius: 12,
          padding: 16,
          marginBottom: 24,
          cursor: 'pointer',
        }}
        onClick={() => setShowTheory(!showTheory)}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-light, #fff)' }}>
            La regla 50/30/20
          </span>
          <span style={{ fontSize: 16, color: 'var(--color-text-light, #fff)' }}>
            {showTheory ? '▾' : '▸'}
          </span>
        </div>
        {showTheory && (
          <div style={{ marginTop: 12, fontSize: 13, lineHeight: 1.5, color: 'var(--color-muted-light, #ccc)' }}>
            <p style={{ marginBottom: 8 }}>
              Dividí tus ingresos en tres bloques:
            </p>
            <p style={{ marginBottom: 4 }}><strong>50% Necesidades</strong> — gastos fijos que no podés evitar.</p>
            <p style={{ marginBottom: 4 }}><strong>30% Deseos</strong> — lo que elegís para disfrutar.</p>
            <p><strong>20% Ahorro</strong> — lo que guardás para el futuro.</p>
          </div>
        )}
      </div>

      {/* Nueva category button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <Pill onClick={onCreateCat}>+ Nueva</Pill>
      </div>

      {/* Category groups */}
      {GROUPS.map((group) => {
        const cats = groupedCategories[group.id] || [];
        const stats = groupStats.find((gs) => gs.id === group.id)!;
        const groupPct = stats.target > 0 ? Math.min((stats.spent / stats.target) * 100, 100) : 0;

        return (
          <div key={group.id} style={{ marginBottom: 28 }}>
            {/* Group header */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <SectionHead>{group.label}</SectionHead>
                <Pill>{group.pct}%</Pill>
              </div>
              <Bar value={groupPct} />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>
                  {fmt(stats.spent)} gastado
                </span>
                <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>
                  de {fmt(stats.target)}
                </span>
              </div>
            </div>

            {/* Category cards */}
            {cats.map((cat) => {
              const budget = budgets.find((b) => b.categoryId === cat.id);
              const spent = budget?.spent || 0;
              const amount = budget?.amount || 0;
              const catPct = amount > 0 ? Math.min((spent / amount) * 100, 100) : 0;
              const isExpanded = expandedCat === cat.id;
              const subcats = cat.subcategories || [];

              return (
                <div
                  key={cat.id}
                  style={{
                    background: 'var(--color-surface)',
                    borderRadius: 12,
                    padding: 14,
                    marginBottom: 8,
                    border: '1px solid var(--color-border, transparent)',
                  }}
                >
                  {/* Category row */}
                  <div
                    style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
                    onClick={() => setExpandedCat(isExpanded ? null : cat.id)}
                  >
                    <span style={{ fontSize: 22 }}>{cat.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)' }}>{cat.name}</span>
                        <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--color-text)' }}>
                          {fmt(spent)}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 2 }}>
                        <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>
                          {subcats.length} subcategoría{subcats.length !== 1 ? 's' : ''}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>
                          {isExpanded ? '▾' : '▸'}
                        </span>
                      </div>
                      <div style={{ marginTop: 6 }}>
                        <Bar value={catPct} color={cat.color} />
                      </div>
                    </div>
                  </div>

                  {/* Expanded: subcategories */}
                  {isExpanded && (
                    <div style={{ marginTop: 12, paddingLeft: 36 }}>
                      {subcats.map((sub) => (
                        <div
                          key={sub.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            paddingBlock: 6,
                            borderBottom: '1px solid var(--color-border, rgba(255,255,255,0.06))',
                          }}
                        >
                          <span
                            style={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              background: 'var(--color-lime, #a3e635)',
                              flexShrink: 0,
                            }}
                          />
                          <span style={{ fontSize: 13, color: 'var(--color-text)' }}>{sub.name}</span>
                        </div>
                      ))}

                      {/* Edit button */}
                      <button
                        onClick={() => onEditCat(cat.id)}
                        style={{
                          marginTop: 10,
                          background: 'none',
                          border: '1px solid var(--color-border, rgba(255,255,255,0.15))',
                          borderRadius: 8,
                          padding: '6px 12px',
                          fontSize: 12,
                          color: 'var(--color-text)',
                          cursor: 'pointer',
                        }}
                      >
                        Editar categoría
                      </button>

                      {/* Add subcategory */}
                      <button
                        style={{
                          marginTop: 6,
                          marginLeft: 8,
                          background: 'none',
                          border: 'none',
                          fontSize: 12,
                          color: 'var(--color-lime, #a3e635)',
                          cursor: 'pointer',
                          padding: '6px 0',
                        }}
                      >
                        + Agregar subcategoría
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        );
      })}

      {/* Fina suggestions card */}
      <div
        style={{
          background: 'var(--color-accent-dark, #1e293b)',
          borderRadius: 12,
          padding: 16,
          marginTop: 12,
        }}
      >
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-lime, #a3e635)', marginBottom: 6 }}>
          Sugerencia de Fina
        </p>
        <p style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--color-text-light, #e2e8f0)' }}>
          Revisá las categorías sin presupuesto asignado. Definir un límite te ayuda a detectar desvíos antes de fin de mes.
        </p>
      </div>
    </Screen>
  );
}
