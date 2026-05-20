import { createBrowserRouter, useRouteError } from "react-router";
import { RootLayout } from "./components/RootLayout";
import { Login } from "./components/Login";
import { PrivacyPolicy } from "./components/PrivacyPolicy";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { OnboardingFlow } from "./components/onboarding/OnboardingFlow";
import { Settings } from "./components/Settings";
import { AdminPanel } from "./components/AdminPanel";

function ErrorFallback() {
  const error = useRouteError() as Error | null;
  const isChunkError =
    error?.message?.includes("dynamically imported module") ||
    error?.message?.includes("Failed to fetch");

  return (
    <div style={{
      minHeight: '100dvh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
      fontFamily: 'var(--sans)',
      textAlign: 'center',
      background: 'var(--bg)',
      color: 'var(--fg)',
    }}>
      <div style={{ fontSize: 40, marginBottom: 16 }}>
        {isChunkError ? '📡' : '😵'}
      </div>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        {isChunkError ? 'Sin conexión' : 'Algo salió mal'}
      </h2>
      <p style={{ fontSize: 14, color: 'var(--fg-3)', marginBottom: 24, maxWidth: 300 }}>
        {isChunkError
          ? 'No se pudo cargar la página. Verificá tu conexión.'
          : 'Ocurrió un error inesperado.'}
      </p>
      <button
        onClick={() => window.location.reload()}
        style={{
          background: 'var(--lime)',
          color: 'var(--ink-stable)',
          border: 'none',
          borderRadius: 14,
          padding: '14px 32px',
          fontSize: 15,
          fontWeight: 700,
          cursor: 'pointer',
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
      { path: "settings", Component: Settings },
      { path: "admin", Component: AdminPanel },
    ],
  },
]);
