import { useState, useEffect } from 'react';
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
  const { categories } = useCatalog();

  const isEditing = !!initial;

  const [amount, setAmount] = useState(initial?.amount?.toString() ?? '');
  const [currency, setCurrency] = useState<'ARS' | 'USD'>('ARS');
  const [date, setDate] = useState(initial?.date ?? new Date().toISOString().slice(0, 10));
  const [categoryId, setCategoryId] = useState(initial?.categoryId ?? '');
  const [subcategoryId, setSubcategoryId] = useState(initial?.subcategoryId ?? '');
  const [merchant, setMerchant] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');
  const [note, setNote] = useState(initial?.description ?? '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (initial) {
      setAmount(initial.amount?.toString() ?? '');
      setDate(initial.date ?? new Date().toISOString().slice(0, 10));
      setCategoryId(initial.categoryId ?? '');
      setSubcategoryId(initial.subcategoryId ?? '');
      setNote(initial.description ?? '');
    } else {
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
          tipo_movimiento: 'Gasto',
          descripcion: note || merchant || 'Gasto manual',
          id_categoria: parseInt(categoryId) || 6,
          id_subcategoria: parseInt(subcategoryId) || 42,
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
                background: LIME, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 16, color: '#14130F', fontWeight: 700,
              }}>
                {isEditing ? '✎' : '+'}
              </div>
              <span style={{ fontFamily: SANS, fontSize: 13, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                {isEditing ? 'EDITAR GASTO' : 'NUEVO GASTO'}
              </span>
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
            {categories.map(cat => (
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
                  background: categoryId === cat.id ? LIME : 'rgba(255,255,255,0.08)',
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
                background: LIME,
                color: '#14130F',
                fontWeight: 700,
                fontSize: 14,
                opacity: saving || !amount ? 0.5 : 1,
              }}
            >
              {saving ? '...' : isEditing ? 'Guardar cambios' : 'Registrar gasto'}
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
   3. Drawer
   ───────────────────────────────────────────────────────────── */

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  theme?: 'light' | 'dark';
  onTheme?: (t: 'light' | 'dark') => void;
  onLogout: () => void;
}

export function Drawer({ open, onClose, theme = 'light', onTheme, onLogout }: DrawerProps) {
  const { user } = useAuth();
  const [expandedSources, setExpandedSources] = useState(false);
  const [expandedProfile, setExpandedProfile] = useState(false);

  if (!open) return null;

  return (
    <>
      <div style={{ ...SCRIM, opacity: open ? 1 : 0 }} onClick={onClose} />
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        bottom: 0,
        width: '86%',
        maxWidth: 360,
        background: 'var(--ink-stable)',
        color: 'var(--paper-stable)',
        zIndex: 920,
        transition: 'transform 320ms cubic-bezier(.2,0,.2,1)',
        transform: open ? 'translateX(0)' : 'translateX(-100%)',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 20px 12px' }}>
          <span style={{ fontFamily: SERIF, fontSize: 22, fontStyle: 'italic' }}>Fina</span>
          <CloseBtn onClick={onClose} />
        </div>

        {/* Profile card */}
        <div style={{
          margin: '0 16px',
          padding: 16,
          borderRadius: 14,
          background: 'rgba(255,255,255,0.06)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 44, height: 44, borderRadius: '50%',
              background: LIME, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20, color: '#14130F', fontWeight: 700,
            }}>
              {user?.name?.[0]?.toUpperCase() ?? '?'}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{user?.name ?? 'Usuario'}</div>
              <div style={{ fontSize: 12, opacity: 0.6 }}>{user?.email ?? ''}</div>
            </div>
          </div>
          <button style={{
            marginTop: 12,
            width: '100%',
            padding: '8px',
            borderRadius: 8,
            border: `1px solid ${LIME}`,
            background: 'transparent',
            color: LIME,
            fontWeight: 600,
            fontSize: 12,
          }}>
            Upgrade
          </button>
        </div>

        {/* Menu items */}
        <div style={{ padding: '20px 16px', flex: 1 }}>
          {/* Fuentes automaticas */}
          <button
            onClick={() => setExpandedSources(!expandedSources)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 0',
              border: 'none',
              background: 'none',
              color: 'var(--paper-stable)',
              fontSize: 14,
              borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <span>Fuentes automaticas</span>
            <span style={{ transform: expandedSources ? 'rotate(90deg)' : 'none', transition: 'transform 200ms' }}>&#x203A;</span>
          </button>
          {expandedSources && (
            <div style={{ padding: '8px 12px', fontSize: 13, opacity: 0.7 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span>Gmail</span>
                <span style={{ color: '#7AA438' }}>Conectado</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>WhatsApp</span>
                <span style={{ color: '#7AA438' }}>Conectado</span>
              </div>
            </div>
          )}

          {/* Mi perfil */}
          <button
            onClick={() => setExpandedProfile(!expandedProfile)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 0',
              border: 'none',
              background: 'none',
              color: 'var(--paper-stable)',
              fontSize: 14,
              borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <span>Mi perfil</span>
            <span style={{ transform: expandedProfile ? 'rotate(90deg)' : 'none', transition: 'transform 200ms' }}>&#x203A;</span>
          </button>
          {expandedProfile && (
            <div style={{ padding: '8px 12px', fontSize: 13, opacity: 0.7 }}>
              <div style={{ marginBottom: 4 }}>Datos personales</div>
              <div>Notificaciones</div>
            </div>
          )}

          {/* Metodos de pago */}
          <button style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            padding: '12px 0',
            border: 'none',
            background: 'none',
            color: 'var(--paper-stable)',
            fontSize: 14,
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}>
            Metodos de pago
          </button>

          {/* Ayuda y soporte */}
          <button style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            padding: '12px 0',
            border: 'none',
            background: 'none',
            color: 'var(--paper-stable)',
            fontSize: 14,
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}>
            Ayuda y soporte
          </button>

          {/* Appearance */}
          <div style={{ marginTop: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.5, marginBottom: 8 }}>
              Apariencia
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => onTheme?.('light')}
                style={{
                  flex: 1,
                  padding: '10px',
                  borderRadius: 10,
                  border: theme === 'light' ? `2px solid ${LIME}` : '2px solid rgba(255,255,255,0.1)',
                  background: theme === 'light' ? 'rgba(213,240,58,0.1)' : 'transparent',
                  color: 'var(--paper-stable)',
                  fontWeight: 600,
                  fontSize: 13,
                }}
              >
                Crudo
              </button>
              <button
                onClick={() => onTheme?.('dark')}
                style={{
                  flex: 1,
                  padding: '10px',
                  borderRadius: 10,
                  border: theme === 'dark' ? `2px solid ${LIME}` : '2px solid rgba(255,255,255,0.1)',
                  background: theme === 'dark' ? 'rgba(213,240,58,0.1)' : 'transparent',
                  color: 'var(--paper-stable)',
                  fontWeight: 600,
                  fontSize: 13,
                }}
              >
                Carbon
              </button>
            </div>
          </div>
        </div>

        {/* Logout */}
        <div style={{ padding: '16px 20px 32px' }}>
          <button
            onClick={onLogout}
            style={{
              width: '100%',
              padding: '14px',
              borderRadius: 12,
              border: '1px solid rgba(255,255,255,0.12)',
              background: 'transparent',
              color: '#E66A3F',
              fontWeight: 600,
              fontSize: 14,
            }}
          >
            Cerrar sesion
          </button>
        </div>
      </div>
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
