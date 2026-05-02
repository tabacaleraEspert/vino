import { Outlet, NavLink } from "react-router";
import { useEffect, useState } from "react";
import { Home, Receipt, FolderOpen, Wallet, Store, TrendingUp, LogOut, RefreshCw, Upload, MessageCircle, MoreHorizontal, Users, CreditCard, Settings as SettingsIcon, Plus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useData } from "../context/DataContext";
import { useNavigate } from "react-router";
import { api } from "@/lib/api";
import { apiFetch } from "@/lib/api/client";
import { QuickAddExpense } from "./QuickAddExpense";

export function RootLayout() {
  const { user, logout } = useAuth();
  const { isLoading, error, refresh } = useData();
  const navigate = useNavigate();
  const [backendVersion, setBackendVersion] = useState<string | null>(null);
  const [hasMissingSetup, setHasMissingSetup] = useState(false);

  useEffect(() => {
    api.health().then((r) => setBackendVersion(r.version)).catch(() => setBackendVersion(null));

    // Check if Gmail or WhatsApp are missing
    Promise.all([
      apiFetch<{ whatsapp?: string; whatsapp_vinculado?: boolean }>("/auth/profile").catch(() => null),
      apiFetch<{ connected?: boolean }>("/gmail/status").catch(() => null),
    ]).then(([profile, gmail]) => {
      const missingWhatsapp = !profile?.whatsapp_vinculado;
      const missingGmail = !gmail?.connected;
      setHasMissingSetup(missingWhatsapp || missingGmail);
    });
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const [showMore, setShowMore] = useState(false);
  const [showQuickAdd, setShowQuickAdd] = useState(false);

  const navItems = [
    { to: "/", icon: Home, label: "Inicio" },
    { to: "/transactions", icon: Receipt, label: "Gastos" },
    { to: "/budgets", icon: Wallet, label: "Presupuestos" },
    { to: "/chat", icon: MessageCircle, label: "Chat" },
    { to: "/upload-statement", icon: Upload, label: "Extracto" },
  ];

  const moreItems = [
    { to: "/categories", icon: FolderOpen, label: "Categorías" },
    { to: "/merchants", icon: Store, label: "Comercios" },
    { to: "/stats", icon: TrendingUp, label: "Estadísticas" },
    { to: "/wallets", icon: CreditCard, label: "Billeteras" },
    { to: "/debts", icon: Users, label: "Me deben" },
    { to: "/uncategorized", icon: FolderOpen, label: "Sin categorizar" },
    { to: "/settings", icon: SettingsIcon, label: "Configuracion" },
  ];

  return (
    <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
      <header className="bg-white border-b border-gray-200 px-4 py-3 sticky top-0 z-10" style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 12px)' }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-lg">Finanzas Personales</h1>
            {user && (
              <p className="text-xs text-gray-500">{user.name}</p>
            )}
            <p className="text-[10px] text-gray-400 mt-0.5" title="Versiones frontend y backend">
              v{__APP_VERSION__}
              {backendVersion != null && ` · API v${backendVersion}`}
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={refresh}
              disabled={isLoading}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
              title="Actualizar datos"
            >
              <RefreshCw className={`w-5 h-5 text-gray-600 ${isLoading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Cerrar sesión"
            >
              <LogOut className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto pb-20 relative">
        {error && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-800">
            {error}
          </div>
        )}
        <Outlet />
      </main>

      {/* "More" menu overlay */}
      {showMore && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowMore(false)}
        >
          <div
            className="absolute bottom-16 right-2 max-w-md mx-auto bg-white rounded-xl shadow-xl border border-gray-200 p-2 min-w-[180px]"
            onClick={(e) => e.stopPropagation()}
          >
            {moreItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setShowMore(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors relative ${
                    isActive ? "text-blue-600 bg-blue-50" : "text-gray-700 hover:bg-gray-50"
                  }`
                }
              >
                <Icon className="w-5 h-5" />
                <span className="text-sm font-medium">{label}</span>
                {to === "/settings" && hasMissingSetup && (
                  <span className="w-2 h-2 bg-red-500 rounded-full ml-auto" />
                )}
              </NavLink>
            ))}
          </div>
        </div>
      )}

      {/* FAB - Quick Add */}
      <button
        onClick={() => setShowQuickAdd(true)}
        className="fixed z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all active:scale-90 hover:shadow-xl"
        style={{
          bottom: 76,
          right: "max(16px, calc(50% - 224px + 16px))",
          background: "linear-gradient(135deg, #D8FF3C 0%, #b8e600 100%)",
          boxShadow: "0 4px 20px rgba(216,255,60,0.4)",
        }}
      >
        <Plus className="w-7 h-7 text-black" strokeWidth={2.5} />
      </button>

      {/* Quick Add Modal */}
      <QuickAddExpense open={showQuickAdd} onClose={() => setShowQuickAdd(false)} />

      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 max-w-md mx-auto z-50">
        <div className="grid grid-cols-6">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center py-2 px-0.5 transition-colors ${
                  isActive
                    ? "text-blue-600 bg-blue-50"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className="w-5 h-5 mb-0.5" strokeWidth={isActive ? 2.5 : 2} />
                  <span className="truncate w-full text-center text-[10px] font-medium leading-tight">
                    {label}
                  </span>
                </>
              )}
            </NavLink>
          ))}
          {/* More button */}
          <button
            onClick={() => setShowMore((p) => !p)}
            className={`flex flex-col items-center justify-center py-2 px-0.5 transition-colors relative ${
              showMore ? "text-blue-600 bg-blue-50" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <MoreHorizontal className="w-5 h-5 mb-0.5" />
            <span className="truncate w-full text-center text-[10px] font-medium leading-tight">
              Más
            </span>
            {hasMissingSetup && (
              <span className="absolute top-1.5 right-2.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white" />
            )}
          </button>
        </div>
      </nav>
    </div>
  );
}