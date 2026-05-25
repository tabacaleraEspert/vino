import { useState, useMemo } from 'react';
import { useData } from '../../context/DataContext';
import { useCatalog } from '../../context/CatalogContext';
import { Screen, SectionHead } from './shared';
import type { MerchantRule } from '../../../lib/api';

/* ─── helpers ─────────────────────────────────── */

function getCatIcon(name: string) {
  const map: Record<string, string> = {
    ocio: '🎬', comida: '🍽️', salud: '💊', transporte: '🚗',
    vivienda: '🏠', compras: '🛍️', ahorro: '💰', educacion: '📚',
  };
  return map[name.toLowerCase()] ?? '📦';
}

/* ─── RuleEditSheet ────────────────────────────── */

function RuleEditSheet({
  rule,
  onClose,
}: {
  rule: MerchantRule;
  onClose: () => void;
}) {
  const { categories } = useCatalog();
  const { updateMerchantRule, deleteMerchantRule } = useData();

  const [catId, setCatId] = useState(rule.categoryId);
  const [subId, setSubId] = useState(rule.subcategoryId ?? '');
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const gastoCategories = categories.filter((c) => c.tipo !== 'Ingreso');
  const selectedCat = gastoCategories.find((c) => c.id === catId);
  const subcats = selectedCat?.subcategories ?? [];

  async function handleSave() {
    setSaving(true);
    try {
      await updateMerchantRule(rule.id, {
        categoryId: catId,
        subcategoryId: subId || undefined,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setSaving(true);
    try {
      await deleteMerchantRule(rule.id);
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.4)',
          zIndex: 120,
        }}
      />

      {/* Sheet */}
      <div style={{
        position: 'fixed',
        bottom: 0, left: '50%',
        transform: 'translateX(-50%)',
        width: '100%',
        maxWidth: 512,
        background: 'var(--bg, #fff)',
        borderRadius: '20px 20px 0 0',
        padding: '0 0 40px',
        zIndex: 121,
        boxShadow: '0 -4px 32px rgba(0,0,0,0.15)',
      }}>
        {/* Handle */}
        <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 4px' }}>
          <div style={{ width: 36, height: 4, borderRadius: 2, background: 'var(--border, #e0e0e0)' }} />
        </div>

        {/* Title */}
        <div style={{ padding: '12px 20px 20px' }}>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-tertiary, #999)', marginBottom: 4 }}>
            Regla de comercio
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary, #1a1a1a)' }}>
            {rule.comercio}
          </div>
        </div>

        {/* Category selector */}
        <div style={{ padding: '0 20px 16px' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary, #555)', marginBottom: 10 }}>
            Categoría
          </div>
          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4, WebkitOverflowScrolling: 'touch', scrollbarWidth: 'none' }}>
            {gastoCategories.map((c) => {
              const active = c.id === catId;
              return (
                <button
                  key={c.id}
                  onClick={() => { setCatId(c.id); setSubId(''); }}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 4,
                    padding: '10px 14px',
                    borderRadius: 12,
                    border: active ? `2px solid ${c.color || '#007AFF'}` : '2px solid transparent',
                    background: active ? `${c.color || '#007AFF'}18` : 'var(--surface-secondary, #f5f5f5)',
                    cursor: 'pointer',
                    flexShrink: 0,
                    minWidth: 70,
                    transition: 'all 0.15s',
                  }}
                >
                  <span style={{ fontSize: 22 }}>{c.icon || getCatIcon(c.name)}</span>
                  <span style={{
                    fontSize: 11,
                    fontWeight: active ? 600 : 400,
                    color: active ? (c.color || '#007AFF') : 'var(--text-secondary, #666)',
                    textAlign: 'center',
                    lineHeight: 1.2,
                    whiteSpace: 'nowrap',
                  }}>
                    {c.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Subcategory selector */}
        {subcats.length > 0 && (
          <div style={{ padding: '0 20px 20px' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary, #555)', marginBottom: 10 }}>
              Subcategoría <span style={{ fontWeight: 400, color: 'var(--text-tertiary,#999)' }}>(opcional)</span>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                onClick={() => setSubId('')}
                style={{
                  padding: '6px 14px',
                  borderRadius: 20,
                  border: subId === '' ? '2px solid var(--lime-deep,#65a30d)' : '2px solid transparent',
                  background: subId === '' ? 'var(--lime-tint,#f7fee7)' : 'var(--surface-secondary,#f5f5f5)',
                  fontSize: 13,
                  fontWeight: subId === '' ? 600 : 400,
                  color: subId === '' ? 'var(--lime-deep,#65a30d)' : 'var(--text-secondary,#666)',
                  cursor: 'pointer',
                }}
              >
                Ninguna
              </button>
              {subcats.map((s) => {
                const active = s.id === subId;
                return (
                  <button
                    key={s.id}
                    onClick={() => setSubId(s.id)}
                    style={{
                      padding: '6px 14px',
                      borderRadius: 20,
                      border: active ? '2px solid var(--lime-deep,#65a30d)' : '2px solid transparent',
                      background: active ? 'var(--lime-tint,#f7fee7)' : 'var(--surface-secondary,#f5f5f5)',
                      fontSize: 13,
                      fontWeight: active ? 600 : 400,
                      color: active ? 'var(--lime-deep,#65a30d)' : 'var(--text-secondary,#666)',
                      cursor: 'pointer',
                    }}
                  >
                    {s.name}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ padding: '0 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <button
            onClick={handleSave}
            disabled={saving || !catId}
            style={{
              width: '100%',
              padding: '14px',
              borderRadius: 14,
              border: 'none',
              background: 'var(--lime, #a3e635)',
              color: '#1a2e05',
              fontSize: 15,
              fontWeight: 700,
              cursor: saving ? 'default' : 'pointer',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </button>

          {/* Delete */}
          {confirming ? (
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setConfirming(false)}
                style={{
                  flex: 1, padding: '12px', borderRadius: 14,
                  border: '1.5px solid var(--border,#e0e0e0)',
                  background: 'transparent', fontSize: 14,
                  color: 'var(--text-secondary,#666)', cursor: 'pointer',
                }}
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                disabled={saving}
                style={{
                  flex: 1, padding: '12px', borderRadius: 14,
                  border: 'none', background: '#ef4444',
                  color: '#fff', fontSize: 14, fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                Sí, eliminar
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirming(true)}
              style={{
                width: '100%', padding: '12px', borderRadius: 14,
                border: '1.5px solid #ef4444',
                background: 'transparent', fontSize: 14,
                fontWeight: 600, color: '#ef4444', cursor: 'pointer',
              }}
            >
              Eliminar regla
            </button>
          )}
        </div>
      </div>
    </>
  );
}

/* ─── ReglasScreen ─────────────────────────────── */

export function ReglasScreen() {
  const { merchantRules, merchants } = useData();
  const { categories } = useCatalog();
  const [search, setSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<MerchantRule | null>(null);

  const filteredRules = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return merchantRules;
    return merchantRules.filter((rule) => {
      const merchant = merchants.find((m) => m.id === rule.merchantId);
      return (
        merchant?.name?.toLowerCase().includes(q) ||
        rule.comercio?.toLowerCase().includes(q)
      );
    });
  }, [merchantRules, merchants, search]);

  function getRuleName(rule: MerchantRule) {
    const merchant = merchants.find((m) => m.id === rule.merchantId);
    return merchant?.name ?? rule.comercio ?? 'Comercio desconocido';
  }

  function getCategoryLabel(categoryId: string) {
    const cat = categories.find((c) => c.id === categoryId);
    return cat ? { name: cat.name, color: cat.color, icon: cat.icon } : null;
  }

  function getSubcategoryLabel(categoryId: string, subcategoryId?: string) {
    if (!subcategoryId) return null;
    const cat = categories.find((c) => c.id === categoryId);
    return cat?.subcategories?.find((s: any) => s.id === subcategoryId)?.name ?? null;
  }

  return (
    <>
      <Screen>
        {/* Header */}
        <div style={{ padding: '24px 20px 0' }}>
          <p style={{ fontSize: 12, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-tertiary,#999)', marginBottom: 4 }}>
            Reglas y comercios
          </p>
          <h1 style={{ fontFamily: 'var(--serif,Georgia,serif)', fontStyle: 'italic', fontSize: 28, fontWeight: 400, color: 'var(--text-primary,#1a1a1a)', margin: '0 0 8px', lineHeight: 1.2 }}>
            Enseñale a Fina a clasificar tus gastos
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary,#666)', margin: '0 0 20px', lineHeight: 1.5 }}>
            Cada regla le dice a Fina cómo categorizar automáticamente los gastos de un comercio.
          </p>
        </div>

        {/* Search */}
        <div style={{ padding: '0 20px 16px' }}>
          {searchOpen ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface-secondary,#f5f5f5)', borderRadius: 12, padding: '10px 14px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary,#999)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text" value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar comercio..." autoFocus
                style={{ flex: 1, border: 'none', background: 'transparent', fontSize: 15, color: 'var(--text-primary,#1a1a1a)', outline: 'none' }}
              />
              <button onClick={() => { setSearch(''); setSearchOpen(false); }} style={{ background: 'none', border: 'none', padding: 4, cursor: 'pointer', color: 'var(--text-tertiary,#999)', fontSize: 18, lineHeight: 1 }}>✕</button>
            </div>
          ) : (
            <button
              onClick={() => setSearchOpen(true)}
              style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface-secondary,#f5f5f5)', borderRadius: 12, padding: '10px 14px', border: 'none', width: '100%', cursor: 'pointer', color: 'var(--text-tertiary,#999)', fontSize: 15, textAlign: 'left' }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              Buscar comercio...
            </button>
          )}
        </div>

        {/* Rules list */}
        <div style={{ padding: '0 20px 100px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontFamily: 'var(--serif,Georgia,serif)', fontStyle: 'italic', fontSize: 18, color: 'var(--text-primary,#1a1a1a)' }}>
              Reglas activas
            </span>
            <span style={{ fontSize: 13, color: 'var(--text-tertiary,#999)' }}>
              {filteredRules.length}
            </span>
          </div>

          {filteredRules.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-tertiary,#999)' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
              <p style={{ fontSize: 15, fontWeight: 500, margin: '0 0 4px' }}>
                {search ? 'Sin resultados' : 'Sin reglas todavía'}
              </p>
              <p style={{ fontSize: 13, margin: 0 }}>
                {search ? 'Probá con otro término.' : 'Cuando Fina detecte un comercio nuevo, va a crear una regla acá.'}
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {filteredRules.map((rule) => {
                const catInfo = getCategoryLabel(rule.categoryId);
                const subLabel = getSubcategoryLabel(rule.categoryId, rule.subcategoryId);
                const name = getRuleName(rule);

                return (
                  <button
                    key={rule.id}
                    onClick={() => setEditingRule(rule)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      background: 'var(--surface-primary,#fff)',
                      borderRadius: 14,
                      padding: '14px 16px',
                      border: '1px solid var(--border,#f0f0f0)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      width: '100%',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                    }}
                  >
                    {/* Cat color dot */}
                    <div style={{
                      width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
                      background: catInfo?.color || 'var(--border,#ccc)',
                    }} />

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary,#1a1a1a)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {name}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-tertiary,#999)', marginTop: 2 }}>
                        {catInfo
                          ? `${catInfo.icon ? catInfo.icon + ' ' : ''}${catInfo.name}${subLabel ? ` · ${subLabel}` : ''}`
                          : 'Sin categoría'}
                      </div>
                    </div>

                    {/* Edit chevron */}
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary,#bbb)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </Screen>

      {/* Edit sheet */}
      {editingRule && (
        <RuleEditSheet
          rule={editingRule}
          onClose={() => setEditingRule(null)}
        />
      )}
    </>
  );
}
