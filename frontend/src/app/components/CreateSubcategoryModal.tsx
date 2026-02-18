import { useState } from "react";
import { X } from "lucide-react";
import { useData } from "../context/DataContext";

interface CreateSubcategoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  categoryId: string;
}

export function CreateSubcategoryModal({ isOpen, onClose, categoryId }: CreateSubcategoryModalProps) {
  const { categories, addSubcategory } = useData();
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const category = categories.find((c) => c.id === categoryId);

  if (!isOpen || !category) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("Por favor ingresa un nombre para la subcategoría");
      return;
    }
    const existingSubcategory = category.subcategories?.find(
      (sub) => sub.name.toLowerCase() === name.trim().toLowerCase()
    );
    if (existingSubcategory) {
      setError("Ya existe una subcategoría con ese nombre");
      return;
    }
    setIsSubmitting(true);
    try {
      await addSubcategory(categoryId, name.trim());
      setName("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setName("");
    setError("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center text-xl"
              style={{ backgroundColor: `${category.color}20` }}
            >
              {category.icon}
            </div>
            <div>
              <h2 className="text-xl font-semibold">Nueva Subcategoría</h2>
              <p className="text-sm text-gray-600">{category.name}</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Contenido */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Subcategorías existentes */}
          {category.subcategories && category.subcategories.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Subcategorías existentes
              </label>
              <div className="bg-gray-50 rounded-lg p-3 max-h-32 overflow-y-auto space-y-1">
                {category.subcategories.map((sub) => (
                  <div key={sub.id} className="flex items-center gap-2 text-sm text-gray-700">
                    <div
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: category.color }}
                    />
                    <span>{sub.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Nombre de la subcategoría */}
          <div>
            <label htmlFor="subcategory-name" className="block text-sm font-medium text-gray-700 mb-2">
              Nombre de la subcategoría
            </label>
            <input
              id="subcategory-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej: Restaurantes, Gasolina, Streaming..."
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              maxLength={40}
              autoFocus
            />
            {error && (
              <p className="text-sm text-red-600 mt-2">{error}</p>
            )}
          </div>

          {/* Ejemplos */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-xs text-blue-800 font-medium mb-1">💡 Ejemplos de subcategorías:</p>
            <p className="text-xs text-blue-700">
              {category.name === "Alimentación" && "Supermercado, Restaurantes, Delivery, Café"}
              {category.name === "Transporte" && "Gasolina, Uber, Transporte público, Mantenimiento"}
              {category.name === "Entretenimiento" && "Streaming, Cine, Conciertos, Videojuegos"}
              {!["Alimentación", "Transporte", "Entretenimiento"].includes(category.name) &&
                "Divide esta categoría en grupos más específicos"}
            </p>
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-2">
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
              className="flex-1 px-4 py-3 rounded-lg font-medium text-white transition-all shadow-lg disabled:opacity-50"
              style={{
                background: `linear-gradient(to right, ${category.color}, ${category.color}dd)`,
              }}
            >
              {isSubmitting ? "Agregando..." : "Agregar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
