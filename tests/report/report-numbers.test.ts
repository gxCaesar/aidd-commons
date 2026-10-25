import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const root = resolve(import.meta.dirname, '../..');
const reportPath = resolve(root, 'report/aidd-commons-living-report-v0.1.md');
const auditPath = resolve(root, 'docs/COMPARISON_AUDIT.md');
const comparisonPath = resolve(root, 'site/public/data/comparison.v1.json');

type Threshold = 'explained' | 'worked' | 'executable' | 'executable-on-real-data' | 'assessed';

type Summary = {
  provider_id: string;
  threshold: Threshold;
  lower: number;
  upper: number;
};

type Comparison = {
  providers: { id: string }[];
  taxonomy: { topics: number; tracks: number };
  observations: {
    total_cells: number;
    direct_cells: number;
    default_unverified_cells: number;
  };
  summaries: Summary[];
  second_readings: {
    id: string;
    equal: number;
    reading_deeper: number;
    reading_shallower: number;
  }[];
  claims: Record<
    string,
    {
      status: string;
      bound_condition_satisfied: boolean;
      correction_window_status: string;
    }
  >;
};

const report = readFileSync(reportPath, 'utf8');
const audit = readFileSync(auditPath, 'utf8');
const comparison = JSON.parse(readFileSync(comparisonPath, 'utf8')) as Comparison;

const thresholds: Threshold[] = [
  'explained',
  'worked',
  'executable',
  'executable-on-real-data',
  'assessed',
];

/** The recorded depth of this project's own row, at one threshold. */
function recordedDepth(threshold: Threshold): number {
  const summary = comparison.summaries.find(
    (entry) => entry.provider_id === 'aidd-commons' && entry.threshold === threshold,
  );
  if (summary === undefined) {
    throw new Error(`no summary for the aidd-commons row at ${threshold}`);
  }
  return summary.lower;
}

/** The threshold's name as the report writes it. */
function thresholdWords(threshold: Threshold): string {
  return threshold === 'executable-on-real-data' ? 'executable on real data' : threshold;
}

describe('living report coverage numbers', () => {
  it('states the recorded depth of every threshold the audit scores', () => {
    const counts = thresholds.map((t) => `${recordedDepth(t)} ${thresholdWords(t)}`);
    const expected =
      `The recorded coverage of this project is ` +
      `${counts.slice(0, -1).join(', ')} and ${counts[counts.length - 1]} topics.`;

    expect(report).toContain(expected);
  });

  it('states the size of the comparison set the audit covers', () => {
    expect(report).toContain(
      `The audit of Chapter 10 crosses ${comparison.providers.length} audited systems and ` +
        `${comparison.taxonomy.topics} topic units`,
    );
  });

  it('states the cell counts the comparison materialises', () => {
    const { total_cells, direct_cells, default_unverified_cells } = comparison.observations;

    expect(report).toContain(
      `${total_cells} provider-topic cells, of which ${direct_cells} direct observations and ` +
        `${default_unverified_cells} explicit unknowns`,
    );
  });

  it('states the outcome of the independent reading of the same topics', () => {
    const reading = comparison.second_readings[0];

    expect(report).toContain(
      `The reading agreed with the record on ${reading.equal} topics, read ${reading.reading_deeper} deeper ` +
        `and read ${reading.reading_shallower} shallower.`,
    );
  });

  it('keeps the claim status that the audit records', () => {
    for (const [name, claim] of Object.entries(comparison.claims)) {
      expect(
        report,
        `the report does not state the status of the ${name} claim`,
      ).toContain(claim.status.replace(/_/g, ' '));
    }

    const windows = Object.values(comparison.claims)
      .map((claim) => claim.correction_window_status)
      .filter((status): status is string => status !== undefined);

    for (const status of windows) {
      expect(
        report,
        'the report does not name the correction-window condition',
      ).toContain(status.replace(/_/g, ' '));
    }
  });

  it('states the same depths in the coverage-bounds table', () => {
    const row = report
      .split('\n')
      .find((line) => line.startsWith('| AIDD Commons |'));

    expect(row, 'the coverage-bounds table has no AIDD Commons row').toBeDefined();

    const cells = (row as string)
      .split('|')
      .map((cell) => cell.trim())
      .filter((cell) => cell.length > 0);

    // The row is provider, direct cells, absent, unknown, then the five thresholds.
    expect(cells[4]).toBe(`${recordedDepth('explained')}`);
    expect(cells[5]).toBe(`${recordedDepth('worked')}`);
    expect(cells[6]).toBe(`${recordedDepth('executable')}`);
    expect(cells[7]).toBe(`${recordedDepth('executable-on-real-data')}`);
    expect(cells[8]).toBe(`${recordedDepth('assessed')}`);
  });

  it('states the same depths in the reading-comparison table', () => {
    for (const threshold of thresholds) {
      const row = report
        .split('\n')
        .find((line) => line.startsWith(`| ${thresholdWords(threshold)} |`));

      expect(row, `the reading-comparison table has no ${threshold} row`).toBeDefined();

      const cells = (row as string)
        .split('|')
        .map((cell) => cell.trim())
        .filter((cell) => cell.length > 0);

      expect(cells[1], `the ${threshold} row records the wrong depth`).toBe(
        `${recordedDepth(threshold)}`,
      );
    }
  });

  it('agrees with the audit document the numbers are regenerated from', () => {
    expect(audit).toContain(`${comparison.providers.length} providers`);
    expect(audit).toContain(`${comparison.taxonomy.topics} topics`);
    expect(audit).toContain(`${comparison.observations.total_cells} provider-topic cells`);
    expect(audit).toContain(`${comparison.observations.direct_cells} direct observations`);
    expect(audit).toContain(
      `${comparison.observations.default_unverified_cells} explicit-default unknown cells`,
    );

    for (const threshold of thresholds) {
      expect(audit).toContain(`${recordedDepth(threshold)}`);
    }
  });
});
