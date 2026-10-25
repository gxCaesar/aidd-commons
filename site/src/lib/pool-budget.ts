/** Match the Python teaching lab: four batches of floor(original pool / 20). */
export function poolBudget(poolSize: number) {
  if (
    !Number.isSafeInteger(poolSize) ||
    poolSize < 20 ||
    poolSize > 1_000_000
  ) {
    throw new Error("Enter a whole-number pool size from 20 to 1,000,000.");
  }
  const batchSize = Math.floor(poolSize / 20);
  return {
    batchSize,
    checkpoints: Array.from({ length: 5 }, (_, index) => index * batchSize),
    total: 4 * batchSize,
    fraction: (4 * batchSize) / poolSize,
  };
}
