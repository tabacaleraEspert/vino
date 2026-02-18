import { useState } from "react";
import { X, Zap } from "lucide-react";
import { useData } from "../context/DataContext";

interface CreateRuleModalProps {
  show: boolean;
  merchant: { id: string; name: string } | null;
  onClose: () => void;
}

export function CreateRuleModal({
  show,
  merchant,
  onClose,
}: CreateRuleModalProps) {
  const { addMerchantRule, categories, merchantRules } = useData();
  const [selectedCategoryId, setSelectedCategoryId] = useState("");
  const [selectedSubcategoryId, setSelectedSubcategoryId] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedCategory = categories.find((c) => c.id === selectedCategoryId);
  const availableSubcategories = selectedCategory?.subcategories || [];

  // Verificar si ya existe una regla para este comercio
  const existingRule = merchant
    ? merchantRules.find((r) => r.merchantId === merchant.id)
    : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchant) return;
    if (!selectedCategoryId) {
      setError("Debes seleccionar una categoría");
      return;
    }
    if (existingRule) {
      setError("Ya existe una regla para este comercio");
      return;
    }
    setIsSubmitting(true);
    try {
      await addMerchantRule({
        merchantId: merchant.id,
        categoryId: selectedCategoryId,
        subcategoryId: selectedSubcategoryId || undefined,
      });
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

  if (!show || !merchant) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              <Zap className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Crear Regla</h2>
              <p className="text-xs text-gray-500">{merchant.name}</p>
            </div>
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

          {existingRule && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm text-yellow-800 font-medium mb-1">
                ⚠️ Regla existente
              </p>
              <p className="text-xs text-yellow-700">
                Este comercio ya tiene una regla de categorización activa. No
                puedes crear otra regla para el mismo comercio.
              </p>
            </div>
          )}

          {/* Categoría */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Categoría *
            </label>
            <select
              value={selectedCategoryId}
              onChange={(e) => {
                setSelectedCategoryId(e.target.value);
                setSelectedSubcategoryId("");
                setError("");
              }}
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
              disabled={!!existingRule}
            >
              <option value="">Selecciona una categoría</option>
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
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                disabled={!!existingRule}
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
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-xs text-green-800">
              ⚡ Las reglas automatizan la categorización. Todas las
              transacciones futuras de <strong>{merchant.name}</strong> se
              asignarán a la categoría seleccionada.
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
              disabled={!!existingRule || isSubmitting}
              className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? "Creando..." : "Crear Regla"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}