import { useState } from "react";
import { useParams, useNavigate } from "react-router";
import { useData } from "../context/DataContext";
import { ArrowLeft, Store, Edit2, X, Check } from "lucide-react";

export function MerchantDetail() {
  const { merchantId } = useParams<{ merchantId: string }>();
  const navigate = useNavigate();
  const { merchants, categories, updateMerchant, merchantRules, transactions } = useData();
  
  const [isEditing, setIsEditing] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState("");
  const [selectedSubcategoryId, setSelectedSubcategoryId] = useState("");

  const merchant = merchants.find((m) => m.id === merchantId);
  const merchantRule = merchantRules.find((r) => r.merchantId === merchantId);
  
  // Obtener la categoría actual (desde la regla o desde el comercio)
  const currentCategoryId = merchantRule?.categoryId || merchant?.defaultCategoryId;
  const currentSubcategoryId = merchantRule?.subcategoryId;
  
  const currentCategory = categories.find((c) => c.id === currentCategoryId);
  const currentSubcategory = currentCategory?.subcategories?.find(
    (s) => s.id === currentSubcategoryId
  );

  // Transacciones de este comercio
  const merchantTransactions = transactions.filter(
    (t) => t.merchantId === merchantId
  );

  const totalSpent = merchantTransactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);

  if (!merchant) {
    return (
      <div className="p-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 font-medium">Comercio no encontrado</p>
          <button
            onClick={() => navigate("/merchants")}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg"
          >
            Volver a Comercios
          </button>
        </div>
      </div>
    );
  }

  const handleStartEdit = () => {
    setSelectedCategoryId(currentCategoryId || "");
    setSelectedSubcategoryId(currentSubcategoryId || "");
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setSelectedCategoryId("");
    setSelectedSubcategoryId("");
    setIsEditing(false);
  };

  const handleSaveEdit = async () => {
    if (selectedCategoryId) {
      await updateMerchant(merchant.id, {
        defaultCategoryId: selectedCategoryId,
        defaultSubcategoryId: selectedSubcategoryId || undefined,
      });
    }
    setIsEditing(false);
  };

  const selectedCategory = categories.find((c) => c.id === selectedCategoryId);
  const availableSubcategories = selectedCategory?.subcategories || [];

  return (
    <div className="pb-20">
      {/* Header */}
      <div className="bg-gradient-to-br from-blue-600 to-blue-700 text-white p-6">
        <button
          onClick={() => navigate("/merchants")}
          className="flex items-center gap-2 mb-4 text-white/90 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="text-sm">Volver</span>
        </button>

        <div className="flex items-start gap-4">
          <div className="w-16 h-16 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center">
            <Store className="w-8 h-8 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold mb-1">{merchant.name}</h1>
            <p className="text-sm text-white/80">
              {merchantTransactions.length} transacciones
            </p>
          </div>
        </div>

        {/* Total gastado */}
        <div className="mt-6 bg-white/10 backdrop-blur-sm rounded-xl p-4">
          <p className="text-xs text-white/70 mb-1">Total gastado</p>
          <p className="text-3xl font-bold">${totalSpent.toLocaleString("es-MX")}</p>
        </div>
      </div>

      {/* Contenido */}
      <div className="p-4 space-y-4">
        {/* Categorización */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Categorización</h2>
            {!isEditing && (
              <button
                onClick={handleStartEdit}
                className="flex items-center gap-1 text-sm text-blue-600 font-medium"
              >
                <Edit2 className="w-4 h-4" />
                Editar
              </button>
            )}
          </div>

          {!isEditing ? (
            // Vista de solo lectura
            <div className="space-y-3">
              {currentCategory ? (
                <>
                  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
                      style={{ backgroundColor: `${currentCategory.color}20` }}
                    >
                      {currentCategory.icon}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs text-gray-500">Categoría</p>
                      <p className="font-medium">{currentCategory.name}</p>
                    </div>
                    <div
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: currentCategory.color }}
                    />
                  </div>

                  {currentSubcategory && (
                    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <div className="w-12 h-12 rounded-full flex items-center justify-center bg-gray-200">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: currentCategory.color }}
                        />
                      </div>
                      <div className="flex-1">
                        <p className="text-xs text-gray-500">Subcategoría</p>
                        <p className="font-medium">{currentSubcategory.name}</p>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-6 text-gray-500">
                  <p className="text-sm">Sin categoría asignada</p>
                  <button
                    onClick={handleStartEdit}
                    className="mt-3 text-blue-600 font-medium text-sm"
                  >
                    Asignar categoría
                  </button>
                </div>
              )}
            </div>
          ) : (
            // Modo de edición
            <div className="space-y-4">
              {/* Selector de categoría */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Categoría
                </label>
                <select
                  value={selectedCategoryId}
                  onChange={(e) => {
                    setSelectedCategoryId(e.target.value);
                    setSelectedSubcategoryId("");
                  }}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                >
                  <option value="">Selecciona una categoría</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.icon} {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Selector de subcategoría */}
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

              {/* Botones de acción */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleCancelEdit}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
                >
                  <X className="w-4 h-4" />
                  Cancelar
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={!selectedCategoryId}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Check className="w-4 h-4" />
                  Guardar
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Historial de transacciones */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="font-semibold mb-4">
            Últimas Transacciones ({merchantTransactions.length})
          </h2>
          
          {merchantTransactions.length === 0 ? (
            <p className="text-center py-6 text-gray-500 text-sm">
              No hay transacciones registradas
            </p>
          ) : (
            <div className="space-y-3">
              {merchantTransactions.slice(0, 10).map((transaction) => {
                const txCategory = categories.find((c) => c.id === transaction.categoryId);
                const txSubcategory = txCategory?.subcategories?.find(
                  (s) => s.id === transaction.subcategoryId
                );

                return (
                  <div
                    key={transaction.id}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                  >
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
                      style={{ backgroundColor: `${txCategory?.color}20` }}
                    >
                      {txCategory?.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{transaction.description}</p>
                      <p className="text-xs text-gray-500">
                        {txSubcategory?.name || txCategory?.name} •{" "}
                        {new Date(transaction.date).toLocaleDateString("es-MX", {
                          day: "numeric",
                          month: "short",
                        })}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-red-600">
                        ${Math.abs(transaction.amount).toLocaleString("es-MX")}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Información adicional */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-sm text-blue-800 font-medium mb-1">💡 Consejo</p>
          <p className="text-xs text-blue-700">
            Al asignar una categoría a este comercio, todas las transacciones futuras
            de {merchant.name} se categorizarán automáticamente.
          </p>
        </div>
      </div>
    </div>
  );
}