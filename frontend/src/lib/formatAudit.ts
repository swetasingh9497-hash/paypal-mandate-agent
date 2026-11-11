import { formatValue } from "./formatDetail";

function formatAuditEntry(step: string, detail: unknown): string {
  switch (step) {
    case "parsed_mandate":
    case "parse": {
      // detail could be: "Mandate: desk lamp, up to $60" or object
      const str = formatValue(detail);
      if (str.toLowerCase().includes("mandate")) {
        return `Understood: ${str.replace(/^Mandate:\s*/i, "").replace(/^Budgie:\s*/i, "")}`;
      }
      return `Understood: ${str}`;
    }
    case "products_found":
    case "search": {
      // detail could be: "Found 10 products" or object with count
      const str = formatValue(detail);
      const match = str.match(/(\d+)\s*products?/i);
      if (match) return `Found ${match[1]} products`;
      return `Found products: ${str}`;
    }
    case "rule_check":
    case "rules": {
      // detail could be object with product_id, action, reasons
      const str = formatValue(detail);
      if (detail && typeof detail === "object" && "product_id" in detail) {
        const d = detail as { product_id?: string; action?: string; reasons?: string[]; title?: string };
        const title = d.title || d.product_id || "Product";
        const action = d.action || "unknown";
        const reason = d.reasons?.[0] || "";
        return `${title}: ${action}${reason ? ` (${reason})` : ""}`;
      }
      return `Rules checked: ${str}`;
    }
    case "ranker_choice":
    case "decide": {
      // detail could be object with chosen_id, reason, notes
      if (detail && typeof detail === "object" && "chosen_id" in detail) {
        const d = detail as { chosen_id?: string; reason?: string; notes?: Record<string, string>; summary?: string };
        if (d.summary) return d.summary;
        if (d.reason) return `Chosen: ${d.reason}`;
        return `Selected product ${d.chosen_id}`;
      }
      const str = formatValue(detail);
      return `Decision: ${str}`;
    }
    case "order_created": {
      // detail could be object with order_id
      if (detail && typeof detail === "object" && "order_id" in detail) {
        return "PayPal order created";
      }
      return `Order created: ${formatValue(detail)}`;
    }
    case "normalize": {
      return `Normalized data: ${formatValue(detail)}`;
    }
    default: {
      return formatValue(detail);
    }
  }
}

export function formatAudit(detail: unknown): string {
  if (detail && typeof detail === "object" && "step" in detail && "detail" in detail) {
    const entry = detail as { step: string; detail: unknown };
    return formatAuditEntry(entry.step, entry.detail);
  }
  return formatValue(detail);
}