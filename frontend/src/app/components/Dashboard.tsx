import { useState, useEffect, useCallback } from "react";
import { useData } from "../context/DataContext";
import { useMonth } from "../context/MonthContext";
import { useAuth } from "../context/AuthContext";
import { MonthSelector } from "./MonthSelector";
import { api } from "../../lib/api";
import { useNavigate } from "react-router";
import { resolveIcon } from "../../lib/categoryIcons";

// ─── Theme ────────────────────────────────────────────────
const cream = "#F5F2EC";
const ink = "#1A1612";
const muted = "#8A7E6F";
const line = "#DCD5C8";
const lime = "#D8FF3C";

const treemapPalette = ["#FF7A45", "#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#8B5CF6"];

const fmt = (n: number) => "$" + n.toLocaleString("es-AR", { maximumFractionDigits: 0 });
const fmtK = (n: number) => n >= 1000 ? "$" + (n / 1000).toFixed(n >= 10000 ? 0 : 1) + "k" : "$" + n;

// Format big number: split by thousands, last group muted
function BigNumber({ value }: { value: number }) {
  const str = Math.round(value).toLocaleString("es-AR");
  const parts = str.split(".");
  const last = parts.pop() || "";
  const rest = parts.join(".");
  return (
    <div
      style={{
        fontFamily: '"Times New Roman", Georgia, serif',
        fontSize: "clamp(48px, 12vw, 76px)",
        lineHeight: 0.92,
        fontWeight: 400,
        letterSpacing: -3,
        display: "flex",
        alignItems: "baseline",
      }}
    >
      <span style={{ fontSize: "clamp(22px, 5vw, 32px)", marginRight: 4, position: "relative", top: "-1.2em" }}>$</span>
      {rest && <span>{rest}.</span>}
      <span style={{ color: muted }}>{last}</span>
    </div>
  );
}

export function Dashboard() {
  const { categories, refresh, refreshTrigger } = useData();
  const { selectedMonth } = useMonth();
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<{ gasto_mes: number; presupuesto_mes: number } | null>(null);
  const [breakdown, setBreakdown] = useState<{
    gastos_por_categoria: Array<{ categoria: string; total: number; pct: number }>;
    transacciones_recientes: Array<{ id: string; fecha: string; titulo: string; descripcion: string; monto: number; categoria: string }>;
    mayor_gasto: number;
    transacciones_count: number;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;

  const fetchDashboard = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const [summaryRes, breakdownRes] = await Promise.all([
        api.views.homeSummary({ period, moneda: "ARS" }),
        api.views.homeBreakdown({ period, currency: "ARS", top_categories: 6, recent_limit: 5 }),
      ]);
      setSummary({ gasto_mes: summaryRes.gasto_mes, presupuesto_mes: summaryRes.presupuesto_mes });
      setBreakdown({
        gastos_por_categoria: breakdownRes.gastos_por_categoria,
        transacciones_recientes: breakdownRes.transacciones_recientes,
        mayor_gasto: breakdownRes.mayor_gasto,
        transacciones_count: breakdownRes.transacciones_count,
      });
    } catch {
      setSummary(null);
      setBreakdown(null);
    } finally {
      setIsLoading(false);
    }
  }, [period, token]);

  useEffect(() => {
    if (!token) { setSummary(null); setBreakdown(null); return; }
    fetchDashboard();
  }, [token, period, refreshTrigger, fetchDashboard]);

  const monthSpent = summary?.gasto_mes ?? 0;
  const totalBudget = summary?.presupuesto_mes ?? 0;
  const percentageUsed = totalBudget > 0 ? (monthSpent / totalBudget) * 100 : 0;
  const remaining = totalBudget - monthSpent;

  const spendingByCategory = (breakdown?.gastos_por_categoria ?? []).slice(0, 6).map((g, i) => {
    const cat = categories.find((c) => c.name.toLowerCase() === g.categoria.toLowerCase());
    return { ...g, icon: cat?.icon, color: treemapPalette[i % treemapPalette.length], amount: g.total };
  });

  const recentTransactions = breakdown?.transacciones_recientes ?? [];

  const firstName = user?.name?.split(" ")[0] || "";
  const monthNames = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"];
  const shortMonth = monthNames[selectedMonth.month] || "";

  // Skeleton component
  const Skeleton = ({ h = "h-4", w = "w-full" }: { h?: string; w?: string }) => (
    <div className={`${h} ${w} rounded`} style={{ background: line, animation: "pulse 1.5s infinite" }} />
  );

  return (
    <div style={{ background: cream, color: ink, minHeight: "100%", paddingBottom: 20, fontFamily: '-apple-system, "SF Pro Text", system-ui' }}>
      {/* Header */}
      <div style={{ padding: "16px 24px 18px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: 2, fontWeight: 600, color: muted, textTransform: "uppercase" }}>
            Inicio · {shortMonth} {String(selectedMonth.year).slice(-2)}
          </div>
          <div
            style={{
              fontFamily: '"Times New Roman", Georgia, serif',
              fontSize: 28, lineHeight: 1, fontWeight: 400, fontStyle: "italic",
              marginTop: 8, letterSpacing: -0.5,
            }}
          >
            Hola, {firstName}.
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={refresh}
            disabled={isLoading}
            style={{
              width: 36, height: 36, borderRadius: 18, border: `1px solid ${ink}`,
              background: "transparent", display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 14, cursor: "pointer", color: ink, opacity: isLoading ? 0.4 : 1,
            }}
          >
            ↻
          </button>
          <MonthSelector />
        </div>
      </div>

      {/* HERO — Editorial big number */}
      {isLoading ? (
        <div style={{ padding: "16px 24px 26px", borderTop: `1px solid ${ink}`, borderBottom: `1px solid ${ink}`, margin: "0 24px" }}>
          <Skeleton h="h-3" w="w-32" />
          <div className="mt-4"><Skeleton h="h-16" w="w-48" /></div>
          <div className="mt-6"><Skeleton h="h-4" w="w-full" /></div>
        </div>
      ) : (
        <div style={{ padding: "16px 24px 26px", borderTop: `1px solid ${ink}`, borderBottom: `1px solid ${ink}`, margin: "0 24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
            <span style={{ fontSize: 11, letterSpacing: 1.5, fontWeight: 600, textTransform: "uppercase" }}>Gastado este mes</span>
            <span style={{ fontSize: 11, letterSpacing: 1, color: muted }}>de {fmt(totalBudget)}</span>
          </div>

          <BigNumber value={monthSpent} />

          {/* Tick marks */}
          <div style={{ marginTop: 22, display: "flex", gap: 2, alignItems: "flex-end" }}>
            {[...Array(40)].map((_, i) => {
              const filled = (i / 40) * 100 < percentageUsed;
              return (
                <div key={i} style={{ flex: 1, height: 18, background: filled ? ink : "transparent", borderTop: !filled ? `1px dashed ${ink}` : "none" }} />
              );
            })}
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 14, fontSize: 12 }}>
            <div>
              <span style={{ color: muted }}>Disponible </span>
              <span style={{ fontWeight: 700 }}>{fmt(remaining)}</span>
            </div>
            <div>
              <span style={{ background: lime, padding: "2px 6px", borderRadius: 2, fontWeight: 700, color: ink, fontFamily: '"SF Mono", monospace', fontSize: 11 }}>
                {percentageUsed.toFixed(0)}%
              </span>
              <span style={{ color: muted, marginLeft: 6 }}>usado</span>
            </div>
          </div>
        </div>
      )}

      {/* Categories Treemap */}
      {isLoading ? (
        <div style={{ padding: "18px 24px 0" }}>
          <Skeleton h="h-3" w="w-24" />
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Skeleton h="h-[200px]" /><Skeleton h="h-[200px]" />
          </div>
        </div>
      ) : spendingByCategory.length > 0 && (
        <div style={{ padding: "18px 24px 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: ink, letterSpacing: 2, textTransform: "uppercase", fontWeight: 600 }}>Categorias</div>
            <button
              onClick={() => navigate("/categories")}
              style={{ fontSize: 11, color: ink, fontWeight: 600, background: lime, padding: "2px 8px", borderRadius: 2, letterSpacing: 0.5, border: "none", cursor: "pointer" }}
            >
              VER TODAS →
            </button>
          </div>

          {/* Top row: 1 big + 2 stacked */}
          {spendingByCategory.length >= 3 ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 6, height: 200 }}>
                <div style={{ background: spendingByCategory[0].color, borderRadius: 18, padding: 14, display: "flex", flexDirection: "column", justifyContent: "space-between", color: "#fff" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.5 }}>{spendingByCategory[0].categoria.toUpperCase()}</div>
                    <div style={{ fontSize: 10, opacity: 0.85, fontWeight: 600 }}>{spendingByCategory[0].pct.toFixed(0)}%</div>
                  </div>
                  <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 36, fontWeight: 400, letterSpacing: -1.5, lineHeight: 1 }}>
                    {fmtK(spendingByCategory[0].amount)}
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateRows: "1fr 1fr", gap: 6 }}>
                  {spendingByCategory.slice(1, 3).map((c) => (
                    <div key={c.categoria} style={{ background: c.color, borderRadius: 14, padding: 12, display: "flex", flexDirection: "column", justifyContent: "space-between", color: "#fff" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.5 }}>{c.categoria.toUpperCase()}</div>
                        <div style={{ fontSize: 9, opacity: 0.85 }}>{c.pct.toFixed(0)}%</div>
                      </div>
                      <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 24, fontWeight: 400, letterSpacing: -0.8, lineHeight: 1 }}>
                        {fmtK(c.amount)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {/* Bottom row */}
              {spendingByCategory.length > 3 && (
                <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(spendingByCategory.length - 3, 3)}, 1fr)`, gap: 6, marginTop: 6 }}>
                  {spendingByCategory.slice(3, 6).map((c) => (
                    <div key={c.categoria} style={{ background: c.color, borderRadius: 12, padding: 10, height: 82, display: "flex", flexDirection: "column", justifyContent: "space-between", color: "#fff" }}>
                      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: 0.5 }}>{c.categoria.toUpperCase()}</div>
                      <div>
                        <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 19, fontWeight: 400, letterSpacing: -0.5, lineHeight: 1 }}>{fmtK(c.amount)}</div>
                        <div style={{ fontSize: 9, opacity: 0.8, marginTop: 2 }}>{c.pct.toFixed(0)}%</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${spendingByCategory.length}, 1fr)`, gap: 6 }}>
              {spendingByCategory.map((c) => (
                <div key={c.categoria} style={{ background: c.color, borderRadius: 14, padding: 14, height: 100, display: "flex", flexDirection: "column", justifyContent: "space-between", color: "#fff" }}>
                  <div style={{ fontSize: 10, fontWeight: 700 }}>{c.categoria.toUpperCase()}</div>
                  <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 24, fontWeight: 400 }}>{fmtK(c.amount)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Recent transactions */}
      <div style={{ padding: "30px 24px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
          <span style={{ fontSize: 11, letterSpacing: 2, fontWeight: 600, textTransform: "uppercase" }}>Recientes</span>
          <button
            onClick={() => navigate("/transactions")}
            style={{ fontSize: 11, color: muted, background: "none", border: "none", cursor: "pointer" }}
          >
            Ver todos →
          </button>
        </div>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ padding: "12px 0", borderTop: `1px solid ${line}` }}>
                <Skeleton h="h-4" w="w-3/4" />
              </div>
            ))}
          </div>
        ) : (
          recentTransactions.map((t) => {
            const category = categories.find((c) => c.name.toLowerCase() === (t.categoria || "").toLowerCase());
            const icon = resolveIcon(category?.icon, t.categoria);
            const dateStr = new Date(t.fecha).toLocaleDateString("es-AR", { day: "numeric", month: "short" });
            return (
              <div
                key={t.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "auto 1fr auto",
                  gap: 14,
                  alignItems: "center",
                  padding: "12px 0",
                  borderTop: `1px solid ${line}`,
                }}
              >
                <div style={{ fontSize: 18, width: 32, textAlign: "center" }}>{icon}</div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 500 }}>{t.titulo || t.descripcion}</div>
                  <div style={{ fontSize: 11, color: muted }}>{dateStr}</div>
                </div>
                <div
                  style={{
                    fontFamily: '"Times New Roman", Georgia, serif',
                    fontSize: 18,
                    fontWeight: 500,
                    letterSpacing: -0.3,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  −{fmtK(Math.abs(t.monto))}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Insights */}
      <div style={{ padding: "0 24px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {isLoading ? (
          <>
            <div style={{ borderTop: `1px solid ${ink}`, paddingTop: 12 }}><Skeleton h="h-3" w="w-20" /><div className="mt-2"><Skeleton h="h-6" w="w-16" /></div></div>
            <div style={{ borderTop: `1px solid ${ink}`, paddingTop: 12 }}><Skeleton h="h-3" w="w-24" /><div className="mt-2"><Skeleton h="h-6" w="w-10" /></div></div>
          </>
        ) : (
          <>
            <div style={{ borderTop: `1px solid ${ink}`, paddingTop: 12 }}>
              <div style={{ fontSize: 10, letterSpacing: 1.5, fontWeight: 600, textTransform: "uppercase", color: muted }}>Mayor gasto</div>
              <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 24, fontWeight: 400, letterSpacing: -0.5, marginTop: 4 }}>
                {fmt(breakdown?.mayor_gasto ?? 0)}
              </div>
            </div>
            <div style={{ borderTop: `1px solid ${ink}`, paddingTop: 12 }}>
              <div style={{ fontSize: 10, letterSpacing: 1.5, fontWeight: 600, textTransform: "uppercase", color: muted }}>Transacciones</div>
              <div style={{ fontFamily: '"Times New Roman", Georgia, serif', fontSize: 24, fontWeight: 400, letterSpacing: -0.5, marginTop: 4 }}>
                {breakdown?.transacciones_count ?? 0}
              </div>
            </div>
          </>
        )}
      </div>

      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
    </div>
  );
}
