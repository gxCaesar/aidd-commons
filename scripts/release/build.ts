import {
  copyFile,
  lstat,
  mkdir,
  readdir,
  stat,
  writeFile,
} from "node:fs/promises";
import {
  basename,
  dirname,
  extname,
  join,
  relative,
  resolve,
  sep,
} from "node:path";

import {
  isTestMaterialFinding,
  scanPublicTree,
  type HygieneFinding,
} from "./hygiene.js";

export type InventoryEntry = {
  path: string;
  size: string;
};

export type ReleaseBuildResult = {
  files: InventoryEntry[];
  findings: HygieneFinding[];
  exemptedFindings: HygieneFinding[];
  skipped: string[];
};

export type ReleaseBuildOptions = {
  destination: string;
  inventoryPath: string;
  sourceRoot: string;
};

export const fileAllowlist = [
  ".github/PULL_REQUEST_TEMPLATE.md",
  ".gitignore",
  "ACKNOWLEDGEMENTS.md",
  "CITATION.cff",
  "CHANGELOG.md",
  "CODE_OF_CONDUCT.md",
  "CONTRIBUTING.md",
  "GOVERNANCE.md",
  "LICENSE",
  "LICENSE-CONTENT",
  "README.md",
  "SECURITY.md",
  "THIRD_PARTY_NOTICES.md",
  "package.json",
  "playwright.config.ts",
  "pnpm-workspace.yaml",
  "pyproject.toml",
  "tsconfig.json",
  "vitest.config.ts",
  "site/astro.config.mjs",
  "site/package.json",
  "site/tsconfig.json",
  "labs/freesolv/README.md",
  "labs/freesolv/environment.txt",
  "labs/freesolv/freesolv_honest_baselines.ipynb",
  "labs/freesolv/reviewed-results.json",
  "labs/freesolv/run_lab.py",
  "labs/chembl_egfr/README.md",
  "labs/chembl_egfr/development-summary.json",
  "labs/chembl_egfr/locked-summary.json",
  "labs/chembl_egfr/export_locked_summary.py",
  "labs/chembl_egfr/protocol.json",
  "labs/chembl_egfr/execution-amendment.json",
  "labs/chembl_egfr/run_lab.py",
  "labs/rmd17_system_state/README.md",
  "labs/rmd17_system_state/development-summary.json",
  "labs/rmd17_system_state/locked-summary.json",
  "labs/rmd17_system_state/export_locked_summary.py",
  "labs/rmd17_system_state/protocol.json",
  "labs/rmd17_system_state/run_lab.py",
  "labs/rmd17_system_state/observable-protocol.json",
  "labs/rmd17_system_state/inspect_dynamics.py",
  // The four labs added for the curriculum tracks that had no executable topic.
  "labs/decision_unit_scope/README.md",
  "labs/decision_unit_scope/protocol.json",
  "labs/decision_unit_scope/run_lab.py",
  "labs/decision_unit_scope/inspect_decision_unit_scope.py",
  "labs/decision_unit_scope/export_summary.py",
  "labs/decision_unit_scope/summary.json",
  "labs/assay_endpoint_controls/README.md",
  "labs/assay_endpoint_controls/protocol.json",
  "labs/assay_endpoint_controls/run_lab.py",
  "labs/assay_endpoint_controls/inspect_assay_endpoint_controls.py",
  "labs/assay_endpoint_controls/export_summary.py",
  "labs/assay_endpoint_controls/summary.json",
  "labs/rosetta_cross_modality/.gitignore",
  "labs/rosetta_cross_modality/README.md",
  "labs/rosetta_cross_modality/protocol.json",
  "labs/rosetta_cross_modality/run_lab.py",
  "labs/rosetta_cross_modality/inspect_rosetta_cross_modality.py",
  "labs/rosetta_cross_modality/export_summary.py",
  "labs/rosetta_cross_modality/summary.json",
  "labs/skempi_affinity/README.md",
  "labs/skempi_affinity/protocol.json",
  "labs/skempi_affinity/run_lab.py",
  "labs/skempi_affinity/inspect_skempi_affinity.py",
  "labs/skempi_affinity/export_summary.py",
  "labs/skempi_affinity/summary.json",
  // The lab that gives the six-objective topic a runnable task.
  "labs/objective_ladder/README.md",
  "labs/objective_ladder/protocol.json",
  "labs/objective_ladder/run_lab.py",
  "labs/objective_ladder/inspect_objective_ladder.py",
  "labs/objective_ladder/export_summary.py",
  "labs/objective_ladder/summary.json",
  // The lab that audits the atlas' own seven openness fields.
  "labs/asset_openness_audit/README.md",
  "labs/asset_openness_audit/protocol.json",
  "labs/asset_openness_audit/run_lab.py",
  "labs/asset_openness_audit/inspect_asset_openness_audit.py",
  "labs/asset_openness_audit/export_summary.py",
  "labs/asset_openness_audit/summary.json",
  // The lab that measures the leakage routes of a row split.
  "labs/split_leakage_audit/README.md",
  "labs/split_leakage_audit/protocol.json",
  "labs/split_leakage_audit/run_lab.py",
  "labs/split_leakage_audit/inspect_split_leakage_audit.py",
  "labs/split_leakage_audit/export_summary.py",
  "labs/split_leakage_audit/summary.json",
  // The lab that audits the atlas as a typed graph.
  "labs/relational_graph_audit/README.md",
  "labs/relational_graph_audit/protocol.json",
  "labs/relational_graph_audit/run_lab.py",
  "labs/relational_graph_audit/inspect_relational_graph_audit.py",
  "labs/relational_graph_audit/export_summary.py",
  "labs/relational_graph_audit/summary.json",
  // The lab that sorts the comparison cells into the four evidence states.
  "labs/claims_evidence_audit/README.md",
  "labs/claims_evidence_audit/protocol.json",
  "labs/claims_evidence_audit/run_lab.py",
  "labs/claims_evidence_audit/inspect_claims_evidence_audit.py",
  "labs/claims_evidence_audit/export_summary.py",
  "labs/claims_evidence_audit/summary.json",
  // The laboratory that sorts the endpoint families of one cohort.
  "labs/multi_endpoint_tradeoff/README.md",
  "labs/multi_endpoint_tradeoff/protocol.json",
  "labs/multi_endpoint_tradeoff/run_lab.py",
  "labs/multi_endpoint_tradeoff/inspect_multi_endpoint_tradeoff.py",
  "labs/multi_endpoint_tradeoff/export_summary.py",
  "labs/multi_endpoint_tradeoff/summary.json",
  // The laboratory that tells a measurement, a response and an outcome apart.
  "labs/functional_validation_audit/README.md",
  "labs/functional_validation_audit/protocol.json",
  "labs/functional_validation_audit/run_lab.py",
  "labs/functional_validation_audit/inspect_functional_validation_audit.py",
  "labs/functional_validation_audit/export_summary.py",
  "labs/functional_validation_audit/summary.json",
  // The laboratory that audits how the atlas binds its own claims.
  "labs/source_review_scope_audit/README.md",
  "labs/source_review_scope_audit/protocol.json",
  "labs/source_review_scope_audit/run_lab.py",
  "labs/source_review_scope_audit/inspect_source_review_scope_audit.py",
  "labs/source_review_scope_audit/export_summary.py",
  "labs/source_review_scope_audit/summary.json",
  // The laboratory that sorts the entity kinds a table names.
  "labs/entity_glossary_audit/README.md",
  "labs/entity_glossary_audit/protocol.json",
  "labs/entity_glossary_audit/run_lab.py",
  "labs/entity_glossary_audit/inspect_entity_glossary_audit.py",
  "labs/entity_glossary_audit/export_summary.py",
  "labs/entity_glossary_audit/summary.json",
  // The laboratory that counts a cohort under each unit a split could use.
  "labs/generalization_unit_audit/README.md",
  "labs/generalization_unit_audit/protocol.json",
  "labs/generalization_unit_audit/run_lab.py",
  "labs/generalization_unit_audit/inspect_generalization_unit_audit.py",
  "labs/generalization_unit_audit/export_summary.py",
  "labs/generalization_unit_audit/summary.json",
  // The laboratory that measures how far a molecule is from the training set.
  "labs/applicability_domain_audit/README.md",
  "labs/applicability_domain_audit/protocol.json",
  "labs/applicability_domain_audit/run_lab.py",
  "labs/applicability_domain_audit/inspect_applicability_domain_audit.py",
  "labs/applicability_domain_audit/export_summary.py",
  "labs/applicability_domain_audit/summary.json",
  // The laboratory that applies a readiness rule fixed before the counts.
  "labs/nomination_readiness_audit/README.md",
  "labs/nomination_readiness_audit/protocol.json",
  "labs/nomination_readiness_audit/run_lab.py",
  "labs/nomination_readiness_audit/inspect_nomination_readiness_audit.py",
  "labs/nomination_readiness_audit/export_summary.py",
  "labs/nomination_readiness_audit/summary.json",
  // The laboratory that counts the partners each protein is measured with.
  "labs/specificity_margin_audit/README.md",
  "labs/specificity_margin_audit/protocol.json",
  "labs/specificity_margin_audit/run_lab.py",
  "labs/specificity_margin_audit/inspect_specificity_margin_audit.py",
  "labs/specificity_margin_audit/export_summary.py",
  "labs/specificity_margin_audit/summary.json",
  // The laboratory that audits this project's own tool return records.
  "labs/tool_contract_audit/README.md",
  "labs/tool_contract_audit/protocol.json",
  "labs/tool_contract_audit/run_lab.py",
  "labs/tool_contract_audit/inspect_tool_contract_audit.py",
  "labs/tool_contract_audit/export_summary.py",
  "labs/tool_contract_audit/summary.json",
  // The laboratory that traces measured clearance through a PK/PD model.
  "labs/pkpd_translation_audit/README.md",
  "labs/pkpd_translation_audit/protocol.json",
  "labs/pkpd_translation_audit/run_lab.py",
  "labs/pkpd_translation_audit/inspect_pkpd_translation_audit.py",
  "labs/pkpd_translation_audit/export_summary.py",
  "labs/pkpd_translation_audit/summary.json",
  // The laboratory that joins the endpoint families that can be joined.
  "labs/multi_endpoint_integration/README.md",
  "labs/multi_endpoint_integration/protocol.json",
  "labs/multi_endpoint_integration/run_lab.py",
  "labs/multi_endpoint_integration/inspect_multi_endpoint_integration.py",
  "labs/multi_endpoint_integration/export_summary.py",
  "labs/multi_endpoint_integration/summary.json",
  // The laboratory that detects a selection rule read back on its own data.
  "labs/oracle_exploitation_audit/README.md",
  "labs/oracle_exploitation_audit/protocol.json",
  "labs/oracle_exploitation_audit/run_lab.py",
  "labs/oracle_exploitation_audit/inspect_oracle_exploitation_audit.py",
  "labs/oracle_exploitation_audit/export_summary.py",
  "labs/oracle_exploitation_audit/summary.json",
  // The laboratory that audits what the catalogue states about a construct.
  "labs/biologic_construct_audit/README.md",
  "labs/biologic_construct_audit/protocol.json",
  "labs/biologic_construct_audit/run_lab.py",
  "labs/biologic_construct_audit/inspect_biologic_construct_audit.py",
  "labs/biologic_construct_audit/export_summary.py",
  "labs/biologic_construct_audit/summary.json",
  // The laboratory that audits the links of a claim chain.
  "labs/claim_chain_audit/README.md",
  "labs/claim_chain_audit/protocol.json",
  "labs/claim_chain_audit/run_lab.py",
  "labs/claim_chain_audit/inspect_claim_chain_audit.py",
  "labs/claim_chain_audit/export_summary.py",
  "labs/claim_chain_audit/summary.json",
  // The laboratory that audits what the records still leave open.
  "labs/open_question_audit/README.md",
  "labs/open_question_audit/protocol.json",
  "labs/open_question_audit/run_lab.py",
  "labs/open_question_audit/inspect_open_question_audit.py",
  "labs/open_question_audit/export_summary.py",
  "labs/open_question_audit/summary.json",
  // The laboratory that audits the released relative free-energy networks.
  "labs/free_energy_network_audit/README.md",
  "labs/free_energy_network_audit/protocol.json",
  "labs/free_energy_network_audit/run_lab.py",
  "labs/free_energy_network_audit/inspect_free_energy_network_audit.py",
  "labs/free_energy_network_audit/export_summary.py",
  "labs/free_energy_network_audit/summary.json",
  // The laboratory that tests a target-mediated response against a control.
  "labs/mechanism_consistency/README.md",
  "labs/mechanism_consistency/protocol.json",
  "labs/mechanism_consistency/run_lab.py",
  "labs/mechanism_consistency/inspect_mechanism_consistency.py",
  "labs/mechanism_consistency/export_summary.py",
  "labs/mechanism_consistency/summary.json",
  // The laboratory that assembles a candidate's evidence into one chain.
  "labs/crossdomain_tradeoff/README.md",
  "labs/crossdomain_tradeoff/protocol.json",
  "labs/crossdomain_tradeoff/run_lab.py",
  "labs/crossdomain_tradeoff/inspect_crossdomain_tradeoff.py",
  "labs/crossdomain_tradeoff/export_summary.py",
  "labs/crossdomain_tradeoff/summary.json",
  "labs/candidate_evidence_chain/README.md",
  "labs/candidate_evidence_chain/protocol.json",
  "labs/candidate_evidence_chain/run_lab.py",
  "labs/candidate_evidence_chain/inspect_candidate_evidence_chain.py",
  "labs/candidate_evidence_chain/export_summary.py",
  "labs/candidate_evidence_chain/summary.json",
  // The laboratory that audits this repository's own laboratories as a task set.
  "labs/agent_evaluation_taskset/README.md",
  "labs/agent_evaluation_taskset/protocol.json",
  "labs/agent_evaluation_taskset/run_lab.py",
  "labs/agent_evaluation_taskset/inspect_agent_evaluation_taskset.py",
  "labs/agent_evaluation_taskset/export_summary.py",
  "labs/agent_evaluation_taskset/summary.json",
  // The laboratory that applies a declared profile to measured compounds.
  "labs/target_product_profile/README.md",
  "labs/target_product_profile/protocol.json",
  "labs/target_product_profile/run_lab.py",
  "labs/target_product_profile/inspect_target_product_profile.py",
  "labs/target_product_profile/export_summary.py",
  "labs/target_product_profile/summary.json",
  "labs/molecule_representations/README.md",
  "labs/molecule_representations/README.zh-CN.md",
  "labs/molecule_representations/build_notebooks.py",
  "labs/molecule_representations/representation_inspector.ipynb",
  "labs/molecule_representations/representation_inspector.zh-CN.ipynb",
  "labs/molecule_representations/examples.csv",
  "configs/scientific-agents/paperqa-local.json",
  "scripts/agents/check_local_profile.py",
  "labs/paperqa_local/README.md",
  "labs/paperqa_local/corpus.json",
  "labs/paperqa_local/run_smoke.py",
  "labs/paperqa_local/build_notebooks.py",
  "labs/paperqa_local/reviewed-example.json",
  "labs/paperqa_local/paperqa_local_tutorial.ipynb",
  "labs/paperqa_local/paperqa_local_tutorial.zh-CN.ipynb",
  "labs/molecule_representations/run_lab.py",
  "labs/student_modelling/README.md",
  "labs/student_modelling/README.zh-CN.md",
  "labs/student_modelling/build_notebooks.py",
  "labs/student_modelling/student_modelling_tutorial.ipynb",
  "labs/student_modelling/student_modelling_tutorial.zh-CN.ipynb",
  "labs/student_modelling/run_lab.py",
  "labs/lipophilicity/README.md",
  "labs/lipophilicity/README.zh-CN.md",
  "labs/lipophilicity/inspect_data.py",
  "labs/lipophilicity/tutorial.py",
  "labs/lipophilicity/build_notebooks.py",
  "labs/lipophilicity/lipophilicity_tutorial.ipynb",
  "labs/lipophilicity/lipophilicity_tutorial.zh-CN.ipynb",
  "labs/pool_budget/README.md",
  "labs/pool_budget/protocol.json",
  "labs/pool_budget/real-protocol.json",
  "labs/pool_budget/REAL_PROTOCOL.md",
  "labs/pool_budget/run_lab.py",
  "labs/pool_budget/run_real_campaign.py",
  "labs/pool_budget/demo-summary.json",
  "labs/pool_budget/real-summary.json",
  "labs/pool_budget/export_summary.py",
  "labs/pool_budget/inspect_contract.py",
  "labs/pool_budget/uncertainty-protocol.json",
  "labs/pool_budget/UNCERTAINTY_PROTOCOL.md",
  "labs/pool_budget/run_uncertainty_campaign.py",
  "labs/pool_budget/uncertainty-summary.json",
  "labs/pool_budget/export_uncertainty_summary.py",
  "labs/chembl_egfr/inspect_contract.py",
  "labs/rmd17_system_state/inspect_contract.py",
  "labs/cyp_assay_system/README.md",
  "labs/cyp_assay_system/protocol.json",
  "labs/cyp_assay_system/run_lab.py",
  "labs/cyp_assay_system/inspect_cyp_assay_system.py",
  "labs/cyp_assay_system/export_summary.py",
  "labs/cyp_assay_system/summary.json",
  "labs/az_clearance_system/README.md",
  "labs/az_clearance_system/protocol.json",
  "labs/az_clearance_system/run_lab.py",
  "labs/az_clearance_system/inspect_az_clearance_system.py",
  "labs/az_clearance_system/export_summary.py",
  "labs/az_clearance_system/summary.json",
  "labs/l1000_perturbation_context/README.md",
  "labs/l1000_perturbation_context/protocol.json",
  "labs/l1000_perturbation_context/run_lab.py",
  "labs/l1000_perturbation_context/inspect_l1000_perturbation_context.py",
  "labs/l1000_perturbation_context/export_summary.py",
  "labs/l1000_perturbation_context/summary.json",
  // Offline inspection labs. Their tests ship in labs/tests, so each lab must ship
  // with them or the released test suite imports files the release does not contain.
  "labs/binder_definition/README.md",
  "labs/binder_definition/dataset.json",
  "labs/binder_definition/inspect_definition.py",
  "labs/cofolding_claims/README.md",
  "labs/cofolding_claims/claim-records.json",
  "labs/cofolding_claims/export_claim_records.py",
  "labs/cofolding_claims/inspect_claims.py",
  "labs/counterevidence/README.md",
  "labs/counterevidence/inspect_dossier.py",
  "labs/design_space/README.md",
  "labs/design_space/inspect_space.py",
  "labs/design_space/spaces.json",
  "labs/docking_protocol/README.md",
  "labs/docking_protocol/inspect_protocol.py",
  "labs/docking_protocol/protocols.json",
  "labs/egfr_structures/README.md",
  "labs/egfr_structures/cif.py",
  "labs/egfr_structures/entries.json",
  "labs/egfr_structures/inspect_complex.py",
  "labs/egfr_structures/inspect_state.py",
  "labs/egfr_structures/structures/1M17.cif",
  "labs/egfr_structures/structures/1XKK.cif",
  "labs/egfr_structures/structures/4HJO.cif",
  "labs/generation_gate/README.md",
  "labs/generation_gate/candidates.json",
  "labs/generation_gate/inspect_gate.py",
  "labs/generation_gate/objective.json",
  "labs/property_decision/README.md",
  "labs/property_decision/decision-rule.json",
  "labs/property_decision/inspect_decision.py",
  "labs/retro_disconnection/README.md",
  "labs/retro_disconnection/inspect_disconnection.py",
  "labs/retro_disconnection/methods.json",
  "labs/retro_disconnection/routes.json",
  "labs/safety_evidence/README.md",
  "labs/safety_evidence/dataset.json",
  "labs/safety_evidence/inspect_safety.py",
  "labs/sar_attribution/README.md",
  "labs/sar_attribution/dataset.json",
  "labs/sar_attribution/inspect_attribution.py",
  "labs/screening_transport/README.md",
  "labs/screening_transport/inspect_transport.py",
  "report/aidd-commons-living-report-v0.1.md",
  "report/aidd-commons-v0.2-addendum.md",
  "report/CITATION-v0.1.cff",
  "report/build.sh",
  "report/fix_pdf_id.py",
  "report/metadata.yaml",
  "report/references.bib",
  // The living-report PDF is not listed here. It ships once, through the
  // site/public route, because the published report page links to
  // /reports/aidd-commons-living-report-v0.1.pdf and that copy is the one a
  // reader can open. The identical file under output/pdf/ is the pandoc build
  // artifact written by report/build.sh; listing it as well published the same
  // PDF twice, under two paths.
];

export const directoryAllowlist = [
  ".github/ISSUE_TEMPLATE",
  ".github/workflows",
  "catalog/comparisons",
  "catalog/curriculum",
  "catalog/resources",
  "catalog/schema",
  "report/figures",
  "docs",
  "labs/src",
  "labs/tests",
  "scripts/catalog",
  "scripts/comparisons",
  "scripts/curriculum",
  "scripts/quality",
  "scripts/release",
  "scripts/report",
  "site/public",
  "site/src",
  "site/scripts",
  "tests/catalog",
  "tests/comparisons",
  "tests/curriculum",
  "tests/e2e",
  "tests/links",
  // The release ships its own gates, so the release ships the tests that prove
  // them, known-bad fixtures included. Without them a reader cannot show that
  // the build rejects a malformed record.
  "tests/release",
  "tests/report",
  "tests/site",
];

const privateDirectoryNames = new Set([
  ".agents",
  ".cache",
  ".codex",
  ".git",
  ".mypy_cache",
  ".pnpm-store",
  ".pytest_cache",
  ".ruff_cache",
  ".superpowers",
  ".venv",
  "__pycache__",
  "node_modules",
  "playwright-report",
  "test-results",
  "tmp",
]);

const privateFileNames = new Set([
  "agents.md",
  "claude.md",
  "claude-codex-workflow-log.md",
  "package-lock.json",
  "pnpm-lock.yaml",
  "uv.lock",
  "yarn.lock",
]);

// Paths that must never reach the curated export even though a directory
// allowlist entry covers them. Each one is a facilitator answer sheet: the
// reader-trial instrument and its two task sheets carry the answers, so a
// downloaded release would hand the answer sheet to the person being tested.
// The facilitator answer key written in this round is excluded for the same reason.\n// The blank observation forms beside them are not answer sheets and ship.
export const excludedReleasePaths = new Set([
  "docs/READER_TRIAL.md",
  "docs/reader-trial/answer-key.md",
  "docs/reader-trial/notebook-reader.en.md",
  "docs/reader-trial/notebook-reader.zh-CN.md",
  "docs/reader-trial/rubric.md",
]);

// Tracked content that is deliberately kept in the repository and out of the
// curated export, with the reason it stays behind. The prefix is matched
// against a release path, and the builder refuses to publish a path that
// carries one of these prefixes even if it is listed by mistake.
export const intentionalReleaseExclusions = new Map<string, string>([
  [
    "labs/freesolv/results/",
    "raw evaluation output stays in the repository, not in the curated export",
  ],
]);

// The curated export ships the release test suite, and part of that suite
// breaks the hygiene rules on purpose. The known-bad fixtures exist to be
// rejected, and a test file has to name the rule it exercises: the receipt
// fixture repeats the phrase its rule looks for, the checksum fixture writes a
// sha256 key, and the builder fixture writes a synthetic absolute path. They
// are test material rather than release content, so their findings are reported
// but do not block the build.

function portablePath(root: string, path: string): string {
  return relative(root, path).split(sep).join("/");
}

function compareCodePoints(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function humanSize(size: number): string {
  if (size >= 1_000_000_000) {
    return `${(size / 1_000_000_000).toFixed(2)} GB`;
  }
  if (size < 10_000) {
    return "<0.01 MB";
  }
  return `${(size / 1_000_000).toFixed(2)} MB`;
}

function isMacosMetadata(path: string): boolean {
  const parts = path.split("/");
  const name = basename(path);
  return (
    parts.some((part) => part.toLowerCase() === "__macosx") ||
    name.toLowerCase() === ".ds_store" ||
    name.startsWith("._")
  );
}

// The known-bad fixtures are negative controls for the release gates. The
// builder must copy them verbatim; the scanner must not fail on them. Those
// are two different decisions and they live in two different files.
const knownBadFixtureDirectory = "tests/release/fixtures/known-bad/";

function exclusionReason(path: string): string | undefined {
  // The deliberate negative controls ship verbatim. A fixture for the
  // agent-instruction rule has to be called AGENTS.md, one for the
  // environment-file rule has to be called .env, and one for the receipt rule
  // has to carry its phrase, or the gates they prove would not be exercised.
  // The directory holds nothing else.
  if (path.startsWith(knownBadFixtureDirectory)) {
    return undefined;
  }

  const parts = path.split("/");
  const name = basename(path).toLowerCase();

  if (excludedReleasePaths.has(path)) {
    return "answer-bearing reader-trial material";
  }
  for (const [prefix, reason] of intentionalReleaseExclusions) {
    if (path.startsWith(prefix)) {
      return reason;
    }
  }
  // macOS records directory view state and resource forks in every tree it
  // touches, and the release hygiene rules reject them.
  if (isMacosMetadata(path)) {
    return "macOS filesystem metadata";
  }
  if (parts.some((part) => privateDirectoryNames.has(part.toLowerCase()))) {
    return "private or generated directory";
  }
  if (
    parts.some((part) => ["prompt", "prompts"].includes(part.toLowerCase()))
  ) {
    return "private prompt directory";
  }
  if (privateFileNames.has(name)) {
    return "private instruction or lockfile";
  }
  if (name === ".env" || name.startsWith(".env.")) {
    return "environment file";
  }
  if (/^task-[a-z0-9._-]*report\.md$/u.test(name)) {
    return "internal task report";
  }
  if (/^task-[a-z0-9._-]*brief\.md$/u.test(name)) {
    return "internal task brief";
  }
  if (/(?:^|[-_])prompt(?:[-_.]|$)/u.test(name)) {
    return "private prompt";
  }
  if (/approval[-_ ]?receipt/u.test(name)) {
    return "private authorization record";
  }
  if (
    /^(?:locked-evaluation\.started|test-evaluation\.started|pipeline-state)\.json$/u.test(
      name,
    )
  ) {
    return "pipeline state";
  }
  if (
    [
      ".log",
      ".trace",
      ".zip",
      ".tar",
      ".gz",
      ".sdf",
      ".parquet",
      ".h5",
      ".hdf5",
      ".npz",
      ".npy",
      ".pt",
      ".pth",
      ".ckpt",
      ".pyc",
    ].includes(extname(name))
  ) {
    return "unapproved raw data, archive, model, or log artifact";
  }

  return undefined;
}

async function pathExists(path: string): Promise<boolean> {
  try {
    await lstat(path);
    return true;
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return false;
    }
    throw error;
  }
}

async function ensureEmptyDestination(destination: string): Promise<void> {
  if (!(await pathExists(destination))) {
    await mkdir(destination, { recursive: true });
    return;
  }

  const destinationStat = await lstat(destination);
  if (!destinationStat.isDirectory()) {
    throw new Error(`Release destination is not a directory: ${destination}`);
  }
  if ((await readdir(destination)).length > 0) {
    throw new Error(
      `Release destination is not empty and will not be deleted: ${destination}`,
    );
  }
}

async function copyAllowlistedFile(
  sourceRoot: string,
  destination: string,
  releasePath: string,
  entries: InventoryEntry[],
  skipped: string[],
): Promise<void> {
  const sourcePath = join(sourceRoot, releasePath);
  if (!(await pathExists(sourcePath))) {
    return;
  }

  const reason = exclusionReason(releasePath);
  if (reason !== undefined) {
    skipped.push(`${releasePath} (${reason})`);
    return;
  }

  const sourceStat = await lstat(sourcePath);
  if (!sourceStat.isFile()) {
    throw new Error(`Allowlisted file is not a regular file: ${releasePath}`);
  }

  const targetPath = join(destination, releasePath);
  await mkdir(dirname(targetPath), { recursive: true });
  await copyFile(sourcePath, targetPath);
  entries.push({
    path: releasePath,
    size: humanSize((await stat(sourcePath)).size),
  });
}

async function copyAllowlistedDirectory(
  sourceRoot: string,
  destination: string,
  releasePath: string,
  entries: InventoryEntry[],
  skipped: string[],
): Promise<void> {
  const sourcePath = join(sourceRoot, releasePath);
  if (!(await pathExists(sourcePath))) {
    return;
  }

  const sourceStat = await lstat(sourcePath);
  if (!sourceStat.isDirectory()) {
    throw new Error(`Allowlisted directory is not a directory: ${releasePath}`);
  }

  const names = await readdir(sourcePath);
  for (const name of names.sort(compareCodePoints)) {
    const childReleasePath = `${releasePath}/${name}`;
    const reason = exclusionReason(childReleasePath);
    if (reason !== undefined) {
      skipped.push(`${childReleasePath} (${reason})`);
      continue;
    }

    const childSourcePath = join(sourceRoot, childReleasePath);
    const childStat = await lstat(childSourcePath);
    if (childStat.isSymbolicLink()) {
      skipped.push(`${childReleasePath} (symbolic link)`);
    } else if (childStat.isDirectory()) {
      await copyAllowlistedDirectory(
        sourceRoot,
        destination,
        childReleasePath,
        entries,
        skipped,
      );
    } else if (childStat.isFile()) {
      await copyAllowlistedFile(
        sourceRoot,
        destination,
        childReleasePath,
        entries,
        skipped,
      );
    } else {
      skipped.push(`${childReleasePath} (unsupported file type)`);
    }
  }
}

function inventory(entries: InventoryEntry[]): string {
  const lines = entries
    .sort((left, right) => compareCodePoints(left.path, right.path))
    .map((entry) => `${entry.path} — ${entry.size}`);
  return `AIDD Commons public release inventory\n\n${lines.join("\n")}\n`;
}

function inventoryIsInsideDestination(
  destination: string,
  inventoryPath: string,
): boolean {
  const pathFromDestination = relative(destination, inventoryPath);
  return (
    pathFromDestination === "" ||
    (!pathFromDestination.startsWith(`..${sep}`) &&
      pathFromDestination !== "..")
  );
}

export async function buildPublicRelease(
  options: ReleaseBuildOptions,
): Promise<ReleaseBuildResult> {
  const sourceRoot = resolve(options.sourceRoot);
  const destination = resolve(options.destination);
  const inventoryPath = resolve(options.inventoryPath);

  if (sourceRoot === destination) {
    throw new Error("Release destination must differ from the source root");
  }
  if (inventoryIsInsideDestination(destination, inventoryPath)) {
    throw new Error(
      "Release inventory must be written outside the public release tree",
    );
  }

  await ensureEmptyDestination(destination);

  const entries: InventoryEntry[] = [];
  const skipped: string[] = [];
  for (const releasePath of fileAllowlist) {
    await copyAllowlistedFile(
      sourceRoot,
      destination,
      releasePath,
      entries,
      skipped,
    );
  }
  for (const releasePath of directoryAllowlist) {
    await copyAllowlistedDirectory(
      sourceRoot,
      destination,
      releasePath,
      entries,
      skipped,
    );
  }

  const scanned = await scanPublicTree(destination);
  const exemptedFindings = scanned.filter(isTestMaterialFinding);
  const findings = scanned.filter((finding) => !isTestMaterialFinding(finding));
  if (findings.length > 0) {
    throw new Error(
      `Release hygiene failed:\n${findings
        .map((finding) => `${finding.path}: ${finding.rule}`)
        .join("\n")}`,
    );
  }

  await mkdir(dirname(inventoryPath), { recursive: true });
  await writeFile(inventoryPath, inventory(entries));
  return {
    files: entries.sort((left, right) =>
      compareCodePoints(left.path, right.path),
    ),
    findings,
    exemptedFindings,
    skipped,
  };
}

type CliOptions = ReleaseBuildOptions;

function parseArguments(argumentsList: string[]): CliOptions {
  let sourceRoot = ".";
  let destination = "public-release";
  let inventoryPath = "public-release.inventory.txt";

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (
      argument === "--source" ||
      argument === "--destination" ||
      argument === "--inventory"
    ) {
      const value = argumentsList[index + 1];
      if (value === undefined) {
        throw new Error(`${argument} requires a path`);
      }
      if (argument === "--source") {
        sourceRoot = value;
      } else if (argument === "--destination") {
        destination = value;
      } else {
        inventoryPath = value;
      }
      index += 1;
    } else {
      throw new Error(`Unknown option: ${argument}`);
    }
  }

  return { destination, inventoryPath, sourceRoot };
}

async function main(): Promise<void> {
  const result = await buildPublicRelease(
    parseArguments(process.argv.slice(2)),
  );
  console.log(
    `Built curated public release with ${result.files.length} files.`,
  );
  if (result.exemptedFindings.length > 0) {
    console.log(
      `${result.exemptedFindings.length} findings came from the shipped test material and were exempted.`,
    );
  }
}

const invokedAsCli =
  process.argv[1] !== undefined && basename(process.argv[1]) === "build.ts";

if (invokedAsCli) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
