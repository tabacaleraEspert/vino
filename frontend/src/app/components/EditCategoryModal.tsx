import { useState, useEffect } from "react";
import { X, Check, Trash2, AlertTriangle } from "lucide-react";
import { useData } from "../context/DataContext";

interface EditCategoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  categoryId: string;
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

export function EditCategoryModal({ isOpen, onClose, categoryId }: EditCategoryModalProps) {
  const { categories, updateCategory, deleteCategory } = useData();
  const category = categories.find((c) => c.id === categoryId);

  const [name, setName] = useState("");
  const [selectedIcon, setSelectedIcon] = useState(AVAILABLE_ICONS[0]);
  const [selectedColor, setSelectedColor] = useState(AVAILABLE_COLORS[2]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (isOpen && category) {
      setName(category.name);
      setSelectedIcon(category.icon || AVAILABLE_ICONS[0]);
      setSelectedColor(category.color || AVAILABLE_COLORS[2]);
      setError("");
      setShowDeleteConfirm(false);
    }
  }, [isOpen, category]);

  if (!isOpen) return null;
  if (!category) return null;

  const hasSubcategories = category.subcategories && category.subcategories.length > 0;
  const subcategoryCount = category.subcategories?.length ?? 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("El nombre es requerido");
      return;
    }
    if (!selectedIcon) {
      setError("Selecciona un ícono");
      return;
    }
    if (!selectedColor) {
      setError("Selecciona un color");
      return;
    }
    setIsSubmitting(true);
    try {
      await updateCategory(categoryId, {
        name: name.trim(),
        icon: selectedIcon,
        color: selectedColor,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteCategory(categoryId);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleClose = () => {
    setError("");
    setShowDeleteConfirm(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl z-10">
          <h2 className="text-xl font-semibold">Editar Categoría</h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Contenido */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Vista previa en tiempo real */}
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
            <label htmlFor="edit-name" className="block text-sm font-medium text-gray-700 mb-2">
              Nombre de la categoría
            </label>
            <input
              id="edit-name"
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

          {/* Selector de icono */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Ícono
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
              Color
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

          {/* Botones Guardar / Cancelar */}
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
              {isSubmitting ? "Guardando..." : "Guardar"}
            </button>
          </div>

          {/* Separador */}
          <div className="border-t border-gray-200 pt-4">
            {/* Botón Eliminar */}
            {!showDeleteConfirm ? (
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg font-medium transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Eliminar categoría
              </button>
            ) : (
              <div className="space-y-3">
                {hasSubcategories && (
                  <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-amber-800">
                      Esta categoría tiene {subcategoryCount} subcategoría{subcategoryCount !== 1 ? "s" : ""} asociada{subcategoryCount !== 1 ? "s" : ""}. También se eliminarán.
                    </p>
                  </div>
                )}
                <p className="text-sm text-gray-600 text-center">
                  ¿Estás seguro de que deseas eliminar esta categoría?
                </p>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setShowDeleteConfirm(false)}
                    className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={isDeleting}
                    className="flex-1 px-4 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
                  >
                    {isDeleting ? "Eliminando..." : "Sí, eliminar"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
