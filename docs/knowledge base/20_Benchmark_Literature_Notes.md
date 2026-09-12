---
title: Benchmark Literature Notes
status: Current
updated: 2026-09-12
tags: [benchmark, literature-notes, intphys, physion]
---

# Benchmark 文献笔记

> 这份文档保留项目形成过程中对物理 benchmark 的广泛调研。很多 benchmark 当前已经不是主实验，但它们直接影响了我们对“什么叫 physical understanding”“为什么要自建统一 diagnostic benchmark”的理解。

## 1. 一个有用的物理 benchmark 分类

### Level 1 — Core intuitive physics / violation detection

主要问：

> 已经看到的事件是否符合最基本世界规律？

典型：

- object permanence；
- solidity；
- continuity；
- support；
- gravity direction；
- impossible disappearance / teleportation。

代表：IntPhys / IntPhys2、部分 GRASP 等。

### Level 2 — Dynamical prediction

主要问：

> 从当前状态出发，未来会怎样？

例如：

- future contact；
- future position；
- collision event；
- post-collision velocity。

代表：Physion、CLEVRER predictive questions 等。

### Level 3 — Causal / parametric physical reasoning

主要涉及：

- counterfactual；
- 哪个参数导致现象；
- material / mass / friction / restitution；
- intervention 后结果如何改变。

代表：CLEVRER counterfactual、ComPhy、部分 physical-property benchmark。

项目后续认识到：这三个 Level 与我们的 State / Prediction / Judgment **不完全一一对应**，但它们帮助我们意识到“physics benchmark”不是单一类型。

---

# IntPhys

## 2. 核心思想：Violation of Expectation

IntPhys 的经典思路是：

- possible event；
- impossible event；
- 如果模型真的形成现实世界预期，那么 impossible continuation 应更 surprising。

原生 VoE 可写成：

\[
S(V)=D(\hat z,z)
\]

或其他 prediction/surprise score。

### 为什么早期觉得 JEPA 很适合

JEPA 本身就是 predictive representation learning，所以似乎天然可以：

- 不训练 QA head；
- 直接比较 possible / impossible 的 latent prediction error。

### 后来的关键 caveat

\[
\boxed{\text{predictability}\neq\text{physical validity}}
\]

例如：

一个球已经连续多帧匀速向上漂浮，下一帧继续向上可能很好预测，但在真实重力语境下仍然不物理。

因此 VoE 测的是：

> 模型自己的 predictive expectation 是否被违反。

而不是直接等价于：

> 这个世界过程是否符合物理法则。

这就是为什么本项目把 Prediction 与 Judgment 分开。

## 3. Matched Minimal Sets

IntPhys 的一个重要 benchmark philosophy 是尽量构造 possible / impossible matched pair，减少 appearance shortcut。

这一思想直接影响我们当前 matched physical violation：

- good/bad 单变量 marginal 尽量匹配；
- 错误只存在于物理关系。

## 4. 经典概念

主要围绕：

- object permanence；
- continuity；
- solidity；
- support / gravity；
- occlusion。

这些更偏 intuitive physical expectation，而不是精确动力学参数。

---

# IntPhys2

## 5. 主要概念

在更长、更复杂的视频中加强：

- object permanence；
- 长时 occlusion；
- object hidden state change；
- solidity / wall interaction；
- camera excursion / view change。

## 6. 重要升级

相对经典 IntPhys：

- 视频更长；
- occlusion 更复杂；
- 需要更强 temporal binding / memory；
- impossible event 往往藏在长时间序列里；
- general models 很容易接近 chance。

## 7. 为什么它最初吸引本项目

早期我们想研究：

> V-JEPA / VLM 内部哪里出现 “possible vs impossible physics” representation？

IntPhys2 恰好：

- 很难；
- V-JEPA2 + simple probe 差；
- 多个 VLM 也差；
- 很适合研究 failure。

## 8. 为什么后来变得谨慎

实际逐 case 观察后发现：

- benchmark 很大比例是“遮挡后物体变化”；
- 其中很多问题更像 object permanence / identity consistency；
- first/last state 或几何 tracking 可能利用很强 shortcut；
- specialized 3D/trajectory 方法可能取得很高成绩；
- 很难说它代表广义碰撞、重力、摩擦等 physical reasoning。

因此：

> 高分 IntPhys2 不应直接等价为“模型通用物理理解强”。

## 9. 不应混淆的 protocol

比较 IntPhys2 结果时必须区分：

- native VoE；
- frozen backbone + linear probe；
- attentive probe；
- full fine-tuning；
- specialized geometry system；
- VLM direct QA。

这些回答的是完全不同的问题，不能只把数字排在一起。

## 10. 早期调研中记录的 baseline 现象

项目调研中反复出现：

- 多个 general VLM 接近 chance 或表现不稳定；
- V-JEPA2 + pooled linear probe 也很弱；
- temporal/attentive readout 能改善；
- specialized geometry / tracking 方案可能显著更强。

这直接促使我们从“benchmark 排名”转向“接口与内部 computation 分解”。

---

# IntPhys2 Probing Follow-up

## 11. Pooled Linear Probe 失败

`What, Where, and How` 等工作显示：

- camera / motion feature 在 V-JEPA2 中可明显读出；
- 但 IntPhys2 judgment 在 simple pooled readout 上很差。

这说明：

> state/dynamics representation 很强，不代表一个完整 physical-validity label 会自动出现在 pooled final vector 中。

## 12. Punzo et al.：Temporal / Attentive Probe

`Do Video Foundation Models Understand Intuitive Physics?` 显示保留 token / temporal structure 的 probe 往往明显强于 mean pooling。

重要方法论结论：

- probe architecture 本身会强烈决定“你认为模型有没有 physics”；
- 不能把 linear pooled failure 直接解释成 information absence。

这促成当前：

\[
\text{Mean}\rightarrow\text{Attentive}\rightarrow\text{Relational}
\]

的分解。

## 13. 3DSPA

### 核心思路

通过显式 3D / object / spatial structure，把长视频中的：

- object tracking；
- geometry；
- persistence；

组织成更适合 physical validity 判断的 representation。

### 概念架构

大致是：

\[
\text{video}
\rightarrow
\text{object/spatial reconstruction}
\rightarrow
\text{state consistency}
\rightarrow
\text{physics score}.
\]

### 对我们的重要启发

它说明：

- IntPhys2 的困难很大部分可以通过显式 object-centric / geometry pipeline 解决；
- “判断是否符合物理”不一定在通用 VFM final embedding 中自然存在；
- specialized interface 可以极大改变 performance。

### 重要 ablation 方向

项目讨论中尤其关注：

- 是否真正依赖 3D；
- first/last frame 是否已足够；
- tracking 是否是主要贡献；
- 若去掉 temporal structure 会怎样。

### Status

作为 related benchmark method，不进入主实验。

## 14. GeoPhys

### 核心思想

使用更显式的 geometry / trajectory / physical consistency 表示完成视频物理判断。

### 为什么概念上重要

它进一步说明：

> judgment benchmark 可以被一个高度 task-specific 的 geometric pipeline 刷得很好，而这与 general visual model 是否形成通用 physics representation 是两个问题。

### 项目讨论中过的 controls

如果未来引用此类工作，应关注：

- 是否利用数据集 camera pattern；
- 是否只依赖首尾状态；
- 是否真正需要 law reasoning；
- 轨迹恢复本身占多大贡献。

### Status

不是当前 benchmark 候选，仅作为“为什么不能用一个 judgment score 定义 physics understanding”的证据。

---

# 其他 Intuitive-Physics Benchmarks

## 15. Physion

Physion 覆盖多个常见物理场景，例如：

- collide；
- roll；
- drop；
- support；
- contain 等。

核心 downstream 是 Object Contact Prediction。

其理论框架本身区分：

\[
X_{\le t}
\xrightarrow{E}
p
\xrightarrow{D}
q
\xrightarrow{C}
P(contact).
\]

### 对项目的关键理论纠正

早期我们把“encoder 上做 future-contact linear probe”理解得太规范性：认为 encoder 不应该有 future 信息。

Physion 的真实意图只是：

- 用统一 adaptor 比较 representation；
- 不意味着 visual encoder 理论上不允许 anticipatory feature。

当前认为：

> future contact 在 encoder 中线性可读可能是 predictive representation 的结果；真正值得研究的是这种 explicitness 在 predictor 中如何变化。

## 16. CLEVRER

特点：

- 合成物体碰撞；
- descriptive / explanatory / predictive / counterfactual questions；
- object/event GT 清楚。

优点：

- 一个世界支撑多个问法；
- 非常接近“One World, Multiple Queries”思想。

缺点：

- QA/symbolic composition 比我们需要的更复杂；
- 物体/事件链可能过长；
- 不方便精确控制 readout target difficulty。

因此是设计参考，不直接复用。

## 17. DeepMind Physical Concepts / PLATO

强调 object-centric / intuitive physical concept learning，例如：

- persistence；
- continuity；
- solidity 等。

这些工作加强了一个长期认识：

> 物理世界建模很可能天然需要 object/state abstraction，而不只是全局 semantic embedding。

## 18. InfLevel

主要关注 intuitive physics representation 在深层模型中的不同层级 / 难度。

对项目早期“physics task 不止一种难度和功能层次”的想法有启发。

## 19. GRASP

偏向更丰富的 physical reasoning / plausibility / causal question。

曾被考虑作为 Judgment 数据，但最终因为与 State/Prediction 数据分布不统一而没有进入主方案。

## 20. PHYRE

重点是 physical reasoning / planning through interaction，常见 2D object dynamics。

优点：

- 可控；
- 强物理；
- intervention / planning 明确。

但它更偏 action planning，和本项目 passive video representation 不完全一致。

## 21. ComPhy

强调 compositional physical reasoning：

- 多物体；
- 属性；
- relation；
- causal interaction。

过于复杂，不适合作为第一版 mechanistic toy world，但可能是未来 generalization extension。

---

# 22. 当前 Benchmark 结论

项目从广泛 benchmark 调研得到的最终原则：

1. 不存在单一 benchmark 可以代表“physics understanding”；
2. native prediction surprise 与 judgment 必须区分；
3. 不同接口（linear probe / attentive head / VLM QA / fine-tune）不能直接按分数比较；
4. benchmark shortcut 可以让 specialized method 高分，而不代表通用 physics 更强；
5. 主研究若要比较 State / Prediction / Judgment，必须尽量统一 underlying world；
6. 现成 benchmark 更适合作为 external sanity check，而不是核心 causal instrument。

这直接导向当前自建：

\[
\boxed{\text{single puck + finite barrier}}
\]

的统一 diagnostic benchmark。
