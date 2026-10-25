export type CoverageDepth =
  | "absent"
  | "unverified"
  | "mentioned"
  | "explained"
  | "worked"
  | "executable"
  | "assessed";

export const comparisonTrackTitles: Readonly<Record<string, string>> = {
  foundations: "Foundations",
  "drug-discovery-foundations": "Drug discovery foundations",
  "machine-learning": "Machine learning",
  "data-governance": "Data governance",
  representations: "Molecular and biological representations",
  "mechanism-targets": "Disease mechanisms and target discovery",
  "qsar-properties": "QSAR and molecular properties",
  "admet-pk": "ADMET, DMPK, and PK/PD",
  "dti-screening": "DTI and virtual screening",
  "structure-and-pockets": "Structure, binding sites, and pockets",
  "physics-based-modeling": "Physics-based modeling",
  "molecular-generation": "Molecular generation and optimization",
  "biologics-design": "Biologics design",
  "synthesis-and-automation": "Synthesis and laboratory automation",
  "active-learning": "Active learning and DMTA loops",
  "scientific-agents": "Scientific language models and agents",
  "evaluation-and-reproducibility": "Evaluation and reproducibility",
  "candidate-nomination": "Candidate nomination and capstone",
};

export function comparisonTrackTitle(trackId: string): string {
  return comparisonTrackTitles[trackId] ?? trackId.replaceAll("-", " ");
}

export type ComparisonEvidence = {
  access: "opened" | "inaccessible";
  evidence_id: string;
  observed_scope: string;
  reviewed_on: string;
  title: string;
  version?: string;
} & (
  | { source_type: "url"; url: string }
  | { repository_path: string; source_type: "repository_path" }
);

export type ComparisonProvider = {
  access: Record<
    "content" | "code" | "data" | "solutions",
    { evidence?: string[]; value: string }
  >;
  canonical_source:
    | { source_type: "url"; url: string }
    | { repository_path: string; source_type: "repository_path" };
  caveats: string[];
  id: string;
  languages: string[];
  last_verified: string;
  name: string;
  provider_class: string;
};

export type ComparisonRow = {
  coverage_origin: "default" | "direct";
  depth: CoverageDepth;
  evidence: ComparisonEvidence[];
  lower_at_explained: 0 | 1;
  note: string;
  provider_class: string;
  provider_id: string;
  provider_name: string;
  reviewed_scope: string;
  run_basis: "real-data" | "authored" | "unverified" | null;
  topic_core: boolean;
  topic_id: string;
  topic_order: number;
  topic_title: string;
  track_id: string;
  track_order: number;
  upper_at_explained: 0 | 1;
};

export type CoverageSummary = {
  default_unverified_cells: number;
  direct_cells: number;
  lower: number;
  provider_id: string;
  threshold:
    | "explained"
    | "worked"
    | "executable"
    | "executable-on-real-data"
    | "assessed";
  total_topics: number;
  upper: number;
};

export type ComparisonGap = {
  external_providers_at_worked_or_deeper: string[];
  self_depth: CoverageDepth;
  strongest_external_depth: CoverageDepth;
  topic_core: boolean;
  topic_id: string;
  topic_title: string;
  track_id: string;
};

export type DepthCandidate = {
  cheap_baseline: {
    name: string;
    protocol: string;
  };
  compute: {
    device: "cpu";
    estimated_download_mb: number;
    estimated_memory_gb: number;
    estimated_runtime_minutes: number;
  };
  data_feasibility: {
    dataset_name: string;
    dataset_version: string;
  };
  evaluation: {
    independent_validation: string;
    primary_metric: string;
  };
  independent_unit: {
    name: string;
    observed_units: number;
  };
  implementation: {
    note: string;
    status: "planned" | "in_progress" | "completed";
    updated_on: string;
  };
  licence: {
    name: string;
    scope: string;
  };
  maintenance: {
    burden: number;
    rationale: string;
  };
  prerequisite_value: number;
  topic_id: string;
  topic_title: string;
  track_id: string;
};

export type ComparisonPayload = {
  as_of: string;
  claims: {
    most_comprehensive: {
      self_lower_at_explained: number;
      status: "not_established";
      strongest_external_upper_at_explained: number;
    };
    most_detailed: {
      executable_or_assessed_self_tracks: number;
      required_self_tracks: number;
      self_lower_at_worked: number;
      status: "not_established";
      strongest_external_upper_at_worked: number;
    };
  };
  gaps: {
    candidates: ComparisonGap[];
    selected_depth_candidates: DepthCandidate[];
    self_audit_needed: ComparisonGap[];
    selection_status:
      | "frozen_three_candidates"
      | "frozen_fewer_than_three_candidates"
      | "no_eligible_candidates"
      | "not_selected_missing_eligibility_records";
  };
  observations: {
    default_unverified_cells: number;
    direct_cells: number;
    total_cells: number;
  };
  providers: ComparisonProvider[];
  publication: {
    correction_url: string | null;
    correction_window_days: 30;
    correction_window_ends_at: string | null;
    correction_window_status: "not_recorded" | "open" | "elapsed";
    first_published_at: string | null;
    repository_url: string | null;
    site_url: string | null;
    status_checked_on: string | null;
  };
  rows: ComparisonRow[];
  schema_version: "comparison.v1";
  summaries: CoverageSummary[];
  taxonomy: {
    core_topics: number;
    topics: number;
    tracks: number;
    version: string;
  };
};
