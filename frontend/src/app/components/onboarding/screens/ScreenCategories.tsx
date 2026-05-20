import { useState } from "react";
import { Frame, Eyebrow, Display, Italic, PrimaryBtn, Body, BackBtn } from "../primitives";
import { lime, ink, subtle, muted, cream } from "../theme";
import { apiFetch } from "../../../../lib/api";

/* ─── Types ─── */
interface SubCat {
  name: string;
  enabled: boolean;
}
interface Cat {
  icon: string;
  name: string;
  color: string;
  bucket: Bucket;
  subs: SubCat[];
  enabled: boolean;
  isCustom?: boolean;
}
type Bucket = "necesidades" | "estilo_vida" | "futuro";

const BUCKET_LABELS: Record<Bucket, { title: string; sub: string; pct: string }> = {
  necesidades: { title: "Necesidades", sub: "Lo esencial para vivir", pct: "50%" },
  estilo_vida: { title: "Estilo de vida", sub: "Lo que te hace disfrutar", pct: "30%" },
  futuro: { title: "Tu futuro", sub: "Se calcula automáticamente", pct: "20%" },
};

const BUCKETS: Bucket[] = ["necesidades", "estilo_vida"];

/* ─── Default recommended categories ─── */
function defaultCats(): Cat[] {
  return [
    { icon: "🏠", name: "Vivienda", color: "#ec4899", bucket: "necesidades", enabled: true, subs: s(["Alquiler", "Expensas", "Hipoteca", "Mantenimiento"]) },
    { icon: "🍴", name: "Comida", color: "#14b8a6", bucket: "necesidades", enabled: true, subs: s(["Súper", "Almacén", "Verdulería", "Carnicería", "Delivery"]) },
    { icon: "🚗", name: "Transporte", color: "#f97316", bucket: "necesidades", enabled: true, subs: s(["Nafta", "SUBE", "Uber", "Estacionamiento", "Peajes"]) },
    { icon: "💡", name: "Servicios", color: "#eab308", bucket: "necesidades", enabled: true, subs: s(["Luz", "Gas", "Agua", "Internet", "Celular"]) },
    { icon: "💊", name: "Salud", color: "#06b6d4", bucket: "necesidades", enabled: true, subs: s(["Prepaga", "Farmacia", "Consultas", "Gimnasio"]) },
    { icon: "🎓", name: "Educación", color: "#8b5cf6", bucket: "necesidades", enabled: true, subs: s(["Cuotas", "Cursos", "Libros"]) },
    { icon: "🎬", name: "Ocio", color: "#d946ef", bucket: "estilo_vida", enabled: true, subs: s(["Restaurantes", "Bar", "Café", "Eventos", "Cine", "Streaming", "Viajes", "Hobbies"]) },
    { icon: "👕", name: "Compras", color: "#57534e", bucket: "estilo_vida", enabled: true, subs: s(["Ropa", "Calzado", "Hogar", "Tecnología"]) },
  ];
}
function s(names: string[]): SubCat[] {
  return names.map((n) => ({ name: n, enabled: true }));
}

/* ─── Icons for custom categories ─── */
const ICONS = ["📦", "🎵", "🐾", "✈️", "🏋️", "🎮", "💼", "🎁", "🔧", "📱"];
const COLORS = ["#ef4444", "#f97316", "#eab308", "#14b8a6", "#3b82f6", "#8b5cf6", "#ec4899", "#d946ef"];

/* ─── Component ─── */
interface Props {
  onNext: () => void;
  onBack?: () => void;
}

export function ScreenCategories({ onNext, onBack }: Props) {
  const [cats, setCats] = useState<Cat[]>(defaultCats);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [adding, setAdding] = useState<Bucket | null>(null);
  const [newName, setNewName] = useState("");
  const [newIcon, setNewIcon] = useState(ICONS[0]);
  const [newBucket, setNewBucket] = useState<Bucket>("necesidades");
  const [addingSub, setAddingSub] = useState<number | null>(null);
  const [newSubName, setNewSubName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  const toggleCat = (i: number) => {
    setCats((p) => p.map((c, j) => (j === i ? { ...c, enabled: !c.enabled } : c)));
  };

  const toggleSub = (ci: number, si: number) => {
    setCats((p) =>
      p.map((c, j) =>
        j === ci ? { ...c, subs: c.subs.map((s, k) => (k === si ? { ...s, enabled: !s.enabled } : s)) } : c
      )
    );
  };

  const addCategory = () => {
    if (!newName.trim()) return;
    const bucket = adding || newBucket;
    setCats((p) => [
      ...p,
      {
        icon: newIcon,
        name: newName.trim(),
        color: COLORS[p.length % COLORS.length],
        bucket,
        enabled: true,
        isCustom: true,
        subs: [],
      },
    ]);
    setNewName("");
    setAdding(null);
  };

  const addSubCategory = (ci: number) => {
    if (!newSubName.trim()) return;
    setCats((p) =>
      p.map((c, j) =>
        j === ci ? { ...c, subs: [...c.subs, { name: newSubName.trim(), enabled: true }] } : c
      )
    );
    setNewSubName("");
    setAddingSub(null);
  };

  const handleContinue = async () => {
    setSaving(true);
    try {
      const selected = cats
        .filter((c) => c.enabled)
        .map((c) => ({
          nombre: c.name,
          icon: c.icon,
          color: c.color,
          bucket: c.bucket,
          subcategorias: c.subs.filter((s) => s.enabled).map((s) => s.name),
        }));
      await apiFetch("/categorias/onboarding", {
        method: "POST",
        body: JSON.stringify({ categorias: selected }),
      });
      onNext();
    } catch (e) {
      console.error("Save categories failed:", e);
      setSaveError("No se pudieron guardar las categorias. Intenta de nuevo.");
    } finally {
      setSaving(false);
    }
  };

  const enabledCount = cats.filter((c) => c.enabled).length;
  const subCount = cats.filter((c) => c.enabled).reduce((a, c) => a + c.subs.filter((s) => s.enabled).length, 0);

  return (
    <Frame>
      {onBack && <BackBtn onClick={onBack} />}
      <Eyebrow>paso 2 · tus categorías</Eyebrow>
      <Display>
        <Italic>Personalizá</Italic> tus<br />categorías.
      </Display>
      <Body>
        <span style={{ marginTop: 6, display: "block" }}>
          Te recomendamos estas {enabledCount} categorías y {subCount} subcategorías.
          Podés activar, desactivar o agregar las que quieras.
        </span>
      </Body>

      <div style={{ flex: 1, overflowY: "auto", marginTop: 16, marginRight: -8, paddingRight: 8, paddingBottom: 16 }}>
        {BUCKETS.map((bucket) => {
          const bl = BUCKET_LABELS[bucket];
          const bucketCats = cats.map((c, i) => ({ ...c, _i: i })).filter((c) => c.bucket === bucket);
          return (
            <div key={bucket} style={{ marginBottom: 20 }}>
              {/* Bucket header */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: -0.3 }}>{bl.title}</div>
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 800,
                    background: lime,
                    color: ink,
                    padding: "2px 7px",
                    borderRadius: 4,
                  }}
                >
                  {bl.pct}
                </div>
                <div style={{ fontSize: 11, color: muted, flex: 1 }}>{bl.sub}</div>
              </div>

              {/* Category cards */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {bucketCats.map((c) => {
                  const isOpen = expandedIdx === c._i;
                  return (
                    <div key={c._i}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          background: c.enabled ? "#fff" : "rgba(0,0,0,0.03)",
                          border: `1px solid ${c.enabled ? subtle : "rgba(0,0,0,0.04)"}`,
                          borderRadius: 12,
                          padding: "10px 12px",
                          opacity: c.enabled ? 1 : 0.5,
                          transition: "opacity .2s, background .2s",
                        }}
                      >
                        {/* Toggle */}
                        <button
                          onClick={() => toggleCat(c._i)}
                          style={{
                            width: 22,
                            height: 22,
                            borderRadius: 6,
                            border: `2px solid ${c.enabled ? c.color : "#ccc"}`,
                            background: c.enabled ? c.color : "transparent",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            cursor: "pointer",
                            flexShrink: 0,
                            transition: "background .2s, border-color .2s",
                          }}
                        >
                          {c.enabled && (
                            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                              <path d="M2.5 6L5 8.5L9.5 3.5" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          )}
                        </button>

                        {/* Icon + name */}
                        <span style={{ fontSize: 18 }}>{c.icon}</span>
                        <span style={{ fontSize: 13, fontWeight: 700, flex: 1, letterSpacing: -0.2 }}>{c.name}</span>

                        {/* Sub count + expand */}
                        <button
                          onClick={() => setExpandedIdx(isOpen ? null : c._i)}
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            color: muted,
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                            padding: "4px 0",
                          }}
                        >
                          {c.subs.filter((s) => s.enabled).length}/{c.subs.length} subs
                          <span style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0)", transition: "transform .2s", fontSize: 12 }}>▾</span>
                        </button>
                      </div>

                      {/* Expanded subcategories */}
                      <div
                        style={{
                          maxHeight: isOpen ? 400 : 0,
                          overflow: "hidden",
                          transition: "max-height .3s ease",
                        }}
                      >
                        <div style={{ padding: "8px 0 4px 44px", display: "flex", flexWrap: "wrap", gap: 5 }}>
                          {c.subs.map((sub, si) => (
                            <button
                              key={si}
                              onClick={() => toggleSub(c._i, si)}
                              style={{
                                fontSize: 11,
                                fontWeight: 600,
                                padding: "5px 10px",
                                borderRadius: 8,
                                border: `1px solid ${sub.enabled ? c.color : "#ddd"}`,
                                background: sub.enabled ? `${c.color}15` : "transparent",
                                color: sub.enabled ? ink : "#aaa",
                                cursor: "pointer",
                                transition: "all .2s",
                                textDecoration: sub.enabled ? "none" : "line-through",
                              }}
                            >
                              {sub.name}
                            </button>
                          ))}
                          {/* Add subcategory */}
                          {addingSub === c._i ? (
                            <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                              <input
                                autoFocus
                                value={newSubName}
                                onChange={(e) => setNewSubName(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && addSubCategory(c._i)}
                                placeholder="Nueva sub..."
                                style={{
                                  fontSize: 11,
                                  padding: "5px 8px",
                                  borderRadius: 8,
                                  border: `1px solid ${c.color}`,
                                  outline: "none",
                                  width: 100,
                                  fontFamily: "inherit",
                                }}
                              />
                              <button
                                onClick={() => addSubCategory(c._i)}
                                style={{ fontSize: 11, fontWeight: 700, color: c.color, background: "none", border: "none", cursor: "pointer" }}
                              >
                                +
                              </button>
                              <button
                                onClick={() => { setAddingSub(null); setNewSubName(""); }}
                                style={{ fontSize: 11, color: "#aaa", background: "none", border: "none", cursor: "pointer" }}
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setAddingSub(c._i)}
                              style={{
                                fontSize: 11,
                                fontWeight: 600,
                                padding: "5px 10px",
                                borderRadius: 8,
                                border: "1px dashed #ccc",
                                background: "transparent",
                                color: muted,
                                cursor: "pointer",
                              }}
                            >
                              + agregar
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Add category to this bucket */}
                {adding === bucket ? (
                  <div
                    style={{
                      background: "#fff",
                      border: `1px solid ${subtle}`,
                      borderRadius: 12,
                      padding: "10px 12px",
                    }}
                  >
                    <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8 }}>
                      {ICONS.map((ic) => (
                        <button
                          key={ic}
                          onClick={() => setNewIcon(ic)}
                          style={{
                            fontSize: 16,
                            padding: 2,
                            border: newIcon === ic ? `2px solid ${ink}` : "2px solid transparent",
                            borderRadius: 6,
                            background: "none",
                            cursor: "pointer",
                          }}
                        >
                          {ic}
                        </button>
                      ))}
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                      <input
                        autoFocus
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && addCategory()}
                        placeholder="Nombre de la categoría"
                        style={{
                          flex: 1,
                          fontSize: 13,
                          padding: "8px 10px",
                          borderRadius: 8,
                          border: `1px solid ${subtle}`,
                          outline: "none",
                          fontFamily: "inherit",
                        }}
                      />
                      <button
                        onClick={addCategory}
                        style={{
                          fontSize: 13,
                          fontWeight: 700,
                          padding: "8px 14px",
                          borderRadius: 8,
                          background: ink,
                          color: "#fff",
                          border: "none",
                          cursor: "pointer",
                        }}
                      >
                        Agregar
                      </button>
                      <button
                        onClick={() => { setAdding(null); setNewName(""); }}
                        style={{
                          fontSize: 13,
                          padding: "8px 10px",
                          borderRadius: 8,
                          background: "none",
                          border: `1px solid ${subtle}`,
                          cursor: "pointer",
                          color: muted,
                        }}
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => { setAdding(bucket); setNewBucket(bucket); }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      padding: "10px 12px",
                      border: "1px dashed rgba(0,0,0,0.15)",
                      borderRadius: 12,
                      background: "transparent",
                      cursor: "pointer",
                      fontSize: 12,
                      fontWeight: 600,
                      color: muted,
                    }}
                  >
                    + Agregar categoría
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {/* Tu Futuro section - informational */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: -0.3 }}>{BUCKET_LABELS.futuro.title}</div>
            <div
              style={{
                fontSize: 10,
                fontWeight: 800,
                background: lime,
                color: ink,
                padding: "2px 7px",
                borderRadius: 4,
              }}
            >
              20%
            </div>
          </div>
          <div
            style={{
              background: `${lime}22`,
              border: `1px solid ${lime}55`,
              borderRadius: 12,
              padding: "12px 14px",
              fontSize: 12,
              color: muted,
              lineHeight: 1.5,
            }}
          >
            💡 Tu ahorro se calcula automáticamente: es lo que sobra después de tus gastos.
            No necesitás una categoría para eso. Más adelante vamos a tener un módulo
            de inversiones para que puedas trackear tu plata.
          </div>
        </div>
      </div>

      {saveError && (
        <div style={{ background: "#FEF2F2", color: "#DC2626", borderRadius: 10, padding: "8px 12px", fontSize: 13, fontWeight: 600, marginTop: 8 }}>
          {saveError}
        </div>
      )}
      <div style={{ marginTop: 8 }}>
        <PrimaryBtn onClick={handleContinue} disabled={saving || enabledCount === 0}>
          {saving ? "Guardando..." : `Continuar con ${enabledCount} categorías →`}
        </PrimaryBtn>
      </div>
    </Frame>
  );
}
