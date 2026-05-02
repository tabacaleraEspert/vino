import { useState, useRef, useEffect } from "react";
import { Upload, FileText, Image, X, Check, AlertCircle, ChevronDown, Trash2, ArrowLeft, FileSearch, Brain, Sparkles, CheckCircle2 } from "lucide-react";
import { api } from "../../lib/api";
import { useData } from "../context/DataContext";
import { useNavigate } from "react-router";

interface ExtractedTx {
  fecha: string;
  descripcion: string;
  monto: number;
  moneda: string;
  tipo: "Gasto" | "Ingreso";
  categoria_id: number | null;
  subcategoria_id: number | null;
  categoria_nombre: string;
  subcategoria_nombre: string;
  included: boolean;
  confianza?: "alta" | "media" | "baja";
  comercio_identificado?: string;
}

type Step = "select-bank" | "upload" | "processing" | "review" | "confirming" | "done";

interface BankOption {
  id: string;
  name: string;
  logo: string;
  formats: string;
  native: boolean;
}

const BANKS: BankOption[] = [
  { id: "santander", name: "Santander", logo: "🔴", formats: "PDF (Visa), Excel", native: true },
  { id: "bbva", name: "BBVA Frances", logo: "🔵", formats: "PDF (Caja de Ahorro)", native: true },
  { id: "otro", name: "Otro banco", logo: "🏦", formats: "PDF, Excel, Imagen", native: false },
];

export function StatementUpload() {
  const { categories, refresh } = useData();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>("select-bank");
  const [selectedBank, setSelectedBank] = useState<BankOption | null>(null);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  const [statementInfo, setStatementInfo] = useState({ period: "", card: "" });
  const [transactions, setTransactions] = useState<ExtractedTx[]>([]);
  const [result, setResult] = useState<{ creados: number; duplicados: number; errores: number } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);

  const handleFile = async (file: File) => {
    const allowed = ["application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"];
    const allowedExt = [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xlsx", ".xls"];
    const extOk = allowedExt.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!allowed.includes(file.type) && !extOk) {
      setError("Formato no soportado. Usa PDF, JPG, PNG o Excel (.xlsx).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("El archivo supera los 10MB");
      return;
    }

    setError("");
    setFileName(file.name);
    setStep("processing");
    setProcessingStep(0);

    // Animate through steps while the API processes
    const stepTimers = [
      setTimeout(() => setProcessingStep(1), 800),
      setTimeout(() => setProcessingStep(2), 2000),
      setTimeout(() => setProcessingStep(3), 4000),
    ];

    try {
      const res = await api.statement.extract(file);
      stepTimers.forEach(clearTimeout);
      setProcessingStep(4); // done
      await new Promise((r) => setTimeout(r, 600)); // brief pause to show completion
      setTransactions(res.transactions || []);
      setStatementInfo({ period: res.statement_period || "", card: res.card_or_account || "" });
      setStep("review");
    } catch (e: any) {
      stepTimers.forEach(clearTimeout);
      setError(e.message || "Error al procesar el archivo");
      setStep("upload");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const handleConfirm = async () => {
    const included = transactions.filter((t) => t.included);
    if (included.length === 0) {
      setError("Selecciona al menos una transaccion");
      return;
    }
    setStep("confirming");
    setError("");
    try {
      const res = await api.statement.confirm({
        transactions: included,
        origen_label: statementInfo.card || "Statement",
      });
      setResult(res);
      await refresh();
      setStep("done");
    } catch (e: any) {
      setError(e.message || "Error al crear movimientos");
      setStep("review");
    }
  };

  const toggleTx = (idx: number) => {
    setTransactions((prev) => prev.map((t, i) => (i === idx ? { ...t, included: !t.included } : t)));
  };

  const updateTxCategory = (idx: number, catId: string) => {
    const cat = categories.find((c) => c.id === catId);
    setTransactions((prev) =>
      prev.map((t, i) =>
        i === idx ? { ...t, categoria_id: catId ? Number(catId) : null, categoria_nombre: cat?.name || "", subcategoria_id: null, subcategoria_nombre: "" } : t
      )
    );
  };

  const updateTxSubcategory = (idx: number, subId: string) => {
    const tx = transactions[idx];
    const cat = categories.find((c) => c.id === String(tx.categoria_id));
    const sub = cat?.subcategories?.find((s) => s.id === subId);
    setTransactions((prev) =>
      prev.map((t, i) => (i === idx ? { ...t, subcategoria_id: subId ? Number(subId) : null, subcategoria_nombre: sub?.name || "" } : t))
    );
  };

  const includedCount = transactions.filter((t) => t.included).length;
  const includedTotal = transactions.filter((t) => t.included).reduce((s, t) => s + t.monto, 0);

  return (
    <div className="p-4 space-y-4 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => {
          if (step === "upload") { setStep("select-bank"); setSelectedBank(null); }
          else navigate(-1);
        }} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <div>
          <h2 className="font-semibold text-lg">
            {step === "select-bank" ? "Cargar extracto" : selectedBank ? `Extracto ${selectedBank.name}` : "Cargar extracto"}
          </h2>
          <p className="text-sm text-gray-500">
            {step === "select-bank" ? "Selecciona tu banco" : "Subi tu resumen bancario o de tarjeta"}
          </p>
        </div>
      </div>

      {/* Select Bank */}
      {step === "select-bank" && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600 px-1">Selecciona tu banco para un mejor procesamiento:</p>
          {BANKS.map((bank) => (
            <button
              key={bank.id}
              onClick={() => { setSelectedBank(bank); setStep("upload"); }}
              className="w-full flex items-center gap-4 p-4 bg-white border border-gray-200 rounded-xl hover:border-purple-300 hover:bg-purple-50 transition-all text-left"
            >
              <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center text-2xl flex-shrink-0">
                {bank.logo}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-gray-900">{bank.name}</p>
                  {bank.native && (
                    <span className="text-[10px] font-bold bg-green-100 text-green-700 px-2 py-0.5 rounded-full">NATIVO</span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-0.5">Formatos: {bank.formats}</p>
              </div>
              <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          ))}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 mt-4">
            <p className="text-xs text-blue-700">
              <strong>Bancos nativos</strong> tienen parser optimizado — extraen transacciones con precision.
              Para otros bancos usamos IA que funciona bien pero puede necesitar ajustes.
            </p>
          </div>
        </div>
      )}

      {/* Upload */}
      {step === "upload" && (
        <div
          className={`border-2 border-dashed rounded-2xl p-10 text-center transition-colors ${
            dragOver ? "border-purple-500 bg-purple-50" : "border-gray-300 bg-white"
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <div className="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Upload className="w-8 h-8 text-purple-600" />
          </div>
          <p className="font-medium text-gray-700 mb-1">Arrastra tu archivo aca</p>
          <p className="text-sm text-gray-500 mb-4">o hace click para seleccionar</p>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.webp,.xlsx,.xls"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white font-medium rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all"
          >
            Seleccionar archivo
          </button>

          <div className="flex items-center justify-center gap-4 mt-6 text-xs text-gray-400">
            <span className="flex items-center gap-1"><FileText className="w-3.5 h-3.5" /> PDF</span>
            <span className="flex items-center gap-1"><FileText className="w-3.5 h-3.5" /> Excel</span>
            <span className="flex items-center gap-1"><Image className="w-3.5 h-3.5" /> JPG / PNG</span>
            <span>Max 10MB</span>
          </div>

          {selectedBank && !selectedBank.native && (
            <p className="mt-4 text-xs text-gray-400 text-center">
              Usamos IA para procesar extractos de {selectedBank.name}. Puede necesitar ajustes manuales.
            </p>
          )}
        </div>
      )}

      {/* Processing — animated steps */}
      {step === "processing" && (
        <div className="bg-white rounded-2xl p-8 shadow-sm space-y-6">
          <div className="text-center mb-2">
            <p className="font-semibold text-gray-800 text-lg">Procesando extracto</p>
            <p className="text-sm text-gray-500">{fileName}</p>
          </div>

          {[
            { icon: FileSearch, label: "Leyendo archivo", desc: "Extrayendo datos del documento" },
            { icon: Upload, label: "Parseando transacciones", desc: "Identificando gastos e ingresos" },
            { icon: Brain, label: "Analizando con IA", desc: "Identificando comercios y categorias" },
            { icon: Sparkles, label: "Categorizando", desc: "Asignando categorias a cada gasto" },
          ].map((s, i) => {
            const isActive = processingStep === i;
            const isDone = processingStep > i;
            const isPending = processingStep < i;

            return (
              <div
                key={i}
                className={`flex items-center gap-4 transition-all duration-500 ${
                  isPending ? "opacity-30" : "opacity-100"
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-500 ${
                    isDone
                      ? "bg-green-100"
                      : isActive
                      ? "bg-purple-100 animate-pulse"
                      : "bg-gray-100"
                  }`}
                >
                  {isDone ? (
                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                  ) : isActive ? (
                    <s.icon className="w-6 h-6 text-purple-600 animate-bounce" />
                  ) : (
                    <s.icon className="w-6 h-6 text-gray-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`font-medium text-sm transition-colors duration-300 ${
                    isDone ? "text-green-700" : isActive ? "text-purple-700" : "text-gray-400"
                  }`}>
                    {s.label}
                    {isDone && <span className="ml-1">-</span>}
                  </p>
                  <p className={`text-xs transition-colors duration-300 ${
                    isActive ? "text-purple-500" : "text-gray-400"
                  }`}>
                    {s.desc}
                  </p>
                </div>
                {isActive && (
                  <div className="w-5 h-5 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin flex-shrink-0" />
                )}
              </div>
            );
          })}

          {/* Progress bar */}
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${(processingStep / 4) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Review */}
      {step === "review" && (
        <>
          {/* Summary bar */}
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-80">{statementInfo.card || "Extracto"}</p>
                <p className="text-2xl font-bold">{includedCount} transacciones</p>
              </div>
              <div className="text-right">
                <p className="text-sm opacity-80">Total seleccionado</p>
                <p className="text-xl font-semibold">${includedTotal.toLocaleString("es-AR")}</p>
              </div>
            </div>
          </div>

          {/* Confidence legend */}
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-green-500" /> Alta</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-yellow-500" /> Media</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Baja</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-gray-300" /> Sin identificar</span>
          </div>

          {/* Transaction list */}
          <div className="space-y-2">
            {transactions.map((tx, idx) => {
              const cat = categories.find((c) => c.id === String(tx.categoria_id));
              const conf = tx.confianza;
              const borderColor =
                conf === "alta" ? "border-l-green-500" :
                conf === "media" ? "border-l-yellow-500" :
                conf === "baja" ? "border-l-red-500" :
                "border-l-gray-300";
              const bgColor =
                conf === "alta" ? "bg-green-50/50" :
                conf === "media" ? "bg-yellow-50/50" :
                conf === "baja" ? "bg-red-50/30" :
                "bg-white";

              return (
                <div
                  key={idx}
                  className={`rounded-xl p-3 shadow-sm transition-opacity border-l-4 ${borderColor} ${bgColor} ${
                    !tx.included ? "opacity-40" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Checkbox */}
                    <button
                      onClick={() => toggleTx(idx)}
                      className={`w-6 h-6 rounded-lg border-2 flex-shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                        tx.included ? "bg-purple-600 border-purple-600" : "border-gray-300"
                      }`}
                    >
                      {tx.included && <Check className="w-3.5 h-3.5 text-white" />}
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-0.5">
                        <p className="font-medium text-gray-800 text-sm truncate">{tx.descripcion}</p>
                        <p className={`font-semibold text-sm flex-shrink-0 ml-2 ${
                          tx.tipo === "Ingreso" ? "text-green-600" : "text-gray-800"
                        }`}>
                          {tx.tipo === "Ingreso" ? "+" : "-"}${tx.monto.toLocaleString("es-AR")}
                        </p>
                      </div>

                      {/* AI identification */}
                      {tx.comercio_identificado && tx.comercio_identificado !== tx.descripcion && (
                        <p className="text-xs text-purple-600 mb-0.5">
                          Identificado: {tx.comercio_identificado}
                        </p>
                      )}

                      <p className="text-xs text-gray-400 mb-2">{tx.fecha} · {tx.moneda}</p>

                      {/* Category selectors */}
                      {tx.included && (
                        <div className="flex gap-2">
                          <select
                            value={tx.categoria_id || ""}
                            onChange={(e) => updateTxCategory(idx, e.target.value)}
                            className={`text-xs border rounded-lg px-2 py-1.5 flex-1 min-w-0 ${
                              !tx.categoria_id ? "border-red-300 bg-red-50" : "border-gray-200 bg-gray-50"
                            }`}
                          >
                            <option value="">Sin categoria</option>
                            {categories.map((c) => (
                              <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                            ))}
                          </select>
                          {cat?.subcategories && cat.subcategories.length > 0 && (
                            <select
                              value={tx.subcategoria_id || ""}
                              onChange={(e) => updateTxSubcategory(idx, e.target.value)}
                              className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-gray-50 flex-1 min-w-0"
                            >
                              <option value="">Subcategoria</option>
                              {cat.subcategories.map((s) => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                              ))}
                            </select>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Actions */}
          <div className="sticky bottom-0 bg-white/90 backdrop-blur-sm p-4 -mx-4 border-t space-y-2">
            <button
              onClick={handleConfirm}
              disabled={includedCount === 0}
              className="w-full py-3.5 bg-gradient-to-r from-purple-600 to-purple-700 text-white font-medium rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Check className="w-4 h-4" />
              Confirmar {includedCount} transacciones
            </button>
            <button
              onClick={() => { setStep("upload"); setTransactions([]); }}
              className="w-full py-2.5 text-sm text-gray-500 hover:text-gray-700"
            >
              Cancelar
            </button>
          </div>
        </>
      )}

      {/* Confirming */}
      {step === "confirming" && (
        <div className="bg-white rounded-2xl p-10 text-center shadow-sm">
          <div className="w-16 h-16 mx-auto mb-4">
            <div className="w-16 h-16 border-4 border-green-200 border-t-green-600 rounded-full animate-spin" />
          </div>
          <p className="font-medium text-gray-700">Creando movimientos...</p>
          <p className="text-sm text-gray-500">{includedCount} transacciones</p>
        </div>
      )}

      {/* Done */}
      {step === "done" && result && (
        <div className="bg-white rounded-2xl p-8 shadow-sm text-center space-y-6">
          <div className="w-20 h-20 bg-gradient-to-br from-green-400 to-green-500 rounded-2xl flex items-center justify-center mx-auto shadow-lg">
            <Check className="w-10 h-10 text-white" />
          </div>
          <div className="space-y-1">
            <h3 className="text-xl font-bold text-gray-800">Extracto procesado!</h3>
            <p className="text-sm text-gray-500">
              {statementInfo.card || "Extracto bancario"}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="bg-green-50 rounded-xl p-3">
              <p className="text-2xl font-bold text-green-600">{result.creados}</p>
              <p className="text-xs text-green-700">Creados</p>
            </div>
            <div className="bg-yellow-50 rounded-xl p-3">
              <p className="text-2xl font-bold text-yellow-600">{result.duplicados}</p>
              <p className="text-xs text-yellow-700">Duplicados</p>
            </div>
            <div className="bg-red-50 rounded-xl p-3">
              <p className="text-2xl font-bold text-red-600">{result.errores}</p>
              <p className="text-xs text-red-700">Errores</p>
            </div>
          </div>

          <div className="space-y-2">
            <button
              onClick={() => navigate("/transactions")}
              className="w-full py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white font-medium rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all"
            >
              Ver mis gastos
            </button>
            <button
              onClick={() => { setStep("upload"); setTransactions([]); setResult(null); }}
              className="w-full py-2.5 text-sm text-gray-500 hover:text-gray-700"
            >
              Cargar otro extracto
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}
