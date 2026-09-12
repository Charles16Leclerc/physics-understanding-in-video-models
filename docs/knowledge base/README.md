# State–Prediction–Judgment 研究知识库

这是本项目的长期维护型研究知识库。它不是一份“当前方案摘要”，而是用于完整保存研究的：

- 当前成立的理论与实验设计；
- 被修改、被否决或暂时搁置的想法；
- 关键 related work 与方法来源；
- benchmark / probe / causal intervention 的技术细节；
- 工程实现、算力规划与实验记录；
- 后续每周进展、实验结果与设计变更。

本知识库面向三类使用场景：

1. **研究者本人 / Obsidian**：作为长期项目笔记与研究决策记录；
2. **Codex / 服务器代码代理**：在执行实验时可直接读取设计、写入日志、同步 Git；
3. **ChatGPT / 后续分析**：当实验结果产生后，可基于同一套文档继续讨论、分析与更新设计。

## 当前工作标题

> **From State to Prediction and Judgment: Dissecting Physical Reasoning across Predictive Video Models and Video-Language Models**

之所以使用 **and** 而不是原来的 `to`，是因为当前理论不再假设所有模型都遵循统一的 `State → Prediction → Judgment` 因果链。见 [[03_Theory_State_Prediction_Judgment|理论框架：State、Prediction 与 Judgment]]。

## 文档导航

从 [[00_HOME|Home]] 开始。

核心文档：

- [[01_Project_Overview|项目概述]]
- [[02_Motivation_and_Research_Questions|研究动机与科学问题]]
- [[03_Theory_State_Prediction_Judgment|理论框架：State、Prediction 与 Judgment]]
- [[04_Model_Scope_and_Architectures|研究对象、模型与架构]]
- [[05_Benchmark_and_Dataset_Design|统一 Benchmark / 数据集设计]]
- [[06_Probe_and_Readout_Design|Probe / Readout 设计]]
- [[07_Mechanistic_Interpretability_and_Causal_Intervention|Mechanistic Interpretability 与因果干预]]
- [[08_Experiment_Plan_and_Evaluation|实验计划与评测]]
- [[09_Engineering_Compute_and_Code_Architecture|工程、算力与代码架构]]
- [[10_Related_Work|Related Work]]
- [[11_Decision_Log_and_Idea_Evolution|研究决策日志与想法演化]]

维护规则见 [[18_Knowledge_Base_Maintenance|知识库维护规范]]。

## 状态标记约定

文档中统一使用以下标签：

- **Current**：当前采用的正式设计或判断；
- **Tentative**：当前倾向采用，但尚未由实验或工程验证；
- **Open Question**：尚未解决的问题；
- **Rejected**：明确不作为当前主方案；
- **Superseded**：曾经采用，但已被新的理论或设计取代；
- **Invalidated**：被实验事实或后续分析证伪。

原则：**不静默删除有价值的历史设计。**旧方案失效时保留原文，并标记为什么失效、由什么新设计取代。
