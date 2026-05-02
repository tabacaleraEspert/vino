import { GoogleOAuthProvider } from "@react-oauth/google";
import { Capacitor } from "@capacitor/core";
import { RouterProvider } from "react-router";
import { Toaster } from "sonner";
import { router } from "./routes";
import { AuthProvider } from "./context/AuthContext";
import { CatalogProvider } from "./context/CatalogContext";
import { DataProvider } from "./context/DataContext";
import { MonthProvider } from "./context/MonthContext";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const isNative = Capacitor.isNativePlatform();

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
  if (isNative) return <AppInner />;
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AppInner />
    </GoogleOAuthProvider>
  );
}