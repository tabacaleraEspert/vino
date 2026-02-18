import { RouterProvider } from "react-router";
import { router } from "./routes";
import { AuthProvider } from "./context/AuthContext";
import { DataProvider } from "./context/DataContext";
import { MonthProvider } from "./context/MonthContext";

export default function App() {
  return (
    <AuthProvider>
      <DataProvider>
        <MonthProvider>
          <RouterProvider router={router} />
        </MonthProvider>
      </DataProvider>
    </AuthProvider>
  );
}