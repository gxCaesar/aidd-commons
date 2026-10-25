export type LearningTrack = {
  entry: "Foundations" | "Research" | "Engineering";
  id: string;
  lesson: string;
  lessonTitle: string;
  summary: string;
  title: string;
  zhSummary: string;
  zhTitle: string;
};

export const learningTracks: LearningTrack[] = [
  {
    id: "foundations",
    lesson: "getting-started",
    lessonTitle: "Start with the AIDD pipeline",
    title: "Start here and orient",
    zhTitle: "起步、路径与术语",
    summary:
      "Choose a route, set up a working environment, and learn the shared vocabulary.",
    zhSummary: "选择学习路径，配置环境，并建立共同术语。",
    entry: "Foundations",
  },
  {
    id: "drug-discovery-foundations",
    lesson: "discovery-context",
    lessonTitle: "Drug discovery context",
    title: "Drug discovery foundations",
    zhTitle: "药物发现基础",
    summary:
      "Connect medicinal chemistry, structural biology, and experimental practice.",
    zhSummary: "连接药物化学、结构生物学与实验实践。",
    entry: "Foundations",
  },
  {
    id: "machine-learning",
    lesson: "scientific-computing",
    lessonTitle: "Scientific machine learning",
    title: "Machine learning and scientific computing",
    zhTitle: "机器学习与科学计算",
    summary:
      "Build the mathematical and geometric learning tools used across AIDD.",
    zhSummary: "建立贯穿 AIDD 的数学、几何学习与计算工具。",
    entry: "Foundations",
  },
  {
    id: "data-governance",
    lesson: "data-contracts",
    lessonTitle: "Data contracts and licences",
    title: "Data, licensing, and alignment",
    zhTitle: "数据、许可与实体对齐",
    summary:
      "Trace standards, licences, cleaning choices, and entity alignment.",
    zhSummary: "追踪标准、许可、清洗选择与实体对齐。",
    entry: "Foundations",
  },
  {
    id: "representations",
    lesson: "biological-representations",
    lessonTitle: "Biological representations",
    title: "Molecular and biological representations",
    zhTitle: "分子与生物表示",
    summary:
      "Compare molecular, protein, complex, omics, and graph representations.",
    zhSummary: "比较分子、蛋白、复合物、组学与图表示。",
    entry: "Foundations",
  },
  {
    id: "mechanism-targets",
    lesson: "disease-to-target",
    lessonTitle: "From disease mechanism to target",
    title: "Disease mechanism and target discovery",
    zhTitle: "疾病机制与靶点发现",
    summary:
      "Use causal and perturbational evidence to reason from disease to target.",
    zhSummary: "利用因果与扰动证据，从疾病机制推断靶点。",
    entry: "Research",
  },
  {
    id: "qsar-properties",
    lesson: "property-prediction",
    lessonTitle: "Property prediction",
    title: "QSAR and molecular properties",
    zhTitle: "QSAR 与分子性质",
    summary: "Set honest baselines for activity and property prediction.",
    zhSummary: "为活性和性质预测建立诚实基线。",
    entry: "Research",
  },
  {
    id: "admet-pk",
    lesson: "admet-evaluation",
    lessonTitle: "ADMET evaluation",
    title: "ADMET, DMPK, and PK/PD",
    zhTitle: "ADMET、DMPK 与 PK/PD",
    summary: "Evaluate exposure, toxicity, and pharmacokinetic evidence.",
    zhSummary: "评估暴露、毒性和药代动力学证据。",
    entry: "Research",
  },
  {
    id: "dti-screening",
    lesson: "screening-and-affinity",
    lessonTitle: "Screening and affinity",
    title: "DTI, affinity, and virtual screening",
    zhTitle: "DTI、亲和力与虚拟筛选",
    summary: "Design task-aware screening and repurposing comparisons.",
    zhSummary: "设计任务一致的筛选与药物再利用比较。",
    entry: "Research",
  },
  {
    id: "structure-and-pockets",
    lesson: "cofolding-frontier",
    lessonTitle: "Structure, pockets, and co-folding",
    title: "Structure prediction and pockets",
    zhTitle: "结构预测、口袋与共折叠",
    summary:
      "Read structure and co-folding claims alongside their openness evidence.",
    zhSummary: "结合开放性证据阅读结构与共折叠主张。",
    entry: "Research",
  },
  {
    id: "physics-based-modeling",
    lesson: "docking-to-fep",
    lessonTitle: "Docking through FEP",
    title: "Docking, dynamics, and physics",
    zhTitle: "对接、动力学与物理建模",
    summary: "Place docking, scoring, dynamics, and FEP in a matched protocol.",
    zhSummary: "在统一协议中定位对接、打分、动力学与 FEP。",
    entry: "Research",
  },
  {
    id: "molecular-generation",
    lesson: "generation-and-search",
    lessonTitle: "Generation and search",
    title: "Small-molecule generation",
    zhTitle: "小分子生成与搜索",
    summary:
      "Make multi-objective molecular generation and search decisions explicit.",
    zhSummary: "显式定义多目标分子生成与搜索决策。",
    entry: "Research",
  },
  {
    id: "biologics-design",
    lesson: "multimodal-design",
    lessonTitle: "Biologics and multimodal design",
    title: "Protein and multimodal design",
    zhTitle: "蛋白与多模态设计",
    summary:
      "Study protein, peptide, antibody, nucleic-acid, and multimodal design.",
    zhSummary: "学习蛋白、多肽、抗体、核酸与多模态设计。",
    entry: "Research",
  },
  {
    id: "synthesis-and-automation",
    lesson: "reaction-to-lab",
    lessonTitle: "Reaction prediction to the lab",
    title: "Synthesis and laboratory automation",
    zhTitle: "合成与实验室自动化",
    summary:
      "Connect retrosynthesis, synthesizability, and laboratory automation.",
    zhSummary: "连接逆合成、可合成性与实验室自动化。",
    entry: "Engineering",
  },
  {
    id: "active-learning",
    lesson: "dmta-loops",
    lessonTitle: "Design-make-test-analyze loops",
    title: "Active learning and optimization",
    zhTitle: "主动学习与优化",
    summary:
      "Run design-make-test-analyze loops with uncertainty-aware decisions.",
    zhSummary: "以不确定性意识运行设计、合成、测试、分析循环。",
    entry: "Engineering",
  },
  {
    id: "scientific-agents",
    lesson: "agents-and-tools",
    lessonTitle: "Scientific agents and tools",
    title: "Scientific language models and agents",
    zhTitle: "科学语言模型与智能体",
    summary: "Evaluate retrieval, tools, and agents against scientific tasks.",
    zhSummary: "针对科学任务评估检索、工具与智能体。",
    entry: "Engineering",
  },
  {
    id: "evaluation-and-reproducibility",
    lesson: "honest-evaluation",
    lessonTitle: "Honest evaluation",
    title: "Benchmarks and reproducibility",
    zhTitle: "基准与可复现性",
    summary:
      "Audit splits, uncertainty, leakage, and out-of-distribution evaluation.",
    zhSummary: "审查划分、不确定性、泄漏与分布外评估。",
    entry: "Engineering",
  },
  {
    id: "candidate-nomination",
    lesson: "capstone",
    lessonTitle: "Candidate nomination capstone",
    title: "Candidate nomination and capstone",
    zhTitle: "候选提名与综合项目",
    summary:
      "Integrate failure analysis, biosecurity, open science, and nomination.",
    zhSummary: "整合失败分析、生物安全、开放科学与候选提名。",
    entry: "Engineering",
  },
];
