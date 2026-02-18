import { createContext, useContext, useState, useMemo, ReactNode } from "react";

export interface MonthYear {
  month: number;
  year: number;
}

interface MonthContextType {
  selectedMonth: MonthYear;
  setSelectedMonth: (m: MonthYear) => void;
  isCurrentMonth: boolean;
}

const d = new Date();
const defaultMonth: MonthYear = { month: d.getMonth(), year: d.getFullYear() };

const MonthContext = createContext<MonthContextType | undefined>(undefined);

export function MonthProvider({ children }: { children: ReactNode }) {
  const [selectedMonth, setSelectedMonth] = useState<MonthYear>(defaultMonth);

  const isCurrentMonth = useMemo(() => {
    const n = new Date();
    return selectedMonth.month === n.getMonth() && selectedMonth.year === n.getFullYear();
  }, [selectedMonth]);

  const value = useMemo(
    () => ({ selectedMonth, setSelectedMonth, isCurrentMonth }),
    [selectedMonth, isCurrentMonth]
  );

  return <MonthContext.Provider value={value}>{children}</MonthContext.Provider>;
}

export function useMonth() {
  const ctx = useContext(MonthContext);
  if (ctx === undefined) {
    throw new Error("useMonth must be used within MonthProvider");
  }
  return ctx;
}
