import { describe, expect, it } from "vitest";
import { formatDetail } from "@/lib/formatDetail";

describe("formatDetail", () => {
  it("returns string as is", () => {
    expect(formatDetail("hello")).toBe("hello");
  });

  it("returns empty string for null/undefined", () => {
    expect(formatDetail(null)).toBe("");
    expect(formatDetail(undefined)).toBe("");
  });

  it("converts numbers and booleans to strings", () => {
    expect(formatDetail(42)).toBe("42");
    expect(formatDetail(3.14)).toBe("3.14");
    expect(formatDetail(true)).toBe("true");
    expect(formatDetail(false)).toBe("false");
  });

  it("formats arrays by joining elements", () => {
    expect(formatDetail([1, 2, 3])).toBe("1, 2, 3");
    expect(formatDetail(["a", "b", "c"])).toBe("a, b, c");
    expect(formatDetail([null, "x", undefined, 5])).toBe("x, 5");
  });

  it("formats objects as key: value pairs", () => {
    expect(formatDetail({ a: 1, b: "two" })).toBe("a: 1 · b: two");
  });

  it("handles nested objects recursively", () => {
    const nested = { outer: { inner: "value", num: 42 } };
    const result = formatDetail(nested);
    expect(result).toContain("outer: inner: value · num: 42");
  });

  it("handles objects with arrays", () => {
    const withArray = { items: [1, 2, 3], name: "test" };
    const result = formatDetail(withArray);
    expect(result).toContain("items: 1, 2, 3");
    expect(result).toContain("name: test");
  });

  it("never returns [object Object]", () => {
    const testCases: unknown[] = [
      { nested: { deep: { deeper: "value" } } },
      [{ a: 1 }, { b: 2 }],
      { arr: [{ x: 1 }, { y: 2 }] },
      { self: null as unknown }, // will be set below
    ];

    (testCases[3] as Record<string, unknown>)["self"] = testCases[3]; // circular reference

    for (const tc of testCases) {
      const result = formatDetail(tc);
      expect(result).not.toContain("[object Object]");
    }
  });

  it("handles circular references safely", () => {
    const circular: any = { a: 1 };
    circular.self = circular;
    const result = formatDetail(circular);
    expect(result).toContain("[Circular]");
    expect(result).not.toContain("[object Object]");
  });

  it("falls back to JSON.stringify for unserializable objects", () => {
    const weird = Object.create(null);
    weird.fn = () => "test";
    const result = formatDetail(weird);
    // Should not crash and should not contain [object Object]
    expect(result).not.toContain("[object Object]");
  });
});