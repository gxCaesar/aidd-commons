"""Build standalone English and Chinese notebooks for the synthetic student lab."""

# Long multilingual teaching and SVG literals are embedded verbatim.
# ruff: noqa: E501

from inspect import getsource
from pathlib import Path
from textwrap import dedent

import nbformat
import run_lab

ROOT = Path(__file__).parent
PURE_FUNCTIONS = (
    run_lab.teaching_rows,
    run_lab.mean,
    run_lab.fit_ridge,
    run_lab.sigmoid,
    run_lab.fit_logistic,
    run_lab.predict_logistic,
    run_lab.log_loss,
    run_lab.classification_metrics,
    run_lab.regression_metrics,
    run_lab.fit_stump,
    run_lab.predict_stump,
)


def source_for(*functions):
    """Embed the tested, dependency-free function definitions verbatim."""
    return "\n\n".join(getsource(function).strip() for function in functions)


def unfolded_protocol():
    """Expose the canonical run body, with its top-level result named for a notebook."""
    body = "\n".join(dedent(getsource(run_lab.run)).splitlines()[1:])
    return dedent(body).replace("return {", "student_report = {", 1)


def protocol_fragments():
    """Split the canonical run body at its existing teaching-stage boundaries."""
    body = unfolded_protocol()
    candidate_start = body.index("candidates, validation_scores = {}, []")
    selection_start = body.index("# Tuple ordering fixes ties")
    optimiser_start = body.index("# With the configuration chosen, vary only the optimiser.")
    evaluation_start = body.index('test_x = [row["feature"] for row in test]')
    return (
        body[:candidate_start].rstrip(),
        body[candidate_start:selection_start].rstrip(),
        body[selection_start:optimiser_start].rstrip(),
        body[optimiser_start:evaluation_start].rstrip(),
        body[evaluation_start:].rstrip(),
    )


def build(language):
    cells = []

    def section(key, english, chinese, code=None, tags=()):
        cells.append(
            nbformat.v4.new_markdown_cell(
                dedent(chinese if language == "zh" else english).strip(), id=f"{key}-text"
            )
        )
        if code is not None:
            cells.append(
                nbformat.v4.new_code_cell(
                    dedent(code).strip(), id=f"{key}-code", metadata={"tags": list(tags)}
                )
            )

    section(
        "welcome",
        """
        # Student modelling sandbox

        This is a **standalone, editable synthetic exercise**. Its ten entities,
        continuous response, and binary `hit` target are invented. They are not
        molecules, assays, QSAR evidence, or biological evidence.

        **Question.** How do fitting, validation-based selection, and held-out
        error analysis fit together without allowing test labels to choose a model?
        You need basic Python plus the idea of train/validation/test partitions.

        **Colab upload.** Download this file, open
        [Google Colab](https://colab.research.google.com/), choose **File → Upload
        notebook**, and select it. CPU is enough; there is no package installation,
        API key, network request, GPU, or Drive mount. Run cells from top to bottom.
        The report is written to a fresh temporary folder in the current runtime;
        download it yourself if you want to retain it.
        """,
        """
        # 学生建模沙盒

        这是一个**可独立运行、可编辑的合成教学练习**。十个实体、连续 `response` 与二元 `hit`
        标签均为编造数据，不是分子、实验测定、QSAR 证据或生物学证据。

        **问题。** 如何把拟合、基于验证集的选择，以及留出集误差分析连起来，同时不让测试标签
        参与模型选择？需要基础 Python，以及训练/验证/测试划分的概念。

        **上传 Colab。** 下载此文件，打开 [Google Colab](https://colab.research.google.com/)，选择
        **File → Upload notebook** 后选中该文件。CPU 足够；无需安装软件包、API key、网络请求、GPU
        或 Drive 挂载。请从上到下运行。报告写入当前运行时中的新临时文件夹；如需保留，请自行下载。
        """,
    )
    section(
        "setup",
        """
        ## 1. Imports and a fresh output folder

        These are Python standard-library modules and the `IPython.display` helper
        already included with Jupyter and Colab. `mkdtemp` creates a new directory
        beneath the current working directory. The notebook does not replace an
        earlier report or alter author result files.
        """,
        """
        ## 1. 导入与新输出文件夹

        这里仅使用 Python 标准库，以及 Jupyter 和 Colab 自带的 `IPython.display`。`mkdtemp`
        会在当前工作目录下创建新目录。本 notebook 不会覆盖之前的报告，也不会改动作者结果文件。
        """,
        """
        import json
        import math
        import tempfile
        from pathlib import Path

        from IPython.display import HTML, SVG, display

        OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="student-modelling-", dir=Path.cwd()))
        print("Fresh student output:", OUTPUT_DIR)
        """,
    )
    section(
        "rows",
        """
        ## 2. Inspect the constructed records before fitting

        Each `entity_id` is unique. The scalar `feature` is deliberately not a
        molecular descriptor. The last two records form the test partition: one is
        extrapolation and one contradicts the training line. Change a **copy** only
        after you predict which quantities should change.
        """,
        """
        ## 2. 拟合前检查构造数据

        每个 `entity_id` 都唯一。这个标量 `feature` 特意不是分子描述符。最后两个记录构成测试划分：
        一个是外推，另一个与训练直线矛盾。只有在先预测哪些量应改变后，才修改一个**副本**。
        """,
        source_for(run_lab.teaching_rows) + "\n\nrows = teaching_rows()\nrows",
        tags=("rows",),
    )
    section(
        "mechanics",
        """
        ## 3. Exact fitting and scoring mechanics

        Read these short pure functions before the protocol cell. Ridge minimizes
        sum of squared residuals plus `alpha * slope²`; its intercept is free.
        Logistic fitting uses 500 fixed full-batch steps on mean cross-entropy plus
        `alpha * slope² / 2`, after training-only standardization. A probability is
        clipped only while calculating log loss. These are instructional mechanics,
        not an assay model or a convergence guarantee.
        """,
        """
        ## 3. 精确的拟合与评分机制

        先阅读这些简短纯函数，再看 protocol cell。Ridge 最小化残差平方和加 `alpha * slope²`，截距
        不受惩罚。Logistic 在仅用训练集标准化后，对平均交叉熵加 `alpha * slope² / 2` 做 500 次固定
        全批量更新。概率仅在计算 log loss 时被截断。这些是教学机制，不是测定模型，也不保证收敛。
        """,
        source_for(*PURE_FUNCTIONS[1:]),
    )
    partition, candidates, selection, optimiser, evaluation = protocol_fragments()
    section(
        "partition",
        """
        ## 4. Validate and partition before fitting

        This is the first visible fragment of the canonical protocol, not a call to
        a runner. It rejects duplicate IDs, invalid splits and invalid labels before
        extracting training and validation values. No test target is read here.
        """,
        """
        ## 4. 拟合前验证与划分

        这是规范 protocol 的第一个可见片段，而不是调用 runner。它在提取训练和验证值之前拒绝重复 ID、
        无效划分和无效标签。此处不读取测试目标。
        """,
        partition + "\n\nprint({name: len(values) for name, values in partitions.items()})",
    )
    section(
        "candidates",
        """
        ## 5. Fit candidate models using training records only

        Two families are fitted here on the same training records. The first is
        linear: ridge for the response and logistic for the constructed hit, over
        three penalties. The second is the smallest member of the tree family, a
        stump that picks one threshold and predicts a constant on each side, over
        three minimum leaf sizes.

        The penalty and the leaf size play the same role. Each one constrains how
        much the family may bend to the training records. What differs between the
        families is not their tuning but their assumption about the shape of the
        relationship, which is the choice this section exists to expose. Neither
        loop inspects a test label.
        """,
        """
        ## 5. 只用训练记录拟合候选模型

        这里在**同一批训练记录**上拟合两个族。第一个是线性族：对响应用 ridge、对构造的 hit 用
        logistic，各跑三个惩罚。第二个是树族中最小的成员——决策桩：选一个阈值，在两侧各预测一个常数，
        跑三个最小叶大小。

        惩罚与叶大小扮演同一个角色：都在约束该族可以多大程度地迁就训练记录。两个族真正不同的
        不是调参，而是它们**对关系形状的假设**——这正是本节要暴露的选择。两个循环都不查看测试标签。
        """,
        candidates,
    )
    section(
        "selection",
        """
        ## 6. Inspect validation scores, then select

        Run and inspect this cell before the next one. It selects lower validation
        MAE for regression and lower validation log loss for classification; exact
        ties use lower alpha. The same rule then selects the stump's leaf size, so
        the two families are chosen under one procedure and differ only in what
        they assume. The displayed table is deliberately available before any test
        scoring.

        Read the stump table before moving on. All three leaf sizes produce the
        same threshold and the same validation MAE here, so the grid decided
        nothing and the tie rule picked the least constrained candidate. A grid
        that cannot separate its candidates is a fact about this dataset, not a
        reason to widen the grid until something wins.
        """,
        """
        ## 6. 先检查验证分数，再选择

        先运行并检查这个 cell，再运行下一个。它为回归选择较低验证 MAE，为分类选择较低验证 log loss；
        完全并列时选较小 alpha。**同一条规则**随后用于选择决策桩的叶大小，因此两个族在同一套程序下
        被选出，差别只在于各自的假设。该表特意在任何测试评分之前展示。

        继续之前请先读决策桩那张表。这里三个叶大小给出**相同的阈值与相同的验证 MAE**，
        所以这个网格什么也没决定，是并列规则选走了约束最少的那个候选。
        **一个分不开候选的网格，是关于这份数据的事实，不是把网格加宽到有人胜出的理由。**
        """,
        selection
        + "\n\ndisplay(HTML('<pre>' + json.dumps(validation_scores, indent=2) + '</pre>'))",
    )
    section(
        "optimiser",
        """
        ## 7. Measure what the optimiser alone contributes

        The configuration is now fixed. This cell changes nothing about the data,
        the penalty or the selection rule, and varies only the search: three
        declared starting points crossed with three step budgets. There is no
        randomness, so every difference below comes from the optimisation and not
        from a seed.

        Read the budget table first. Compute is counted as gradient evaluations,
        the step budget times the six training records, and the two questions asked
        of each budget are whether the three starting points agree on the
        **decision** at the 0.5 threshold, and how far apart their probabilities
        still are.

        The spread across starting points is not a confidence interval. It measures
        how far the search has travelled, not how much the six records constrain
        the answer. A well-converged optimiser with badly insufficient data would
        show a small spread and still be uncertain.
        """,
        """
        ## 7. 只测量优化过程本身贡献了什么

        配置已经固定。本 cell 不改变数据、惩罚或选择规则，只改变搜索本身：三个写明的起始点
        与三个步数预算的交叉。**过程中没有任何随机性**，因此下面的差异全部来自优化，而不是种子。

        先读预算表。算力按**梯度评估次数**计（步数乘以六条训练记录），对每个预算问两个问题：
        三个起始点在 0.5 阈值上是否给出相同的**决策**，以及它们的概率还相差多远。

        起始点之间的跨度**不是置信区间**。它度量的是搜索走了多远，而不是这六条记录把答案约束得
        多紧。一个收敛良好但数据严重不足的优化过程，跨度会很小，却依然不确定。
        """,
        optimiser + "\n\ndisplay(HTML('<pre>' + json.dumps(budget_summary, indent=2) + '</pre>'))",
    )
    section(
        "evaluation",
        """
        ## 8. Score the held-out records once

        Only after selection does this final canonical fragment read the test
        records, produce predictions and calculate errors. It does not refit with
        validation rows. Read the report and avoid using these values to change the
        already selected recipe.
        """,
        """
        ## 8. 仅一次评分留出记录

        仅在选择之后，这个最终规范片段才读取测试记录、产生预测并计算误差。它不使用验证行重新拟合。
        请阅读报告，避免用这些值改动已经选择的 recipe。
        """,
        evaluation + "\n\ndisplay(HTML('<pre>' + json.dumps(student_report, indent=2) + '</pre>'))",
    )
    section(
        "plot",
        """
        ## 9. Plot what was actually fitted

        The SVG below is made directly from the selected models and the current
        records. Circles show continuous responses by partition; the dark line is
        the selected ridge prediction. The response axis includes the whole drawn
        extrapolation. Bars show selected logistic probabilities and a 0.5 reference.
        This is a small visual check, not a claim of model quality.
        """,
        """
        ## 9. 绘制实际拟合的结果

        下方 SVG 直接由当前记录和所选模型生成。圆点按划分显示连续 response；深色直线是所选 ridge
        预测。response 坐标轴包含整条已绘制外推线。柱形显示所选 logistic 概率与 0.5 参考线。
        这只是一个小型可视化检查，不代表模型质量结论。
        """,
        """
        width, height, left, bottom = 820, 430, 70, 330
        features = [row["feature"] for row in rows]
        responses = [row["response"] for row in rows]
        x_min, x_max = min(features) - 0.5, max(features) + 0.5
        intercept, slope = student_report["models"]["regression"]
        displayed_predictions = [intercept + slope * value for value in (x_min, x_max)]
        y_min = math.floor(min(*responses, *displayed_predictions) - 1)
        y_max = math.ceil(max(*responses, *displayed_predictions) + 1)
        def x_to_px(value):
            return left + (value - x_min) / (x_max - x_min) * 290

        def y_to_px(value):
            return bottom - (value - y_min) / (y_max - y_min) * 250
        colors = {"train": "#2563eb", "validation": "#d97706", "test": "#dc2626"}
        line = " ".join(
            f"{x_to_px(value):.1f},{y_to_px(intercept + slope * value):.1f}"
            for value in (x_min, x_max)
        )
        circles = "".join(
            f'<circle cx="{x_to_px(row["feature"]):.1f}" cy="{y_to_px(row["response"]):.1f}" r="5" fill="{colors[row["split"]]}"/>'
            for row in rows
        )
        probabilities = predict_logistic(
            student_report["models"]["classification"], features
        )
        probability_left, probability_top, probability_bottom = 470, 80, bottom
        def probability_to_px(value):
            return probability_bottom - value * (probability_bottom - probability_top)
        bars = "".join(
            f'<rect x="{probability_left + 20 + index * 25}" y="{probability_to_px(probability):.1f}" width="15" height="{probability_bottom - probability_to_px(probability):.1f}" fill="#7c3aed"/>'
            for index, probability in enumerate(probabilities)
        )
        response_ticks = "".join(
            f'<line x1="{left - 4}" y1="{y_to_px(value):.1f}" x2="{left}" y2="{y_to_px(value):.1f}" stroke="black"/><text x="{left - 9}" y="{y_to_px(value) + 4:.1f}" text-anchor="end" font-size="11">{value}</text>'
            for value in range(y_min, y_max + 1, 2)
        )
        feature_ticks = "".join(
            f'<text x="{x_to_px(value):.1f}" y="{bottom + 18}" text-anchor="middle" font-size="11">{value}</text>'
            for value in range(math.ceil(x_min), math.floor(x_max) + 1)
        )
        probability_ticks = "".join(
            f'<text x="{probability_left - 9}" y="{probability_to_px(value) + 4:.1f}" text-anchor="end" font-size="11">{value:.1f}</text>'
            for value in (0.0, 0.5, 1.0)
        )
        entity_labels = "".join(
            f'<text x="{probability_left + 28 + index * 25}" y="{bottom + 18}" text-anchor="end" font-size="9" transform="rotate(-55 {probability_left + 28 + index * 25} {bottom + 18})">{row["entity_id"]}</text>'
            for index, row in enumerate(rows)
        )
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <rect width="100%" height="100%" fill="white"/><text x="70" y="25" font-size="15">Ridge response (left) and logistic probability (right)</text>
        <line x1="{left}" y1="{bottom}" x2="{left + 290}" y2="{bottom}" stroke="black"/><line x1="{left}" y1="{probability_top}" x2="{left}" y2="{bottom}" stroke="black"/>{response_ticks}{feature_ticks}<polyline points="{line}" fill="none" stroke="#111827" stroke-width="2"/>{circles}
        <text x="{left + 145}" y="{bottom + 40}" text-anchor="middle" font-size="12">synthetic feature</text><text x="18" y="205" font-size="12" transform="rotate(-90 18 205)">constructed response</text>
        <circle cx="80" cy="55" r="5" fill="#2563eb"/><text x="90" y="59" font-size="11">train</text><circle cx="145" cy="55" r="5" fill="#d97706"/><text x="155" y="59" font-size="11">validation</text><circle cx="245" cy="55" r="5" fill="#dc2626"/><text x="255" y="59" font-size="11">test</text><line x1="305" y1="55" x2="325" y2="55" stroke="#111827" stroke-width="2"/><text x="332" y="59" font-size="11">selected ridge</text>
        <line x1="{probability_left}" y1="{bottom}" x2="760" y2="{bottom}" stroke="black"/><line x1="{probability_left}" y1="{probability_top}" x2="{probability_left}" y2="{bottom}" stroke="black"/>{probability_ticks}<line x1="{probability_left}" y1="{probability_to_px(0.5):.1f}" x2="760" y2="{probability_to_px(0.5):.1f}" stroke="#6b7280" stroke-dasharray="4 3"/><text x="615" y="65" text-anchor="middle" font-size="11">decision threshold = 0.5</text>{bars}{entity_labels}
        <text x="615" y="{bottom + 72}" text-anchor="middle" font-size="12">constructed entity ID</text><text x="428" y="205" font-size="12" transform="rotate(-90 428 205)">hit probability (0 to 1)</text></svg>'''
        svg_path = OUTPUT_DIR / "fitted_models.svg"
        with svg_path.open("x", encoding="utf-8") as handle:
            handle.write(svg)
        display(SVG(svg))
        """,
    )
    section(
        "failure-comparison",
        """
        ## 10. Read the constructed predictive failure against baselines

        Lower MAE and log loss are better. On these intentionally contradictory
        held-out labels, selected ridge has a worse MAE than the training-mean
        baseline. Logistic has the same thresholded accuracy as prevalence, but a
        much worse log loss because it assigns a very confident probability to the
        negative test entity. These are observed toy outputs, not evidence about
        real molecular prediction.

        The stump reaches a much lower test MAE than either the linear model or the
        constant. Read why before reading it as a win. The test features lie beyond
        every training feature, and the constructed responses turn over there. A
        linear model must extrapolate, so a slope fitted on the rising training
        records carries it far past the true values. A stump cannot extrapolate at
        all: outside the training range it repeats a leaf constant, and here that
        refusal happens to land close to the held-out responses.

        That is an argument about assumptions and a data regime, not about tree
        methods being stronger. Two test entities cannot establish which family is
        better, and a stump that had landed on the wrong side of its threshold
        would have looked equally decisive in the other direction.
        """,
        """
        ## 10. 相对于基线阅读构造的预测失败

        较低的 MAE 和 log loss 更好。在这些特意矛盾的留出标签上，所选 ridge 的 MAE 比训练均值基线
        更差。Logistic 与 prevalence 的阈值化 accuracy 相同，但 logistic 对阴性测试实体给出极高置信度，
        因而 log loss 更差。这些是观察到的 toy 输出，不是对真实分子预测的证据。

        决策桩的测试 MAE 远低于线性模型，也低于常数。**在把它读成"胜利"之前，先读清楚原因。**
        测试特征位于全部训练特征之外，而构造的响应在那里发生了转折。线性模型必须外推，
        于是在上升的训练记录上拟合出的斜率把它带得远超真实值。决策桩则**根本无法外推**：
        在训练范围之外它只会重复一个叶常数，而这里这种"拒绝外推"恰好落在留出响应附近。

        这是关于**假设与数据规模**的论证，不是"树方法更强"的论证。两个测试实体不足以确定哪个族更好；
        若决策桩落在阈值的另一侧，它同样会显得很有说服力，只是方向相反。
        """,
        """
        ridge_mae = student_report["test_metrics"]["ridge"]["mae"]
        stump_mae = student_report["test_metrics"]["stump"]["mae"]
        mean_mae = student_report["test_metrics"]["train_mean"]["mae"]
        logistic_loss = student_report["test_metrics"]["logistic"]["log_loss"]
        prevalence_loss = student_report["test_metrics"]["train_prevalence"]["log_loss"]
        threshold, left, right = student_report["models"]["stump"]
        display(HTML(
            f"<p><b>Observed constructed comparison:</b> ridge MAE = {ridge_mae:.3f} "
            f"versus stump MAE = {stump_mae:.3f} versus training-mean MAE = {mean_mae:.3f}; "
            f"logistic log loss = {logistic_loss:.3f} versus prevalence log loss = "
            f"{prevalence_loss:.3f}.</p>"
            f"<p>The selected stump splits at {threshold} and predicts {left} below it and "
            f"{right} at or above it, so every test feature receives {right} no matter how "
            f"far outside the training range it lies. That is the assumption, not a fit.</p>"
        ))
        """,
    )
    section(
        "export",
        """
        ## 11. Save your observed synthetic result

        The exclusive-create mode (`"x"`) would reject an existing target. Here the
        parent was freshly made in step 1, so a re-run from the top makes a separate
        report folder. The JSON is a record of this constructed exercise only.
        """,
        """
        ## 11. 保存你观察到的合成结果

        独占创建模式（`"x"`）会拒绝已有目标。第 1 步创建了全新父目录，因此从头重跑会产生单独的
        报告文件夹。该 JSON 只记录这个构造练习。
        """,
        """
        report_path = OUTPUT_DIR / "student_report.json"
        with report_path.open("x", encoding="utf-8") as handle:
            json.dump(student_report, handle, indent=2, allow_nan=False)
            handle.write("\\n")
        print("Saved:", report_path)
        """,
    )
    section(
        "exercises",
        """
        ## 12. Independent exercises, then answers

        1. Add 100 to both **test** responses. Which candidates, selections, and
           predictions must stay unchanged? Which output changes?
        2. Replace both validation responses with 6. Which fitted candidates stay
           unchanged, and which regression alpha should selection favor?
        3. Duplicate an entity ID. Should fitting start?
        4. Why can thresholded accuracy match while logistic and prevalence log loss
           differ strongly?
        5. The stump beat both the linear model and the constant on these test
           records. Name the property of the two families that produced the
           difference, and say what would have to change about the **records**, not
           the models, for the linear family to win instead.
        6. Going from 50 to 200 steps costs 900 further gradient evaluations and
           changes the decision agreement. Going from 200 to 500 costs 1800 more
           and does not. What should that pattern change about how you report the
           result, and why is the remaining probability spread still not an
           uncertainty estimate?

        **Answers.** (1) Candidate parameters, selection, and predictions remain
        fixed; residuals and regression test errors change. (2) Candidates stay
        fixed; alpha 10 is closest to 6. (3) Validation rejects duplicate IDs before
        fitting. (4) Accuracy discards confidence; a confident wrong probability is
        heavily penalized by log loss. (5) The linear family extrapolates and the
        stump does not: beyond the training range the stump repeats a leaf constant
        while the fitted slope keeps rising. The constructed responses turn over
        outside the training features, so refusing to extrapolate lands closer. Put
        the test features inside the training range, or make the response continue
        rising through them, and the ordering reverses. The families were selected
        under one procedure, so the difference is the assumption, not the tuning.
        (6) The cheaper budget already fixes the decision, so the extra compute buys
        agreement in a quantity nobody acts on. Report the budget at which the
        decision stopped moving and state it as part of the recipe, rather than
        quoting the largest budget as though it were required. The remaining spread
        is a distance between three searches on identical data, so it can shrink to
        nothing while the six records still fail to determine the answer. An
        estimate of that would have to come from the data, not from the optimiser.
        None of these toy outcomes supports a claim about unseen molecules or
        biology, and two test entities cannot rank model families.
        """,
        """
        ## 12. 独立练习，再看答案

        1. 给两个**测试** response 都加 100。哪些候选、选择和预测必须保持不变？哪些输出会改变？
        2. 将两个验证 response 都替换为 6。哪些已拟合候选不变？选择应偏向哪个回归 alpha？
        3. 复制一个实体 ID。拟合是否应开始？
        4. 为什么阈值化 accuracy 可以相同，而 logistic 与 prevalence 的 log loss 却显著不同？
        5. 决策桩在这些测试记录上同时胜过线性模型与常数。请指出**两个族的哪一个性质**造成了这个
           差异，并说明要让线性族反过来取胜，需要改变的是**记录**的什么（而不是模型的什么）。
        6. 从 50 步到 200 步多花 900 次梯度评估，并改变了决策一致性；从 200 步到 500 步多花
           1800 次，却没有改变它。这个模式应当改变你**如何报告结果**的哪一点？以及为什么剩下的
           概率跨度仍然不是不确定性估计？

        **答案。** (1) 候选参数、选择和预测不变；残差与回归测试误差会改变。(2) 候选不变；alpha 10
        最接近 6。(3) 输入检查会在拟合前拒绝重复 ID。(4) Accuracy 丢弃置信度；高置信度错误概率会受到
        log loss 的重罚。(5) 线性族会外推而决策桩不会：在训练范围之外，决策桩只重复一个叶常数，
        而拟合出的斜率会继续上升。构造的响应恰在训练特征之外发生转折，因此"拒绝外推"反而更接近。
        把测试特征放回训练范围之内，或让响应在其中继续上升，排序就会反转。两个族是在同一套程序下
        选出的，所以差异来自**假设**而不是调参。这些 toy 结果不支持关于未见分子或生物学的结论，
        (6) 更便宜的预算已经把决策定住了，因此多花的算力买到的是**没有人据以行动**的一致性。
        应当报告"决策不再变化的那个预算"并把它写进 recipe，而不是把最大预算当成必需值引用。
        剩下的跨度是三次搜索在**完全相同数据**上的距离，它可以缩到零，而那六条记录依然无法确定
        答案。对后者的估计只能来自数据，不能来自优化器。
        两个测试实体也不足以给模型族排序。
        """,
    )
    book = nbformat.v4.new_notebook(cells=cells)
    book.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    book.metadata.language_info = {"name": "python", "version": "3"}
    return book


def main():
    for language, suffix in (("en", ""), ("zh", ".zh-CN")):
        nbformat.write(build(language), ROOT / f"student_modelling_tutorial{suffix}.ipynb")


if __name__ == "__main__":
    main()
