/**
 * Map category icon keys (stored in DB) to emoji.
 * SQL Server NVARCHAR can't store emoji (supplementary Unicode chars),
 * so we store text keys and map to emoji in the frontend.
 */
const ICON_MAP: Record<string, string> = {
  // New system (text keys)
  casa: "🏠",
  comida: "🍴",
  auto: "🚗",
  servicios: "💡",
  salud: "💊",
  educacion: "🎓",
  salidas: "🍻",
  ocio: "🎬",
  compras: "👕",
  ahorro: "💰",
  inversion: "📈",
  otros: "📁",
};

/**
 * Resolve a category icon value to an emoji.
 * If it's already an emoji (legacy data), return as-is.
 * If it's a text key, map to emoji.
 * If it's "?" (corrupted emoji), try to match by category name.
 */
export function resolveIcon(icon: string | undefined | null, categoryName?: string): string {
  if (!icon || icon === "?") {
    // Fallback: try to match by category name
    if (categoryName) {
      const key = categoryName.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      const mapped = ICON_MAP[key];
      if (mapped) return mapped;
      // Partial matches
      if (key.includes("vivien")) return "🏠";
      if (key.includes("comid") || key.includes("aliment")) return "🍴";
      if (key.includes("transport")) return "🚗";
      if (key.includes("servic")) return "💡";
      if (key.includes("salud")) return "💊";
      if (key.includes("educa")) return "🎓";
      if (key.includes("salid")) return "🍻";
      if (key.includes("ocio") || key.includes("entret")) return "🎬";
      if (key.includes("compr") || key.includes("ropa")) return "👕";
      if (key.includes("ahorr")) return "💰";
      if (key.includes("inver")) return "📈";
    }
    return "📁";
  }

  // Check if it's a text key
  const mapped = ICON_MAP[icon.toLowerCase()];
  if (mapped) return mapped;

  // Already an emoji or unknown — return as-is
  return icon;
}
