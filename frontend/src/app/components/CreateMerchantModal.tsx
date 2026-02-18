import { useState } from "react";
import { X, Store } from "lucide-react";
import { useData } from "../context/DataContext";

interface CreateMerchantModalProps {
  show: boolean;
  onClose: () => void;
}

export function CreateMerchantModal({ show, onClose }: CreateMerchantModalProps) {
  const { addMerchant, categories } = useData();
  const [merchantName, setMerchantName] = useState("");
  const [selectedCategoryId, setSelectedCategoryId] = useState("");
  const [selectedSubcategoryId, setSelectedSubcategoryId] = useState("");
  const [error, setError] = useState("");

  const selectedCategory = categories.find((c) => c.id === selectedCategoryId);
  const availableSubcategories = selectedCategory?.subcategories || [];

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchantName.trim()) {
      setError("El nombre del comercio es requerido");
      return;
    }
    setIsSubmitting(true);
    try {
      await addMerchant({
        name: merchantName.trim(),
        defaultCategoryId: selectedCategoryId || undefined,
        defaultSubcategoryId: selectedSubcategoryId || undefined,
      });
      setMerchantName("");
      setSelectedCategoryId("");
      setSelectedSubcategoryId("");
      setError("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <Store className="w-5 h-5 text-blue-600" />
            </div>
            <h2 className="text-xl font-semibold">Nuevo Comercio</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Contenido */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Nombre del comercio */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nombre del Comercio *
            </label>
            <input
              type="text"
              value={merchantName}
              onChange={(e) => {
                setMerchantName(e.target.value);
                setError("");
              }}
              placeholder="Ej: Starbucks, Walmart, etc."
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              autoFocus
            />
          </div>

          {/* Categoría por defecto */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Categoría por Defecto (opcional)
            </label>
            <select
              value={selectedCategoryId}
              onChange={(e) => {
                setSelectedCategoryId(e.target.value);
                setSelectedSubcategoryId("");
              }}
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            >
              <option value="">Sin categoría por defecto</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.icon} {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Subcategoría */}
          {selectedCategoryId && availableSubcategories.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subcategoría (opcional)
              </label>
              <select
                value={selectedSubcategoryId}
                onChange={(e) => setSelectedSubcategoryId(e.target.value)}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              >
                <option value="">Sin subcategoría</option>
                {availableSubcategories.map((sub) => (
                  <option key={sub.id} value={sub.id}>
                    {sub.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-xs text-blue-800">
              💡 Al asignar una categoría por defecto, todas las transacciones
              futuras de este comercio se categorizarán automáticamente.
            </p>
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? "Creando..." : "Crear Comercio"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}