import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft, Sparkles, Check, X, AlertCircle, Search, Loader2 } from "lucide-react";
import { api } from "../../lib/api";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { MonthSelector } from "./MonthSelector";

interface UncategorizedMerchant {
  comercio: string;
  count: number;
  total_monto: number;
  movimiento_ids: string[];
  last_fecha: string;
}

interface Suggestion {
  merchant_identified: string;
  rubro: string;
  confianza: string;
  categoria_id: number | null;
  categoria_nombre: string;
  subcategoria_id: number | null;
  subcategoria_nombre: string;
  explicacion: string;
  web_search_used: boolean;
}

export function UncategorizedReview() {
  const navigate = useNavigate();
  const { categories, refresh } = useData();
  const { selectedMonth } = useMonth();
  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;

  const [merchants, setMerchants] = useState<UncategorizedMerchant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalUncategorized, setTotalUncategorized] = useState(0);

  // Per-merchant state
  const [identifyingSet, setIdentifyingSet] = useState<Set<string>>(new Set());
  const [identifyingAll, setIdentifyingAll] = useState(false);
  const [suggestions, setSuggestions] = useState<Record<string, Suggestion>>({});
  const [selectedCategories, setSelectedCategories] = useState<Record<string, { catId: string; subId: string }>>({});
  const [categorizingSet, setCategorizingSet] = useState<Set<string>>(new Set());
  const [categorized, setCategorized] = useState<Set<string>>(new Set());

  const fetchUncategorized = async () => {
    setIsLoading(true);
    try {
      const res = await api.merchants.smart.uncategorized(period);
      setMerchants(res.merchants || []);
      setTotalUncategorized(res.total_uncategorized || 0);
    } catch (e) {
      console.error("Failed to fetch uncategorized:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchUncategorized(); }, [period]);

  const handleIdentify = async (comercio: string) => {
    setIdentifyingSet((prev) => new Set(prev).add(comercio));
    try {
      const res = await api.merchants.smart.identify(comercio);
      setSuggestions((prev) => ({ ...prev, [comercio]: res }));
      if (res.categoria_id) {
        setSelectedCategories((prev) => ({
          ...prev,
          [comercio]: { catId: String(res.categoria_id), subId: res.subcategoria_id ? String(res.subcategoria_id) : "" },
        }));
      }
    } catch (e) {
      console.error("Identification failed:", e);
    } finally {
      setIdentifyingSet((prev) => { const n = new Set(prev); n.delete(comercio); return n; });
    }
  };

  const handleCategorize = async (comercio: string) => {
    const sel = selectedCategories[comercio];
    if (!sel?.catId) return;
    setCategorizingSet((prev) => new Set(prev).add(comercio));
    try {
      await api.merchants.smart.categorize({
        comercio,
        categoria_id: Number(sel.catId),
        subcategoria_id: sel.subId ? Number(sel.subId) : null,
        create_rule: true,
      });
      setCategorized((prev) => new Set(prev).add(comercio));
    } catch (e) {
      console.error("Categorize failed:", e);
    } finally {
      setCategorizingSet((prev) => { const n = new Set(prev); n.delete(comercio); return n; });
    }
  };

  const handleAcceptSuggestion = async (comercio: string) => {
    const suggestion = suggestions[comercio];
    if (!suggestion?.categoria_id) return;
    // Set the category from suggestion and immediately categorize
    setSelectedCategories((prev) => ({
      ...prev,
      [comercio]: {
        catId: String(suggestion.categoria_id),
        subId: suggestion.subcategoria_id ? String(suggestion.subcategoria_id) : "",
      },
    }));
    setCategorizingSet((prev) => new Set(prev).add(comercio));
    try {
      await api.merchants.smart.categorize({
        comercio,
        categoria_id: Number(suggestion.categoria_id),
        subcategoria_id: suggestion.subcategoria_id ? Number(suggestion.subcategoria_id) : null,
        create_rule: true,
      });
      setCategorized((prev) => new Set(prev).add(comercio));
    } catch (e) {
      console.error("Accept suggestion failed:", e);
    } finally {
      setCategorizingSet((prev) => { const n = new Set(prev); n.delete(comercio); return n; });
    }
  };

  const handleIdentifyAll = async () => {
    const pending = merchants.filter((m) => !suggestions[m.comercio] && !categorized.has(m.comercio));
    if (pending.length === 0) return;

    setIdentifyingAll(true);
    const names = pending.map((m) => m.comercio);
    // Mark all as loading
    setIdentifyingSet(new Set(names));

    try {
      const res = await api.merchants.smart.identifyBatch(names);
      const results = res?.results || [];
      const newSuggestions: Record<string, Suggestion> = {};
      const newCategories: Record<string, { catId: string; subId: string }> = {};

      for (const r of results) {
        newSuggestions[r.merchant_raw] = r;
        if (r.categoria_id) {
          newCategories[r.merchant_raw] = {
            catId: String(r.categoria_id),
            subId: r.subcategoria_id ? String(r.subcategoria_id) : "",
          };
        }
      }

      setSuggestions((prev) => ({ ...prev, ...newSuggestions }));
      setSelectedCategories((prev) => ({ ...prev, ...newCategories }));
    } catch (e) {
      console.error("Batch identify failed:", e);
    } finally {
      setIdentifyingSet(new Set());
      setIdentifyingAll(false);
    }
  };

  const handleAcceptAll = async () => {
    const toAccept = merchants.filter((m) =>
      !categorized.has(m.comercio) && suggestions[m.comercio]?.categoria_id
    );
    for (const m of toAccept) {
      await handleAcceptSuggestion(m.comercio);
    }
    await refresh();
  };

  const pendingMerchants = merchants.filter((m) => !categorized.has(m.comercio));

  return (
    <div className="p-4 space-y-4 max-w-2xl mx-auto">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <div className="flex-1">
          <h2 className="font-semibold text-lg">Gastos sin categorizar</h2>
          <p className="text-sm text-gray-500">Revisa y categoriza comercios desconocidos</p>
        </div>
      </div>

      <MonthSelector />

      {isLoading ? (
        <div className="bg-white rounded-2xl p-10 text-center shadow-sm">
          <Loader2 className="w-8 h-8 text-purple-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-500">Cargando...</p>
        </div>
      ) : pendingMerchants.length === 0 ? (
        <div className="bg-white rounded-2xl p-10 text-center shadow-sm">
          <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Check className="w-8 h-8 text-green-500" />
          </div>
          <p className="font-medium text-gray-700 mb-1">Todo categorizado!</p>
          <p className="text-sm text-gray-500">No hay gastos pendientes de categorizar este mes</p>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="bg-gradient-to-r from-amber-500 to-orange-500 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-80">Pendientes</p>
                <p className="text-2xl font-bold">{pendingMerchants.length} comercios</p>
                <p className="text-sm opacity-80">{totalUncategorized} transacciones</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleIdentifyAll}
                  disabled={identifyingAll || identifyingSet.size > 0}
                  className="px-3 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {identifyingAll ? <Loader2 className="w-4 h-4 inline mr-1 animate-spin" /> : <Sparkles className="w-4 h-4 inline mr-1" />}
                  Identificar todos
                </button>
                {Object.keys(suggestions).length > 0 && (
                  <button
                    onClick={handleAcceptAll}
                    disabled={categorizingSet.size > 0}
                    className="px-3 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                  >
                    <Check className="w-4 h-4 inline mr-1" />
                    Aceptar todos
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Merchant list */}
          <div className="space-y-3">
            {pendingMerchants.map((m) => {
              const suggestion = suggestions[m.comercio];
              const sel = selectedCategories[m.comercio];
              const isIdentifying = identifyingSet.has(m.comercio);
              const isCategorizing = categorizingSet.has(m.comercio);
              const isAnyLoading = identifyingAll || identifyingSet.size > 0;
              const selectedCat = sel ? categories.find((c) => c.id === sel.catId) : null;

              return (
                <div key={m.comercio} className="bg-white rounded-xl p-4 shadow-sm space-y-3">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div className="min-w-0">
                      <p className="font-medium text-gray-800 truncate">{m.comercio}</p>
                      <p className="text-xs text-gray-400">
                        {m.count} {m.count === 1 ? "transaccion" : "transacciones"} · ${m.total_monto.toLocaleString("es-AR")}
                      </p>
                    </div>
                    {!suggestion ? (
                      <button
                        onClick={() => handleIdentify(m.comercio)}
                        disabled={isIdentifying || isAnyLoading}
                        className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg text-xs font-medium hover:bg-purple-200 transition-colors disabled:opacity-50 flex items-center gap-1"
                      >
                        {isIdentifying ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Search className="w-3 h-3" />
                        )}
                        {isIdentifying ? "Buscando..." : "Identificar"}
                      </button>
                    ) : suggestion.categoria_id ? (
                      <button
                        onClick={() => handleAcceptSuggestion(m.comercio)}
                        disabled={isCategorizing}
                        className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-xs font-medium hover:bg-green-200 transition-colors disabled:opacity-50 flex items-center gap-1"
                      >
                        {isCategorizing ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Check className="w-3 h-3" />
                        )}
                        Aceptar
                      </button>
                    ) : null}
                  </div>

                  {/* AI Suggestion */}
                  {suggestion && (
                    <div className={`rounded-lg p-3 text-sm ${
                      suggestion.confianza === "alta" ? "bg-green-50 border border-green-200" :
                      suggestion.confianza === "media" ? "bg-blue-50 border border-blue-200" :
                      "bg-gray-50 border border-gray-200"
                    }`}>
                      <div className="flex items-start gap-2">
                        <Sparkles className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                          suggestion.confianza === "alta" ? "text-green-500" :
                          suggestion.confianza === "media" ? "text-blue-500" : "text-gray-400"
                        }`} />
                        <div className="min-w-0">
                          <p className="font-medium text-gray-700">
                            {suggestion.merchant_identified}
                            {suggestion.rubro && <span className="text-gray-400 font-normal"> · {suggestion.rubro}</span>}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">{suggestion.explicacion}</p>
                          {suggestion.web_search_used && (
                            <p className="text-xs text-blue-500 mt-0.5">Verificado con busqueda web</p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Category selector */}
                  <div className="flex gap-2">
                    <select
                      value={sel?.catId || ""}
                      onChange={(e) => setSelectedCategories((prev) => ({
                        ...prev,
                        [m.comercio]: { catId: e.target.value, subId: "" },
                      }))}
                      className="text-sm border border-gray-200 rounded-lg px-2 py-2 bg-gray-50 flex-1 min-w-0"
                    >
                      <option value="">Categoria...</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                      ))}
                    </select>
                    {selectedCat?.subcategories && selectedCat.subcategories.length > 0 && (
                      <select
                        value={sel?.subId || ""}
                        onChange={(e) => setSelectedCategories((prev) => ({
                          ...prev,
                          [m.comercio]: { ...prev[m.comercio], subId: e.target.value },
                        }))}
                        className="text-sm border border-gray-200 rounded-lg px-2 py-2 bg-gray-50 flex-1 min-w-0"
                      >
                        <option value="">Subcategoria...</option>
                        {selectedCat.subcategories.map((s) => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                    )}
                    <button
                      onClick={() => handleCategorize(m.comercio)}
                      disabled={!sel?.catId || isCategorizing}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center gap-1 flex-shrink-0"
                    >
                      {isCategorizing ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Check className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
