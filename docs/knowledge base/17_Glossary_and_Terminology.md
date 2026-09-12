---
title: Glossary and Terminology
status: Current
updated: 2026-09-12
tags: [glossary, terminology]
---

# 术语表与表述规范

## 1. Physical State

当前观测世界中可定义的物理状态或几何变量，例如：

- position；
- velocity；
- heading；
- barrier normal；
- contact state。

不要把 State 定义成“encoder 必须输出的唯一最小充分统计量”。它是 functional target。

## 2. Physical Prediction

基于当前 state / context 对未来事件或状态的估计，例如：

- future contact；
- TTC；
- post-collision velocity。

注意：future target 若只是当前 state 的线性变换，不能作为强 prediction-computation 证据。

## 3. Physical Judgment

对已经观察到的动态过程是否符合真实物理规律进行判断，例如：

- valid / invalid；
- violation severity。

不预设 Judgment 必须通过显式 Prediction 形成。

## 4. Predictive Video Model

当前项目主要指 JEPA-style、具有显式 predictive latent objective / predictor 的视频模型，例如 V-JEPA2。

## 5. Video-Language Model

是标准学术称呼，不是误写 VLM。

本文具体指：

> **video-capable vision-language models with a visual encoder and an LLM-based reasoning backbone**。

例如 Qwen2.5-VL、LLaVA-OneVision。

## 6. Video Foundation Model (VFM)

学界用法较宽，可包括 pretrained video encoder / generator 等。

本项目标题不优先使用，因为研究对象还包含 predictor 与 LLM backbone，容易让人误解成只研究视频视觉编码器。

## 7. Probe / Readout

冻结 backbone 后，为读取某个 target 训练的小模型。

本项目必须明确 probe 输入：

- mean-pooled representation；
- object-pooled tokens；
- full tokens；
- specific LLM token positions。

## 8. Mean-Linear

$$
H\rightarrow\bar h\rightarrow W\bar h+b.
$$

Claim：目标可从 **mean-pooled representation** 线性读取。

不能自动写成“完整层 representation 线性编码目标”。

## 9. Mean-MLP

先 mean pooling，再做静态 nonlinear readout。

它无法恢复 pooling 已经完全删除的信息。

## 10. Attentive Pooling

用 learned query / cross-attention 从 full tokens 中选择与聚合信息，不先让 tokens 做新的 relational computation。

主要测试 aggregation difficulty。

## 11. Relational Transformer Probe

在 full tokens 上加入新的 self-attention / token-token interaction，再聚合输出。

主要测试是否需要额外 relation computation。

## 12. Computational Accessibility / Explicitness

描述一个 quantity 从某层 representation 中被简单 readout 恢复的难易程度。

比“readout complexity”更推荐，因为不同 readout 的 inductive bias 不构成严格一维复杂度尺。

## 13. Minimal Readout Class

达到预设 normalized performance threshold 所需的最简单 readout 类别。

### Tentative metric

是否成为主论文正式指标取决于 pilot 稳定性。

## 14. Decodability

某信息能被 probe 读出。

统一纪律：

$$
\text{decodable}\neq\text{used}.
$$

## 15. Causal Use / Causal Contribution

在对 activation 做控制性 intervention 后，downstream output 发生符合预期的变化。

仍需说明 intervention 的具体形式和 off-manifold 风险。

## 16. Interchange Intervention

把 base example 某 candidate subspace 的 activation 换成 source example：

$$
h_A'=(I-P)h_A+Ph_B.
$$

用于对齐高层 causal variable 的 counterfactual edit。

## 17. Activation Patching

直接把某层 / token / head / residual stream 的 activation 从 source example patch 到 base example。

不要求先有线性 probe direction。

## 18. Steering

沿某 direction/subspace 对 activation 增加或替换，使输出受控改变。

Steering 成功不等于找到唯一“存储位置”。

## 19. DAS

Distributed Alignment Search。学习一个 distributed subspace，使 neural intervention 与高层 causal variable intervention 对齐。

当前作为 nonlinear/distributed representation 的 fallback。

## 20. PEZ

Physics Emergence Zone。Joseph et al. 用于描述视频 encoder 中物理表征在中前层开始明显线性可读的区域。

本项目可引用该现象，但不预设所有 model/task 都存在相同 PEZ。

## 21. VoE

Violation of Expectation。用模型 prediction error / surprise 区分 possible vs impossible event。

注意：

$$
\text{surprise}\neq\text{physical invalidity}.
$$

## 22. Claim 词汇等级

### Probe 证据

推荐：

- encodes；
- contains information about；
- makes X accessible；
- X is linearly decodable from ...

避免：

- uses X to reason；
- computes X；

除非有 causal evidence。

### Causal Intervention

推荐：

- causally contributes under this intervention；
- intervention on X-aligned subspace changes Y consistently；
- supports a causal role。

### Circuit Evidence

只有 writer/reader/path 等证据充分时，才使用：

- computes；
- transmits；
- uses；
- implements a mechanism。
