export type Rmd17Metrics = {
  mae: number;
  rmse: number;
  target_range: number;
};

export type Rmd17DevelopmentSummary = {
  artifact_type: string;
  aggregates: Record<string, { mae_range: number; median_mae: number }>;
  development_evaluation: Record<
    string,
    { ridge: Rmd17Metrics; train_mean: Rmd17Metrics }
  >;
  features: {
    bins_per_channel: number;
    by_system: Record<
      string,
      {
        channel_count: number;
        element_pair_channels: string[];
        feature_dimension: number;
      }
    >;
    construction: string;
    distance_bin_width_angstrom: number;
  };
  locked_evaluations: Record<string, string>;
  selection: {
    selected_alpha: number;
    validation_grid: Array<{
      alpha: number;
      median_validation_mae: number;
      per_system_validation_mae: Record<string, number>;
    }>;
  };
  split: {
    ordering_diagnostics_by_system: Record<
      string,
      {
        adjacent_original_index_gap: {
          maximum: number;
          median: number;
          minimum: number;
        };
        partition_boundary_gap: {
          train_to_validation: number;
          validation_to_evaluation: number;
        };
        strictly_increasing: boolean;
      }
    >;
    partitions: Record<string, number>;
    selected_frames: number;
  };
  systems: Record<string, string>;
};

const developmentSystemIds = ["ethanol", "malonaldehyde"] as const;
const lockedSystemIds = ["benzene", "uracil"] as const;
const allSystemIds = ["ethanol", "malonaldehyde", "benzene", "uracil"] as const;

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

function requireExactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
  label: string,
): void {
  const actualKeys = Object.keys(value).sort();
  const expectedKeys = [...expected].sort();
  if (
    actualKeys.length !== expectedKeys.length ||
    actualKeys.some((key, index) => key !== expectedKeys[index])
  ) {
    throw new Error(`${label} must contain exactly ${expected.join(", ")}`);
  }
}

function requireFiniteNumber(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`${label} must be a finite number`);
  }
  return value;
}

function requirePositiveInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    throw new Error(`${label} must be a positive integer`);
  }
  return value;
}

function validateMetrics(value: unknown, label: string): void {
  const metrics = asRecord(value, label);
  requireExactKeys(metrics, ["mae", "rmse", "target_range"], label);
  for (const key of ["mae", "rmse", "target_range"] as const) {
    requireFiniteNumber(metrics[key], `${label}.${key}`);
  }
}

function validateDevelopmentEvaluation(value: unknown): void {
  const evaluations = asRecord(value, "development_evaluation");
  requireExactKeys(evaluations, developmentSystemIds, "development_evaluation");
  for (const systemId of developmentSystemIds) {
    const evaluation = asRecord(
      evaluations[systemId],
      `development_evaluation.${systemId}`,
    );
    requireExactKeys(
      evaluation,
      ["ridge", "train_mean"],
      `development_evaluation.${systemId}`,
    );
    validateMetrics(
      evaluation.ridge,
      `development_evaluation.${systemId}.ridge`,
    );
    validateMetrics(
      evaluation.train_mean,
      `development_evaluation.${systemId}.train_mean`,
    );
  }
}

function validateLockedEvaluations(value: unknown): void {
  const locked = asRecord(value, "locked_evaluations");
  requireExactKeys(locked, lockedSystemIds, "locked_evaluations");
  for (const systemId of lockedSystemIds) {
    if (locked[systemId] !== "not_run") {
      throw new Error(`locked_evaluations.${systemId} must be not_run`);
    }
  }
}

function validateSystemStatuses(value: unknown): void {
  const systems = asRecord(value, "systems");
  requireExactKeys(systems, allSystemIds, "systems");
  for (const systemId of developmentSystemIds) {
    if (systems[systemId] !== "development_evaluation_complete") {
      throw new Error(
        `systems.${systemId} must be development_evaluation_complete`,
      );
    }
  }
  for (const systemId of lockedSystemIds) {
    if (systems[systemId] !== "not_run") {
      throw new Error(`systems.${systemId} must be not_run`);
    }
  }
}

function validateAggregates(value: unknown): void {
  const aggregates = asRecord(value, "aggregates");
  requireExactKeys(aggregates, ["ridge", "train_mean"], "aggregates");
  for (const modelName of ["ridge", "train_mean"] as const) {
    const aggregate = asRecord(
      aggregates[modelName],
      `aggregates.${modelName}`,
    );
    requireExactKeys(
      aggregate,
      ["mae_range", "median_mae"],
      `aggregates.${modelName}`,
    );
    requireFiniteNumber(
      aggregate.mae_range,
      `aggregates.${modelName}.mae_range`,
    );
    requireFiniteNumber(
      aggregate.median_mae,
      `aggregates.${modelName}.median_mae`,
    );
  }
}

function validateFeatures(value: unknown): void {
  const features = asRecord(value, "features");
  const binsPerChannel = requirePositiveInteger(
    features.bins_per_channel,
    "features.bins_per_channel",
  );
  requireFiniteNumber(
    features.distance_bin_width_angstrom,
    "features.distance_bin_width_angstrom",
  );
  if (
    typeof features.construction !== "string" ||
    features.construction === ""
  ) {
    throw new Error("features.construction must be a non-empty string");
  }

  const bySystem = asRecord(features.by_system, "features.by_system");
  requireExactKeys(bySystem, developmentSystemIds, "features.by_system");
  for (const systemId of developmentSystemIds) {
    const feature = asRecord(
      bySystem[systemId],
      `features.by_system.${systemId}`,
    );
    const channelCount = requirePositiveInteger(
      feature.channel_count,
      `features.by_system.${systemId}.channel_count`,
    );
    const featureDimension = requirePositiveInteger(
      feature.feature_dimension,
      `features.by_system.${systemId}.feature_dimension`,
    );
    if (
      !Array.isArray(feature.element_pair_channels) ||
      feature.element_pair_channels.length !== channelCount ||
      feature.element_pair_channels.some(
        (channel) => typeof channel !== "string" || channel === "",
      )
    ) {
      throw new Error(
        `features.by_system.${systemId}.element_pair_channels must match channel_count`,
      );
    }
    if (featureDimension !== channelCount * binsPerChannel) {
      throw new Error(
        `features.by_system.${systemId}.feature_dimension must equal channel_count times bins_per_channel`,
      );
    }
  }
}

function validateSelection(value: unknown): void {
  const selection = asRecord(value, "selection");
  const selectedAlpha = requireFiniteNumber(
    selection.selected_alpha,
    "selection.selected_alpha",
  );
  if (
    !Array.isArray(selection.validation_grid) ||
    selection.validation_grid.length === 0
  ) {
    throw new Error("selection.validation_grid must be a non-empty array");
  }

  let selectedAlphaObserved = false;
  for (const [index, value] of selection.validation_grid.entries()) {
    const entry = asRecord(value, `selection.validation_grid.${index}`);
    const alpha = requireFiniteNumber(
      entry.alpha,
      `selection.validation_grid.${index}.alpha`,
    );
    requireFiniteNumber(
      entry.median_validation_mae,
      `selection.validation_grid.${index}.median_validation_mae`,
    );
    const perSystem = asRecord(
      entry.per_system_validation_mae,
      `selection.validation_grid.${index}.per_system_validation_mae`,
    );
    requireExactKeys(
      perSystem,
      developmentSystemIds,
      `selection.validation_grid.${index}.per_system_validation_mae`,
    );
    for (const systemId of developmentSystemIds) {
      requireFiniteNumber(
        perSystem[systemId],
        `selection.validation_grid.${index}.per_system_validation_mae.${systemId}`,
      );
    }
    selectedAlphaObserved ||= alpha === selectedAlpha;
  }
  if (!selectedAlphaObserved) {
    throw new Error("selection.selected_alpha must appear in validation_grid");
  }
}

function validateSplit(value: unknown): void {
  const split = asRecord(value, "split");
  const partitions = asRecord(split.partitions, "split.partitions");
  requireExactKeys(
    partitions,
    ["train", "validation", "evaluation"],
    "split.partitions",
  );
  for (const partition of ["train", "validation", "evaluation"] as const) {
    requirePositiveInteger(
      partitions[partition],
      `split.partitions.${partition}`,
    );
  }
  requirePositiveInteger(split.selected_frames, "split.selected_frames");

  const diagnostics = asRecord(
    split.ordering_diagnostics_by_system,
    "split.ordering_diagnostics_by_system",
  );
  requireExactKeys(
    diagnostics,
    developmentSystemIds,
    "split.ordering_diagnostics_by_system",
  );
  for (const systemId of developmentSystemIds) {
    const system = asRecord(
      diagnostics[systemId],
      `split.ordering_diagnostics_by_system.${systemId}`,
    );
    if (system.strictly_increasing !== true) {
      throw new Error(
        `split.ordering_diagnostics_by_system.${systemId}.strictly_increasing must be true`,
      );
    }
    const adjacent = asRecord(
      system.adjacent_original_index_gap,
      `split.ordering_diagnostics_by_system.${systemId}.adjacent_original_index_gap`,
    );
    for (const key of ["minimum", "median", "maximum"] as const) {
      requireFiniteNumber(
        adjacent[key],
        `split.ordering_diagnostics_by_system.${systemId}.adjacent_original_index_gap.${key}`,
      );
    }
    const boundaries = asRecord(
      system.partition_boundary_gap,
      `split.ordering_diagnostics_by_system.${systemId}.partition_boundary_gap`,
    );
    for (const key of [
      "train_to_validation",
      "validation_to_evaluation",
    ] as const) {
      requireFiniteNumber(
        boundaries[key],
        `split.ordering_diagnostics_by_system.${systemId}.partition_boundary_gap.${key}`,
      );
    }
  }
}

export function validateRmd17DevelopmentSummary(
  value: unknown,
): Rmd17DevelopmentSummary {
  const summary = asRecord(value, "rMD17 development summary");
  if (summary.artifact_type !== "reviewed-development-summary") {
    throw new Error(
      "artifact_type must be reviewed-development-summary before publication",
    );
  }
  validateDevelopmentEvaluation(summary.development_evaluation);
  validateLockedEvaluations(summary.locked_evaluations);
  validateSystemStatuses(summary.systems);
  validateAggregates(summary.aggregates);
  validateFeatures(summary.features);
  validateSelection(summary.selection);
  validateSplit(summary.split);
  return summary as unknown as Rmd17DevelopmentSummary;
}
