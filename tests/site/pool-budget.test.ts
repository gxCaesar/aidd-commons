import { describe, expect, it } from "vitest";
import { poolBudget } from "../../site/src/lib/pool-budget.js";

describe("original-pool budgets", () => {
  it("rounds every equal batch before summing", () => {
    expect(poolBudget(42)).toMatchObject({
      batchSize: 2,
      total: 8,
      checkpoints: [0, 2, 4, 6, 8],
    });
    expect(poolBudget(631)).toMatchObject({ batchSize: 31, total: 124 });
    expect(poolBudget(20).total).toBe(4);
  });
  it("rejects unusable and fractional input", () => {
    for (const size of [NaN, Infinity, 19, -1, 42.5, 1_000_001]) {
      expect(() => poolBudget(size)).toThrow("whole-number");
    }
  });
});
