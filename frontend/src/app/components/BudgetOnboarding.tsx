import { useState } from "react";
import { X, Wallet, Sparkles, ArrowRight, ArrowLeft, DollarSign, Check, PiggyBank, ShoppingBag, Home, Calendar, ChevronRight } from "lucide-react";
import { api, mapPresupuestosToBudgets } from "../../lib/api";
import { useData } from "../context/DataContext";

interface BudgetOnboardingProps {
  isOpen: boolean;
  onClose: () => void;
  mesAnio: string; // "2026-04"
}

function getMonthLabel(period: string): string {
  const [y, m] = period.split("-").map(Number);
  return new Date(y, m - 1).toLocaleDateString("es-AR", { month: "long", year: "numeric" });
}

function getNextMonths(basePeriod: string, count: number): string[] {
  const [y, m] = basePeriod.split("-").map(Number);
  const months: string[] = [];
  for (let i = 0; i < count; i++) {
    const d = new Date(y, m - 1 + i);
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  return months;
}

export function BudgetOnboarding({ isOpen, onClose, mesAnio }: BudgetOnboardingProps) {
  const { setBudgets } = useData();
  const [step, setStep] = useState(0);
  const [totalAmount, setTotalAmount] = useState("");
  const [selectedMonths, setSelectedMonths] = useState<Set<string>>(new Set([mesAnio]));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<{
    total_months: number;
    total_budgets: number;
    distribucion: { categoria: string; bucket: string; pct_bucket: string; monto: number }[];
  } | null>(null);
  const [error, setError] = useState("");

  const availableMonths = getNextMonths(mesAnio, 6);

  if (!isOpen) return null;

  const toggleMonth = (m: string) => {
    setSelectedMonths((prev) => {
      const next = new Set(prev);
      if (next.has(m)) {
        if (next.size > 1) next.delete(m); // keep at least one
      } else {
        next.add(m);
      }
      return next;
    });
  };

  const handleAutoAssign = async () => {
    const amount = parseFloat(totalAmount.replace(/[^0-9]/g, ""));
    if (!amount || amount <= 0) {
      setError("Ingresa un monto mayor a 0");
      return;
    }
    setError("");
    setIsSubmitting(true);
    try {
      let lastDistribucion: any[] = [];
      let totalCreated = 0;

      for (const month of Array.from(selectedMonths).sort()) {
        const res = await api.budgets.autoAssign(amount, month);
        if (res) {
          lastDistribucion = res.distribucion;
          totalCreated += res.presupuestos_creados;
        }
      }

      setResult({
        total_months: selectedMonths.size,
        total_budgets: totalCreated,
        distribucion: lastDistribucion,
      });

      // Refresh budgets for current view
      const rows = await api.budgets.list({ mes_anio: mesAnio });
      setBudgets(mapPresupuestosToBudgets(rows ?? []));
      setStep(3);
    } catch (e: any) {
      setError(e?.message || "Error al crear presupuestos");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setStep(0);
    setTotalAmount("");
    setSelectedMonths(new Set([mesAnio]));
    setResult(null);
    setError("");
    onClose();
  };

  const bucketInfo = [
    {
      name: "Necesidades",
      pct: "50%",
      icon: <Home className="w-5 h-5" />,
      color: "text-blue-600 bg-blue-100",
      examples: "Vivienda, alimentacion, transporte, servicios, salud",
    },
    {
      name: "Deseos",
      pct: "30%",
      icon: <ShoppingBag className="w-5 h-5" />,
      color: "text-purple-600 bg-purple-100",
      examples: "Entretenimiento, delivery, ropa, suscripciones",
    },
    {
      name: "Ahorro",
      pct: "20%",
      icon: <PiggyBank className="w-5 h-5" />,
      color: "text-green-600 bg-green-100",
      examples: "Ahorro, inversiones, deudas, emergencias",
    },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center">
      <div className="bg-white w-full max-w-md rounded-t-3xl sm:rounded-2xl max-h-[90vh] overflow-y-auto animate-slide-up">
        {/* Header */}
        <div className="sticky top-0 bg-white p-4 border-b flex items-center justify-between rounded-t-3xl sm:rounded-t-2xl z-10">
          <h3 className="font-semibold text-lg">
            {step === 0 && "Presupuestos"}
            {step === 1 && "Como queres configurar?"}
            {step === 2 && "Configurar presupuesto"}
            {step === 3 && "Listo!"}
          </h3>
          <button onClick={handleClose} className="p-2 hover:bg-gray-100 rounded-full">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-6">
          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="text-center space-y-6">
              <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto shadow-lg">
                <Wallet className="w-10 h-10 text-white" />
              </div>
              <div className="space-y-2">
                <h4 className="text-xl font-bold text-gray-800">Controla tus gastos</h4>
                <p className="text-gray-500 text-sm leading-relaxed">
                  Los presupuestos te ayudan a definir cuanto queres gastar por categoria cada mes.
                  Vas a poder ver en tiempo real si te estas pasando o si vas bien.
                </p>
              </div>
              <div className="bg-purple-50 rounded-xl p-4 text-left">
                <p className="text-sm text-purple-700 font-medium mb-2">Con presupuestos vas a poder:</p>
                <ul className="text-sm text-purple-600 space-y-1.5">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>Ver cuanto te queda por gastar en cada categoria</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>Recibir alertas cuando te acerques al limite</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>Ver un resumen de como te fue al final del mes</span>
                  </li>
                </ul>
              </div>
              <button
                onClick={() => setStep(1)}
                className="w-full py-3.5 bg-gradient-to-r from-purple-600 to-purple-700 text-white font-medium rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all flex items-center justify-center gap-2"
              >
                Empezar
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Step 1: Choose method */}
          {step === 1 && (
            <div className="space-y-4">
              <p className="text-sm text-gray-500 text-center mb-2">
                Elegi como queres configurar tus presupuestos
              </p>

              <button
                onClick={handleClose}
                className="w-full text-left p-4 border-2 border-gray-200 rounded-xl hover:border-blue-400 hover:bg-blue-50/50 transition-all group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-blue-200 transition-colors">
                    <Wallet className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-800">Quiero ponerlos yo</p>
                    <p className="text-sm text-gray-500 mt-0.5">
                      Elegi manualmente cuanto asignar a cada categoria
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 mt-2" />
                </div>
              </button>

              <button
                onClick={() => setStep(2)}
                className="w-full text-left p-4 border-2 border-gray-200 rounded-xl hover:border-purple-400 hover:bg-purple-50/50 transition-all group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-purple-200 transition-colors">
                    <Sparkles className="w-5 h-5 text-purple-600" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-800">Hacelo automaticamente</p>
                    <p className="text-sm text-gray-500 mt-0.5">
                      Usamos la regla 50/30/20 para distribuir tu presupuesto
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 mt-2" />
                </div>
              </button>

              <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Regla 50/30/20</p>
                {bucketInfo.map((b) => (
                  <div key={b.name} className="flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${b.color}`}>
                      {b.icon}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-700">{b.pct} {b.name}</p>
                      <p className="text-xs text-gray-400">{b.examples}</p>
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => setStep(0)}
                className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 flex items-center justify-center gap-1"
              >
                <ArrowLeft className="w-4 h-4" />
                Volver
              </button>
            </div>
          )}

          {/* Step 2: Enter total + select months */}
          {step === 2 && (
            <div className="space-y-5">
              {/* Amount */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Presupuesto total mensual</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    inputMode="numeric"
                    value={totalAmount}
                    onChange={(e) => {
                      const v = e.target.value.replace(/[^0-9]/g, "");
                      setTotalAmount(v ? Number(v).toLocaleString("es-AR") : "");
                    }}
                    placeholder="500.000"
                    className="w-full pl-10 pr-4 py-3.5 border border-gray-300 rounded-xl text-lg font-semibold focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    autoFocus
                  />
                </div>
              </div>

              {/* Month selector */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <label className="text-sm font-medium text-gray-700">Meses a configurar</label>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {availableMonths.map((m) => {
                    const selected = selectedMonths.has(m);
                    const [y, mo] = m.split("-").map(Number);
                    const label = new Date(y, mo - 1).toLocaleDateString("es-AR", { month: "short" });
                    const yearLabel = y.toString().slice(-2);
                    return (
                      <button
                        key={m}
                        onClick={() => toggleMonth(m)}
                        className={`py-2.5 px-3 rounded-lg text-sm font-medium transition-all border-2 ${
                          selected
                            ? "border-purple-500 bg-purple-50 text-purple-700"
                            : "border-gray-200 text-gray-500 hover:border-gray-300"
                        }`}
                      >
                        {label} '{yearLabel}
                      </button>
                    );
                  })}
                </div>
                <p className="text-xs text-gray-400">
                  Se creara el mismo presupuesto para {selectedMonths.size} {selectedMonths.size === 1 ? "mes" : "meses"}
                </p>
              </div>

              {/* Preview */}
              {totalAmount && (
                <div className="bg-gray-50 rounded-xl p-4 space-y-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase">Vista previa por mes</p>
                  {bucketInfo.map((b) => {
                    const pct = b.name === "Necesidades" ? 0.5 : b.name === "Deseos" ? 0.3 : 0.2;
                    const val = parseFloat(totalAmount.replace(/[^0-9]/g, "")) * pct;
                    return (
                      <div key={b.name} className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">{b.pct} {b.name}</span>
                        <span className="text-sm font-semibold text-gray-800">
                          ${isNaN(val) ? "0" : val.toLocaleString("es-AR")}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-600">
                  {error}
                </div>
              )}

              <button
                onClick={handleAutoAssign}
                disabled={isSubmitting || !totalAmount}
                className="w-full py-3.5 bg-gradient-to-r from-purple-600 to-purple-700 text-white font-medium rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Crear para {selectedMonths.size} {selectedMonths.size === 1 ? "mes" : "meses"}
                  </>
                )}
              </button>

              <button
                onClick={() => setStep(1)}
                className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 flex items-center justify-center gap-1"
              >
                <ArrowLeft className="w-4 h-4" />
                Volver
              </button>
            </div>
          )}

          {/* Step 3: Success */}
          {step === 3 && result && (
            <div className="text-center space-y-6">
              <div className="w-20 h-20 bg-gradient-to-br from-green-400 to-green-500 rounded-2xl flex items-center justify-center mx-auto shadow-lg animate-bounce">
                <Check className="w-10 h-10 text-white" />
              </div>
              <div className="space-y-2">
                <h4 className="text-xl font-bold text-gray-800">Presupuestos creados!</h4>
                <p className="text-gray-500 text-sm">
                  Se crearon {result.total_budgets} presupuestos en {result.total_months} {result.total_months === 1 ? "mes" : "meses"} con la regla 50/30/20
                </p>
              </div>

              <div className="bg-gray-50 rounded-xl p-4 space-y-2 text-left">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Distribucion por categoria</p>
                {result.distribucion.map((d, i) => (
                  <div key={i} className="flex items-center justify-between py-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          d.bucket === "necesidades"
                            ? "bg-blue-100 text-blue-700"
                            : d.bucket === "deseos"
                            ? "bg-purple-100 text-purple-700"
                            : "bg-green-100 text-green-700"
                        }`}
                      >
                        {d.pct_bucket}
                      </span>
                      <span className="text-sm text-gray-700">{d.categoria}</span>
                    </div>
                    <span className="text-sm font-semibold text-gray-800">
                      ${d.monto.toLocaleString("es-AR")}
                    </span>
                  </div>
                ))}
              </div>

              <p className="text-xs text-gray-400">
                Podes editar cualquier presupuesto tocando el icono de lapiz
              </p>

              <button
                onClick={handleClose}
                className="w-full py-3.5 bg-gradient-to-r from-green-500 to-green-600 text-white font-medium rounded-xl hover:from-green-600 hover:to-green-700 transition-all"
              >
                Ver mis presupuestos
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
