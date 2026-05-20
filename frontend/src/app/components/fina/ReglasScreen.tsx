import { useState, useMemo } from 'react';
import { useData } from '../../context/DataContext';
import { useCatalog } from '../../context/CatalogContext';
import { Screen, SectionHead, Pill, fmt } from './shared';

export function ReglasScreen() {
  const { merchantRules, merchants } = useData();
  const { categories } = useCatalog();
  const [search, setSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);

  const filteredRules = useMemo(() => {
    if (!search.trim()) return merchantRules;
    const q = search.toLowerCase();
    return merchantRules.filter((rule) => {
      const merchant = merchants.find((m) => m.id === rule.merchantId);
      return merchant?.name?.toLowerCase().includes(q);
    });
  }, [merchantRules, merchants, search]);

  const getMerchantName = (merchantId: string) => {
    const merchant = merchants.find((m) => m.id === merchantId);
    return merchant?.name ?? 'Comercio desconocido';
  };

  const getCategoryLabel = (categoryId: string) => {
    const cat = categories.find((c) => c.id === categoryId);
    return cat?.name ?? '';
  };

  const getSubcategoryLabel = (categoryId: string, subcategoryId?: string) => {
    if (!subcategoryId) return null;
    const cat = categories.find((c) => c.id === categoryId);
    const sub = cat?.subcategories?.find((s: any) => s.id === subcategoryId);
    return sub?.name ?? null;
  };

  return (
    <Screen>
      {/* Header */}
      <div style={{ padding: '24px 20px 0' }}>
        <p style={{
          fontSize: '12px',
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: 'var(--color-text-tertiary, #999)',
          marginBottom: '4px',
        }}>
          Reglas y comercios
        </p>
        <h1 style={{
          fontFamily: 'var(--font-serif, Georgia, serif)',
          fontStyle: 'italic',
          fontSize: '28px',
          fontWeight: 400,
          color: 'var(--color-text-primary, #1a1a1a)',
          margin: '0 0 8px',
          lineHeight: 1.2,
        }}>
          Enseñale a Fina a clasificar tus gastos
        </h1>
        <p style={{
          fontSize: '14px',
          color: 'var(--color-text-secondary, #666)',
          margin: '0 0 20px',
          lineHeight: 1.5,
        }}>
          Cada regla le dice a Fina cómo categorizar automáticamente los gastos de un comercio.
        </p>
      </div>

      {/* Search bar */}
      <div style={{ padding: '0 20px 16px' }}>
        {searchOpen ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--color-surface, #f5f5f5)',
            borderRadius: '12px',
            padding: '10px 14px',
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-tertiary, #999)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar comercio..."
              autoFocus
              style={{
                flex: 1,
                border: 'none',
                background: 'transparent',
                fontSize: '15px',
                color: 'var(--color-text-primary, #1a1a1a)',
                outline: 'none',
              }}
            />
            <button
              onClick={() => { setSearch(''); setSearchOpen(false); }}
              style={{
                background: 'none',
                border: 'none',
                padding: '4px',
                cursor: 'pointer',
                color: 'var(--color-text-tertiary, #999)',
                fontSize: '18px',
                lineHeight: 1,
              }}
            >
              ✕
            </button>
          </div>
        ) : (
          <button
            onClick={() => setSearchOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'var(--color-surface, #f5f5f5)',
              borderRadius: '12px',
              padding: '10px 14px',
              border: 'none',
              width: '100%',
              cursor: 'pointer',
              color: 'var(--color-text-tertiary, #999)',
              fontSize: '15px',
              textAlign: 'left',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            Buscar comercio...
          </button>
        )}
      </div>

      {/* Rules section */}
      <div style={{ padding: '0 20px' }}>
        <SectionHead title="Reglas activas" count={filteredRules.length} />

        {filteredRules.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '48px 20px',
            color: 'var(--color-text-tertiary, #999)',
          }}>
            <div style={{ fontSize: '40px', marginBottom: '12px' }}>📋</div>
            <p style={{ fontSize: '15px', fontWeight: 500, margin: '0 0 4px' }}>
              {search ? 'Sin resultados' : 'Sin reglas todavía'}
            </p>
            <p style={{ fontSize: '13px', margin: 0 }}>
              {search
                ? 'Probá con otro término de búsqueda.'
                : 'Cuando Fina detecte un comercio nuevo, va a crear una regla acá.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {filteredRules.map((rule) => {
              const categoryLabel = getCategoryLabel(rule.categoryId);
              const subcategoryLabel = getSubcategoryLabel(rule.categoryId, rule.subcategoryId);

              return (
                <div
                  key={rule.id}
                  style={{
                    background: 'var(--color-surface, #f5f5f5)',
                    borderRadius: '14px',
                    padding: '14px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  <div style={{
                    fontSize: '15px',
                    fontWeight: 600,
                    color: 'var(--color-text-primary, #1a1a1a)',
                  }}>
                    {getMerchantName(rule.merchantId)}
                  </div>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {categoryLabel && <Pill>{categoryLabel}</Pill>}
                    {subcategoryLabel && <Pill>{subcategoryLabel}</Pill>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Screen>
  );
}
