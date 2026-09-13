---
title: Project Overview
status: Current
updated: 2026-09-12
tags: [overview, proposal]
---

# 项目概述

## 工作标题

**From State to Prediction and Judgment: Dissecting Physical Reasoning across Predictive Video Models and Video-Language Models**

## 1. 核心问题

本研究仍然围绕“模型怎样理解物理”这个大问题进行展开。

“理解物理”这个概念有许多截然不同的表现形式。而现有工作在研究“模型是否/怎样理解物理”这个问题时，常常把多种不同的形式混在一起。

所以我们做的第一件事是把常见的“物理理解”概念拆分为以下三点：

- 对当前物理状态进行表征；
- 预测未来物理状态或事件；
- 判断已经观察到的事件是否符合物理规律。

也即，本项目将 “physical understanding” 操作化为三个主要目标：

$$
\boxed{\text{Physical State}},\qquad
\boxed{\text{Physical Prediction}},\qquad
\boxed{\text{Physical Judgment}}.
$$

在这个三分法的框架下，我们就能更加清晰地研究”模型怎样理解物理“这个问题了。

于是，我们的研究目标是分析：

> **不同训练目标和架构的模型，分别怎样组织 State、Prediction 与 Judgment进行物理理解和推理？**

## 2. 核心模型对比

### 2.1 Predictive Video Models：V-JEPA 系

V-JEPA 风格系统显式具有：

$$
X \xrightarrow{E} Z \xrightarrow{P} \hat Z.
$$

其中 encoder 与 predictor 通过 predictive latent objective 联合训练，因此存在较强的结构先验：

$$
\text{current state}\rightarrow\text{future prediction}.
$$

但 **physical judgment 并不是原生训练目标**。因此没有理由提前假设：

- `possible / impossible` 一定在 predictor 后部出现；
- 判断一定晚于 prediction；
- 所有 judgment task 共享统一的 representation。

### 2.2 Video-Language Models：现代支持视频的 VLM

以 Qwen2.5-VL 为例，其结构大致为：

$$
\text{video}
\rightarrow
\text{vision encoder}
\rightarrow
\text{merger/projector}
\rightarrow
\text{LLM}
\rightarrow
\text{answer}.
$$

它没有显式的 latent future predictor。对 VLM 而言，Prediction 与 Judgment 都可能只是 general VQA / multimodal reasoning 下的两种子任务，因此更合理的先验是：

$$
\text{visual state}
\rightarrow
\begin{cases}
\text{prediction}\\
\text{judgment}
\end{cases}
$$

而不是统一的 `State → Prediction → Judgment`。

## 3. 主科学问题

> **预训练 predictive video models 与 video-language models 如何把视觉物理信息组织成当前状态、未来预测和物理判断？这种组织方式如何由模型架构与预训练目标决定？**

## 4. 两部分实验

### Experiment 1：Functional / Computational Accessibility Map

在不同模型层、模块和物理 target 上，训练固定类别的 readout：

- mean-pooled linear probe；
- mean-pooled MLP；
- full-token attentive pooling；
- full-token relational transformer probe。

研究空间为：

$$
\text{model family}
\times
\text{functional target}
\times
\text{network location}
\times
\text{readout class}.
$$

核心问题是：

> **一个物理变量在什么时候变得显式？为了从当前 representation 中恢复它，还需要多少 aggregation 或额外 computation？**

### Experiment 2：Mechanistic Microscope

第二部分使用与 Experiment 1 相同数据生成分布中的 canonical、低 nuisance 子集。其 ground-truth computation graph 已知：

$$
(p,v,n,c)
\rightarrow
\tau_{\text{collision}}
\rightarrow
v^+
\rightarrow
\text{prediction/judgment}.
$$

对这些 intermediate 做：

- probing；
- projection / ablation；
- activation patching；
- matched interchange intervention；
- 在有依据时做低维 steering；
- 若线性/低维子空间不足，再考虑 Distributed Alignment Search (DAS)。

第二部分不是另起一个 toy story，而是：

> **对第一部分同一物理世界的“显微镜式”机制分析。**

## 5. 为什么需要自建统一 benchmark

若 State、Prediction、Judgment 分别来自三个现成数据集，则任何差异都可能来自：

- scene complexity；
- object/background diversity；
- camera motion；
- temporal length；
- label entropy；
- train-set size；
- shortcut structure；
- simulation artifacts。

因此主 benchmark 遵循：

> **One World, Multiple Queries.**

同一个 latent physical trajectory 同时生成：

- state labels；
- prediction labels；
- judgment labels；
- 可选的 counterfactual labels；
- 多种视觉 render。

数据集设计原则是：

> **physically narrow, causally and visually broad**。

即物理规律尽量简单统一，但 initial conditions、几何关系、视觉皮肤、counterfactual intervention 足够丰富。

## 6. 当前主模型

### Predictive 侧

**V-JEPA2 ViT-L + native predictor** 作为开发主模型。

- ViT-L encoder：约 300M，24 层，hidden 1024，16 heads；
- native predictor：约 22M，12 层，hidden 384，12 heads；
- 关键结论之后可 scale 到 ViT-g。

**Tentative robustness model：** V-JEPA2.1 ViT-L。

### VLM 侧

当前首选 **Qwen2.5-VL-7B**，因为：

- 原生支持视频；
- 开源；
- 能力足够强；
- 结构相对干净：

$$
\text{video ViT}\rightarrow\text{patch merger}\rightarrow\text{Qwen2.5 LLM}.
$$

若后续需要架构 robustness，可增加 **LLaVA-OneVision-7B**。

## 7. 主物理系统

当前首选：

$$
\boxed{\text{single moving ball/disk/puck + fixed finite barrier}}
$$


原因：

- 可解析求精确动力学；
- 不需要 physics engine；
- 可设计非线性 relational prediction target；
- GT state/intermediate 完整；
- matched counterfactual invalid transition 容易构造；
- 非常适合因果 intervention；
- 避免 long-horizon multi-collision 的敏感性；
- 初状态的微小差异不会导致结果的巨大差异，对模型预测友好。

## 8. 渲染哲学

同一个 latent trajectory 可以渲染成多个语义 skin：

- billiards-like overhead table；
- air-hockey-like tabletop；
- 显示完整桌面边界的 lab/tabletop surface。

这样既解决“相机到底是不是俯拍、重力是否应该作用在 image plane 内”的歧义，又避免整个 benchmark 只测“台球场景先验”。

## 9. 预期贡献

1. **Architecture-aware functional decomposition**：把 physical understanding 拆成 State、Prediction、Judgment，但不强行假设统一顺序链。
2. **Computational accessibility map**：研究不同层、不同模块、不同 readout class 下物理量的显式程度。
3. **Architecture-specific organization**：比较 V-JEPA encoder/predictor 与 VLM vision/LLM 的内部功能组织。
4. **Causal mechanistic validation**：验证被 probe 出来的物理变量是否真正被下游计算使用。
5. **Optional extension**：若主实验得到清晰机制，可进一步尝试 interpretability-guided layer fusion、selective tuning 或 shortcut suppression 以提升 OOD 性能。

## 10. 为什么负结果也有价值

本项目不是押注某一个必须成立的 performance hypothesis。以下结果都可能构成有意义的科学发现：

- V-JEPA 的 state 在 encoder 早期显式，prediction 在 predictor 中显式；
- prediction 在 encoder 中已经线性显式，说明 predictive pretraining 形成 anticipatory encoding；
- judgment 在 V-JEPA 中没有固定定位；
- VLM 对定量 state 表征弱，但 judgment 很强，暗示 coarse visual evidence + LLM prior；
- prediction 与 judgment 在 VLM 中由不同路径完成；
- 不同 judgment task 并不共享同一“physical validity”表示；
- decodability 与 causal use 不一致。

只要 benchmark 足够严谨、claim 边界清晰，反直觉或 negative result 同样能够回答科学问题。
