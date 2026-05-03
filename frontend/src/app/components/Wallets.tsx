import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { Plus, Wallet, TrendingDown, TrendingUp, Settings, Loader2, ChevronRight } from "lucide-react";
import { api } from "../../lib/api";

interface WalletData {
  id: number;
  nombre: string;
  moneda: string;
  icono: string;
  color: string;
  saldo_inicial: number;
  saldo_actual: number;
  gastos_total: number;
  ingresos_total: number;
  activa: boolean;
  es_default: boolean;
}

export function Wallets() {
  const navigate = useNavigate();
  const [wallets, setWallets] = useState<WalletData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newMoneda, setNewMoneda] = useState("ARS");
  const [newSaldo, setNewSaldo] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const fetchWallets = async () => {
    setIsLoading(true);
    try {
      const res = await api.billeteras.list();
      setWallets(res || []);
    } catch (e) {
      console.error("Failed to load wallets:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchWallets(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setIsCreating(true);
    try {
      const iconMap: Record<string, string> = { ARS: "🇦🇷", USD: "🇺🇸", EUR: "🇪🇺", BRL: "🇧🇷" };
      await api.billeteras.create({
        nombre: newName.trim(),
        moneda: newMoneda,
        icono: iconMap[newMoneda] || "💰",
        saldo_inicial: parseFloat(newSaldo.replace(/[^0-9]/g, "")) || 0,
      });
      setShowCreate(false);
      setNewName("");
      setNewSaldo("");
      await fetchWallets();
    } catch (e) {
      console.error("Failed to create wallet:", e);
    } finally {
      setIsCreating(false);
    }
  };

  const totalARS = wallets.filter(w => w.moneda === "ARS").reduce((s, w) => s + w.saldo_actual, 0);
  const totalUSD = wallets.filter(w => w.moneda === "USD").reduce((s, w) => s + w.saldo_actual, 0);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-lg">Mis Billeteras</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1 text-sm text-purple-600 font-medium"
        >
          <Plus className="w-4 h-4" />
          Nueva
        </button>
      </div>

      {/* Totals */}
      {!isLoading && wallets.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {totalARS !== 0 && (
            <div className="bg-gradient-to-br from-teal-500 to-teal-600 rounded-xl p-4 text-white">
              <p className="text-xs opacity-80">Total ARS</p>
              <p className="text-xl font-bold">${totalARS.toLocaleString("es-AR")}</p>
            </div>
          )}
          {totalUSD !== 0 && (
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-4 text-white">
              <p className="text-xs opacity-80">Total USD</p>
              <p className="text-xl font-bold">US${totalUSD.toLocaleString("es-AR")}</p>
            </div>
          )}
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="bg-white rounded-xl p-4 shadow-sm space-y-3">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nombre (ej: Cuenta sueldo)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            autoFocus
          />
          <div className="flex gap-2">
            <select
              value={newMoneda}
              onChange={(e) => setNewMoneda(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="ARS">🇦🇷 ARS</option>
              <option value="USD">🇺🇸 USD</option>
              <option value="EUR">🇪🇺 EUR</option>
            </select>
            <input
              type="text"
              inputMode="numeric"
              value={newSaldo}
              onChange={(e) => {
                const v = e.target.value.replace(/[^0-9]/g, "");
                setNewSaldo(v ? Number(v).toLocaleString("es-AR") : "");
              }}
              placeholder="Saldo inicial"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={!newName.trim() || isCreating}
            className="w-full py-2.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
          >
            {isCreating ? "Creando..." : "Crear billetera"}
          </button>
        </div>
      )}

      {/* Wallet list */}
      {isLoading ? (
        <div className="text-center py-8">
          <Loader2 className="w-6 h-6 text-gray-400 animate-spin mx-auto" />
        </div>
      ) : wallets.length === 0 ? (
        <div className="bg-white rounded-2xl p-8 shadow-sm text-center">
          <Wallet className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No tenés billeteras creadas</p>
        </div>
      ) : (
        <div className="space-y-3">
          {wallets.filter(w => w.activa).map((w) => (
            <button
              key={w.id}
              onClick={() => navigate(`/transactions?currency=${w.moneda}`)}
              className="bg-white rounded-xl p-4 shadow-sm w-full text-left hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
                  style={{ backgroundColor: `${w.color}20` }}
                >
                  {w.icono}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{w.nombre}</p>
                  <p className="text-xs text-gray-400">{w.moneda}{w.es_default ? " · Default" : ""}</p>
                </div>
                <div className="flex items-center gap-2">
                  <p className={`text-lg font-bold ${w.saldo_actual >= 0 ? "text-gray-800" : "text-red-600"}`}>
                    {w.moneda === "USD" ? "US" : ""}${w.saldo_actual.toLocaleString("es-AR")}
                  </p>
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <div className="flex items-center gap-1">
                  <TrendingDown className="w-3.5 h-3.5 text-red-400" />
                  <span>Gastos: ${w.gastos_total.toLocaleString("es-AR")}</span>
                </div>
                <div className="flex items-center gap-1">
                  <TrendingUp className="w-3.5 h-3.5 text-green-400" />
                  <span>Ingresos: ${w.ingresos_total.toLocaleString("es-AR")}</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
