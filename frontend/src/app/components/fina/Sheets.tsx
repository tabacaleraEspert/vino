import { useState, useEffect, useRef } from 'react';
import { useData } from '../../context/DataContext';
import { useCatalog } from '../../context/CatalogContext';
import { useAuth } from '../../context/AuthContext';
import { api } from '@/lib/api';
import { fmt, fmtK } from './shared';

/* ─────────────────────────────────────────────────────────────
   Shared styles & helpers
   ───────────────────────────────────────────────────────────── */

const SCRIM: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.55)',
  zIndex: 900,
  transition: 'opacity 320ms cubic-bezier(.2,0,.2,1)',
};

const SHEET_BASE: React.CSSProperties = {
  position: 'fixed',
  left: 0,
  right: 0,
  bottom: 0,
  background: 'var(--ink-stable)',
  color: 'var(--paper-stable)',
  borderRadius: '18px 18px 0 0',
  maxHeight: '94vh',
  overflowY: 'auto',
  zIndex: 910,
  transition: 'transform 320ms cubic-bezier(.2,0,.2,1)',
};

const LIME = '#D5F03A';
const SERIF = "'Instrument Serif', 'Times New Roman', serif";
const SANS = "'Geist', -apple-system, BlinkMacSystemFont, system-ui, sans-serif";
const MONO = "'Geist Mono', 'SF Mono', ui-monospace, monospace";

function CloseBtn({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'none',
        border: 'none',
        color: 'var(--paper-stable)',
        fontSize: 22,
        padding: 8,
        lineHeight: 1,
        opacity: 0.7,
      }}
    >
      &#x2715;
    </button>
  );
}

/* ─────────────────────────────────────────────────────────────
   1. NewExpenseSheet
   ───────────────────────────────────────────────────────────── */

interface ExpenseInitial {
  id: string;
  amount: number;
  description: string;
  date: string;
  categoryId: string;
  subcategoryId?: string;
}

interface NewExpenseSheetProps {
  open: boolean;
  onClose: () => void;
  initial?: ExpenseInitial;
  onDelete?: (id: string) => void;
}

export function NewExpenseSheet({ open, onClose, initial, onDelete }: NewExpenseSheetProps) {
  const { updateTransaction } = useData();
  const { categories, expenseCategories, incomeCategories } = useCatalog();

  const isEditing = !!initial;

  const [tipo, setTipo] = useState<'Gasto' | 'Ingreso'>('Gasto');
  const [amount, setAmount] = useState(initial?.amount?.toString() ?? '');
  const [currency, setCurrency] = useState<'ARS' | 'USD'>('ARS');
  const [date, setDate] = useState(initial?.date ?? new Date().toISOString().slice(0, 10));
  const [categoryId, setCategoryId] = useState(initial?.categoryId ?? '');
  const [subcategoryId, setSubcategoryId] = useState(initial?.subcategoryId ?? '');
  const [merchant, setMerchant] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');
  const [note, setNote] = useState(initial?.description ?? '');
  const [saving, setSaving] = useState(false);

  const filteredCategories = tipo === 'Ingreso' ? incomeCategories : expenseCategories;
  const accentColor = tipo === 'Ingreso' ? '#22c55e' : LIME;

  useEffect(() => {
    if (initial) {
      setAmount(initial.amount?.toString() ?? '');
      setDate(initial.date ?? new Date().toISOString().slice(0, 10));
      setCategoryId(initial.categoryId ?? '');
      setSubcategoryId(initial.subcategoryId ?? '');
      setNote(initial.description ?? '');
    } else {
      setTipo('Gasto');
      setAmount('');
      setDate(new Date().toISOString().slice(0, 10));
      setCategoryId('');
      setSubcategoryId('');
      setMerchant('');
      setPaymentMethod('');
      setNote('');
    }
  }, [initial, open]);

  const selectedCategory = categories.find(c => c.id === categoryId);

  function handleNumpad(key: string) {
    if (key === 'del') {
      setAmount(prev => prev.slice(0, -1));
    } else if (key === ',') {
      if (!amount.includes(',')) setAmount(prev => prev + ',');
    } else {
      setAmount(prev => prev + key);
    }
  }

  function parseAmount(): number {
    return parseFloat(amount.replace(',', '.')) || 0;
  }

  async function handleSave() {
    setSaving(true);
    try {
      if (isEditing && initial) {
        await updateTransaction(initial.id, {
          amount: parseAmount(),
          description: note,
          date,
          categoryId,
          subcategoryId,
        });
      } else {
        // Convert date from YYYY-MM-DD to DD/MM/YYYY
        const [y, m, d] = date.split('-');
        const fechaFormatted = `${d}/${m}/${y}`;
        await api.movimientos.create({
          fecha: fechaFormatted,
          monto: parseAmount(),
          tipo_movimiento: tipo,
          descripcion: note || merchant || (tipo === 'Ingreso' ? 'Ingreso manual' : 'Gasto manual'),
          id_categoria: parseInt(categoryId) || undefined,
          id_subcategoria: parseInt(subcategoryId) || undefined,
          moneda: currency,
        });
      }
      onClose();
    } catch (e) {
      console.error('Error saving expense', e);
    } finally {
      setSaving(false);
    }
  }

  const numpadKeys = ['1','2','3','4','5','6','7','8','9',',','0','del'];

  if (!open) return null;

  return (
    <>
      <div style={{ ...SCRIM, opacity: open ? 1 : 0 }} onClick={onClose} />
      <div style={{ ...SHEET_BASE, transform: open ? 'translateY(0)' : 'translateY(100%)' }}>
        <div style={{ padding: '20px 20px 0' }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 32, height: 32, borderRadius: '50%',
                background: accentColor, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 16, color: '#14130F', fontWeight: 700,
              }}>
                {isEditing ? '✎' : '+'}
              </div>
              {isEditing ? (
                <span style={{ fontFamily: SANS, fontSize: 13, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                  EDITAR {tipo === 'Ingreso' ? 'INGRESO' : 'GASTO'}
                </span>
              ) : (
                <div style={{ display: 'flex', borderRadius: 8, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.15)' }}>
                  {(['Gasto', 'Ingreso'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => { setTipo(t); setCategoryId(''); setSubcategoryId(''); }}
                      style={{
                        padding: '4px 12px',
                        border: 'none',
                        fontSize: 11,
                        fontWeight: 700,
                        fontFamily: SANS,
                        letterSpacing: '0.05em',
                        textTransform: 'uppercase',
                        background: tipo === t ? (t === 'Ingreso' ? '#22c55e' : LIME) : 'transparent',
                        color: tipo === t ? '#14130F' : 'rgba(255,255,255,0.5)',
                        cursor: 'pointer',
                        transition: 'all 200ms',
                      }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <CloseBtn onClick={onClose} />
          </div>

          {/* Amount display */}
          <div style={{ marginTop: 24, textAlign: 'center' }}>
            <span style={{ fontFamily: MONO, fontSize: 44, fontWeight: 300 }}>
              ${amount || '0'}
            </span>
            <span style={{
              display: 'inline-block',
              width: 2, height: 36,
              background: LIME,
              marginLeft: 2,
              animation: 'blink 1s step-end infinite',
              verticalAlign: 'middle',
            }} />
            <style>{`@keyframes blink { 50% { opacity: 0; } }`}</style>
          </div>

          {/* Chips: currency + date */}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 12 }}>
            {(['ARS', 'USD'] as const).map(c => (
              <button
                key={c}
                onClick={() => setCurrency(c)}
                style={{
                  padding: '4px 12px',
                  borderRadius: 20,
                  border: 'none',
                  fontSize: 12,
                  fontWeight: 600,
                  background: currency === c ? LIME : 'rgba(255,255,255,0.1)',
                  color: currency === c ? '#14130F' : 'var(--paper-stable)',
                }}
              >
                {c}
              </button>
            ))}
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              style={{
                padding: '4px 10px',
                borderRadius: 20,
                border: 'none',
                fontSize: 12,
                background: 'rgba(255,255,255,0.1)',
                color: 'var(--paper-stable)',
              }}
            />
          </div>

          {/* Category picker */}
          <div style={{ marginTop: 20, overflowX: 'auto', whiteSpace: 'nowrap', paddingBottom: 8 }}>
            {filteredCategories.map(cat => (
              <button
                key={cat.id}
                onClick={() => { setCategoryId(cat.id); setSubcategoryId(''); }}
                style={{
                  display: 'inline-block',
                  padding: '6px 14px',
                  marginRight: 6,
                  borderRadius: 20,
                  border: 'none',
                  fontSize: 12,
                  fontWeight: 500,
                  background: categoryId === cat.id ? accentColor : 'rgba(255,255,255,0.08)',
                  color: categoryId === cat.id ? '#14130F' : 'var(--paper-stable)',
                }}
              >
                {cat.icon} {cat.name}
              </button>
            ))}
          </div>

          {/* Subcategory chips */}
          {selectedCategory?.subcategories && selectedCategory.subcategories.length > 0 && (
            <div style={{ marginTop: 8, overflowX: 'auto', whiteSpace: 'nowrap', paddingBottom: 8 }}>
              {selectedCategory.subcategories.map(sub => (
                <button
                  key={sub.id}
                  onClick={() => setSubcategoryId(sub.id)}
                  style={{
                    display: 'inline-block',
                    padding: '4px 12px',
                    marginRight: 6,
                    borderRadius: 16,
                    border: '1px solid rgba(255,255,255,0.15)',
                    fontSize: 11,
                    background: subcategoryId === sub.id ? 'rgba(213,240,58,0.2)' : 'transparent',
                    color: subcategoryId === sub.id ? LIME : 'var(--paper-stable)',
                  }}
                >
                  {sub.name}
                </button>
              ))}
            </div>
          )}

          {/* Merchant input */}
          <input
            placeholder="Comercio"
            value={merchant}
            onChange={e => setMerchant(e.target.value)}
            style={{
              width: '100%',
              marginTop: 12,
              padding: '10px 14px',
              borderRadius: 10,
              border: 'none',
              background: 'rgba(255,255,255,0.06)',
              color: 'var(--paper-stable)',
              fontSize: 14,
            }}
          />

          {/* Payment method */}
          <input
            placeholder="Medio de pago"
            value={paymentMethod}
            onChange={e => setPaymentMethod(e.target.value)}
            style={{
              width: '100%',
              marginTop: 8,
              padding: '10px 14px',
              borderRadius: 10,
              border: 'none',
              background: 'rgba(255,255,255,0.06)',
              color: 'var(--paper-stable)',
              fontSize: 14,
            }}
          />

          {/* Note */}
          <input
            placeholder="Nota"
            value={note}
            onChange={e => setNote(e.target.value)}
            style={{
              width: '100%',
              marginTop: 8,
              padding: '10px 14px',
              borderRadius: 10,
              border: 'none',
              background: 'rgba(255,255,255,0.06)',
              color: 'var(--paper-stable)',
              fontSize: 14,
            }}
          />

          {/* Numpad */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 8,
            marginTop: 16,
            paddingBottom: 8,
          }}>
            {numpadKeys.map(key => (
              <button
                key={key}
                onClick={() => handleNumpad(key)}
                style={{
                  padding: '14px 0',
                  borderRadius: 10,
                  border: 'none',
                  background: 'rgba(255,255,255,0.06)',
                  color: 'var(--paper-stable)',
                  fontSize: 20,
                  fontFamily: MONO,
                  fontWeight: 500,
                }}
              >
                {key === 'del' ? '⌫' : key}
              </button>
            ))}
          </div>

          {/* CTAs */}
          <div style={{ display: 'flex', gap: 10, padding: '12px 0 24px' }}>
            {isEditing && onDelete && initial && (
              <button
                onClick={() => { onDelete(initial.id); onClose(); }}
                style={{
                  flex: 1,
                  padding: '14px',
                  borderRadius: 12,
                  border: 'none',
                  background: '#E66A3F',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Eliminar
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={saving || !amount}
              style={{
                flex: 2,
                padding: '14px',
                borderRadius: 12,
                border: 'none',
                background: accentColor,
                color: '#14130F',
                fontWeight: 700,
                fontSize: 14,
                opacity: saving || !amount ? 0.5 : 1,
              }}
            >
              {saving ? '...' : isEditing ? 'Guardar cambios' : tipo === 'Ingreso' ? 'Registrar ingreso' : 'Registrar gasto'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/* ─────────────────────────────────────────────────────────────
   2. CategoryEditSheet
   ───────────────────────────────────────────────────────────── */

interface CategoryInitial {
  id: string;
  name: string;
  icon: string;
  color: string;
  bucket?: string;
  subcategories?: { id: string; name: string }[];
}

interface CategoryEditSheetProps {
  open: boolean;
  onClose: () => void;
  initial?: CategoryInitial;
  onDelete?: (id: string) => void;
}

const EMOJI_GRID = [
  '🍔','🏠','🚗','💊','🎬','🛒',
  '✈️','📚','🎵','💡','👕','🏋️',
  '☕','🍷','🎮','📱','💳','🎁',
];

const BUCKET_OPTIONS = [
  { value: 'necesidades', label: '50% Necesidades', desc: 'Gastos esenciales' },
  { value: 'deseos', label: '30% Deseos', desc: 'Gastos opcionales' },
  { value: 'ahorro', label: '20% Ahorro', desc: 'Ahorro e inversiones' },
];

export function CategoryEditSheet({ open, onClose, initial, onDelete }: CategoryEditSheetProps) {
  const { addCategory, updateCategory, deleteCategory, addSubcategory, deleteSubcategory } = useCatalog();

  const isEditing = !!initial;

  const [name, setName] = useState(initial?.name ?? '');
  const [icon, setIcon] = useState(initial?.icon ?? '🍔');
  const [bucket, setBucket] = useState(initial?.bucket ?? 'necesidades');
  const [budgetAmount, setBudgetAmount] = useState('');
  const [subcategories, setSubcategories] = useState<{ id: string; name: string }[]>(initial?.subcategories ?? []);
  const [newSub, setNewSub] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (initial) {
      setName(initial.name ?? '');
      setIcon(initial.icon ?? '🍔');
      setBucket(initial.bucket ?? 'necesidades');
      setSubcategories(initial.subcategories ?? []);
    } else {
      setName('');
      setIcon('🍔');
      setBucket('necesidades');
      setBudgetAmount('');
      setSubcategories([]);
    }
  }, [initial, open]);

  function handleAddSub() {
    if (!newSub.trim()) return;
    setSubcategories(prev => [...prev, { id: `new_${Date.now()}`, name: newSub.trim() }]);
    setNewSub('');
  }

  function handleRemoveSub(id: string) {
    setSubcategories(prev => prev.filter(s => s.id !== id));
  }

  async function handleSave() {
    setSaving(true);
    try {
      if (isEditing && initial) {
        await updateCategory(initial.id, { name, icon, bucket });
      } else {
        await addCategory({ name, icon, color: LIME, bucket });
      }
      onClose();
    } catch (e) {
      console.error('Error saving category', e);
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  return (
    <>
      <div style={{ ...SCRIM, opacity: open ? 1 : 0 }} onClick={onClose} />
      <div style={{ ...SHEET_BASE, transform: open ? 'translateY(0)' : 'translateY(100%)' }}>
        <div style={{ padding: '20px 20px 24px' }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontFamily: SANS, fontSize: 13, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              {isEditing ? 'EDITAR CATEGORIA' : 'NUEVA CATEGORIA'}
            </span>
            <CloseBtn onClick={onClose} />
          </div>

          {/* Hero: emoji + name */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 20 }}>
            <div style={{
              width: 66, height: 66, borderRadius: 14,
              background: LIME, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 32,
            }}>
              {icon}
            </div>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Nombre"
              style={{
                flex: 1,
                border: 'none',
                background: 'transparent',
                color: 'var(--paper-stable)',
                fontFamily: SERIF,
                fontStyle: 'italic',
                fontSize: 28,
                outline: 'none',
                borderBottom: '1px solid rgba(255,255,255,0.15)',
                paddingBottom: 4,
              }}
            />
          </div>

          {/* Emoji picker */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: 8,
            marginTop: 16,
          }}>
            {EMOJI_GRID.map(e => (
              <button
                key={e}
                onClick={() => setIcon(e)}
                style={{
                  padding: '8px 0',
                  borderRadius: 8,
                  border: icon === e ? `2px solid ${LIME}` : '2px solid transparent',
                  background: icon === e ? 'rgba(213,240,58,0.12)' : 'rgba(255,255,255,0.04)',
                  fontSize: 22,
                  cursor: 'pointer',
                }}
              >
                {e}
              </button>
            ))}
          </div>

          {/* Group picker (50/30/20) */}
          <div style={{ marginTop: 20 }}>
            {BUCKET_OPTIONS.map(opt => (
              <label
                key={opt.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 12px',
                  borderRadius: 10,
                  marginBottom: 6,
                  background: bucket === opt.value ? 'rgba(213,240,58,0.1)' : 'transparent',
                  border: bucket === opt.value ? `1px solid ${LIME}` : '1px solid rgba(255,255,255,0.08)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="bucket"
                  value={opt.value}
                  checked={bucket === opt.value}
                  onChange={() => setBucket(opt.value)}
                  style={{ accentColor: LIME }}
                />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{opt.label}</div>
                  <div style={{ fontSize: 11, opacity: 0.6 }}>{opt.desc}</div>
                </div>
              </label>
            ))}
          </div>

          {/* Budget input */}
          <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 18, fontFamily: MONO }}>$</span>
            <input
              type="number"
              placeholder="0"
              value={budgetAmount}
              onChange={e => setBudgetAmount(e.target.value)}
              style={{
                flex: 1,
                padding: '10px 12px',
                borderRadius: 10,
                border: 'none',
                background: 'rgba(255,255,255,0.06)',
                color: 'var(--paper-stable)',
                fontSize: 18,
                fontFamily: MONO,
              }}
            />
            <span style={{ fontSize: 11, opacity: 0.5 }}>ARS &middot; MES</span>
          </div>

          {/* Subcategories */}
          <div style={{ marginTop: 20 }}>
            <div style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8, opacity: 0.6 }}>
              Subcategorias
            </div>
            {subcategories.map(sub => (
              <div key={sub.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', borderRadius: 8, marginBottom: 4, background: 'rgba(255,255,255,0.04)' }}>
                <span style={{ fontSize: 13 }}>{sub.name}</span>
                <button
                  onClick={() => handleRemoveSub(sub.id)}
                  style={{ background: 'none', border: 'none', color: '#E66A3F', fontSize: 16, padding: 4 }}
                >
                  &#x2715;
                </button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
              <input
                placeholder="Nueva subcategoria"
                value={newSub}
                onChange={e => setNewSub(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleAddSub()}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: 'none',
                  background: 'rgba(255,255,255,0.06)',
                  color: 'var(--paper-stable)',
                  fontSize: 13,
                }}
              />
              <button
                onClick={handleAddSub}
                style={{
                  padding: '8px 14px',
                  borderRadius: 8,
                  border: 'none',
                  background: LIME,
                  color: '#14130F',
                  fontWeight: 600,
                  fontSize: 13,
                }}
              >
                +
              </button>
            </div>
          </div>

          {/* CTAs */}
          <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
            {isEditing && onDelete && initial && (
              <button
                onClick={() => { onDelete(initial.id); onClose(); }}
                style={{
                  flex: 1,
                  padding: '14px',
                  borderRadius: 12,
                  border: 'none',
                  background: '#E66A3F',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Eliminar
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={saving || !name.trim()}
              style={{
                flex: 2,
                padding: '14px',
                borderRadius: 12,
                border: 'none',
                background: LIME,
                color: '#14130F',
                fontWeight: 700,
                fontSize: 14,
                opacity: saving || !name.trim() ? 0.5 : 1,
              }}
            >
              {saving ? '...' : isEditing ? 'Guardar cambios' : 'Crear categoria'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/* ─────────────────────────────────────────────────────────────
   3. Drawer — helpers
   ───────────────────────────────────────────────────────────── */

function DrawerItem({ icon, label, sub, onClick }: { icon?: (c: string) => React.ReactNode; label: string; sub?: string; onClick?: () => void }) {
  return (
    <button onClick={onClick} style={{ width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 12, padding: '13px 6px', borderBottom: '1px solid var(--hairline)', background: 'transparent' }}>
      {icon && (
        <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--surface)', border: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--fg-2)', flexShrink: 0 }}>
          {icon('currentColor')}
        </div>
      )}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--fg)' }}>{label}</div>
        {sub && <div style={{ fontSize: 11.5, color: 'var(--fg-3)', marginTop: 2 }}>{sub}</div>}
      </div>
      <svg width="7" height="12" viewBox="0 0 7 12"><path d="M1 1l5 5-5 5" stroke="var(--fg-3)" strokeWidth="1.6" fill="none" strokeLinecap="round" /></svg>
    </button>
  );
}

function DrawerExpandable({ icon, label, sub, open, onToggle, children }: { icon?: (c: string) => React.ReactNode; label: string; sub?: string; open: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <div style={{ borderBottom: '1px solid var(--hairline)' }}>
      <button onClick={onToggle} style={{ width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 12, padding: '13px 6px', background: 'transparent' }}>
        {icon && (
          <div style={{ width: 30, height: 30, borderRadius: 8, background: open ? 'rgba(213,240,58,0.12)' : 'var(--surface)', border: open ? '1px solid rgba(213,240,58,0.3)' : '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: open ? '#7AA438' : 'var(--fg-2)', flexShrink: 0, transition: 'background 160ms' }}>
            {icon('currentColor')}
          </div>
        )}
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--fg)' }}>{label}</div>
          {sub && <div style={{ fontSize: 11.5, color: 'var(--fg-3)', marginTop: 2 }}>{sub}</div>}
        </div>
        <svg width="11" height="11" viewBox="0 0 14 14" style={{ transform: open ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 200ms', color: 'var(--fg-3)', flexShrink: 0 }}>
          <path d="M2 5l5 5 5-5" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      <div style={{ maxHeight: open ? 600 : 0, overflow: 'hidden', transition: 'max-height 300ms cubic-bezier(.2,0,.2,1)' }}>
        <div style={{ padding: '0 6px 10px 42px' }}>{children}</div>
      </div>
    </div>
  );
}

function DrawerSubItem({ label, sub, onClick }: { label: string; sub?: string; onClick?: () => void }) {
  return (
    <button onClick={onClick} style={{ width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: '1px solid var(--hairline)', background: 'transparent' }}>
      <span style={{ width: 5, height: 5, borderRadius: 5, background: 'var(--hairline)', flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg)' }}>{label}</div>
        {sub && <div style={{ fontSize: 10.5, color: 'var(--fg-3)', marginTop: 1 }}>{sub}</div>}
      </div>
      <svg width="6" height="10" viewBox="0 0 7 12"><path d="M1 1l5 5-5 5" stroke="var(--fg-3)" strokeWidth="1.6" fill="none" strokeLinecap="round" /></svg>
    </button>
  );
}

function SourceCard({ provider, name, desc, connected }: { provider: 'gmail' | 'wpp'; name: string; desc: string; connected: boolean }) {
  const [confirming, setConfirming] = useState(false);
  const [wppInfo, setWppInfo] = useState(false);

  const icon = provider === 'gmail' ? (
    <div style={{ width: 32, height: 32, borderRadius: 9, background: '#fff', border: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
      <svg width="18" height="13" viewBox="0 0 24 18" fill="none">
        <path d="M2 16V4l10 7L22 4v12" stroke="#C5221F" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M2 4l10 7L22 4" stroke="#EA4335" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M2 4v12" stroke="#34A853" strokeWidth="1.6" />
        <path d="M22 4v12" stroke="#FBBC04" strokeWidth="1.6" />
      </svg>
    </div>
  ) : (
    <div style={{ width: 32, height: 32, borderRadius: 9, background: '#25D366', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
        <path d="M12 2a10 10 0 00-8.6 15L2 22l5.2-1.4A10 10 0 1012 2zm4 13c-.2.5-1 1-1.5 1.1-.4.1-.9.1-1.5-.1-.4-.1-.8-.3-1.3-.5-2.3-1-3.8-3.3-3.9-3.5-.1-.2-1-1.3-1-2.5s.6-1.8.8-2c.2-.2.5-.3.7-.3h.5c.2 0 .4 0 .6.4.2.5.6 1.6.7 1.7.1.1.1.3 0 .4-.1.2-.2.3-.3.5-.1.1-.3.3-.1.6.2.3.7 1.2 1.6 2 1.1.9 2 1.2 2.3 1.4.3.1.5.1.6 0 .2-.2.7-.8.9-1.1.2-.3.4-.2.6-.1.3.1 1.6.8 1.9 1 .3.1.5.2.5.3.1.2.1.6-.1 1.2z" fill="#fff" />
      </svg>
    </div>
  );
  return (
    <div style={{ padding: '12px', background: connected ? 'var(--surface)' : 'transparent', border: `1px ${connected ? 'solid' : 'dashed'} var(--hairline)`, borderRadius: 12, marginBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {icon}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{name}</span>
            {connected && (
              <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 14, height: 14, borderRadius: 14, background: '#4CAF50', color: '#fff', flexShrink: 0 }}>
                <svg width="8" height="8" viewBox="0 0 10 10" fill="none"><path d="M2 5l2 2 4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </span>
            )}
          </div>
          <div style={{ fontSize: 10.5, color: 'var(--fg-3)', marginTop: 2, lineHeight: 1.35 }}>{desc}</div>
        </div>
        <button
          onClick={() => provider === 'gmail' && connected ? setConfirming(true) : provider === 'wpp' && !connected ? setWppInfo(v => !v) : undefined}
          style={{ padding: '5px 10px', borderRadius: 100, background: connected ? 'transparent' : LIME, border: connected ? '1px solid var(--hairline)' : 'none', color: connected ? 'var(--fg-3)' : 'var(--ink-stable)', fontSize: 10.5, fontWeight: 700, letterSpacing: 0.06, textTransform: 'uppercase', flexShrink: 0 }}>
          {connected ? 'Desconectar' : 'Conectar'}
        </button>
      </div>

      {/* Gmail disconnect confirm */}
      {confirming && (
        <div style={{ marginTop: 10, padding: '10px 12px', background: '#FFF3CD', border: '1px solid #FFCA28', borderRadius: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#7A5700', marginBottom: 4 }}>⚠️ ¿Desconectar Gmail?</div>
          <div style={{ fontSize: 11.5, color: '#7A5700', lineHeight: 1.4, marginBottom: 10 }}>
            Perdés el relevamiento automático de gastos desde tu correo. Tus gastos existentes no se borran.
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setConfirming(false)} style={{ flex: 1, padding: '7px', borderRadius: 8, border: '1px solid #FFCA28', background: 'transparent', color: '#7A5700', fontSize: 12, fontWeight: 600 }}>
              Cancelar
            </button>
            <button onClick={() => setConfirming(false)} style={{ flex: 1, padding: '7px', borderRadius: 8, background: '#7A5700', color: '#fff', fontSize: 12, fontWeight: 600 }}>
              Sí, desconectar
            </button>
          </div>
        </div>
      )}

      {/* WhatsApp connect info */}
      {wppInfo && (
        <div style={{ marginTop: 10, padding: '10px 12px', background: '#E8F5E9', border: '1px solid #4CAF50', borderRadius: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#1B5E20', marginBottom: 4 }}>📲 Conectar WhatsApp</div>
          <div style={{ fontSize: 11.5, color: '#2E7D32', lineHeight: 1.4 }}>
            Mandá una foto del ticket, un audio o un mensaje de texto al número de Fina y lo registramos automáticamente. Disponible en el plan Pro.
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   3. Drawer
   ───────────────────────────────────────────────────────────── */

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  theme?: 'light' | 'dark';
  onTheme?: (t: 'light' | 'dark') => void;
  onLogout: () => void;
  onOpenPlans?: () => void;
  onOpenStories?: () => void;
}

export function Drawer({ open, onClose, theme = 'light', onTheme, onLogout, onOpenPlans, onOpenStories }: DrawerProps) {
  const { user } = useAuth();
  const [fuentesOpen, setFuentesOpen] = useState(true);
  const [perfilOpen, setPerfilOpen] = useState(false);
  const [profileSheetOpen, setProfileSheetOpen] = useState(false);
  const [currencySheetOpen, setCurrencySheetOpen] = useState(false);

  if (!open) return null;

  return (
    <>
      <div style={{ ...SCRIM, opacity: 1 }} onClick={onClose} />
      <div style={{
        position: 'fixed',
        top: 0, left: 0, bottom: 0,
        width: '86%', maxWidth: 340,
        background: 'var(--bg)',
        borderRadius: '0 24px 24px 0',
        transform: 'translateX(0)',
        transition: 'transform 320ms cubic-bezier(.2,0,.2,1)',
        zIndex: 920,
        paddingTop: 56,
        paddingBottom: 18,
        boxShadow: '20px 0 40px rgba(0,0,0,0.35)',
        borderRight: '1px solid var(--hairline)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 18px 14px', flexShrink: 0 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 26, height: 26, borderRadius: 7, background: LIME, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontFamily: SERIF, fontStyle: 'italic', fontSize: 20, lineHeight: 1, color: '#14130F', marginTop: 1 }}>F</span>
            </div>
            <span style={{ fontFamily: SERIF, fontSize: 22, letterSpacing: -0.5, color: 'var(--fg)', lineHeight: 1 }}>Fina</span>
          </div>
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: 10, background: 'var(--surface)', border: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="12" height="12" viewBox="0 0 12 12"><path d="M2 2l8 8M10 2l-8 8" stroke="var(--fg)" strokeWidth="1.6" strokeLinecap="round" /></svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>

          {/* Profile card */}
          <div style={{ padding: '0 14px 16px' }}>
            <div style={{ background: 'var(--surface)', borderRadius: 16, padding: '14px', display: 'flex', gap: 12, alignItems: 'center', border: '1px solid var(--hairline)' }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: LIME, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, fontWeight: 700, color: '#14130F', flexShrink: 0 }}>
                {user?.name?.[0]?.toUpperCase() ?? '?'}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--fg)' }}>{user?.name ?? 'Usuario'}</div>
                <div style={{ fontSize: 11.5, color: 'var(--fg-3)', marginTop: 2 }}>{user?.email ?? ''}</div>
              </div>
              <button onClick={() => { onClose(); onOpenPlans?.(); }} style={{ padding: '7px 11px', borderRadius: 100, background: 'var(--ink-stable)', color: LIME, fontSize: 10.5, fontWeight: 700, letterSpacing: 0.06, textTransform: 'uppercase', flexShrink: 0 }}>
                Upgrade
              </button>
            </div>
          </div>

          {/* Menu */}
          <div style={{ padding: '0 14px' }}>
            <DrawerExpandable
              icon={(c) => <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M4 6h16v12H4z" stroke={c} strokeWidth="1.7" strokeLinejoin="round" /><path d="M4 6l8 7 8-7" stroke={c} strokeWidth="1.7" strokeLinejoin="round" /></svg>}
              label="Fuentes automáticas"
              sub="Gmail conectado"
              open={fuentesOpen}
              onToggle={() => setFuentesOpen(o => !o)}
            >
              <SourceCard provider="gmail" name="Gmail" desc="Lee notificaciones de bancos en tu correo" connected />
              <SourceCard provider="wpp" name="WhatsApp" desc="Mandá foto, audio o texto y se carga solo" connected={false} />
            </DrawerExpandable>

            <DrawerExpandable
              icon={(c) => <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke={c} strokeWidth="1.7" /><path d="M4 21c0-4 4-7 8-7s8 3 8 7" stroke={c} strokeWidth="1.7" strokeLinecap="round" /></svg>}
              label="Mi perfil"
              sub="Datos, idioma, notificaciones"
              open={perfilOpen}
              onToggle={() => setPerfilOpen(o => !o)}
            >
              <DrawerSubItem label="Datos personales" sub="Nombre, email, apodo" onClick={() => setProfileSheetOpen(true)} />
              <DrawerSubItem label="Notificaciones" sub="Alertas y resúmenes" />
              <DrawerSubItem label="Idioma y moneda" sub="Español · ARS" onClick={() => setCurrencySheetOpen(true)} />
              <DrawerSubItem label="Exportar datos" sub="CSV, PDF del mes" />
            </DrawerExpandable>

            <DrawerItem
              icon={(c) => <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="2.5" y="6" width="19" height="13" rx="2.5" stroke={c} strokeWidth="1.7" /><path d="M2.5 10.5h19" stroke={c} strokeWidth="1.7" /></svg>}
              label="Métodos de pago"
              sub="Tus bancos y billeteras"
            />

            <DrawerItem
              icon={(c) => <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke={c} strokeWidth="1.7" /><path d="M9 9a3 3 0 116 0c0 2-3 2-3 4M12 17v.5" stroke={c} strokeWidth="1.7" strokeLinecap="round" /></svg>}
              label="Ayuda y soporte"
              sub="Chat con el equipo"
            />
          </div>

          {/* Stories teaser */}
          <div style={{ padding: '14px 14px 4px' }}>
            <button onClick={() => { onClose(); onOpenStories?.(); }} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', background: 'var(--ink-stable)', borderRadius: 14, textAlign: 'left' }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: LIME, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontFamily: 'var(--serif)', fontStyle: 'italic', fontSize: 20, color: '#14130F', lineHeight: 1 }}>F</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--paper-stable)' }}>Lógicas de Fina</div>
                <div style={{ fontSize: 11, color: 'rgba(239,233,212,0.55)', marginTop: 2 }}>8 tips · cómo funciona todo</div>
              </div>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M9 18l6-6-6-6" stroke="rgba(239,233,212,0.4)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </button>
          </div>

          {/* Appearance */}
          <div style={{ padding: '18px 14px 4px' }}>
            <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: 0.12, textTransform: 'uppercase', color: 'var(--fg-3)', paddingLeft: 6, marginBottom: 6 }}>Apariencia</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', background: 'var(--surface)', border: '1px solid var(--hairline)', borderRadius: 14 }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M13 9.5A6 6 0 016.5 3a.6.6 0 00-.9-.6 6.5 6.5 0 108 8 .6.6 0 00-.6-.9z" stroke="var(--fg)" strokeWidth="1.4" strokeLinejoin="round" />
              </svg>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--fg)' }}>Modo oscuro</div>
                <div style={{ fontSize: 11.5, color: 'var(--fg-3)', marginTop: 1 }}>Crudo o carbón</div>
              </div>
              <div style={{ display: 'flex', padding: 2, borderRadius: 100, background: 'var(--bg)', border: '1px solid var(--hairline)' }}>
                {(['light', 'dark'] as const).map(opt => (
                  <button key={opt} onClick={() => onTheme?.(opt)} style={{ padding: '5px 11px', borderRadius: 100, background: theme === opt ? LIME : 'transparent', color: theme === opt ? '#14130F' : 'var(--fg-3)', letterSpacing: 0.04, textTransform: 'uppercase', fontSize: 10, fontWeight: 600 }}>
                    {opt === 'light' ? 'Crudo' : 'Carbón'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Cerrar sesión */}
          <div style={{ padding: '18px 14px 0' }}>
            <button onClick={onLogout} style={{ width: '100%', textAlign: 'center', padding: '12px', color: 'var(--fg-3)', fontSize: 12.5, fontWeight: 500, border: '1px solid var(--hairline)', borderRadius: 12, background: 'transparent' }}>
              Cerrar sesión
            </button>
          </div>

        </div>
      </div>

      <ProfileEditSheet open={profileSheetOpen} onClose={() => setProfileSheetOpen(false)} />
      <CurrencyLanguageSheet open={currencySheetOpen} onClose={() => setCurrencySheetOpen(false)} />
    </>
  );
}

/* ─────────────────────────────────────────────────────────────
   4. NotificationsPanel
   ───────────────────────────────────────────────────────────── */

interface NotificationsPanelProps {
  open: boolean;
  onClose: () => void;
}

const DEMO_NOTIFICATIONS = [
  { emoji: '🔥', title: 'Racha de 7 dias', body: 'Registraste gastos toda la semana. Seguiste el habito.', time: 'Hoy' },
  { emoji: '⚠️', title: 'Presupuesto al 90%', body: 'Tu categoria Delivery esta por superar el limite mensual.', time: 'Hace 2h' },
  { emoji: '📊', title: 'Resumen semanal', body: 'Gastaste $45.200 esta semana. 12% menos que la anterior.', time: 'Lun' },
  { emoji: '🔔', title: 'Gasto sin categorizar', body: 'Tienes 3 gastos pendientes de revision.', time: 'Dom' },
  { emoji: '🎯', title: 'Meta de ahorro', body: 'Estas al 68% de tu meta de ahorro mensual.', time: 'Sab' },
  { emoji: '💡', title: 'Tip de Fina', body: 'Los gastos hormiga suman $12.400 este mes. Revisalos.', time: 'Vie' },
];

export function NotificationsPanel({ open, onClose }: NotificationsPanelProps) {
  if (!open) return null;

  return (
    <>
      <div style={{ ...SCRIM, opacity: open ? 1 : 0 }} onClick={onClose} />
      <div style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '86%',
        maxWidth: 360,
        background: 'var(--ink-stable)',
        color: 'var(--paper-stable)',
        zIndex: 920,
        transition: 'transform 320ms cubic-bezier(.2,0,.2,1)',
        transform: open ? 'translateX(0)' : 'translateX(100%)',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
      }}>
        {/* Header */}
        <div style={{ padding: '20px 20px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.6 }}>
              Notificaciones
            </span>
            <CloseBtn onClick={onClose} />
          </div>
          <h2 style={{ fontFamily: SERIF, fontStyle: 'italic', fontSize: 24, fontWeight: 400, marginTop: 4 }}>
            Tu semana con Fina
          </h2>
        </div>

        {/* Notification list */}
        <div style={{ flex: 1, padding: '16px 20px' }}>
          {DEMO_NOTIFICATIONS.map((n, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                gap: 12,
                padding: '14px 0',
                borderBottom: i < DEMO_NOTIFICATIONS.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
              }}
            >
              <span style={{ fontSize: 22, flexShrink: 0 }}>{n.emoji}</span>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{n.title}</span>
                  <span style={{ fontSize: 11, opacity: 0.4 }}>{n.time}</span>
                </div>
                <p style={{ fontSize: 12, opacity: 0.65, marginTop: 2, lineHeight: 1.4 }}>{n.body}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Mark all read */}
        <div style={{ padding: '16px 20px 32px' }}>
          <button
            onClick={onClose}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: 10,
              border: '1px solid rgba(255,255,255,0.12)',
              background: 'transparent',
              color: 'var(--paper-stable)',
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            Marcar todo como leido
          </button>
        </div>
      </div>
    </>
  );
}

// ─── Currency & Language Sheet ────────────────────────────────────────────────

const CURRENCIES = [
  { code: 'ARS', label: 'Peso argentino', flag: '🇦🇷' },
  { code: 'USD', label: 'Dólar estadounidense', flag: '🇺🇸' },
  { code: 'BRL', label: 'Real brasileño', flag: '🇧🇷' },
];

const LANGUAGES = [
  { code: 'es', label: 'Español', flag: '🇦🇷', available: true },
  { code: 'pt', label: 'Português', flag: '🇧🇷', available: false },
];

function CurrencyLanguageSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [currency, setCurrency] = useState(() => localStorage.getItem('fina-currency') || 'ARS');

  function handleSave() {
    localStorage.setItem('fina-currency', currency);
    onClose();
  }

  return (
    <>
      <div onClick={onClose} style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)', opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none', transition: 'opacity 200ms', zIndex: 930 }} />
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        background: 'var(--bg)', borderRadius: '20px 20px 0 0',
        transform: open ? 'translateY(0)' : 'translateY(105%)',
        transition: 'transform 300ms cubic-bezier(.2,0,.2,1)',
        zIndex: 931, paddingBottom: 24,
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ width: 36, height: 4, borderRadius: 4, background: 'var(--hairline)', margin: '10px auto 0', flexShrink: 0 }} />

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', flexShrink: 0 }}>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 20, fontStyle: 'italic', color: 'var(--fg)', letterSpacing: -0.3 }}>Idioma y moneda</div>
          <button onClick={onClose} style={{ width: 28, height: 28, borderRadius: 14, background: 'var(--surface)', border: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--fg-3)' }}>
            <svg width="10" height="10" viewBox="0 0 12 12"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" fill="none"/></svg>
          </button>
        </div>

        <div style={{ padding: '0 18px 16px', display: 'flex', flexDirection: 'column', gap: 22 }}>

          {/* Idioma */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.1, textTransform: 'uppercase', color: 'var(--fg-3)', marginBottom: 10 }}>Idioma</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {LANGUAGES.map(lang => (
                <div key={lang.code} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 14px', borderRadius: 14,
                  background: lang.available ? 'var(--surface)' : 'transparent',
                  border: `1.5px solid ${lang.available ? 'var(--lime)' : 'var(--hairline)'}`,
                  opacity: lang.available ? 1 : 0.6,
                }}>
                  <span style={{ fontSize: 22 }}>{lang.flag}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--fg)' }}>{lang.label}</div>
                    {!lang.available && (
                      <div style={{ fontSize: 10.5, color: 'var(--fg-3)', marginTop: 2 }}>Próximamente</div>
                    )}
                  </div>
                  {lang.available && (
                    <div style={{ width: 18, height: 18, borderRadius: 18, border: '5px solid var(--lime)', background: 'var(--bg)' }} />
                  )}
                  {!lang.available && (
                    <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: 0.08, textTransform: 'uppercase', padding: '3px 8px', borderRadius: 100, background: 'var(--hairline)', color: 'var(--fg-3)' }}>Pronto</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Moneda */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.1, textTransform: 'uppercase', color: 'var(--fg-3)', marginBottom: 10 }}>Moneda por defecto</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {CURRENCIES.map(cur => {
                const selected = currency === cur.code;
                return (
                  <button key={cur.code} onClick={() => setCurrency(cur.code)} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '12px 14px', borderRadius: 14, textAlign: 'left',
                    background: selected ? 'rgba(213,240,58,0.08)' : 'var(--surface)',
                    border: `1.5px solid ${selected ? 'var(--lime)' : 'var(--hairline)'}`,
                    transition: 'border-color 150ms, background 150ms',
                  }}>
                    <span style={{ fontSize: 22 }}>{cur.flag}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--fg)' }}>{cur.code}</div>
                      <div style={{ fontSize: 11, color: 'var(--fg-3)', marginTop: 1 }}>{cur.label}</div>
                    </div>
                    <div style={{
                      width: 18, height: 18, borderRadius: 18, flexShrink: 0,
                      border: selected ? '5px solid var(--lime)' : '1.5px solid var(--hairline)',
                      background: selected ? 'var(--bg)' : 'transparent',
                      transition: 'border 140ms',
                    }} />
                  </button>
                );
              })}
            </div>
            <div style={{ fontSize: 11, color: 'var(--fg-3)', marginTop: 8, lineHeight: 1.4 }}>
              Fina usa esta moneda por defecto al registrar gastos. Podés cambiarla por transacción.
            </div>
          </div>
        </div>

        <div style={{ padding: '0 18px', flexShrink: 0 }}>
          <button onClick={handleSave} style={{ width: '100%', height: 50, borderRadius: 14, background: 'var(--lime)', color: 'var(--ink-stable)', fontSize: 14.5, fontWeight: 700 }}>
            Guardar
          </button>
        </div>
      </div>
    </>
  );
}

// ─── Profile Edit Sheet ───────────────────────────────────────────────────────

interface ProfileEditSheetProps {
  open: boolean;
  onClose: () => void;
}

function ProfileEditSheet({ open, onClose }: ProfileEditSheetProps) {
  const [nombre, setNombre] = useState('');
  const [apellido, setApellido] = useState('');
  const [apodo, setApodo] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError('');
    setSuccess(false);
    fetch('/api/v1/auth/profile', {
      headers: { Authorization: `Bearer ${localStorage.getItem('finanzas_token')}` },
    })
      .then(r => r.json())
      .then(d => {
        setNombre(d.nombre || '');
        setApellido(d.apellido || '');
        // apodo: from server if available, fallback to localStorage
        setApodo(d.apodo || localStorage.getItem('fina-apodo') || '');
        setEmail(d.email || '');
      })
      .catch(() => setError('No se pudo cargar el perfil'))
      .finally(() => setLoading(false));
  }, [open]);

  async function handleSave() {
    setSaving(true);
    setError('');
    setSuccess(false);
    try {
      const res = await fetch('/api/v1/auth/profile', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('finanzas_token')}`,
        },
        body: JSON.stringify({ nombre: nombre.trim(), apellido: apellido.trim(), apodo: apodo.trim() }),
      });
      if (!res.ok) throw new Error('Error al guardar');
      // Also save apodo to localStorage as fallback until DB migration runs
      if (apodo.trim()) localStorage.setItem('fina-apodo', apodo.trim());
      else localStorage.removeItem('fina-apodo');
      setSuccess(true);
      setTimeout(onClose, 900);
    } catch {
      setError('No se pudo guardar. Intentá de nuevo.');
    } finally {
      setSaving(false);
    }
  }

  const fieldStyle = {
    width: '100%',
    padding: '12px 14px',
    borderRadius: 12,
    border: '1.5px solid var(--hairline)',
    background: 'var(--surface)',
    color: 'var(--fg)',
    fontSize: 14,
    outline: 'none',
    boxSizing: 'border-box' as const,
  };

  return (
    <>
      <div onClick={onClose} style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)', opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none', transition: 'opacity 200ms', zIndex: 930 }} />
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        background: 'var(--bg)',
        borderRadius: '20px 20px 0 0',
        transform: open ? 'translateY(0)' : 'translateY(105%)',
        transition: 'transform 300ms cubic-bezier(.2,0,.2,1)',
        zIndex: 931,
        paddingBottom: 24,
        maxHeight: '90%',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ width: 36, height: 4, borderRadius: 4, background: 'var(--hairline)', margin: '10px auto 0', flexShrink: 0 }} />

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', flexShrink: 0 }}>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 20, fontStyle: 'italic', color: 'var(--fg)', letterSpacing: -0.3 }}>Datos personales</div>
          <button onClick={onClose} style={{ width: 28, height: 28, borderRadius: 14, background: 'var(--surface)', border: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--fg-3)' }}>
            <svg width="10" height="10" viewBox="0 0 12 12"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" fill="none"/></svg>
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 18px 8px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--fg-3)', fontSize: 13 }}>Cargando...</div>
          ) : (
            <>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.1, textTransform: 'uppercase', color: 'var(--fg-3)', marginBottom: 6 }}>Nombre</div>
                <input value={nombre} onChange={e => setNombre(e.target.value)} placeholder="Tu nombre" style={fieldStyle} />
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.1, textTransform: 'uppercase', color: 'var(--fg-3)', marginBottom: 6 }}>Apellido</div>
                <input value={apellido} onChange={e => setApellido(e.target.value)} placeholder="Tu apellido" style={fieldStyle} />
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.1, textTransform: 'uppercase', color: 'var(--fg-3)', marginBottom: 6 }}>
                  Apodo <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, color: 'var(--fg-3)' }}>· opcional</span>
                </div>
                <input value={apodo} onChange={e => setApodo(e.target.value)} placeholder="¿Cómo te decimos? Ej: Nacho" style={fieldStyle} />
                <div style={{ fontSize: 11, color: 'var(--fg-3)', marginTop: 5 }}>Fina te va a saludar con este nombre en el chat.</div>
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.1, textTransform: 'uppercase', color: 'var(--fg-3)', marginBottom: 6 }}>Email</div>
                <input value={email} disabled style={{ ...fieldStyle, opacity: 0.5, cursor: 'not-allowed' }} />
                <div style={{ fontSize: 11, color: 'var(--fg-3)', marginTop: 5 }}>El email no se puede cambiar desde acá.</div>
              </div>

              {error && <div style={{ fontSize: 12.5, color: '#C62828', background: '#FFEBEE', borderRadius: 8, padding: '8px 12px' }}>{error}</div>}
              {success && <div style={{ fontSize: 12.5, color: '#1B5E20', background: '#E8F5E9', borderRadius: 8, padding: '8px 12px' }}>✓ Perfil actualizado</div>}
            </>
          )}
        </div>

        {/* CTA */}
        {!loading && (
          <div style={{ padding: '8px 18px 0', flexShrink: 0 }}>
            <button onClick={handleSave} disabled={saving} style={{ width: '100%', height: 50, borderRadius: 14, background: saving ? 'var(--hairline)' : 'var(--lime)', color: 'var(--ink-stable)', fontSize: 14.5, fontWeight: 700, transition: 'background 150ms' }}>
              {saving ? 'Guardando...' : 'Guardar cambios'}
            </button>
          </div>
        )}
      </div>
    </>
  );
}

// ─── Plans Sheet ─────────────────────────────────────────────────────────────

const FINA_PLANS = [
  {
    id: 'free',
    name: 'Empezá',
    tagline: 'Para ordenarte solo',
    priceM: 0,
    priceY: 0,
    current: false,
    badge: null as string | null,
    features: [
      { ok: true,  t: 'Carga manual ilimitada' },
      { ok: true,  t: 'Categorías y presupuesto 50/30/20' },
      { ok: true,  t: 'Chat con Fina · 20 consultas/mes' },
      { ok: false, t: 'Banco automático por Gmail' },
      { ok: false, t: 'WhatsApp · foto y audio' },
      { ok: false, t: 'Importar extractos PDF/Excel' },
    ],
  },
  {
    id: 'plus',
    name: 'Plus',
    tagline: 'Carga automática',
    priceM: 4.99,
    priceY: 53.89,
    current: true,
    badge: 'TU PLAN' as string | null,
    features: [
      { ok: true,  t: 'Todo lo del plan Empezá' },
      { ok: true,  t: 'Banco automático por Gmail' },
      { ok: true,  t: 'Chat con Fina · ilimitado' },
      { ok: true,  t: 'Notificaciones inteligentes' },
      { ok: false, t: 'WhatsApp · foto y audio' },
      { ok: false, t: 'Importar extractos PDF/Excel' },
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    tagline: 'Sin fricciones',
    priceM: 5.99,
    priceY: 64.69,
    current: false,
    badge: 'POPULAR' as string | null,
    features: [
      { ok: true,  t: 'Todo lo del plan Plus' },
      { ok: true,  t: 'WhatsApp · foto, audio y mensajes' },
      { ok: true,  t: 'Importar extractos PDF / Excel' },
      { ok: true,  t: 'Historial completo (todos los meses)' },
      { ok: true,  t: 'Coach proactivo · alertas en vivo' },
      { ok: true,  t: 'Cuotas compartidas con tu pareja' },
    ],
  },
];

interface PlansSheetProps {
  open: boolean;
  onClose: () => void;
}

export function PlansSheet({ open, onClose }: PlansSheetProps) {
  const [billing, setBilling] = useState<'monthly' | 'yearly'>('monthly');
  const [selectedId, setSelectedId] = useState('pro');

  useEffect(() => { if (open) setSelectedId('pro'); }, [open]);

  return (
    <>
      <div onClick={onClose} style={{
        position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.55)',
        opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none',
        transition: 'opacity 220ms', zIndex: 110,
      }} />
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        background: 'var(--ink-stable)', color: 'var(--paper-stable)',
        borderRadius: '24px 24px 0 0',
        transform: open ? 'translateY(0)' : 'translateY(105%)',
        transition: 'transform 320ms cubic-bezier(.2,0,.2,1)',
        zIndex: 111,
        paddingBottom: 18,
        maxHeight: '94%',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{
          width: 38, height: 4, borderRadius: 4,
          background: 'rgba(239,233,212,0.25)',
          margin: '10px auto 4px', flexShrink: 0,
        }} />

        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 18px 14px', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontFamily: 'var(--serif)', fontStyle: 'italic', fontSize: 22, color: 'var(--lime)' }}>F</span>
            <div>
              <div style={{ fontFamily: 'var(--serif)', fontSize: 19, fontStyle: 'italic', color: 'var(--paper-stable)', lineHeight: 1, letterSpacing: -0.2 }}>Elegí tu plan</div>
              <div style={{ fontSize: 10.5, color: 'rgba(239,233,212,0.55)', marginTop: 3 }}>Cancelás cuando quieras</div>
            </div>
          </div>
          <button onClick={onClose} style={{ width: 30, height: 30, borderRadius: 15, background: 'rgba(239,233,212,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--paper-stable)' }}>
            <svg width="11" height="11" viewBox="0 0 12 12"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" fill="none"/></svg>
          </button>
        </div>

        <div style={{ padding: '0 18px 14px', flexShrink: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, padding: 3, borderRadius: 100, background: 'rgba(239,233,212,0.08)', border: '1px solid rgba(239,233,212,0.1)' }}>
            {([{ id: 'monthly', l: 'Mensual' }, { id: 'yearly', l: 'Anual · −10%' }] as const).map(b => (
              <button key={b.id} onClick={() => setBilling(b.id)} style={{ padding: '7px 10px', borderRadius: 100, background: billing === b.id ? 'var(--lime)' : 'transparent', color: billing === b.id ? 'var(--ink-stable)' : 'rgba(239,233,212,0.7)', fontSize: 11.5, fontWeight: 600 }}>{b.l}</button>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, padding: '0 14px 12px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {FINA_PLANS.map(plan => {
              const isSelected = selectedId === plan.id;
              const price = billing === 'monthly' ? plan.priceM : plan.priceY;
              const isPro = plan.id === 'pro';
              return (
                <button key={plan.id} onClick={() => setSelectedId(plan.id)} style={{ width: '100%', textAlign: 'left', padding: '14px 14px', background: isPro ? 'linear-gradient(165deg, #29261B 0%, #14130F 100%)' : isSelected ? 'rgba(213,240,58,0.06)' : 'rgba(239,233,212,0.04)', border: '1.5px solid', borderColor: isSelected ? 'var(--lime)' : isPro ? 'rgba(239,233,212,0.15)' : 'rgba(239,233,212,0.08)', borderRadius: 16, position: 'relative', transition: 'border-color 160ms, background 160ms' }}>
                  {plan.badge && (
                    <div style={{ position: 'absolute', top: -8, left: 14, padding: '2px 10px', borderRadius: 100, background: plan.current ? 'var(--lime)' : 'var(--paper-stable)', color: 'var(--ink-stable)', fontSize: 9, fontWeight: 800, letterSpacing: 0.1 }}>{plan.badge}</div>
                  )}
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ width: 18, height: 18, borderRadius: 18, border: isSelected ? '5px solid var(--lime)' : '1.5px solid rgba(239,233,212,0.25)', background: isSelected ? 'var(--ink-stable)' : 'transparent', flexShrink: 0, marginTop: 3, transition: 'border 140ms' }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 }}>
                        <div>
                          <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontStyle: 'italic', color: 'var(--paper-stable)', lineHeight: 1, letterSpacing: -0.2 }}>{plan.name}</div>
                          <div style={{ fontSize: 11, color: 'rgba(239,233,212,0.55)', marginTop: 4 }}>{plan.tagline}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          {price === 0 ? (
                            <div style={{ fontFamily: 'var(--mono)', fontSize: 18, fontWeight: 600, color: 'var(--paper-stable)', lineHeight: 1 }}>Gratis</div>
                          ) : (
                            <>
                              <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
                                <span style={{ fontSize: 11, color: 'rgba(239,233,212,0.55)' }}>US$</span>
                                <span style={{ fontSize: 26, fontWeight: 600, color: 'var(--paper-stable)', lineHeight: 1, letterSpacing: -0.02 }}>{price}</span>
                              </div>
                              <div style={{ fontSize: 10, color: 'rgba(239,233,212,0.5)', marginTop: 2 }}>/{billing === 'monthly' ? 'mes' : 'año'}</div>
                            </>
                          )}
                        </div>
                      </div>
                      <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {plan.features.map((f, i) => (
                          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                            <span style={{ width: 14, height: 14, borderRadius: 14, marginTop: 2, background: f.ok ? 'var(--lime)' : 'transparent', border: f.ok ? 'none' : '1px solid rgba(239,233,212,0.2)', color: 'var(--ink-stable)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                              {f.ok
                                ? <svg width="8" height="8" viewBox="0 0 10 10"><path d="M2 5l2 2 4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg>
                                : <svg width="6" height="6" viewBox="0 0 8 8" style={{ color: 'rgba(239,233,212,0.3)' }}><path d="M2 2l4 4M6 2l-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
                              }
                            </span>
                            <span style={{ fontSize: 12, lineHeight: 1.4, color: f.ok ? 'var(--paper-stable)' : 'rgba(239,233,212,0.4)' }}>{f.t}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          <div style={{ marginTop: 16, padding: '12px 14px', background: 'rgba(239,233,212,0.04)', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 18, lineHeight: 1, flexShrink: 0 }}>🔒</span>
            <div>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--paper-stable)' }}>Pago seguro y sin compromiso</div>
              <div style={{ fontSize: 10.5, color: 'rgba(239,233,212,0.55)', marginTop: 1, lineHeight: 1.35 }}>Probás 14 días gratis. Si no te convence, cancelás con un tap.</div>
            </div>
          </div>
        </div>

        <div style={{ padding: '8px 18px 4px', flexShrink: 0 }}>
          {(() => {
            const sel = FINA_PLANS.find(p => p.id === selectedId)!;
            const price = billing === 'monthly' ? sel.priceM : sel.priceY;
            if (sel.current) return <button onClick={onClose} style={{ width: '100%', height: 50, borderRadius: 16, background: 'rgba(239,233,212,0.08)', color: 'var(--paper-stable)', fontSize: 14, fontWeight: 600 }}>Mantener mi plan</button>;
            if (price === 0) return <button onClick={onClose} style={{ width: '100%', height: 50, borderRadius: 16, background: 'rgba(239,233,212,0.1)', color: 'var(--paper-stable)', fontSize: 14, fontWeight: 600 }}>Bajar a {sel.name}</button>;
            return (
              <button onClick={onClose} style={{ width: '100%', height: 50, borderRadius: 16, background: 'var(--lime)', color: 'var(--ink-stable)', fontSize: 14.5, fontWeight: 700, letterSpacing: 0.02, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                Empezar Fina {sel.name} · US${price}/{billing === 'monthly' ? 'mes' : 'año'}
                <svg width="14" height="14" viewBox="0 0 14 14"><path d="M2 7h10M7 2l5 5-5 5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </button>
            );
          })()}
        </div>
      </div>
    </>
  );
}

// ─── Stories Viewer ───────────────────────────────────────────────────────────

const FINA_STORIES = [
  { id: 'welcome', bg: 'linear-gradient(165deg, #14130F 0%, #29261B 100%)', fg: 'var(--paper-stable)', emoji: 'F' as string | null, bigStat: null as string | null, eyebrow: 'BIENVENIDO', title: 'Soy Fina.', body: 'Soy tu asistente financiero. No te muestro gráficos sin sentido — te digo qué hacer y qué no.', list: null as {emoji:string;t:string}[] | null, cta: null as {label:string;target:string} | null, duration: 5000 },
  { id: '50-30-20', bg: 'var(--lime)', fg: 'var(--ink-stable)', emoji: null, bigStat: '50 · 30 · 20', eyebrow: 'LA REGLA', title: 'Repartí cada peso así.', body: '50% Necesidades · 30% Deseos · 20% Ahorro. Es la regla que más sirve a quien arranca a ordenarse.', list: null, cta: null, duration: 6000 },
  { id: 'needs-vs-wants', bg: '#2A3318', fg: '#EFE9D4', emoji: null, bigStat: null, eyebrow: 'NECESIDADES VS DESEOS', title: '¿Lo necesitás o lo querés?', body: 'Vivienda, comida, transporte, salud son necesidades. Bares, viajes, ropa nueva son deseos. La diferencia no es buena ni mala — pero tiene techo distinto.', list: [{ emoji: '🏠', t: 'Necesidades · 50%' }, { emoji: '🎁', t: 'Deseos · 30%' }], cta: null, duration: 7000 },
  { id: 'save-first', bg: 'linear-gradient(165deg, #2A3318 0%, #0E0D0B 100%)', fg: 'var(--paper-stable)', emoji: '💰', bigStat: null, eyebrow: 'AHORRO', title: 'Pagate a vos primero.', body: 'Antes de gastar, separá. Si dejás el ahorro para el final del mes nunca queda nada. Fina te ayuda a apartar 20% apenas entra la plata.', list: null, cta: null, duration: 6000 },
  { id: 'multi-channel', bg: 'var(--paper-stable)', fg: 'var(--ink-stable)', emoji: null, bigStat: null, eyebrow: 'CÓMO CARGÁS GASTOS', title: 'Como vos quieras.', body: 'Banco (auto), foto del ticket, audio de WhatsApp o un mensaje. Fina entiende todos los formatos y los pone donde van.', list: [{ emoji: '🏦', t: 'Banco · automático' }, { emoji: '📸', t: 'Foto del ticket' }, { emoji: '🎤', t: 'Audio de WPP' }, { emoji: '✍️', t: 'Manual' }], cta: null, duration: 7000 },
  { id: 'prescriptive', bg: 'var(--ink-stable)', fg: 'var(--lime)', emoji: null, bigStat: null, eyebrow: 'EL CHAT', title: '¿Puedo gastar X?', body: 'Preguntale antes de comprar. Yo cruzo tu presupuesto con cuánto te queda del mes y te digo Sí · Cuidado · Mejor no. Es mi superpoder.', list: null, cta: { label: 'Probar el chat', target: 'chat' }, duration: 7000 },
  { id: 'rules-learn', bg: '#FAF6E7', fg: 'var(--ink-stable)', emoji: null, bigStat: null, eyebrow: 'CATEGORIZACIÓN', title: 'Aprendo de vos.', body: 'La primera vez que asignás categoría a un comercio, lo recuerdo. La próxima vez que veas un cobro del mismo lugar, ya está clasificado.', list: null, cta: null, duration: 6000 },
  { id: 'future-months', bg: 'linear-gradient(180deg, #E9E3D0 0%, #DCD4BB 100%)', fg: 'var(--ink-stable)', emoji: null, bigStat: null, eyebrow: 'PLANIFICACIÓN', title: 'Mirá hacia adelante.', body: 'En meses futuros ya ves tus cuotas activas y gastos fijos. Sabés qué tenés comprometido antes de que llegue el mes.', list: null, cta: { label: 'Ver mi presupuesto', target: 'cats' }, duration: 6000 },
];

interface StoriesViewerProps {
  open: boolean;
  onClose: () => void;
  onNav?: (tab: string) => void;
}

export function StoriesViewer({ open, onClose, onNav }: StoriesViewerProps) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (open) { setIndex(0); setProgress(0); setPaused(false); }
  }, [open]);

  const current = FINA_STORIES[index];
  const total = FINA_STORIES.length;

  useEffect(() => {
    if (!open || paused || !current) return;
    startRef.current = null;
    const tick = (ts: number) => {
      if (startRef.current == null) startRef.current = ts - progress * current.duration;
      const elapsed = ts - startRef.current;
      const p = Math.min(1, elapsed / current.duration);
      setProgress(p);
      if (p >= 1) {
        if (index < total - 1) { setIndex(i => i + 1); setProgress(0); }
        else { setProgress(1); setPaused(true); }
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [open, index, paused, current?.duration]);

  useEffect(() => { setProgress(0); }, [index]);

  if (!open) return null;

  const goNext = () => { if (index < total - 1) { setIndex(i => i + 1); setPaused(false); } else onClose(); };
  const goPrev = () => { if (index > 0) { setIndex(i => i - 1); setPaused(false); } else setProgress(0); };

  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 950, background: current.bg, color: current.fg, display: 'flex', flexDirection: 'column', overflow: 'hidden', animation: 'finaStoryFade 220ms ease' }}>
      {/* progress bars */}
      <div style={{ position: 'absolute', top: 14, left: 12, right: 12, display: 'flex', gap: 4, zIndex: 2 }}>
        {FINA_STORIES.map((_, i) => (
          <div key={i} style={{ flex: 1, height: 3, borderRadius: 3, background: 'rgba(0,0,0,0.18)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${i < index ? 100 : i === index ? progress * 100 : 0}%`, background: 'rgba(255,255,255,0.95)', transition: 'width 80ms linear' }} />
          </div>
        ))}
      </div>

      {/* header */}
      <div style={{ position: 'absolute', top: 26, left: 0, right: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', zIndex: 3 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 26, height: 26, borderRadius: 7, background: current.fg, color: current.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--serif)', fontStyle: 'italic', fontSize: 17, lineHeight: 1 }}>F</div>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.12, textTransform: 'uppercase', opacity: 0.7 }}>Lógicas de Fina · {index + 1}/{total}</span>
        </div>
        <button onClick={onClose} style={{ width: 28, height: 28, borderRadius: 14, background: 'rgba(0,0,0,0.15)', color: current.fg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="11" height="11" viewBox="0 0 12 12"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none"/></svg>
        </button>
      </div>

      {/* tap zones */}
      <div onClick={goPrev} onPointerDown={() => setPaused(true)} onPointerUp={() => setPaused(false)} onPointerLeave={() => setPaused(false)} style={{ position: 'absolute', top: 60, bottom: 80, left: 0, width: '35%', zIndex: 1 }} />
      <div onClick={goNext} onPointerDown={() => setPaused(true)} onPointerUp={() => setPaused(false)} onPointerLeave={() => setPaused(false)} style={{ position: 'absolute', top: 60, bottom: 80, right: 0, width: '35%', zIndex: 1 }} />

      {/* content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '70px 28px 80px', position: 'relative', zIndex: 0 }}>
        {current.emoji && (
          <div style={{ fontSize: 64, marginBottom: 24, lineHeight: 1, fontFamily: current.emoji === 'F' ? 'var(--serif)' : 'inherit', fontStyle: current.emoji === 'F' ? 'italic' : 'normal' }}>{current.emoji}</div>
        )}
        {current.bigStat && (
          <div style={{ fontFamily: 'var(--mono)', fontSize: 48, fontWeight: 600, letterSpacing: -0.04, marginBottom: 20, lineHeight: 1 }}>{current.bigStat}</div>
        )}
        <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: 0.16, textTransform: 'uppercase', opacity: 0.55, marginBottom: 12 }}>{current.eyebrow}</div>
        <div style={{ fontFamily: 'var(--serif)', fontSize: 36, fontStyle: 'italic', lineHeight: 1.1, letterSpacing: -0.5, marginBottom: 18 }}>{current.title}</div>
        <div style={{ fontSize: 15, lineHeight: 1.5, opacity: 0.85, fontWeight: 400, letterSpacing: -0.1 }}>{current.body}</div>

        {current.list && (
          <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {current.list.map(item => (
              <div key={item.t} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', background: 'rgba(0,0,0,0.08)', borderRadius: 10 }}>
                <span style={{ fontSize: 18, lineHeight: 1 }}>{item.emoji}</span>
                <span style={{ fontSize: 13.5, fontWeight: 500 }}>{item.t}</span>
              </div>
            ))}
          </div>
        )}

        {current.cta && (
          <button onClick={() => { onNav?.(current.cta!.target); onClose(); }} style={{ marginTop: 24, padding: '12px 18px', borderRadius: 100, background: current.fg, color: current.bg, fontSize: 13, fontWeight: 600, alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            {current.cta.label}
            <svg width="11" height="11" viewBox="0 0 14 14"><path d="M2 7h10M7 2l5 5-5 5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </button>
        )}
      </div>

      <div style={{ position: 'absolute', bottom: 20, left: 0, right: 0, textAlign: 'center', fontSize: 10, opacity: 0.5, letterSpacing: 0.1, textTransform: 'uppercase', fontWeight: 600 }}>
        Tocá para avanzar · Mantené para pausar
      </div>

      <style>{`@keyframes finaStoryFade { from { opacity: 0 } to { opacity: 1 } }`}</style>
    </div>
  );
}
