import { useState } from "react";
import { X, Check } from "lucide-react";
import { useData } from "../context/DataContext";

interface CreateCategoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const AVAILABLE_ICONS = [
  "🍔", "🍕", "🍜", "☕", "🥗", "🍱",
  "🚗", "✈️", "🚌", "🚲", "⛽", "🚕",
  "🎬", "🎮", "🎵", "📺", "🎨", "📚",
  "⚕️", "💊", "🏥", "💪", "🧘", "⚡",
  "🛍️", "👕", "👟", "💻", "📱", "🏠",
  "💡", "💰", "🎓", "🐕", "🌳", "🎁",
];

const AVAILABLE_COLORS = [
  "#ef4444", "#f97316", "#f59e0b", "#eab308",
  "#84cc16", "#22c55e", "#10b981", "#14b8a6",
  "#06b6d4", "#0ea5e9", "#3b82f6", "#6366f1",
  "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
  "#f43f5e", "#64748b", "#78716c", "#57534e",
];

export function CreateCategoryModal({ isOpen, onClose }: CreateCategoryModalProps) {
  const { addCategory } = useData();
  const [name, setName] = useState("");
  const [selectedIcon, setSelectedIcon] = useState(AVAILABLE_ICONS[0]);
  const [selectedColor, setSelectedColor] = useState(AVAILABLE_COLORS[2]);
  const [selectedBucket, setSelectedBucket] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const BUCKETS = [
    { value: "necesidades", label: "Necesidades", desc: "Lo que no podés dejar de pagar" },
    { value: "estilo_vida", label: "Estilo de vida", desc: "Lo que disfrutás pero podrías recortar" },
    { value: "otros", label: "Otros", desc: "No estoy seguro" },
  ];

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("Por favor ingresa un nombre para la categoría");
      return;
    }
    if (!selectedBucket) {
      setError("Elegí a qué grupo pertenece esta categoría");
      return;
    }
    setIsSubmitting(true);
    try {
      await addCategory({
        name: name.trim(),
        icon: selectedIcon,
        color: selectedColor,
        bucket: selectedBucket,
        subcategories: [],
      });
      setName("");
      setSelectedIcon(AVAILABLE_ICONS[0]);
      setSelectedColor(AVAILABLE_COLORS[2]);
      setSelectedBucket("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setName("");
    setSelectedIcon(AVAILABLE_ICONS[0]);
    setSelectedColor(AVAILABLE_COLORS[2]);
    setError("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl">
          <h2 className="text-xl font-semibold">Nueva Categoría</h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Contenido */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Vista previa */}
          <div className="flex justify-center">
            <div
              className="w-24 h-24 rounded-full flex items-center justify-center text-5xl shadow-lg"
              style={{ backgroundColor: `${selectedColor}20` }}
            >
              {selectedIcon}
            </div>
          </div>

          {/* Nombre */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
              Nombre de la categoría
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej: Alimentación, Transporte..."
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              maxLength={30}
            />
            {error && (
              <p className="text-sm text-red-600 mt-2">{error}</p>
            )}
          </div>

          {/* Selector de grupo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ¿A qué grupo pertenece? *
            </label>
            <div className="space-y-2">
              {BUCKETS.map((b) => (
                <button
                  key={b.value}
                  type="button"
                  onClick={() => { setSelectedBucket(b.value); setError(""); }}
                  className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                    selectedBucket === b.value
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 bg-gray-50 hover:border-gray-300"
                  }`}
                >
                  <p className={`text-sm font-semibold ${selectedBucket === b.value ? "text-blue-700" : "text-gray-800"}`}>
                    {b.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{b.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Selector de icono */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Selecciona un icono
            </label>
            <div className="grid grid-cols-6 gap-2 max-h-48 overflow-y-auto p-2 bg-gray-50 rounded-lg">
              {AVAILABLE_ICONS.map((icon) => (
                <button
                  key={icon}
                  type="button"
                  onClick={() => setSelectedIcon(icon)}
                  className={`w-12 h-12 flex items-center justify-center text-2xl rounded-lg transition-all ${
                    selectedIcon === icon
                      ? "bg-blue-100 ring-2 ring-blue-500 scale-110"
                      : "bg-white hover:bg-gray-100 hover:scale-105"
                  }`}
                >
                  {icon}
                </button>
              ))}
            </div>
          </div>

          {/* Selector de color */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Selecciona un color
            </label>
            <div className="grid grid-cols-10 gap-2">
              {AVAILABLE_COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setSelectedColor(color)}
                  className={`w-9 h-9 rounded-full transition-all ${
                    selectedColor === color
                      ? "ring-2 ring-offset-2 ring-gray-900 scale-110"
                      : "hover:scale-105"
                  }`}
                  style={{ backgroundColor: color }}
                >
                  {selectedColor === color && (
                    <Check className="w-5 h-5 text-white mx-auto" strokeWidth={3} />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg font-medium hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg shadow-blue-500/30 disabled:opacity-50"
            >
              {isSubmitting ? "Creando..." : "Crear Categoría"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
