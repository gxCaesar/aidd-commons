# 亲脂性：以 notebook 为入口的学生实战

[English canonical version](README.md)

这是[合成数据建模沙盒](../student_modelling/README.md)的真实数据续篇。
现已实现独立 notebook，包含数据检查、骨架划分、特征、训练选参、配对误差比较、绘图和导出。
两个语言版本已在全新本地内核上用 20 个分子的人工标签样例执行通过。
英文 notebook 另于 2026 年 9 月 9 日完成一次真实 4,200 行数据的本地 CPU 执行。
**尚未在真实 Colab 运行时验证。** 教学问题是：简单的
分子表示在 pH 7.4 的实测 logD 预测中如何比较，以及怎样解释误差而不回头修改测试协议。
本练习不宣称新方法、前瞻药物发现或 SOTA。

## 优先从 notebook 开始

下载[中文 notebook](lipophilicity_tutorial.zh-CN.ipynb)或[英文 notebook](lipophilicity_tutorial.ipynb)，
打开 [Google Colab](https://colab.research.google.com/)，登录后选择 **File → Upload notebook**。
保存自己的副本，选择 CPU 运行时。单个文件已包含依赖安装、数据下载与可见的核心函数，
无需另传 Python 文件、克隆仓库、提供 API key 或挂载 Drive。
目前没有已发布的仓库链接，因此提供的是上传入口，不是已经验证的一键 Colab 按钮。
临时运行时与资源限制见 [Colab 官方 FAQ](https://research.google.com/colaboratory/faq.html)。

本地 Jupyter 可使用项目环境：

```sh
uv sync --python 3.11
uv run jupyter lab labs/lipophilicity/lipophilicity_tutorial.zh-CN.ipynb
```

安装 cell 会在当前环境安装缺失或版本不匹配的固定依赖，本地请使用独立环境。
若旧版依赖已导入，需按提示重启内核。完整执行创建新的临时输出目录；重复导出 cell 会
更新该目录内的文件。断开运行时前，请下载 `summary.json`、`split-membership.csv`、
`test-predictions.csv` 和 `prediction-errors.png`，不会写入旧实验结果目录。

中英文版本的可执行 cell 完全一致。`tutorial.py` 保存经过测试的小函数，
`build_notebooks.py` 将其源码嵌入教学 cell，方便读者理解与修改。
维护者修改源码后重新生成两种语言版本：

```sh
uv run python labs/lipophilicity/build_notebooks.py
uv run pytest labs/tests/test_lipophilicity_tutorial.py labs/tests/test_lipophilicity_notebook.py -q
```

## 数据、版本与许可

原始来源为 AstraZeneca 的 [ChEMBL 数据存档 CHEMBL3301361](https://doi.org/10.6019/CHEMBL3301361)。
对应的 [CHEMBL3301363 测定](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL3301363.json)
记录摇瓶法测量的辛醇/水分配系数，pH 为 7.4，报告测定范围为 −1.5 至 4.5。
教学表使用 [DeepChem 2.8.0 loader](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/molnet/load_function/lipo_datasets.py)
指向的 `Lipophilicity.csv`，字段为 `CMPD_CHEMBLID`、`exp`、`smiles`。
`exp` 是 logD，不能解释成结合亲和力、pChEMBL、logP 或溶解度。

[ChEMBL 数据许可](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/LICENSE)
声明 CC BY-SA 3.0；使用时应注明原始数据存档和 MoleculeNet/DeepChem 整理来源。
本仓库代码许可不替代第三方数据许可。准备包只提供下载说明，不包含数据副本。

2026 年 9 月 9 日核实：下载文件为 0.283 MB，服务器报告的修改时间为
`Fri, 10 Jul 2020 06:42:23 GMT`。Loader 有版本标签，CSV 地址却不是不可变的
数据版本；请保留自己的带日期下载，不要在后续服务器更新时静默替换。
当前 ChEMBL API 对该测定也报告 4,200 条 activity，但本轮**未完成历史 CSV 与
当前 API 的逐条连接核验**，因此不能称它为某个新 ChEMBL 版本的导出。

## 运行

在仓库根目录，按[主 README](../../README.md)使用现有 Python 3.11 环境。
无需安装 DeepChem；检查器使用项目中固定版本的 RDKit。

```sh
uv sync --python 3.11
intake_dir=$(mktemp -d "${TMPDIR:-/tmp}/aidd-lipo.XXXXXX")
curl --fail --location --max-time 60 \
  https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/Lipophilicity.csv \
  --output "$intake_dir/Lipophilicity.csv"
uv run python labs/lipophilicity/inspect_data.py "$intake_dir/Lipophilicity.csv"
uv run pytest labs/tests/test_lipophilicity_intake.py -q
```

保留自己的下载命令与工作目录。检查器只读取指定 CSV 并输出 JSON，不联网、不写文件、
不删行、不划分数据、不构造训练特征，也不拟合模型。缺字段、重复化合物 ID、无效结构、
非有限标签或空数据都会明确失败。相同 canonical SMILES 会被计数，不会自动合并标签。

## 实际检查结果

使用上述下载文件及 RDKit 2025.09.6，观察到：

| 项目                             |          结果 |
| -------------------------------- | ------------: |
| 数据行 / 唯一 ChEMBL ID          | 4,200 / 4,200 |
| 唯一 canonical isomeric SMILES   |         4,200 |
| 重复 canonical 结构组            |             0 |
| 非空、非手性 Bemis–Murcko 骨架组 |         2,407 |
| 最大非空骨架组                   |         76 行 |
| 空骨架的无环分子                 |             5 |
| 多组分结构                       |             1 |
| 标签范围                         |   −1.5 至 4.5 |

4,200 行不等于 4,200 次独立实验重复。相似化合物共享化学特征与测定条件；CSV 没有
重复测量、批次或实验不确定性字段。canonical SMILES 不同也不能证明母体、互变异构体
或质子化状态完全独立。

多组分记录 `CHEMBL3545252` 含三个独立水片段，检查阶段原样保留。
去除片段会改变表示，必须明确列为预处理选择。另有 1 条 −1.5 和 4 条 4.5 的记录。
CSV 不含不等号或测定限定字段，抽查的 ChEMBL 端点记录 relation 为 null；这不能证明
端点是未截尾的精确测量。保留并报告限制，不根据后续预测误差删掉它们。

## 已实现的教学协议

以下为 notebook 默认设置。人工标签样例验证的是工程流程，不是实测任务上的模型性能。

1. **问题与样本。** 比较训练中未出现骨架的分子预测。主练习保留原始标签、结构及多组分
   记录，不去盐、不合并互变异构体、不裁剪标签、不按误差排除样本。
2. **划分。** 复现 [DeepChem 2.8.0 `ScaffoldSplitter`](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/splits/splitters.py) 的非手性骨架与确定性分组排序，
   按原 CSV 行序请求 0.8/0.1/0.1。全部空骨架记录留在同一组。实际行数比例可因整组
   分配而偏离；拟合前保存划分并验证 ID、相同结构与骨架不跨集合。只实现一个同名
   splitter 不等于复现原 recipe。
3. **基线。** 训练均值；八描述符 Ridge（`MolWt`、`MolLogP`、`TPSA`、`NumHDonors`、
   `NumHAcceptors`、`RingCount`、`NumRotatableBonds`、`FractionCSP3`）；以及不含
   手性的 radius-2、2,048-bit Morgan Ridge。`MolLogP` 仅作为特征，不是 logD 的物理
   预测值。预处理仅在训练集拟合；描述符中心化并缩放，bit 特征按训练方差缩放但不中心化。
   因此比较包含这些预处理差异，不是单独识别表示作用的因果消融。
4. **选择。** 两种 Ridge 各比较 alpha `[0.1, 1, 10, 100]`，按验证 RMSE 选择，同分选
   较大 alpha。使用现有 scikit-learn，`solver="lsqr"`、`tol=1e-6`、
   `max_iter=10000` 并保留截距。选中后不合并 train/validation 重训；不收敛必须报告。
5. **评估。** RMSE 为主，MAE 为辅，单位均为 logD。选择完成后测试一次，所有方法使用
   相同测试分子。使用整组测试骨架重采样，不把重复运行当作新增样本。
   种子 20260909，对 G 个组有放回抽取 G 次，共 2,000 轮，重新计算按分子加权的 RMSE 差。
   对两种 Ridge 各减训练均值，以及描述符减 Morgan，报告第 2.5/97.5 百分位区间。
   这是固定模型下、假设骨架组可交换的条件性区间，没有多重比较校正或显著性主张，也不覆盖
   训练集与测定变化。少于两个组时不估计区间，不静默丢弃行或组。
6. **误差解释。** 预先列出范围端点、被保留的多组分记录（若在测试中）、骨架组大小与
   训练近邻相似度等描述性检查。不能据此重新调参同一测试集；劣于常数预测也要报告。

这对应八次候选拟合和三种最终方法的评估，是有界的 CPU 教学练习，不是架构搜索。
下述本地执行不是受控的运行时间基准。不要调用现有冻结的 ChEMBL EGFR、FreeSolv、rMD17 或
pool-budget runner 来启动新实战。

## 范围判断与下一步

- **数据适配**：对本教学回归任务可行，4,200 行均同时具有结构、ID、标签；不能
  从此 CSV 获得批次独立性或跨测定验证。
- **已有工作**：预测任务本身已是公开 benchmark，不声称任务或方法新颖性，也未执行
  新方法的穷尽查新。
- **贡献定位**：AIDD Commons 教学基础设施，不是独立的顶会或 Nature 系科研成果。

## 本地 notebook 实测

2026 年 9 月 9 日，英文版 12 个代码单元在全新本地 Python 3.11 内核完成，使用固定依赖和
单线程 BLAS 配置。协议未改动：训练 3,360 行，验证 420 行，测试 420 行，无排除；
两种 Ridge 均按验证集选择 alpha 100。

| 方法         | 测试 RMSE | 测试 MAE |
| ------------ | --------: | -------: |
| 训练均值     |  1.122067 | 0.930171 |
| 描述符 Ridge |  0.976236 | 0.777160 |
| Morgan Ridge |  1.243239 | 0.940115 |

误差单位为 logD。这只是固定划分与配置的结果，不是分子表示的普遍排名。
Morgan Ridge 劣于常数基线；看到测试结果后未扩大 alpha 范围。测试骨架均为单分子组。
三个测试分子与训练分子的 2,048-bit Morgan 指纹完全相同，但 canonical 结构与骨架不同：
`CHEMBL1807872`、`CHEMBL1682822`、`CHEMBL1732699`。骨架隔离不保证表示隔离，
也不保证化学结构不相似。

运行器退出码为 0，全部单元具有执行编号，无单元错误。由导出预测重算的 RMSE、MAE
均一致；ID、canonical 结构、骨架隔离、标签对齐与仅用训练数据计算均值的检查通过。
预测图与分子 SVG 已生成并检查。代码单元时间戳跨度约 20 秒，含导入和绘图，不是纯训练耗时。
本地沙箱出现字体缓存警告，以及单元完成后的内核退出进程枚举权限错误；没有为此重跑。
本次未测量训练峰值内存，也未验证真实 Colab 执行或云端下载、安装路径。

当前 notebook 测试使用 20 个分子结构与人工标签，在全新内核执行两个语言版本，并确认
修改测试标签不改变验证选参和预测，但改变误差。这不是第二份实验结果。
真实 Colab 验证与对外发布仍是后续独立步骤。
