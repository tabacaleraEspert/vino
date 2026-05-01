import { createBrowserRouter } from "react-router";
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
import { ProtectedRoute } from "./components/ProtectedRoute";
import { OnboardingFlow } from "./components/onboarding/OnboardingFlow";

export const router = createBrowserRouter([
  {
    path: "/login",
    Component: Login,
  },
  {
    path: "/onboarding",
    Component: OnboardingFlow,
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <RootLayout />
      </ProtectedRoute>
    ),
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