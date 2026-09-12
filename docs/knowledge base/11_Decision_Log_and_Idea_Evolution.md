---
title: Decision Log and Idea Evolution
status: Current
updated: 2026-09-12
tags: [decision-log, history]
---

# 研究决策日志与想法演化

> 本文件的目的不是只保留“正确答案”，而是保留研究为什么走到当前版本。未来如果实验推翻现有理论，不删除旧设计，而是在这里追加新的状态与理由。

## 1. 最早方向：视频生成物理保真度评测

### Historical Context

项目最初来自“视频生成模型是否遵守物理”的研究：

- PISA；
- PDI；
- GAUGE；
- NewtonRewards；
- VideoPhy；
- PhyFPS / LDR / PhyCo / PhyParam 等。

关注：

- 重力；
- 碰撞；
- 摩擦；
- 弹跳；
- 动量/能量；
- 生成视频普遍慢动作；
- 模型是否学到正确物理参数。

也曾计划通过自由落体 / 平抛 LoRA 微调测试物理规律能否泛化。

### Status：Superseded as core direction

原因：

- benchmark + 少量微调的创新性不够强；
- 更有科学价值的问题是：**模型内部的物理知识在哪里、以什么形式存在、如何被使用。**

这些早期问题仍构成 Judgment 任务和“为什么 VLM 被用作 physics evaluator”的背景。

---

## 2. 早期 mech-interp 表述：“物理知识存在哪里？”

### Earlier Formulation

一开始希望定位：

- 哪层；
- 哪个 head；
- 哪些参数；
- gravity/contact/conservation 是否线性可分。

### Revision

“物理知识”不是一个单一静态 feature。项目逐步改为：

\[
\text{Representation}
\rightarrow
\text{Prediction}
\rightarrow
\text{Judgment/Reasoning}
\]

并进一步修正为 architecture-conditioned 的 State / Prediction / Judgment 三功能框架。

### Status：Superseded but conceptually retained

“where is physics?” 仍是子问题，但不再是整篇论文唯一理论。

---

## 3. IntPhys / IntPhys2 作为中心 benchmark

### Initial Attraction

- intuitive physics；
- possible/impossible；
- V-JEPA/VLM 都有人测；
- 可用于 judgment。

### What Changed

实际检查 IntPhys2 后发现：

- 很多 case 集中在长时遮挡、object permanence、隐藏后状态变化；
- 并不等价于广义 rigid-body dynamics；
- 当前 general models 很弱；
- specialized geometry / trajectory 方法可针对数据结构取得高分；
- 不同 violation 很可能走完全不同机制。

### Current Status

**Rejected as primary benchmark.**

保留为：

- stress test；
- optional appendix；
- benchmark-design 反例：不能把“physical validity”假设成统一维度。

---

## 4. 对 Physion linear probe 的早期理解

### Earlier Assumption

曾认为：

> “encoder 理论上只应编码当前 state，因此用 linear probe 从 encoder 直接预测 future contact 很不自然。”

### Revision

Physion 本身明确区分：

\[
E\rightarrow D\rightarrow C.
\]

标准 linear/SVM readout 只是统一 task adaptor，不是理论宣言。

此外，V-JEPA encoder 在 predictive objective 下训练，完全可能把 future-relevant function 编译/线性化进 state representation。

### Current Status

**Superseded strong claim.**

当前更准确：

> future contact 在 encoder 中可读并不等于 encoder “不该这样”；真正问题是 predictor 是否进一步改变其 explicitness / causal organization。

---

## 5. 早期中心 idea：做 V-JEPA–VLM physics evaluator

### Motivation

当时观察：

- V-JEPA 视觉前端很懂 dynamics；
- 现有 physics evaluator 大量使用 VLM；
- LLM 擅长 world knowledge + logical judgment。

因此提出：

> V-JEPA encoder + LLM 是否是更好的 physics evaluator？甚至 V-JEPA encoder + predictor + LLM？

### Why Attractive

理论上它结合：

- dynamics-centric representation；
- language/world prior；
- judgment interface。

### Why It Moved Out of Core

- 没有现成开源完整 V-JEPA–VLM checkpoint；
- 自己做 video-language alignment 需要大量数据/算力；
- 难以做公平 controlled comparison；
- 容易把研究变成 evaluator engineering。

### Current Status

**Deferred to Discussion / future work.**

若最终结果显示：

- V-JEPA state/prediction 强；
- VLM judgment 强；

则可以提出：

> dynamics-specialized encoder/predictor + knowledge-rich LLM 是值得未来研究的 hybrid architecture。

但不声称“理论最优”或自己必须把它训练出来。

---

## 6. 初始三级理论：State → Prediction → Judgment

### Earlier Formulation

曾希望论文直接预测：

\[
\text{State}\rightarrow\text{Prediction}\rightarrow\text{Judgment}
\]

在所有模型中都是逐层递进。

### Problem

VLM 根本没有明确 latent predictor，而且 judgment 可以直接由：

\[
\text{visual evidence}+\text{LLM prior}
\]

完成，不必先显式生成 future state。

### Current Formulation

#### V-JEPA

\[
\text{State}\rightarrow\text{Prediction}
\]

是强 architecture-conditioned hypothesis；Judgment 是 open question。

#### VLM

更合理：

\[
\text{Visual State}
\rightarrow
\begin{cases}
\text{Prediction}\\
\text{Judgment}
\end{cases}
\]

二者可平行或部分共享。

### Title Change

从：

`From State to Prediction to Judgment`

改为：

`From State to Prediction and Judgment`

### Status

**Current.**

---

## 7. “Encoder 不应该线性预测 future”的强说法

### Earlier Strong Statement

“如果 future contact 在 encoder 中线性可读，说明 benchmark / encoder 功能定义不合理。”

### Revision

predictive objective 可能把：

\[
f(s)
\]

通过非线性 feature lifting 变成：

\[
f(s)\approx w^\top h.
\]

这可能意味着 future-relevant relation 被提前 explicit，而不是错误。

### Current Interpretation

真正有信息量的是：

- encoder 与 predictor 的 readout class 差异；
- causal intervention 是否显示 predictor 真的使用 state variable；
- ground-truth state 上任务本身需要什么 computation。

### Status：Superseded

---

## 8. “Readout Complexity” 演化为 Aggregation vs Computation

### Early Idea

把：

- linear；
- MLP；
- attention；
- transformer；
- LLM

理解成一条越来越复杂的 readout ladder，并定义 minimal readout complexity。

### Problems Discovered

1. Mean pooling 会先丢 token information；MLP 无法恢复。
2. Attention 的优势可能只是找 relevant token，不是 reasoning。
3. 不同 architecture 的 inductive bias 不可严格当作一维“complexity”。
4. pretrained LLM 携带大量世界知识，不能与 scratch probe 放在同一尺度。

### Current Refinement

四类 controlled readout：

\[
\text{Mean-Linear}
\rightarrow
\text{Mean-MLP}
\rightarrow
\text{Attentive Pooling}
\rightarrow
\text{Relational Transformer}.
\]

分别区分：

- pooled linear explicitness；
- static nonlinear accessibility；
- aggregation / token selection；
- additional relational computation。

LLM 单独视为 knowledge-rich reasoner。

推荐术语：

- minimal readout class；
- computational accessibility；
- computational explicitness。

### Status：Current

---

## 9. 早期数据方案：多个现成 benchmark

### Earlier Plan

- State 用动态物理属性数据；
- Prediction 用 Physion；
- Judgment 用 IntPhys/GRASP/IntPhys2。

### Problem

不同 dataset 之间：

- difficulty 无法统一；
- scene distribution 不同；
- shortcut 不同；
- task size / visual complexity 不同；
- 甚至物理机制不同。

因此无法把 layer/readout difference 归因于 State/Prediction/Judgment。

### Current Principle

> **One World, Multiple Queries.**

同一 latent physics distribution 同时生成三类任务。

### External Dataset

降级为 optional sanity check，不进入主矩阵。

### Status：Current

---

## 10. DynSuperCLEVR 代码复用想法

### Earlier Idea

一度认为 DynSuperCLEVR：

- 有 velocity / acceleration / collision；
- 有 factual / predictive / counterfactual；
- 有 generator code；

可能直接作为主数据起点。

### Revision After Inspection

实际场景/资产与目标差异较大；主系统只需要极简单 2D analytic dynamics，直接复用其 physics code 反而更复杂。

### Current Role

只参考其：

- dataset directory；
- config；
- metadata；
- parallel generation；
- deterministic seed；
- question/label organization；
- train/val/test split。

不依赖其具体 simulation/render code。

### Status：Superseded as implementation base

---

## 11. Physics engine vs analytic simulator

### Earlier Possibility

考虑 Kubric / PyBullet / Blender。

### Current Conclusion

对 single puck + fixed barrier，physics engine 是 unnecessary complexity。

采用：

- exact event-based analytic collision；
- NumPy simulator；
- 2D raster renderer。

优点：GT 精确、无 engine artifact、极快。

### Status：Current

---

## 12. 纯白背景 canonical set

### Earlier Idea

Experiment 2 用最极简 white background + ball + line。

### Concern

对 natural-video pretrained foundation model 太 OOD；也可能无法判断平面是水平还是竖直，造成 gravity ambiguity。

### Current Design

Canonical 使用：

- 简洁但自然的 overhead tabletop；
- fixed surface；
- fixed puck skin；
- fixed barrier style；
- 无 clutter。

Mechanistic subset 是 broad benchmark 的子分布，而不是完全不同 domain。

### Status：Current

---

## 13. 渲染场景：台球 vs 普通桌面

### New Concern

必须强烈表达：

> 这是俯视水平面，重力不应沿 image y 方向作用。

### Candidate Solution

同时使用多个 semantic skin：

- billiards-like；
- air-hockey-like；
- visible-boundary tabletop/lab。

### Barrier Design Revision

曾考虑台球杆/三角架，但它们现实中可移动，与 fixed infinite-mass barrier 的 simulator law 冲突。

改为：

- fixed barrier rail；
- clamp/support/anchor visual cue。

### Object Skin Revision

条纹/号码台球会带来真实 3D rolling texture 问题。

第一版更倾向：

- plain color；
- radial shading；
- puck-like disk。

### Status：Current/Tentative（具体 skin 比例尚未 pilot）

---

## 14. Ball–Ball dynamics

### Earlier Dislike

曾认为球-球系统“混沌”，小扰动导致结果巨大变化，不适合分析。

### Clarification

单次 two-ball collision 本身解析且稳定；真正高度敏感的是：

- 多球；
- 多次碰撞；
- 长 rollout。

### Current Decision

第一版仍不做 Ball–Ball，因为 single puck + barrier 已足够回答主要问题。

### Status：Deferred

---

## 15. VLM 选择演化

### Naive Criterion

“选当前开源最强 VLM”。

### Revised Criterion

更重要的是：

- strong enough；
- video-native；
- open；
- clean architecture；
- activation accessible；
- 4×A800 feasible。

### Current Primary Choice

**Qwen2.5-VL-7B**。

原因：

\[
\text{Video ViT}\rightarrow\text{Patch Merger}\rightarrow\text{LLM}
\]

结构较清楚。

### Why Not Qwen3-VL Primary

DeepStack / multi-level visual injection 增加 mechanistic confound。

### Status：Current

---

## 16. V-JEPA 版本选择

### Current Primary

V-JEPA2 ViT-L + native predictor。

### Secondary

V-JEPA2.1 ViT-L 作为 training-objective robustness。

### Why Not Start Only with 2.1

2.1 增加 dense/deep supervision，本身改变 representation objective；如果只做 2.1，会让最干净的 encoder-predictor narrative 少一个基础参照。

### Status：Current

---

## 17. Supervised Fine-Tuning 作为主实验轴

### Earlier Plan

曾考虑：

- frozen；
- LoRA；
- partial FT；
- full FT

统一比较，并分析 SFT 前后 physics representation。

### Revision

主问题已经从“怎样做最好 physics evaluator”转向：

> pretrained model 本身怎样组织 physical computation？

大量 FT 会混淆：

- pretraining 自发形成的结构；
- benchmark supervision 后新学的结构。

### Current Status

**Rejected as main axis.**

只有出现明确机制 hypothesis 时再做 follow-up。

---

## 18. 性能提升 extension

### Question

Mechanistic interpretability 是否应该导出直接 performance improvement？

### Current Position

不是顶会成立的必要条件，但可以自然做 optional extension：

- layer fusion；
- physics-head selective LoRA；
- shortcut suppression；
- circuit-guided tuning。

必须由主结果“指向”改进，而不是为了涨点强行加模块。

### Status：Optional

---

## 19. Publication Strategy

当前判断：

- 只有大规模 layerwise probe table：贡献可能偏 incremental；
- probe + 严格统一 benchmark + architecture-level finding：具有主会潜力；
- 再加 causal intermediate / interchange intervention：更接近真正强的 mechanistic story。

不要求新 SOTA 或新 architecture。已有 Othello-GPT、Joseph 等工作证明：

> 可信、非平凡的模型内部科学发现本身可以成为顶会贡献。
