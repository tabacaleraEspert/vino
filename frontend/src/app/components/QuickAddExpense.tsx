import { useState, useCallback, useEffect, useRef } from "react";
import { X, ChevronRight, Zap, Check } from "lucide-react";
import { useData } from "../context/DataContext";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface Props {
  open: boolean;
  onClose: () => void;
}

const TODAY = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export function QuickAddExpense({ open, onClose }: Props) {
  const { categories, refresh } = useData();
  const [amount, setAmount] = useState("0");
  const [selectedCatId, setSelectedCatId] = useState<string | null>(null);
  const [selectedSubId, setSelectedSubId] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [fecha, setFecha] = useState(TODAY());
  const [cuotas, setCuotas] = useState(1);
  const [step, setStep] = useState<"amount" | "category" | "details" | "saving" | "done">("amount");
  const [saving, setSaving] = useState(false);
  const descRef = useRef<HTMLInputElement>(null);

  // Reset on open
  useEffect(() => {
    if (open) {
      setAmount("0");
      setSelectedCatId(null);
      setSelectedSubId(null);
      setDescription("");
      setFecha(TODAY());
      setCuotas(1);
      setStep("amount");
      setSaving(false);
    }
  }, [open]);

  // Focus description when reaching details step
  useEffect(() => {
    if (step === "details") setTimeout(() => descRef.current?.focus(), 300);
  }, [step]);

  const numericAmount = parseFloat(amount) || 0;

  const handleNumpad = useCallback((key: string) => {
    setAmount((prev) => {
      if (key === "backspace") {
        const next = prev.slice(0, -1);
        return next || "0";
      }
      if (key === ".") {
        if (prev.includes(".")) return prev;
        return prev + ".";
      }
      if (key === "00") {
        if (prev === "0") return prev;
        if (prev.includes(".") && prev.split(".")[1].length >= 2) return prev;
        return prev + "00";
      }
      // Limit decimals to 2
      if (prev.includes(".") && prev.split(".")[1].length >= 2) return prev;
      // Replace initial 0
      if (prev === "0" && key !== ".") return key;
      // Limit total length
      if (prev.replace(".", "").length >= 10) return prev;
      return prev + key;
    });
  }, []);

  const handleCategorySelect = (catId: string) => {
    setSelectedCatId(catId);
    setSelectedSubId(null);
    setStep("details");
  };

  const handleSave = async () => {
    if (numericAmount <= 0) return;
    setSaving(true);
    setStep("saving");

    try {
      const payload: Record<string, unknown> = {
        fecha,
        monto: numericAmount,
        tipo: "Gasto",
        moneda: "ARS",
        MedioCarga: "Manual",
      };
      if (description.trim()) payload.descripcion = description.trim();
      if (selectedCatId) payload.idCategoria = Number(selectedCatId);
      if (selectedSubId) payload.idSubcategoria = Number(selectedSubId);
      if (cuotas > 1) payload.cuotas = cuotas;

      await api.movimientos.create(payload);
      setStep("done");
      toast.success("Gasto registrado");
      await refresh();
      setTimeout(() => onClose(), 800);
    } catch (e: any) {
      toast.error(e.message || "Error al guardar");
      setStep("details");
    } finally {
      setSaving(false);
    }
  };

  const selectedCat = categories.find((c) => c.id === selectedCatId);

  if (!open) return null;

  // Format amount for display
  const displayAmount = (() => {
    if (amount === "0") return "0";
    const parts = amount.split(".");
    const intPart = parseInt(parts[0] || "0", 10).toLocaleString("es-AR");
    if (parts.length === 2) return `${intPart},${parts[1]}`;
    if (amount.endsWith(".")) return `${intPart},`;
    return intPart;
  })();

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* Sheet */}
      <div className="relative w-full max-w-md bg-[#0a0a0f] text-white rounded-t-[28px] shadow-2xl animate-slide-up overflow-hidden"
        style={{ maxHeight: "92vh" }}
      >
        {/* Grab handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-white/20" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-5 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-[#D8FF3C] flex items-center justify-center">
              <Zap className="w-4 h-4 text-black" strokeWidth={3} />
            </div>
            <span className="text-sm font-bold tracking-wide text-white/60">NUEVO GASTO</span>
          </div>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-white/10 transition-colors">
            <X className="w-5 h-5 text-white/60" />
          </button>
        </div>

        {/* Amount Display */}
        <div className="px-5 pt-2 pb-4">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold text-white/40">$</span>
            <span
              className="font-bold tracking-tight transition-all duration-200"
              style={{
                fontSize: amount.length > 8 ? 36 : amount.length > 5 ? 48 : 56,
                fontVariantNumeric: "tabular-nums",
                color: numericAmount > 0 ? "#fff" : "rgba(255,255,255,0.25)",
              }}
            >
              {displayAmount}
            </span>
          </div>
          {/* Date + category tag */}
          <div className="flex items-center gap-2 mt-2">
            <input
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              className="bg-white/10 text-white/70 text-xs font-medium rounded-lg px-2.5 py-1.5 border-none outline-none"
              style={{ colorScheme: "dark" }}
            />
            {selectedCat && (
              <div
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold"
                style={{ background: selectedCat.color + "30", color: selectedCat.color }}
              >
                <span>{selectedCat.icon}</span>
                {selectedCat.name}
              </div>
            )}
          </div>
        </div>

        {/* Step: Amount - Numpad */}
        {step === "amount" && (
          <div className="px-4 pb-4">
            {/* Numpad */}
            <div className="grid grid-cols-3 gap-2">
              {["1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "0", "backspace"].map((key) => (
                <button
                  key={key}
                  onClick={() => handleNumpad(key)}
                  className="h-14 rounded-2xl text-xl font-bold transition-all active:scale-95 active:bg-white/20"
                  style={{
                    background: key === "backspace" ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.06)",
                    color: key === "backspace" ? "rgba(255,255,255,0.5)" : "#fff",
                  }}
                >
                  {key === "backspace" ? "⌫" : key === "." ? "," : key}
                </button>
              ))}
            </div>

            {/* Continue button */}
            <button
              onClick={() => numericAmount > 0 && setStep("category")}
              disabled={numericAmount <= 0}
              className="w-full mt-3 py-4 rounded-2xl text-base font-bold transition-all active:scale-[0.98] disabled:opacity-30"
              style={{
                background: numericAmount > 0 ? "#D8FF3C" : "rgba(255,255,255,0.08)",
                color: numericAmount > 0 ? "#0a0a0f" : "rgba(255,255,255,0.3)",
              }}
            >
              Elegir categoria →
            </button>
          </div>
        )}

        {/* Step: Category */}
        {step === "category" && (
          <div className="px-4 pb-4">
            <div className="grid grid-cols-2 gap-2 max-h-[45vh] overflow-y-auto pr-1">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => handleCategorySelect(cat.id)}
                  className="flex items-center gap-3 p-3.5 rounded-2xl text-left transition-all active:scale-[0.97]"
                  style={{ background: "rgba(255,255,255,0.06)" }}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
                    style={{ background: cat.color + "25" }}
                  >
                    {cat.icon}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-bold truncate">{cat.name}</p>
                    <p className="text-[10px] text-white/40 font-medium">
                      {cat.subcategories?.length || 0} subs
                    </p>
                  </div>
                </button>
              ))}
            </div>

            <button
              onClick={() => { setStep("amount"); }}
              className="w-full mt-3 py-3 rounded-2xl text-sm font-semibold bg-white/8 text-white/50 transition-all"
            >
              ← Volver al monto
            </button>
          </div>
        )}

        {/* Step: Details (subcategory + description) */}
        {step === "details" && selectedCat && (
          <div className="px-4 pb-4 space-y-4">
            {/* Subcategories */}
            {selectedCat.subcategories && selectedCat.subcategories.length > 0 && (
              <div>
                <p className="text-xs font-bold text-white/40 uppercase tracking-wider mb-2">Subcategoria</p>
                <div className="flex flex-wrap gap-1.5">
                  {selectedCat.subcategories.map((sub) => (
                    <button
                      key={sub.id}
                      onClick={() => setSelectedSubId(selectedSubId === sub.id ? null : sub.id)}
                      className="px-3 py-2 rounded-xl text-xs font-semibold transition-all active:scale-95"
                      style={{
                        background: selectedSubId === sub.id ? selectedCat.color : "rgba(255,255,255,0.08)",
                        color: selectedSubId === sub.id ? "#0a0a0f" : "rgba(255,255,255,0.7)",
                      }}
                    >
                      {sub.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Cuotas */}
            <div>
              <p className="text-xs font-bold text-white/40 uppercase tracking-wider mb-2">Cuotas</p>
              <div className="flex flex-wrap gap-1.5">
                {[1, 3, 6, 9, 12, 18, 24].map((n) => (
                  <button
                    key={n}
                    onClick={() => setCuotas(n)}
                    className="px-3 py-2 rounded-xl text-xs font-semibold transition-all active:scale-95"
                    style={{
                      background: cuotas === n ? "#D8FF3C" : "rgba(255,255,255,0.08)",
                      color: cuotas === n ? "#0a0a0f" : "rgba(255,255,255,0.7)",
                    }}
                  >
                    {n === 1 ? "Sin cuotas" : `${n} cuotas`}
                  </button>
                ))}
              </div>
              {cuotas > 1 && (
                <p className="text-xs text-white/50 mt-2 font-medium">
                  {cuotas}x ${(numericAmount / cuotas).toLocaleString("es-AR", { maximumFractionDigits: 0 })} = ${numericAmount.toLocaleString("es-AR", { maximumFractionDigits: 0 })} total
                </p>
              )}
            </div>

            {/* Description */}
            <div>
              <p className="text-xs font-bold text-white/40 uppercase tracking-wider mb-2">Descripcion (opcional)</p>
              <input
                ref={descRef}
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Ej: Almuerzo con amigos"
                className="w-full px-4 py-3 rounded-xl bg-white/8 text-white text-sm font-medium placeholder:text-white/25 border border-white/10 outline-none focus:border-[#D8FF3C]/50 transition-colors"
              />
            </div>

            {/* Action buttons */}
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => setStep("category")}
                className="px-4 py-4 rounded-2xl text-sm font-semibold bg-white/8 text-white/50 transition-all"
              >
                ←
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 py-4 rounded-2xl text-base font-bold transition-all active:scale-[0.98]"
                style={{ background: "#D8FF3C", color: "#0a0a0f" }}
              >
                Guardar gasto
              </button>
            </div>
          </div>
        )}

        {/* Step: Saving animation */}
        {step === "saving" && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-12 h-12 border-3 border-white/20 border-t-[#D8FF3C] rounded-full animate-spin" />
            <p className="text-sm text-white/50 mt-4 font-medium">Guardando...</p>
          </div>
        )}

        {/* Step: Done */}
        {step === "done" && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 rounded-full bg-[#D8FF3C] flex items-center justify-center animate-bounce-in">
              <Check className="w-8 h-8 text-black" strokeWidth={3} />
            </div>
            <p className="text-lg font-bold mt-4">Listo</p>
            <p className="text-sm text-white/50 mt-1">
              ${displayAmount} registrado
            </p>
          </div>
        )}

        {/* Safe area bottom padding */}
        <div style={{ height: "env(safe-area-inset-bottom, 0px)" }} />
      </div>

      <style>{`
        @keyframes fade-in { from { opacity: 0 } to { opacity: 1 } }
        @keyframes bounce-in { 0% { transform: scale(0) } 50% { transform: scale(1.2) } 100% { transform: scale(1) } }
        .animate-fade-in { animation: fade-in .2s ease }
        .animate-bounce-in { animation: bounce-in .4s cubic-bezier(.2,1.4,.4,1) }
        .animate-slide-up { animation: slideUp .35s cubic-bezier(.2,.8,.2,1) }
        @keyframes slideUp { from { transform: translateY(100%) } to { transform: translateY(0) } }
      `}</style>
    </div>
  );
}
