---
title: V-JEPA Downstream and Extension Survey
status: Current
updated: 2026-09-12
tags: [vjepa, downstream, survey]
---

# V-JEPA 下游与扩展工作调研

> 这份文档保留项目形成阶段对“学界把 V-JEPA2 用到什么程度”的调研。它的主要作用是帮助判断：V-JEPA encoder/predictor 能承担什么功能、哪些 extension 已被证明可行、哪些方向不需要我们自己重新训练。

## 1. 总体结论

V-JEPA2 已经不只是一个“视频编码器 benchmark backbone”。现有工作大致证明它可以作为：

- frozen video representation；
- future latent predictor；
- VQA / multimodal visual front-end；
- action anticipation module；
- action-conditioned world model；
- VLA temporal/dynamics plug-in；
- dynamic physical property reader；
- 各类 task-specific fine-tuning backbone。

这支持本项目一个重要认识：

> **Encoder 和 Predictor 应该被作为两个有不同功能角色的研究对象，而不应只 probe final encoder feature。**

---

# V-JEPA2 原始工作

## 2. Frozen Encoder + Attentive Probe

V-JEPA2 原始工作大量下游评测采用：

\[
\text{frozen encoder}
+
\text{attentive probe/readout}.
\]

而不是简单 global mean linear classifier。

这说明官方本身已经承认：

> dense video tokens 中的信息往往需要 learnable aggregation 才能用于下游。

### 对本项目的启发

- Mean pooling 不是唯一合理接口；
- attentive readout 是正式、标准的 V-JEPA evaluation 方式；
- 我们把 aggregation 与 relational computation 分开是合理扩展。

## 3. V-JEPA2 + LLM

原论文中 V-JEPA2 visual encoder 被接入 LLaVA-style multimodal system，用作视频语言理解前端。

典型：

\[
\text{video}
\rightarrow
\text{V-JEPA2}
\rightarrow
\text{attentive pooler/projector}
\rightarrow
\text{LLM}.
\]

在受控比较中，V-JEPA2 visual representation 在多个 temporal/video benchmark 上表现很有竞争力。

### 对项目的启发

早期曾提出：

> V-JEPA2 + LLM 可能是很自然的 physics evaluator。

从原论文看，这个方向工程上是成立的。

### 当前项目决策

**Deferred。**

没有合适的官方完整 V-JEPA2+LLM checkpoint 可直接做当前所需 controlled mechanistic comparison，自行做 video-language alignment 代价过大。

因此只把它作为未来 implication，而不是主实验。

## 4. V-JEPA2-AC

V-JEPA2-AC 是 action-conditioned predictor / world-model 方向，更接近真正 causal dynamics：

\[
(z_t,a_t,s_t)\rightarrow \hat z_{t+1}.
\]

采用更适合 forward dynamics 的 causal / block attention 设计。

### 对项目的启发

它帮助纠正：

> 原始 V-JEPA2 predictor 不应被过度称作“物理 forward simulator”。

原始 predictor 更像 masked latent completion；V-JEPA2-AC 才更接近 action-conditioned causal dynamics model。

### 当前角色

不是主模型，但可在 Discussion 说明：

- predictor 类型本身也会决定 Prediction 的内部组织；
- 若未来扩展到 action-conditioned physics，可考虑 V-JEPA2-AC。

---

# Task-specific Fine-Tuning Examples

## 5. BADAS

利用 V-JEPA2 representation 做特定视频/行为理解任务，并进行有针对性的 adaptation。

### 对我们的意义

说明 V-JEPA2：

- frozen representation 已强；
- task-specific tuning 可进一步强化；
- 并不是只能做原生 JEPA objective。

### 为什么 Fine-Tuning 不作为当前主线

本项目研究：

> **pretrained model 本身已经形成什么 physical organization。**

若一开始大量 fine-tune，很难区分：

- pretraining 形成；
- benchmark supervision 教进去。

## 6. BADAS-2.0

BADAS 后续强化了更复杂时序/行为理解能力，说明 V-JEPA2 可以在 task-specific setting 中被继续挖掘。

项目只把它当“adaptability”证据，不把其方法直接引入主实验。

## 7. FERAL

代表另一类利用 frozen/self-supervised video feature 做更复杂时空任务的工作。

意义仍是：

> V-JEPA representation 可以被各种轻量 head 读取，但 head 本身的能力会显著影响 downstream score。

---

# V-JEPA2 作为互补 Temporal Representation

## 8. PVI — Plug-in Visual Injection for Vision-Language-Action Models

PVI 类工作将 V-JEPA2 representation 作为额外 temporal/dynamics feature 注入 VLA / multimodal policy。

### 对我们的启发

它直接支持：

\[
\text{dynamics-centric representation}
+
\text{semantic/reasoning model}
\]

可能互补。

这与我们未来 Discussion 中的 hybrid idea 一致：

> V-JEPA state/prediction substrate + LLM judgment reasoner。

但现有 PVI 主要目标是 policy/VLA 性能，而不是解释 physics computation。

## 9. StageWAM

JEPA-style representation 被引入 world/action modeling 的 staged pipeline。

项目层面意义：

- JEPA representation 可以作为中间 world state；
- downstream module 不必与 encoder 同目标训练。

## 10. PiJEPA

代表 JEPA 与 policy/control/interaction 结合的方向。

进一步说明 JEPA representation 并不局限于 classification，而天然适合被视作 world-state substrate。

---

# V-JEPA2 作为 Physics-aware Representation

## 11. Inferring Dynamic Physical Properties from Video Foundation Models

从 frozen V-JEPA2 等 representation 中读出：

- elasticity；
- viscosity；
- dynamic friction。

### 对我们的启发

这是“V-JEPA 中存在可用动态物理量”的直接实证。

同时也提醒：

- readout architecture 很重要；
- 能读属性 ≠ 模型一定在 future computation 中使用这些属性。

正好与我们的 causal stage 互补。

## 12. PHANTOM

代表利用视频 foundation representation 做更物理/动态相关理解的扩展。

### 对项目的启发

说明 temporal self-supervised representation 在 physics-aware task 上确实有迁移价值。

但现有工作主要问“能不能用”，我们要问“内部怎样组织和使用”。

---

# Representation-analysis Work

## 13. What, Where, and How

逐层 probe V-JEPA2 / VideoMAE 等时空 representation。

重要结论：

- motion/camera feature 有明确 layer structure；
- IntPhys2 judgment 并不会因为 dynamics representation 强就自动变得线性可读。

这直接支持 State/Prediction/Judgment 分解。

## 14. Do Video Foundation Models Understand Intuitive Physics?

比较：

- pooled linear；
- pooled MLP；
- attentive probe。

重要结论：

> readout interface 会大幅改变你对 representation 中 physics information 的判断。

这直接演化成我们的 aggregation vs computation 框架。

## 15. Interpreting Physics in Video World Models

Joseph et al., ICML 2026。

这是当前最直接前驱：

- physics emergence；
- subspace geometry；
- attention ablation；
- steering。

我们的差异是把：

- predictor；
- prediction computation；
- VLM judgment；
- causal intermediate

纳入统一问题。

---

# V-JEPA2.1

## 16. V-JEPA2.1: Unlocking Dense Features in Video Self-Supervised Learning

V-JEPA2.1 加入更强的：

- dense predictive loss；
- deep self-supervision；
- multi-level feature constraints。

其目标之一就是改善 dense/local feature quality，同时保留 high-level representation。

### 为什么对本项目重要

我们当前非常关心：

> 一个 spatiotemporal token 到底有多少 local 信息、多少 globalized information？

V-JEPA2.1 本身的设计就说明：

- 原始 V-JEPA2 dense token 未必已经是完美 local physical descriptor；
- pretraining objective 可以显著改变中间 token 的 spatial grounding。

因此 V-JEPA2.1 是非常有意义的 robustness model：

> stronger dense-state supervision 是否让 State 更早、更局部、更低 readout cost 地出现？

---

# Negative / Boundary Cases

## 17. Surgical Phase Segmentation 等比较

一些下游研究显示：V-JEPA2 并非在所有视频任务都天然压倒其他 representation。

这对项目很重要：

> 不要把“predictive self-supervised representation”提前神化成“必然最懂一切 dynamics”。

V-JEPA predictor 也不是专门物理引擎，尤其原始 pretraining 是 masked latent prediction，不是干净的 frame-to-frame simulator。

---

# JEPA + Semantic Reasoner Hybrids

## 18. ThinkJEPA

代表将 JEPA-style latent/world representation 与更强 reasoning/semantic module 结合的方向。

### 对项目的意义

这类工作从侧面支持早期 intuition：

- JEPA 强在 state/dynamics substrate；
- LLM/semantic model 强在 reasoning/judgment；
- 两者组合可能是自然方向。

但本项目不以“训练一个 hybrid system”为主贡献，因为：

- alignment 成本高；
- 研究问题会转向模型设计；
- 很难保持 mechanistic comparison 洁净。

---

# 19. 当前综合判断

从整个 V-JEPA ecosystem 得到的项目级结论：

1. **V-JEPA2 encoder 是强视频 state representation，但不能假设所有物理量都在 final mean-pooled feature 中显式。**
2. **原始 predictor 是非常值得单独研究的模块，但应称为 latent conditional predictor，而不是直接等同真实 physics simulator。**
3. **V-JEPA2 已被成功接到 LLM / VLA / planning / action model，因此 state representation 与 semantic reasoner 的互补性有现实基础。**
4. **已有工作大量关注下游性能和 representation quality，仍缺少 State / Prediction / Judgment 的统一机制比较。**
5. **V-JEPA2.1 提供一个很好的“改变 pretraining objective 后内部物理 organization 是否改变”的 secondary model。**
6. **本项目不需要重复证明 V-JEPA“有用”，而应回答它和 VLM 究竟以什么不同方式组织物理 computation。**
