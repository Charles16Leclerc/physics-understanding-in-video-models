---
title: Proposal Distilled
status: Current
updated: 2026-09-12
tags: [proposal, distilled]
---

# 蒸馏版 Research Proposal

## 题目

> **From State to Prediction and Judgment: Dissecting Physical Reasoning across Predictive Video Models and Video-Language Models**

## 一句话问题

现有工作常把“模型是否懂物理”当成一个能力，但我们希望问：

> **不同架构的视频模型，究竟如何分别表示当前物理状态、形成未来预测、以及作出物理合理性判断？**

## 为什么拆成 State / Prediction / Judgment

这不是任意分类。

### V-JEPA

$$
X\xrightarrow{Encoder}Z\xrightarrow{Predictor}\hat Z
$$

其 architecture/pretraining 天然提供：

$$
\text{State}\rightarrow\text{Prediction}
$$

的结构先验；Judgment 不是原生任务。

### VLM

$$
\text{Video ViT}\rightarrow\text{LLM}\rightarrow\text{answer}
$$

没有专门 future predictor，因此 Prediction 与 Judgment 很可能只是从 shared visual state 出发的两个并列 reasoning task。

所以我们不是用同一个理论套两个模型，而是检验：

> **不同 training objective 是否形成不同的 physical-computation organization。**

## 实验 1：Computational Accessibility Map

在：

- V-JEPA encoder / predictor；
- VLM vision tower / merger / LLM

不同位置 probe：

- State：位置、速度、方向、barrier geometry；
- Prediction：future collision、TTC、post-collision velocity；
- Judgment：valid/invalid、severity。

使用：

1. Mean-Linear；
2. Mean-MLP；
3. Attentive Pooling；
4. Relational Transformer。

目的不是“找最强 head”，而是区分：

- 信息是否已在线性 pooled summary 中 explicit；
- 是否只是 pooling 丢了局部 token；
- 是否还需要新的 relation computation。

## 实验 2：Causal Mechanistic Microscope

统一 benchmark 中使用极简：

$$
\text{moving puck}+\text{fixed finite barrier}
$$

解析计算：

$$
(p,v,n,c)\rightarrow\tau\rightarrow v^+.
$$

找到 velocity / barrier orientation / TTC representation 后做：

$$
h_A'=(I-P)h_A+Ph_B
$$

的 interchange intervention，测试：

> 修改内部某个物理变量后，模型 downstream prediction 是否按真实 counterfactual physics 改变？

## 为什么自建 benchmark

若 State、Prediction、Judgment 用三个不同数据集，就无法区分“功能差异”和“数据集难度差异”。

因此：

> **One World, Multiple Queries.**

同一 latent trajectory 同时生成三类 label。

数据原则：

> **physically narrow, causally and visually broad.**

## 主数据

第一版只做：

$$
\text{single puck/disk + fixed barrier}
$$

解析模拟，不用 physics engine。

渲染成多个明确俯视水平面的 semantic skin：

- billiards-like；
- air-hockey-like；
- lab tabletop。

Canonical subset 用于 mechanism；Diverse subset 用于 robustness。

Judgment 使用 marginal-matched invalid transition，避免 `bad = 某方向/某颜色/某速度`。

## 主模型

### Predictive

- V-JEPA2 ViT-L + native 22M predictor；
- 关键结果后续 scale 到 ViT-g；
- V-JEPA2.1-L 作为 robustness。

### VLM

- Qwen2.5-VL-7B 作为 primary；
- LLaVA-OneVision 作为 optional architecture control。

## 可能主要发现

任何以下结果都有价值：

- V-JEPA predictor 将 implicit future relation 变成 linear-explicit；
- future variable 在 encoder 已经 explicit，说明 anticipatory representation；
- V-JEPA judgment 没有稳定层级；
- VLM judgment 强但 quantitative state 弱；
- VLM prediction / judgment 在不同 LLM pathways 分叉；
- 不同 physics judgment 没有共享 validity representation；
- probe decodability 与 causal use 不一致。

## 贡献

1. architecture-aware 的 State / Prediction / Judgment 分解；
2. layer × module × readout class 的 computational accessibility map；
3. predictive model 与 VLM 的内部 physical organization 对比；
4. 真实 physical intermediate 的 causal intervention；
5. 可选：interpretability-guided performance improvement。

## 为什么有顶会潜力

若只做 probing table，贡献偏 incremental；但如果完成：

- 严格统一 benchmark；
- architecture-level finding；
- causal intermediate intervention；

则与已有：

- Joseph 的 physics representation probing；
- SHO 的内部物理算法恢复；
- Othello-GPT 的 causal world-state intervention；
- VLM mech interp

形成明显互补，而不是简单重复。

项目也不依赖新 SOTA。Mechanistic scientific finding 本身可以是顶会 contribution。
