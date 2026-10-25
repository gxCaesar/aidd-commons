# 学生建模沙盒

这是一个独立的合成教学练习。十个实体、连续 `response` 和二元 `hit` 标签均为编造数据，
不是分子、测定结果、QSAR 证据或生物学证据。

## 可上传的 notebook

- [英文 notebook](student_modelling_tutorial.ipynb)
- [中文 notebook](student_modelling_tutorial.zh-CN.ipynb)

下载其中一个文件后，在 [Google Colab](https://colab.research.google.com/) 选择
**File → Upload notebook**。使用 CPU 即可；不需要安装包、网络、GPU、API key 或 Drive 挂载。
从上到下运行 cells。JSON 报告和已拟合模型 SVG 写在当前运行时中新建的临时文件夹；如果要保留，请自行下载。

notebook 将经过测试的纯函数直接放入各 cell，并将训练/验证/测试 protocol 展开显示。它不会
调用本仓库 CLI，也不会写入作者的实验目录或覆盖已有报告。

回归使用训练集的 ridge 候选（alpha 为 0、1、10），按验证 MAE 选择；分类使用 500 次固定的
full-batch logistic 更新，按验证 log loss 选择。测试集只在选择后评分，且不会把验证行加入重拟合。
最后两个记录故意包含外推与矛盾标签，所以较差的测试结果是教学用的预测失败，而不是经验性结论。

要从源文件重新生成这两个干净 notebook：

```sh
.venv/bin/python labs/student_modelling/build_notebooks.py
```
