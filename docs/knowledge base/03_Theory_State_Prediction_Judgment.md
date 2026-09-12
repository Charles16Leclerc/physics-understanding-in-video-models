---
title: Theory - State, Prediction, and Judgment
status: Current
updated: 2026-09-12
tags: [theory, state, prediction, judgment]
---

# 理论框架：State、Prediction 与 Judgment

## 1. 当前最重要的理论修正

早期曾采用较强叙述：

\[
\text{State}\rightarrow\text{Prediction}\rightarrow\text{Judgment}.
\]

### Superseded

这条链不应作为所有模型的 universal causal theory。

当前框架是：

> **State、Prediction、Judgment 是三个可实验操作化的功能对象；不同架构可能以完全不同的方式组织它们。**

标题也因此从 `From State to Prediction to Judgment` 改为：

> **From State to Prediction and Judgment**

以避免暗示强因果先后关系。

## 2. 为什么三分法仍然不是 arbitrary

三分法来源于三个相互独立但一致的考虑：

1. V-JEPA encoder/predictor 的结构与 predictive pretraining，天然提供 State / Prediction 的功能来源；
2. 现代 VLM 的核心原生接口是 visual understanding / QA，Prediction 与 Judgment 都是常见 reasoning 子任务；
3. 现有视频物理保真度 benchmark 大量使用 VLM 做 “physical plausibility judge”，因此 Judgment 具有现实研究重要性。

所以我们不是为了方便把“物理”随便切成三段，而是在研究两类模型时选取了最自然、可比较、且与真实应用直接相关的三个 functional target。

## 3. V-JEPA：强 `State → Prediction` 先验，弱 Judgment 先验

V-JEPA 结构：

\[
X\xrightarrow{E}Z\xrightarrow{P}\hat Z.
\]

### 3.1 Encoder 的理论角色

Encoder 接收当前/上下文视频，并把原始时空像素组织成 latent state representation。

我们因此预期它适合表征：

- object state；
- position；
- velocity；
- geometry；
- contact cues；
- motion direction 等。

但必须避免过强措辞：encoder 并不是“人工设计的最小物理状态估计器”。因为它本身在 predictive objective 下训练，所以它完全可能提前把 future-relevant relation 编进 representation。

因此若 future contact 在线性 probe 下已经从 encoder 读出，这不应被解释为“encoder 做错了工作”，而可能说明：

> predictive training 将一个未来相关函数线性化 / 编译到了当前 representation 中。

### 3.2 Predictor 的理论角色

原始 V-JEPA2 predictor 更准确的表述是：

> **latent conditional inference / masked latent completion module**

而不是直接称其为“物理定律 reasoner”。

但在架构上，它仍然是最自然观察：

- future-related quantity 是否变得更 explicit；
- relational state 是否被转化为预测状态；
- readout class 是否降低。

### 3.3 Judgment 的位置不应预设

Judgment 不是 V-JEPA 的 native training objective，因此没有理论理由预设：

- predictor 越深 judgment 越好；
- judgment 必须由 predictor 产生；
- 所有 violation task 都共享统一轴。

可能机制包括：

- encoder 从完整观察视频直接编码 anomaly；
- predictor expectation 与 observed latent 的 mismatch 形成 VoE-like signal；
- 某些 task 需要复杂 readout 才能从 latent 中重新计算；
- 不同 judgment task 在不同位置和不同子空间中实现。

## 4. VLM：Prediction 与 Judgment 更可能是并列任务

典型现代 video-capable VLM：

\[
\text{video}
\rightarrow
\text{vision tower}
\rightarrow
\text{merger/projector}
\rightarrow
\text{LLM}
\rightarrow
\text{text output}.
\]

### 4.1 没有显式 future predictor

VLM 的大规模训练包括视觉预训练、多模态 alignment、captioning、VQA、instruction tuning 等，但通常没有一个独立模块被训练成：

\[
z_t\rightarrow z_{t+1}.
\]

因此对 VLM 来说，Prediction 与 Judgment 都可以只是“根据视觉内容回答问题”。

### 4.2 Prediction 与 Judgment 不一定有先后

合理先验：

\[
\text{visual state}
\rightarrow
\begin{cases}
\text{prediction}\\
\text{judgment}
\end{cases}
\]

甚至 Judgment 可能比 Prediction 更符合 VLM 原生 QA 形式：

- Judgment：描述/判断当前已经看到的视频是否合理；
- Prediction：要求构造一个未观察未来。

### 4.3 LLM prior 是关键区别

VLM 可能通过：

\[
\text{coarse visual evidence}
+
\text{textual/world prior}
\rightarrow
\text{judgment}
\]

完成物理判断，而无需形成 metrically precise 的内部 velocity / acceleration state。

因此：

- final answer 正确不代表 vision tower 精确理解了动力学；
- VLM 的 “physical reasoning” 可能更多体现语言先验与 task-conditioned abstraction。

## 5. Architecture-conditioned hypotheses

### H1：V-JEPA 的 State / Prediction 分工应比 VLM 更有结构性

若 benchmark target 需要 nonlinear state relation，则预测：

\[
C^*_{\text{Prediction}}(P)
<
C^*_{\text{Prediction}}(E)
\]

即 predictor 层所需 readout class 更低 / accessibility 更高。

### H2：VLM 中 Prediction 与 Judgment 不要求顺序 emergence

可能出现：

- prediction 先；
- judgment 先；
- 同层并行；
- 依赖不同 token / pathway。

任何一种都应作为结果而非“违反理论”。

### H3：State 可能是两类模型更共同的基础

无论 V-JEPA 还是 VLM，都需要先从视觉输入形成某种可用 representation，因此 State 是最自然的共同参照点。

但即便这里也不预设哪一类模型一定更强。

## 6. 从“出现在哪层”升级到“多显式”

单一 linear probe 只能回答：

\[
\text{Can }y\text{ be linearly decoded from a chosen summary of }h_l?
\]

本项目更关注：

> 在 layer \(l\) 上，为达到给定性能阈值，最简单的哪一类 readout 足够？

可定义：

\[
C^*(y,l)=
\min_{r\in\mathcal R}
\left\{
C(r):\tilde P(r(h_l),y)\ge\tau
\right\}.
\]

更推荐将其称为：

- **minimal readout class**；
- **computational accessibility**；
- 或 **computational explicitness**。

不应声称 Linear、MLP、Attention、Transformer 构成严格数学意义的一维“复杂度尺”。它们不仅参数量不同，inductive bias 也不同。

## 7. 两个不同的难点必须拆开

### Aggregation difficulty

信息已经存在于局部 token，但 mean pooling 抹掉了，需要 learnable attention 找到它。

### Computational difficulty

即使找到了 relevant tokens，答案仍需要多个 token/state variable 之间进行新的关系计算。

因此建议 readout ladder：

\[
\text{Mean-Linear}
\rightarrow
\text{Mean-MLP}
\rightarrow
\text{Attentive Pooling}
\rightarrow
\text{Relational Transformer}.
\]

其中第三、第四项的差异具有重要解释意义。详见 [[06_Probe_and_Readout_Design]]。

## 8. 不能越界的理论 claim

- probe 可读 → 只能说信息可访问 / decodable；
- subspace geometry → 可说组织方式；
- ablation / patching → 可讨论 causal contribution；
- steering → 可说某方向具有控制作用；
- circuit / interchange intervention → 才更接近“模型如何使用该变量进行 computation”。

统一原则：

\[
\boxed{\text{encoded} \neq \text{used} \neq \text{causally necessary} \neq \text{the algorithm}}
\]
