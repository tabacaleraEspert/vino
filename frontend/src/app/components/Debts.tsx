import { useState, useEffect } from "react";
import { Check, Trash2, Users, DollarSign, Loader2 } from "lucide-react";
import { api } from "../../lib/api";

interface Deuda {
  id: number;
  movimiento_id: number;
  nombre: string;
  monto: number;
  moneda: string;
  pagado: boolean;
  fecha: string;
  fecha_pago: string | null;
}

interface PersonaSummary {
  nombre: string;
  total: number;
  count: number;
}

export function Debts() {
  const [deudas, setDeudas] = useState<Deuda[]>([]);
  const [summary, setSummary] = useState<{ total_pendiente: number; personas: PersonaSummary[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showPaid, setShowPaid] = useState(false);
  const [actionId, setActionId] = useState<number | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [deudasRes, summaryRes] = await Promise.all([
        api.deudas.list(showPaid ? undefined : false),
        api.deudas.summary(),
      ]);
      setDeudas(deudasRes || []);
      setSummary(summaryRes);
    } catch (e) {
      console.error("Failed to load debts:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [showPaid]);

  const handlePagar = async (id: number) => {
    setActionId(id);
    try {
      await api.deudas.pagar(id);
      await fetchData();
    } catch (e) {
      console.error("Failed to mark as paid:", e);
    } finally {
      setActionId(null);
    }
  };

  const handleDelete = async (id: number) => {
    setActionId(id);
    try {
      await api.deudas.delete(id);
      await fetchData();
    } catch (e) {
      console.error("Failed to delete:", e);
    } finally {
      setActionId(null);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <h2 className="font-semibold text-lg">Me deben</h2>

      {/* Summary card */}
      {summary && summary.total_pendiente > 0 && (
        <div className="bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl p-6 text-white shadow-lg">
          <p className="text-sm opacity-90 mb-1">Total pendiente</p>
          <p className="text-3xl font-bold mb-3">
            ${summary.total_pendiente.toLocaleString("es-AR")}
          </p>
          <div className="space-y-2">
            {summary.personas.map((p) => (
              <div key={p.nombre} className="flex items-center justify-between text-sm">
                <span className="opacity-90">{p.nombre}</span>
                <span className="font-semibold">${p.total.toLocaleString("es-AR")}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {summary && summary.total_pendiente === 0 && !isLoading && (
        <div className="bg-white rounded-2xl p-8 shadow-sm text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="w-8 h-8 text-green-500" />
          </div>
          <p className="font-medium text-gray-700">Nadie te debe nada</p>
          <p className="text-sm text-gray-500 mt-1">
            Cuando hagas un split ("pagué yo, somos 4"), las deudas aparecen acá
          </p>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setShowPaid(false)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium ${!showPaid ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600"}`}
        >
          Pendientes
        </button>
        <button
          onClick={() => setShowPaid(true)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium ${showPaid ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}
        >
          Todas
        </button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="text-center py-8">
          <Loader2 className="w-6 h-6 text-gray-400 animate-spin mx-auto" />
        </div>
      ) : (
        <div className="space-y-2">
          {deudas.map((d) => (
            <div
              key={d.id}
              className={`bg-white rounded-xl p-4 shadow-sm flex items-center gap-3 ${d.pagado ? "opacity-50" : ""}`}
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${d.pagado ? "bg-green-100" : "bg-orange-100"}`}>
                {d.pagado ? (
                  <Check className="w-5 h-5 text-green-600" />
                ) : (
                  <DollarSign className="w-5 h-5 text-orange-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800">{d.nombre}</p>
                <p className="text-xs text-gray-400">
                  {new Date(d.fecha).toLocaleDateString("es-AR")}
                  {d.pagado && d.fecha_pago && ` · Pagó ${new Date(d.fecha_pago).toLocaleDateString("es-AR")}`}
                </p>
              </div>
              <p className="font-semibold text-gray-800 flex-shrink-0">
                ${d.monto.toLocaleString("es-AR")}
              </p>
              {!d.pagado && (
                <div className="flex gap-1 flex-shrink-0">
                  <button
                    onClick={() => handlePagar(d.id)}
                    disabled={actionId === d.id}
                    className="p-2 bg-green-100 text-green-600 rounded-lg hover:bg-green-200 transition-colors disabled:opacity-50"
                    title="Marcar como pagado"
                  >
                    {actionId === d.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => handleDelete(d.id)}
                    disabled={actionId === d.id}
                    className="p-2 bg-red-50 text-red-400 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50"
                    title="Eliminar"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
