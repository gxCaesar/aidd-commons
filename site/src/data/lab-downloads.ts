import freesolvNotebook from "../../../labs/freesolv/freesolv_honest_baselines.ipynb?raw";
import freesolvEnvironment from "../../../labs/freesolv/environment.txt?raw";
import freesolvResults from "../../../labs/freesolv/reviewed-results.json?raw";
import chemblAmendment from "../../../labs/chembl_egfr/execution-amendment.json?raw";
import chemblProtocol from "../../../labs/chembl_egfr/protocol.json?raw";
import chemblResults from "../../../labs/chembl_egfr/locked-summary.json?raw";
import rmd17Protocol from "../../../labs/rmd17_system_state/protocol.json?raw";
import rmd17Development from "../../../labs/rmd17_system_state/development-summary.json?raw";
import rmd17Results from "../../../labs/rmd17_system_state/locked-summary.json?raw";
import poolProtocol from "../../../labs/pool_budget/protocol.json?raw";
import poolRealProtocol from "../../../labs/pool_budget/real-protocol.json?raw";
import poolDemo from "../../../labs/pool_budget/demo-summary.json?raw";
import poolResults from "../../../labs/pool_budget/real-summary.json?raw";
import representationExamples from "../../../labs/molecule_representations/examples.csv?raw";
import lipophilicityNotebook from "../../../labs/lipophilicity/lipophilicity_tutorial.ipynb?raw";
import lipophilicityChineseNotebook from "../../../labs/lipophilicity/lipophilicity_tutorial.zh-CN.ipynb?raw";
import studentNotebook from "../../../labs/student_modelling/student_modelling_tutorial.ipynb?raw";
import studentChineseNotebook from "../../../labs/student_modelling/student_modelling_tutorial.zh-CN.ipynb?raw";
import representationNotebook from "../../../labs/molecule_representations/representation_inspector.ipynb?raw";
import representationChineseNotebook from "../../../labs/molecule_representations/representation_inspector.zh-CN.ipynb?raw";
import paperqaLocalProfile from "../../../configs/scientific-agents/paperqa-local.json?raw";
import localProfileChecker from "../../../scripts/agents/check_local_profile.py?raw";
import paperqaNotebook from "../../../labs/paperqa_local/paperqa_local_tutorial.ipynb?raw";
import paperqaChineseNotebook from "../../../labs/paperqa_local/paperqa_local_tutorial.zh-CN.ipynb?raw";
import paperqaExample from "../../../labs/paperqa_local/reviewed-example.json?raw";
import chemblContractInspector from "../../../labs/chembl_egfr/inspect_contract.py?raw";
import rmd17ContractInspector from "../../../labs/rmd17_system_state/inspect_contract.py?raw";
import poolBudgetContractInspector from "../../../labs/pool_budget/inspect_contract.py?raw";
import poolBudgetRealProtocol from "../../../labs/pool_budget/real-protocol.json?raw";
import rmd17ContractProtocol from "../../../labs/rmd17_system_state/protocol.json?raw";
import cofoldingClaimInspector from "../../../labs/cofolding_claims/inspect_claims.py?raw";
import cofoldingClaimExporter from "../../../labs/cofolding_claims/export_claim_records.py?raw";
import cofoldingClaimRecords from "../../../labs/cofolding_claims/claim-records.json?raw";
import counterevidenceInspector from "../../../labs/counterevidence/inspect_dossier.py?raw";
import generationGateInspector from "../../../labs/generation_gate/inspect_gate.py?raw";
import generationObjective from "../../../labs/generation_gate/objective.json?raw";
import generationCandidates from "../../../labs/generation_gate/candidates.json?raw";
import propertyDecisionInspector from "../../../labs/property_decision/inspect_decision.py?raw";
import propertyDecisionRule from "../../../labs/property_decision/decision-rule.json?raw";
import screeningTransportInspector from "../../../labs/screening_transport/inspect_transport.py?raw";
import retroDisconnectionInspector from "../../../labs/retro_disconnection/inspect_disconnection.py?raw";
import retroRoutes from "../../../labs/retro_disconnection/routes.json?raw";
import retroMethods from "../../../labs/retro_disconnection/methods.json?raw";
import sarAttributionInspector from "../../../labs/sar_attribution/inspect_attribution.py?raw";
import sarAttributionDataset from "../../../labs/sar_attribution/dataset.json?raw";
import binderDefinitionInspector from "../../../labs/binder_definition/inspect_definition.py?raw";
import binderDefinitionDataset from "../../../labs/binder_definition/dataset.json?raw";
import safetyEvidenceInspector from "../../../labs/safety_evidence/inspect_safety.py?raw";
import safetyEvidenceDataset from "../../../labs/safety_evidence/dataset.json?raw";
import dockingProtocolInspector from "../../../labs/docking_protocol/inspect_protocol.py?raw";
import dockingProtocols from "../../../labs/docking_protocol/protocols.json?raw";
import egfrStructureReader from "../../../labs/egfr_structures/cif.py?raw";
import egfrStateInspector from "../../../labs/egfr_structures/inspect_state.py?raw";
import egfrComplexInspector from "../../../labs/egfr_structures/inspect_complex.py?raw";
import egfrStructureManifest from "../../../labs/egfr_structures/entries.json?raw";
import egfrStructure1M17 from "../../../labs/egfr_structures/structures/1M17.cif?raw";
import egfrStructure4HJO from "../../../labs/egfr_structures/structures/4HJO.cif?raw";
import egfrStructure1XKK from "../../../labs/egfr_structures/structures/1XKK.cif?raw";
import designSpaceInspector from "../../../labs/design_space/inspect_space.py?raw";
import designSpaces from "../../../labs/design_space/spaces.json?raw";

// Only curated teaching artifacts, never an entire experiment directory.
export const labDownloads = [
  {
    lab: "design-space",
    path: "labs/design_space/inspect_space.py",
    label: "Offline enumerator testing what each declared design space reaches",
    content: designSpaceInspector,
  },
  {
    lab: "design-space",
    path: "labs/design_space/spaces.json",
    label: "Three declared constructions and the targets tested against them",
    content: designSpaces,
  },
  {
    lab: "docking-protocol",
    path: "labs/docking_protocol/inspect_protocol.py",
    label: "Offline comparability inspector for declared docking protocols",
    content: dockingProtocolInspector,
  },
  {
    lab: "docking-protocol",
    path: "labs/docking_protocol/protocols.json",
    label: "Three declared protocols with all seven components stated",
    content: dockingProtocols,
  },
  {
    lab: "egfr-structure-evidence",
    path: "labs/egfr_structures/inspect_state.py",
    label:
      "Offline reader for what three deposited structures say and how a site is defined",
    content: egfrStateInspector,
  },
  {
    lab: "egfr-structure-evidence",
    path: "labs/egfr_structures/inspect_complex.py",
    label:
      "Offline contact, interaction and pose inspector for the same structures",
    content: egfrComplexInspector,
  },
  {
    lab: "egfr-structure-evidence",
    path: "labs/egfr_structures/cif.py",
    label: "Standard-library mmCIF reader both commands import",
    content: egfrStructureReader,
  },
  {
    lab: "egfr-structure-evidence",
    path: "labs/egfr_structures/entries.json",
    label: "Manifest with sources, declared cutoffs and ligand roles",
    content: egfrStructureManifest,
  },
  {
    lab: "egfr-structure-evidence",
    path: "labs/egfr_structures/structures/1M17.cif",
    label: "PDB 1M17, EGFR kinase domain with erlotinib (CC0)",
    content: egfrStructure1M17,
  },
  {
    lab: "egfr-structure-evidence",
    path: "labs/egfr_structures/structures/4HJO.cif",
    label: "PDB 4HJO, EGFR kinase domain with erlotinib (CC0)",
    content: egfrStructure4HJO,
  },
  {
    lab: "egfr-structure-evidence",
    path: "labs/egfr_structures/structures/1XKK.cif",
    label: "PDB 1XKK, EGFR kinase domain with lapatinib (CC0)",
    content: egfrStructure1XKK,
  },
  {
    lab: "safety-evidence",
    path: "labs/safety_evidence/inspect_safety.py",
    label: "Offline inspector separating five kinds of safety evidence",
    content: safetyEvidenceInspector,
  },
  {
    lab: "safety-evidence",
    path: "labs/safety_evidence/dataset.json",
    label: "Constructed safety record storing findings but never an alert",
    content: safetyEvidenceDataset,
  },
  {
    lab: "binder-definition",
    path: "labs/binder_definition/inspect_definition.py",
    label:
      "Offline inspector for the choices that turn molecules into a binder dataset",
    content: binderDefinitionInspector,
  },
  {
    lab: "binder-definition",
    path: "labs/binder_definition/dataset.json",
    label: "Constructed measurements and decoys, with no class label stored",
    content: binderDefinitionDataset,
  },
  {
    lab: "sar-attribution",
    path: "labs/sar_attribution/inspect_attribution.py",
    label:
      "Offline attribution demonstration on data whose generating rule is known",
    content: sarAttributionInspector,
  },
  {
    lab: "sar-attribution",
    path: "labs/sar_attribution/dataset.json",
    label: "Constructed dataset storing a generating rule rather than labels",
    content: sarAttributionDataset,
  },
  {
    lab: "retro-disconnection",
    path: "labs/retro_disconnection/inspect_disconnection.py",
    label: "Offline comparison of rule, retrieval and template disconnections",
    content: retroDisconnectionInspector,
  },
  {
    lab: "retro-disconnection",
    path: "labs/retro_disconnection/routes.json",
    label:
      "Constructed route set with its precedent membership and unassessed feasibility",
    content: retroRoutes,
  },
  {
    lab: "retro-disconnection",
    path: "labs/retro_disconnection/methods.json",
    label:
      "Declared disconnection families, including the one that does not run",
    content: retroMethods,
  },
  {
    lab: "screening-transport",
    path: "labs/screening_transport/inspect_transport.py",
    label:
      "Offline transport inspector over the completed two-assay screening replay",
    content: screeningTransportInspector,
  },
  {
    lab: "property-decision",
    path: "labs/property_decision/inspect_decision.py",
    label:
      "Offline threshold and abstention inspector over calibrated intervals",
    content: propertyDecisionInspector,
  },
  {
    lab: "property-decision",
    path: "labs/property_decision/decision-rule.json",
    label:
      "Frozen decision rule with its threshold, abstention branch and both selection criteria",
    content: propertyDecisionRule,
  },
  {
    lab: "generation-gate",
    path: "labs/generation_gate/inspect_gate.py",
    label:
      "Offline objective and gate inspector for a constructed candidate set",
    content: generationGateInspector,
  },
  {
    lab: "generation-gate",
    path: "labs/generation_gate/objective.json",
    label: "Frozen design objective with its five declared parts",
    content: generationObjective,
  },
  {
    lab: "generation-gate",
    path: "labs/generation_gate/candidates.json",
    label:
      "Twenty constructed candidates, each labelled with the gate it exercises",
    content: generationCandidates,
  },
  {
    lab: "counterevidence-dossier",
    path: "labs/counterevidence/inspect_dossier.py",
    label: "Offline counterevidence inspector for the completed lab artifacts",
    content: counterevidenceInspector,
  },
  {
    lab: "cofolding-claims",
    path: "labs/cofolding_claims/inspect_claims.py",
    label:
      "Offline claim inspector for the registered structure and affinity systems",
    content: cofoldingClaimInspector,
  },
  {
    lab: "cofolding-claims",
    path: "labs/cofolding_claims/claim-records.json",
    label: "Frozen registry extract of the twenty-four structure-family records",
    content: cofoldingClaimRecords,
  },
  {
    lab: "cofolding-claims",
    path: "labs/cofolding_claims/export_claim_records.py",
    label: "Regenerates the extract from the published registry",
    content: cofoldingClaimExporter,
  },
  {
    lab: "pool-budget-contract",
    path: "labs/pool_budget/inspect_contract.py",
    label: "Offline contract inspector for the frozen pool-budget campaign",
    content: poolBudgetContractInspector,
  },
  {
    lab: "pool-budget-contract",
    path: "labs/pool_budget/real-protocol.json",
    label: "Frozen retrospective pool-budget protocol",
    content: poolBudgetRealProtocol,
  },
  {
    lab: "rmd17-contract",
    path: "labs/rmd17_system_state/inspect_contract.py",
    label: "Offline contract inspector for the frozen rMD17 lab",
    content: rmd17ContractInspector,
  },
  {
    lab: "rmd17-contract",
    path: "labs/rmd17_system_state/protocol.json",
    label: "Frozen rMD17 system-state protocol",
    content: rmd17ContractProtocol,
  },
  {
    lab: "chembl-contract",
    path: "labs/chembl_egfr/inspect_contract.py",
    label: "Offline contract inspector for the frozen ChEMBL EGFR lab",
    content: chemblContractInspector,
  },
  {
    lab: "chembl-contract",
    path: "labs/chembl_egfr/protocol.json",
    label: "Frozen ChEMBL 37 EGFR protocol",
    content: chemblProtocol,
  },
  {
    lab: "paperqa-local",
    path: "labs/paperqa_local/paperqa_local_tutorial.ipynb",
    label: "English local-paper evidence notebook",
    content: paperqaNotebook,
  },
  {
    lab: "paperqa-local",
    path: "labs/paperqa_local/paperqa_local_tutorial.zh-CN.ipynb",
    label: "Chinese local-paper evidence notebook",
    content: paperqaChineseNotebook,
  },
  {
    lab: "paperqa-local",
    path: "labs/paperqa_local/reviewed-example.json",
    label: "Observed answers, attributed texts and source-review notes",
    content: paperqaExample,
  },
  {
    lab: "local-agent-config",
    path: "configs/scientific-agents/paperqa-local.json",
    label: "Local-only PaperQA teaching profile",
    content: paperqaLocalProfile,
  },
  {
    lab: "local-agent-config",
    path: "scripts/agents/check_local_profile.py",
    label: "Dependency-free local profile checker",
    content: localProfileChecker,
  },
  {
    lab: "student-modelling",
    path: "labs/student_modelling/student_modelling_tutorial.ipynb",
    label: "English editable tutorial notebook",
    content: studentNotebook,
  },
  {
    lab: "student-modelling",
    path: "labs/student_modelling/student_modelling_tutorial.zh-CN.ipynb",
    label: "Chinese editable tutorial notebook",
    content: studentChineseNotebook,
  },
  {
    lab: "representation-inspector",
    path: "labs/molecule_representations/representation_inspector.ipynb",
    label: "English editable tutorial notebook",
    content: representationNotebook,
  },
  {
    lab: "representation-inspector",
    path: "labs/molecule_representations/representation_inspector.zh-CN.ipynb",
    label: "Chinese editable tutorial notebook",
    content: representationChineseNotebook,
  },
  {
    lab: "freesolv",
    path: "labs/freesolv/freesolv_honest_baselines.ipynb",
    label: "Read-only results notebook",
    content: freesolvNotebook,
  },
  {
    lab: "freesolv",
    path: "labs/freesolv/environment.txt",
    label: "Reference environment",
    content: freesolvEnvironment,
  },
  {
    lab: "freesolv",
    path: "labs/freesolv/reviewed-results.json",
    label: "Reviewed aggregate results",
    content: freesolvResults,
  },
  {
    lab: "chembl-egfr",
    path: "labs/chembl_egfr/protocol.json",
    label: "Frozen protocol",
    content: chemblProtocol,
  },
  {
    lab: "chembl-egfr",
    path: "labs/chembl_egfr/execution-amendment.json",
    label: "Execution amendment",
    content: chemblAmendment,
  },
  {
    lab: "chembl-egfr",
    path: "labs/chembl_egfr/locked-summary.json",
    label: "Completed primary and assay-replication results",
    content: chemblResults,
  },
  {
    lab: "rmd17",
    path: "labs/rmd17_system_state/protocol.json",
    label: "Frozen protocol",
    content: rmd17Protocol,
  },
  {
    lab: "rmd17",
    path: "labs/rmd17_system_state/development-summary.json",
    label: "Historical development snapshot",
    content: rmd17Development,
  },
  {
    lab: "rmd17",
    path: "labs/rmd17_system_state/locked-summary.json",
    label: "Completed paired-system results",
    content: rmd17Results,
  },
  {
    lab: "pool-budget",
    path: "labs/pool_budget/protocol.json",
    label: "Synthetic simulator protocol",
    content: poolProtocol,
  },
  {
    lab: "pool-budget",
    path: "labs/pool_budget/real-protocol.json",
    label: "Retrospective ChEMBL protocol",
    content: poolRealProtocol,
  },
  {
    lab: "pool-budget",
    path: "labs/pool_budget/demo-summary.json",
    label: "Synthetic simulator results",
    content: poolDemo,
  },
  {
    lab: "pool-budget",
    path: "labs/pool_budget/real-summary.json",
    label: "Completed retrospective results",
    content: poolResults,
  },
  {
    lab: "representation-inspector",
    path: "labs/molecule_representations/examples.csv",
    label: "Seven label-free input examples",
    content: representationExamples,
  },
  {
    lab: "lipophilicity-notebook",
    path: "labs/lipophilicity/lipophilicity_tutorial.ipynb",
    label: "English editable tutorial notebook",
    content: lipophilicityNotebook,
  },
  {
    lab: "lipophilicity-notebook",
    path: "labs/lipophilicity/lipophilicity_tutorial.zh-CN.ipynb",
    label: "Chinese editable tutorial notebook",
    content: lipophilicityChineseNotebook,
  },
] as const;
