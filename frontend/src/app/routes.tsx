import { createBrowserRouter } from "react-router";
import { RootLayout } from "./components/RootLayout";
import { Dashboard } from "./components/Dashboard";
import { Transactions } from "./components/Transactions";
import { Categories } from "./components/Categories";
import { Budgets } from "./components/Budgets";
import { Merchants } from "./components/Merchants";
import { MerchantDetail } from "./components/MerchantDetail";
import { Stats } from "./components/Stats";
import { Login } from "./components/Login";
import { ProtectedRoute } from "./components/ProtectedRoute";

export const router = createBrowserRouter([
  {
    path: "/login",
    Component: Login,
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
    ],
  },
]);