import { Outlet, NavLink } from "react-router";
import { Home, Receipt, FolderOpen, Wallet, Store, TrendingUp, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useData } from "../context/DataContext";
import { useNavigate } from "react-router";

export function RootLayout() {
  const { user, logout } = useAuth();
  const { isLoading, error } = useData();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    { to: "/", icon: Home, label: "Inicio" },
    { to: "/transactions", icon: Receipt, label: "Gastos" },
    { to: "/budgets", icon: Wallet, label: "Presupuestos" },
    { to: "/categories", icon: FolderOpen, label: "Categorías" },
    { to: "/merchants", icon: Store, label: "Comercios" },
    { to: "/stats", icon: TrendingUp, label: "Estadísticas" },
  ];

  return (
    <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
      <header className="bg-white border-b border-gray-200 px-4 py-3 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-lg">Finanzas Personales</h1>
            {user && (
              <p className="text-xs text-gray-500">{user.name}</p>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Cerrar sesión"
          >
            <LogOut className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto pb-20 relative">
        {error && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-800">
            {error}
          </div>
        )}
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center min-h-[200px]">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <Outlet />
        )}
      </main>

      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 max-w-md mx-auto">
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
        </div>
      </nav>
    </div>
  );
}