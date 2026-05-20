import { GoogleOAuthProvider } from "@react-oauth/google";
import { RouterProvider } from "react-router";
import { Toaster } from "sonner";
import { Component, type ReactNode } from "react";
import { Capacitor } from "@capacitor/core";
import { router } from "./routes";
import { AuthProvider } from "./context/AuthContext";
import { CatalogProvider } from "./context/CatalogContext";
import { DataProvider } from "./context/DataContext";
import { MonthProvider } from "./context/MonthContext";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const isNative = Capacitor.isNativePlatform();

/** Catches errors that happen outside the router (e.g. GoogleOAuthProvider crash). */
class AppErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
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
          <div style={{ fontSize: 40, marginBottom: 16 }}>😵</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
            Algo salió mal
          </h2>
          <p
            style={{
              fontSize: 14,
              color: "#666",
              marginBottom: 24,
              maxWidth: 300,
            }}
          >
            Ocurrió un error inesperado al iniciar la app.
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
    return this.props.children;
  }
}

function AppInner() {
  return (
    <AuthProvider>
      <MonthProvider>
        <CatalogProvider>
          <DataProvider>
            <RouterProvider router={router} />
            <Toaster position="top-center" richColors closeButton />
          </DataProvider>
        </CatalogProvider>
      </MonthProvider>
    </AuthProvider>
  );
}

export default function App() {
  // Google OAuth web SDK doesn't work inside Capacitor WebView — skip provider on native
  const inner = <AppInner />;
  return (
    <AppErrorBoundary>
      {isNative ? (
        inner
      ) : (
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
          {inner}
        </GoogleOAuthProvider>
      )}
    </AppErrorBoundary>
  );
}