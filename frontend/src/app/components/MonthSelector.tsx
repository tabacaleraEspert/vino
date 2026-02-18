import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMonth } from "../context/MonthContext";

const MONTH_NAMES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
];

export function MonthSelector() {
  const { selectedMonth, setSelectedMonth, isCurrentMonth } = useMonth();

  const goPrev = () => {
    if (selectedMonth.month === 0) {
      setSelectedMonth({ month: 11, year: selectedMonth.year - 1 });
    } else {
      setSelectedMonth({ month: selectedMonth.month - 1, year: selectedMonth.year });
    }
  };

  const goNext = () => {
    const now = new Date();
    const atCurrent = selectedMonth.month === now.getMonth() && selectedMonth.year === now.getFullYear();
    if (atCurrent) return;

    if (selectedMonth.month === 11) {
      setSelectedMonth({ month: 0, year: selectedMonth.year + 1 });
    } else {
      setSelectedMonth({ month: selectedMonth.month + 1, year: selectedMonth.year });
    }
  };

  const now = new Date();
  const canGoNext =
    selectedMonth.year < now.getFullYear() ||
    (selectedMonth.year === now.getFullYear() && selectedMonth.month < now.getMonth());

  return (
    <div
      className={`flex items-center justify-between rounded-xl px-4 py-3 ${
        isCurrentMonth ? "bg-white shadow-sm" : "bg-amber-50 border border-amber-200"
      }`}
    >
      <button
        onClick={goPrev}
        className="p-2 -ml-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <ChevronLeft className="w-5 h-5 text-gray-600" />
      </button>
      <span className="font-semibold text-gray-800">
        {MONTH_NAMES[selectedMonth.month]} {selectedMonth.year}
      </span>
      <button
        onClick={goNext}
        disabled={!canGoNext}
        className={`p-2 -mr-2 rounded-lg transition-colors ${
          canGoNext ? "hover:bg-gray-100" : "opacity-40 cursor-not-allowed"
        }`}
      >
        <ChevronRight className="w-5 h-5 text-gray-600" />
      </button>
    </div>
  );
}
