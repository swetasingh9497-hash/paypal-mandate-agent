export function formatDetail(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => formatDetail(item))
      .filter(Boolean)
      .join(", ");
  }
  if (typeof detail === "object") {
    return Object.entries(detail as Record<string, unknown>)
      .map(([key, value]) => {
        const formattedValue = formatValue(value);
        return `${key}: ${formattedValue}`;
      })
      .join(" · ");
  }
  return String(detail);
}

function formatValue(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "number") {
    if (Number.isInteger(value) && value > 10 && value < 100000) {
      return `$${value}`;
    }
    return value.toString();
  }
  if (typeof value === "string") {
    const num = Number(value);
    if (!Number.isNaN(num) && Number.isInteger(num) && num > 10 && num < 100000) {
      return `$${num}`;
    }
    return value;
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
