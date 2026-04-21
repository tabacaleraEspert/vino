import { useState } from "react";
import { useData } from "../context/DataContext";
import { ChevronDown, ChevronRight, Plus, Edit2 } from "lucide-react";
import { CreateCategoryModal } from "./CreateCategoryModal";
import { CreateSubcategoryModal } from "./CreateSubcategoryModal";
import { EditCategoryModal } from "./EditCategoryModal";
import { EditSubcategoryModal } from "./EditSubcategoryModal";

export function Categories() {
  const { categories } = useData();
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set()
  );
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [subcategoryModal, setSubcategoryModal] = useState<{
    isOpen: boolean;
    categoryId: string | null;
  }>({ isOpen: false, categoryId: null });
  const [editCategoryModal, setEditCategoryModal] = useState<{
    isOpen: boolean;
    categoryId: string | null;
  }>({ isOpen: false, categoryId: null });
  const [editSubcategoryModal, setEditSubcategoryModal] = useState<{
    isOpen: boolean;
    categoryId: string | null;
    subcategoryId: string | null;
    subcategoryName: string | null;
  }>({ isOpen: false, categoryId: null, subcategoryId: null, subcategoryName: null });

  const openEditCategoryModal = (categoryId: string) => {
    setEditCategoryModal({ isOpen: true, categoryId });
  };

  const closeEditCategoryModal = () => {
    setEditCategoryModal({ isOpen: false, categoryId: null });
  };

  const openEditSubcategoryModal = (
    categoryId: string,
    subcategoryId: string,
    subcategoryName: string
  ) => {
    setEditSubcategoryModal({
      isOpen: true,
      categoryId,
      subcategoryId,
      subcategoryName,
    });
  };

  const closeEditSubcategoryModal = () => {
    setEditSubcategoryModal({
      isOpen: false,
      categoryId: null,
      subcategoryId: null,
      subcategoryName: null,
    });
  };

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(categoryId)) {
        newSet.delete(categoryId);
      } else {
        newSet.add(categoryId);
      }
      return newSet;
    });
  };

  const openSubcategoryModal = (categoryId: string) => {
    setSubcategoryModal({ isOpen: true, categoryId });
  };

  const closeSubcategoryModal = () => {
    setSubcategoryModal({ isOpen: false, categoryId: null });
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Categorías y Subcategorías</h2>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-1 text-sm text-blue-600 font-medium"
        >
          <Plus className="w-4 h-4" />
          Nueva
        </button>
      </div>

      {/* Lista de categorías */}
      <div className="space-y-2">
        {categories.map((category) => {
          const isExpanded = expandedCategories.has(category.id);
          const hasSubcategories =
            category.subcategories && category.subcategories.length > 0;

          return (
            <div key={category.id} className="bg-white rounded-xl shadow-sm overflow-hidden group">
              {/* Categoría principal */}
              <div className="flex items-center gap-3 p-4 relative">
                <div
                  onClick={() => hasSubcategories && toggleCategory(category.id)}
                  className="flex-1 flex items-center gap-3 cursor-pointer hover:bg-gray-50 rounded-lg -m-2 p-2 transition-colors min-w-0"
                >
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center text-2xl flex-shrink-0"
                    style={{ backgroundColor: `${category.color}20` }}
                  >
                    {category.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium">{category.name}</p>
                    {hasSubcategories && (
                      <p className="text-xs text-gray-500">
                        {category.subcategories!.length} subcategorías
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: category.color }}
                    />
                    {hasSubcategories && (
                      isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-400" />
                      )
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    openEditCategoryModal(category.id);
                  }}
                  className="p-2 hover:bg-blue-50 rounded-lg transition-colors opacity-70 group-hover:opacity-100 flex-shrink-0"
                  title="Editar categoría"
                >
                  <Edit2 className="w-4 h-4 text-blue-600" />
                </button>
              </div>

              {/* Subcategorías */}
              {isExpanded && (
                <div className="border-t border-gray-100 bg-gray-50">
                  {hasSubcategories && category.subcategories!.map((sub, idx) => (
                    <div
                      key={sub.id}
                      className={`flex items-center gap-3 py-3 px-4 pl-16 group ${
                        idx !== category.subcategories!.length - 1
                          ? "border-b border-gray-100"
                          : ""
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-700">
                          {sub.name}
                        </p>
                      </div>
                      <div
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: category.color }}
                      />
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditSubcategoryModal(category.id, sub.id, sub.name);
                        }}
                        className="p-2 hover:bg-purple-50 rounded-lg transition-colors opacity-70 group-hover:opacity-100 flex-shrink-0"
                        title="Editar subcategoría"
                      >
                        <Edit2 className="w-4 h-4 text-purple-600" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openSubcategoryModal(category.id);
                    }}
                    className="w-full py-3 px-4 pl-16 text-left text-sm text-blue-600 font-medium hover:bg-gray-100 transition-colors flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Agregar subcategoría
                  </button>
                </div>
              )}

              {/* Botón para agregar primera subcategoría si no está expandida */}
              {!hasSubcategories && (
                <div className="border-t border-gray-100 bg-gray-50">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openSubcategoryModal(category.id);
                    }}
                    className="w-full py-3 px-4 text-left text-sm text-blue-600 font-medium hover:bg-gray-100 transition-colors flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Agregar subcategoría
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Botón para agregar categoría */}
      <button
        onClick={() => setIsModalOpen(true)}
        className="w-full py-4 bg-white rounded-xl shadow-sm text-blue-600 font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
      >
        <Plus className="w-5 h-5" />
        Crear Nueva Categoría
      </button>

      {/* Modal para crear categoría */}
      <CreateCategoryModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />

      {/* Modal para crear subcategoría */}
      {subcategoryModal.categoryId && (
        <CreateSubcategoryModal
          isOpen={subcategoryModal.isOpen}
          onClose={closeSubcategoryModal}
          categoryId={subcategoryModal.categoryId}
        />
      )}

      {/* Modal para editar categoría */}
      {editCategoryModal.categoryId && (
        <EditCategoryModal
          isOpen={editCategoryModal.isOpen}
          onClose={closeEditCategoryModal}
          categoryId={editCategoryModal.categoryId}
        />
      )}

      {/* Modal para editar subcategoría */}
      {editSubcategoryModal.categoryId && editSubcategoryModal.subcategoryId && (
        <EditSubcategoryModal
          isOpen={editSubcategoryModal.isOpen}
          onClose={closeEditSubcategoryModal}
          categoryId={editSubcategoryModal.categoryId}
          subcategoryId={editSubcategoryModal.subcategoryId}
          subcategoryName={editSubcategoryModal.subcategoryName}
        />
      )}
    </div>
  );
}