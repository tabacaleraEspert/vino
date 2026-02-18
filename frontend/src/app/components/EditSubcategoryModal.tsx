import { useState, useEffect } from "react";
import { X, Trash2, AlertTriangle } from "lucide-react";
import { useData } from "../context/DataContext";

interface EditSubcategoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  categoryId: string | null;
  subcategoryId: string | null;
  subcategoryName: string | null;
}

export function EditSubcategoryModal({
  isOpen,
  onClose,
  categoryId,
  subcategoryId,
  subcategoryName,
}: EditSubcategoryModalProps) {
  const { categories, updateSubcategory, deleteSubcategory } = useData();
  const category = categories.find((c) => c.id === categoryId);

  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (isOpen && subcategoryName != null) {
      setName(subcategoryName);
      setError("");
      setShowDeleteConfirm(false);
    }
  }, [isOpen, subcategoryName]);

  if (!isOpen || !categoryId || !subcategoryId) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("El nombre es requerido");
      return;
    }
    setIsSubmitting(true);
    try {
      await updateSubcategory(categoryId, subcategoryId, name.trim());
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
      await deleteSubcategory(categoryId, subcategoryId);
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
      <div className="bg-white w-full max-w-md rounded-t-3xl shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-3xl">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center text-xl"
              style={{ backgroundColor: `${category?.color ?? "#6b7280"}20` }}
            >
              {category?.icon ?? "📁"}
            </div>
            <div>
              <h2 className="text-xl font-semibold">Editar Subcategoría</h2>
              <p className="text-sm text-gray-600">{category?.name}</p>
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
          {/* Nombre */}
          <div>
            <label
              htmlFor="edit-subcategory-name"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Nombre de la subcategoría
            </label>
            <input
              id="edit-subcategory-name"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setError("");
              }}
              placeholder="Ej: Supermercado, Restaurantes..."
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
              maxLength={40}
              autoFocus
            />
            {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
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
              className="flex-1 px-4 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? "Guardando..." : "Guardar"}
            </button>
          </div>

          {/* Separador - Botón Eliminar */}
          <div className="border-t border-gray-200 pt-4">
            {!showDeleteConfirm ? (
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg font-medium transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Eliminar subcategoría
              </button>
            ) : (
              <div className="space-y-3">
                <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-amber-800">
                    Esta acción es irreversible. La subcategoría se eliminará permanentemente.
                  </p>
                </div>
                <p className="text-sm text-gray-600 text-center">
                  ¿Estás seguro de que deseas eliminar esta subcategoría?
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
