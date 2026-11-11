export function formatValue(value: unknown, seen = new WeakSet<object>()): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    return value
      .map((item) => formatValue(item, seen))
      .filter(Boolean)
      .join(", ");
  }
  if (typeof value === "object") {
    // Prevent circular reference loops
    if (seen.has(value)) return "[Circular]";
    seen.add(value);

    try {
      return Object.entries(value as Record<string, unknown>)
        .map(([key, val]) => {
          const formattedVal = formatValue(val, seen);
          return `${key}: ${formattedVal}`;
        })
        .join(" · ");
    } catch {
      // Fallback if something goes wrong
      try {
        return JSON.stringify(value);
      } catch {
        return "[Unserializable]";
      }
    } finally {
      seen.delete(value);
    }
  }
  return String(value);
}

export function formatDetail(detail: unknown): string {
  return formatValue(detail);
}