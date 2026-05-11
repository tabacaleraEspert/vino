import { createBrowserRouter, useRouteError } from "react-router";
import { RootLayout } from "./components/RootLayout";
import { Dashboard } from "./components/Dashboard";
import { Transactions } from "./components/Transactions";
import { Categories } from "./components/Categories";
import { Budgets } from "./components/Budgets";
import { Merchants } from "./components/Merchants";
import { MerchantDetail } from "./components/MerchantDetail";
import { Stats } from "./components/Stats";
import { AdminPanel } from "./components/AdminPanel";
import { StatementUpload } from "./components/StatementUpload";
import { UncategorizedReview } from "./components/UncategorizedReview";
import { Chat } from "./components/Chat";
import { Debts } from "./components/Debts";
import { Wallets } from "./components/Wallets";
import { Settings } from "./components/Settings";
import { Login } from "./components/Login";
import { PrivacyPolicy } from "./components/PrivacyPolicy";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { OnboardingFlow } from "./components/onboarding/OnboardingFlow";

function ErrorFallback() {
  const error = useRouteError() as Error | null;
  const isChunkError =
    error?.message?.includes("dynamically imported module") ||
    error?.message?.includes("Failed to fetch");

  return (
    <div
      style={{
        minHeight: "100dvh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        fontFamily: "-apple-system, system-ui, sans-serif",
        textAlign: "center",
        background: "#FAFAF5",
      }}
    >
      <div style={{ fontSize: 40, marginBottom: 16 }}>
        {isChunkError ? "📡" : "😵"}
      </div>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        {isChunkError ? "Sin conexión" : "Algo salió mal"}
      </h2>
      <p style={{ fontSize: 14, color: "#666", marginBottom: 24, maxWidth: 300 }}>
        {isChunkError
          ? "No se pudo cargar la página. Verificá tu conexión a internet."
          : "Ocurrió un error inesperado."}
      </p>
      <button
        onClick={() => window.location.reload()}
        style={{
          background: "#0A0A0F",
          color: "#fff",
          border: "none",
          borderRadius: 14,
          padding: "14px 32px",
          fontSize: 15,
          fontWeight: 700,
          cursor: "pointer",
        }}
      >
        Reintentar
      </button>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: "/login",
    Component: Login,
    errorElement: <ErrorFallback />,
  },
  {
    path: "/privacy",
    Component: PrivacyPolicy,
  },
  {
    path: "/onboarding",
    Component: OnboardingFlow,
    errorElement: <ErrorFallback />,
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <RootLayout />
      </ProtectedRoute>
    ),
    errorElement: <ErrorFallback />,
    children: [
      { index: true, Component: Dashboard },
      { path: "transactions", Component: Transactions },
      { path: "categories", Component: Categories },
      { path: "budgets", Component: Budgets },
      { path: "merchants", Component: Merchants },
      { path: "merchants/:merchantId", Component: MerchantDetail },
      { path: "stats", Component: Stats },
      { path: "upload-statement", Component: StatementUpload },
      { path: "uncategorized", Component: UncategorizedReview },
      { path: "chat", Component: Chat },
      { path: "debts", Component: Debts },
      { path: "wallets", Component: Wallets },
      { path: "settings", Component: Settings },
      { path: "admin", Component: AdminPanel },
    ],
  },
]);