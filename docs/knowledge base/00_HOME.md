---
title: Home
status: Current
updated: 2026-09-12
tags: [home, navigation]
---

# Home

这是本项目的 Obsidian 总导航页。

## 一、核心叙事

1. [[01_Project_Overview|项目概述]]：整项研究当前版本的完整但相对精炼的说明。
2. [[02_Motivation_and_Research_Questions|研究动机与科学问题]]：为什么“模型懂不懂物理”需要被拆开分析，我们真正要回答什么。
3. [[03_Theory_State_Prediction_Judgment|理论框架：State、Prediction 与 Judgment]]：architecture-conditioned 的核心理论。
4. [[04_Model_Scope_and_Architectures|研究对象、模型与架构]]：V-JEPA encoder/predictor、VLM vision tower/projector/LLM、模型选择与规模。

## 二、实验设计

5. [[05_Benchmark_and_Dataset_Design|统一 Benchmark / 数据集设计]]：解析 2D 刚体动力学、渲染、标签、shortcut 防护、benchmark 合格性测试。
6. [[06_Probe_and_Readout_Design|Probe / Readout 设计]]：mean pooling、Linear/MLP、attentive pooling、relational transformer、layer sweep、computational accessibility。
7. [[07_Mechanistic_Interpretability_and_Causal_Intervention|Mechanistic Interpretability 与因果干预]]：子空间、patching、interchange intervention、steering、DAS 备选方案、因果 claim 边界。
8. [[08_Experiment_Plan_and_Evaluation|实验计划与评测]]：从 benchmark 资格测试到 broad sweep、token-aware probing、causal microscope 的执行顺序。
9. [[09_Engineering_Compute_and_Code_Architecture|工程、算力与代码架构]]：simulator / renderer、activation 缓存、在线 frozen-backbone 训练、4×A800 规划。

## 三、学术背景与研究历史

10. [[10_Related_Work|Related Work]]：关键论文、方法来源、与本项目的关系、当前发表状态。
11. [[11_Decision_Log_and_Idea_Evolution|研究决策日志与想法演化]]：重要旧想法、被修改/否决的方案，以及为什么改。
12. [[12_Risks_Failure_Modes_and_Claim_Discipline|风险、失败模式与 Claim 纪律]]：哪些实验最容易被 shortcut 或过度解释破坏。
13. [[13_Open_Questions_and_TODO|Open Questions 与 TODO]]：当前未解决问题。

## 四、记录与模板

14. [[14_Results_Log_Template|结果记录模板]]
15. [[15_Weekly_Log_Template|周报模板]]
16. [[16_Experiment_Record_Template|实验记录模板]]
17. [[17_Glossary_and_Terminology|术语表]]
18. [[18_Knowledge_Base_Maintenance|知识库维护规范]]
19. [[19_Proposal_Distilled|蒸馏版 Proposal]]
20. [[20_Benchmark_Literature_Notes|Benchmark 文献笔记]]
21. [[21_VJEPA_Downstream_Survey|V-JEPA 下游工作调研]]

## 当前工作标题

> **From State to Prediction and Judgment: Dissecting Physical Reasoning across Predictive Video Models and Video-Language Models**

### 为什么是 “and”，不是 “to”

早期标题使用 `From State to Prediction to Judgment`，容易暗示一个普适的三级顺序链：

$$
\text{State}\rightarrow\text{Prediction}\rightarrow\text{Judgment}.
$$

当前理论已经明确修正：

- 对 **V-JEPA**，`State → Prediction` 有很强的结构先验，因为它本身就是 encoder–predictor 架构，并以 predictive latent objective 训练；但 **Judgment** 不是原生任务，出现位置和机制都应当作为开放问题。
- 对 **VLM**，Prediction 与 Judgment 很可能是从视觉/语义状态出发的两个并列、task-conditioned 的 reasoning 分支，并不要求 `Prediction → Judgment`。

因此标题中的 **State, Prediction, and Judgment** 表示三个功能分析维度，而不预设它们在所有模型里存在统一因果顺序。
