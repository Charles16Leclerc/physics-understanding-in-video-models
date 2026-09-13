---
title: Related Work
status: Current
updated: 2026-09-12
tags: [related-work, literature]
---

# Related Work

> 本文档不是普通“论文列表”，而是记录：**每篇工作具体做了什么、给本项目的哪一项设计提供了方法学地基、它没有解决什么，以及当前发表状态。**

## 1. 最直接前驱：Interpreting Physics in Video World Models

**Sonia Joseph et al., 2026**  
**发表状态：ICML 2026。**

### 做了什么

这项工作系统分析大型视频 encoder 中的 intuitive-physics representation，主要模型包括 V-JEPA 2 与 VideoMAE-v2。

主要方法：

- layerwise linear probing；
- 对速度、加速度等物理量做解码；
- representation geometry / subspace 分析；
- patch-level / attention 分析；
- attention ablation；
- causal steering（仅对单一物理量steer后再probe，并非steer某物理量后看预测/判断变化）。

核心结果之一是所谓 **Physics Emergence Zone (PEZ)**：部分物理量在网络约三分之一深度附近开始明显线性可读。

他们还发现：

- speed / acceleration magnitude 往往较早可读；
- direction 更晚稳定；
- 方向并不是一个简单一维变量，而是高维、近似圆形/分布式的 population code；
- 不同 physical task 的子空间未必共享一个紧凑“physics state”，甚至可接近正交；
- 某些 local spatial/temporal heads 对物理表示有明显 causal contribution；
- PEZ对attention ablation基本保持（可能是IntPhys shortcut原因？）；
- 以表征的patch/时空分布的视角来看，在PEZ区域，表征从零散分布在部分patch中变为分布在全部patch中，使得单一patch也突然能读出表征了。

### 对本项目的方法学贡献

这篇工作证明了：

> **大型 pretrained video encoder 的内部物理表示可以被逐层 probe、几何分析、ablation 和 steering。**

直接影响我们：

- 全层 cheap probe 的设计；
- 不把 final layer 当作唯一表示；
- 对不同 physical variable 分别画 emergence curve；
- 重视 causal test，而不满足于 decodability；
- 不假定“physics”是单一低维向量。

### 它没有回答什么

- 重点是 **encoder representation**，不是 encoder→predictor 的计算链；
- 没系统区分 State / Prediction / Judgment；
- 没比较 V-JEPA predictor 与 VLM LLM 的功能组织；
- 没用 ground-truth intermediate 去恢复从 state 到 future event 的内部算法；
- judgment 并不是核心分析对象。

因此它是最直接的 representation-level 前驱，但本项目希望进一步研究：

$$
\text{state representation}
\rightarrow
\text{future computation}
\quad\text{以及}\quad
\text{judgment/reasoning}.
$$

---

## 2. Do Video Foundation Models Understand Intuitive Physics? A Layerwise Probing Analysis

**2026**  
**发表状态：截至 2026-09-12 为 arXiv / CoRR preprint，未查到正式主会发表。**

### 做了什么

对 V-JEPA、VideoMAE、LTX-Video 等模型进行 intuitive-physics layerwise probing，并比较不同 readout：

- mean-pooled linear；
- mean-pooled MLP；
- 保留时空 token 的 attentive probe。

重要结果：

> physics performance 对 readout 形式非常敏感，尤其 temporal/spatial structure 被 mean pooling 抹掉时，简单 probe 会显著低估 representation 中的信息。

论文中 attentive probe 使用：

- 1 个 self-attention block；
- 1 个 cross-attention classification block；
- 多头注意力；
- 结构参考了 V-JEPA attentive probing、EVL 类 frozen-video learner 以及 attentive-probing 文献。

其 MLP 还做过较多超参数搜索。

### 对本项目的重要性

这项工作直接促使我们把“probe complexity”进一步拆成：

- **aggregation difficulty**；
- **computational difficulty**。

并形成当前四级 readout：

$$
\text{Mean-Linear}
\rightarrow
\text{Mean-MLP}
\rightarrow
\text{Attentive Pooling}
\rightarrow
\text{Relational Transformer}.
$$

### 我们怎样扩展它

我们不只问“哪个 probe 更强”，而是希望解释：

- Mean→Attentive 的提升是否来自 token selection；
- Attentive→Relational 的提升是否说明仍需要新的关系计算；
- readout class 如何与 State/Prediction/Judgment 和模型 stage 共同变化。

此外，我们不打算像该工作那样对每层独立搜索不同 MLP architecture，因为这会破坏 layer comparison 的解释洁净度。

---

## 3. What, Where, and How: Probing Spatiotemporal Representations in Video Foundation Models

**2026-09**  
**发表状态：arXiv preprint。**

### 做了什么

对 V-JEPA2 / VideoMAE-v2 逐层研究：

- camera motion；
- anomaly detection；
- IntPhys2 intuitive physics；
- representation 的 temporal trajectory / geometry。

重要现象包括：

- camera motion 有很清晰的 layer organization；
- anomaly signal 某些层可读；
- IntPhys2 在简单 pooled probing 下仍然很差；
- 强 spatiotemporal representation 不等于存在一个简单可读的 “physics-validity” label。

### 对我们的意义

它进一步支持：

> **representation 中有丰富动态结构，并不意味着 judgment 可以被简单线性读取。**

这正是我们将 State / Prediction / Judgment 拆开的理由。

### 与我们的 gap

- 没有显式 V-JEPA predictor analysis；
- 没有 readout-class 梯度地分析 aggregation vs computation；
- 没有 VLM ViT/LLM 对比；
- 没有使用解析 physical intermediate 做 causal intervention。

---

## 4. Inferring Dynamic Physical Properties from Video Foundation Models

**2026**  
**发表状态：CVPR 2026 Workshop（VGBE）。**

### 做了什么

从 frozen V-JEPA2 等视频模型 representation 中，用轻量 readout 估计动态物理属性：

- elasticity；
- viscosity；
- dynamic friction。

主要使用小型 cross-attention / probe，而不是大规模 fine-tuning。

### 对我们的意义

证明：

> V-JEPA2 representation 不只是 action/semantic feature，还包含可用于读取真实动态物理属性的信息。

这为我们把 velocity / geometry / dynamics intermediate 作为 probe target 提供支持。

### Gap

它研究的是“能否读出物理属性”，不是：

- state 如何变 prediction；
- predictor 是否显式化 future；
- judgment 如何形成；
- 这些量是否被模型 causally used。

---

## 5. How Do Transformers “Do” Physics? Investigating the Simple Harmonic Oscillator

**Kantamneni, Liu, Tegmark, 2024**  
**发表状态：Entropy 2024。**

### 做了什么

在一个受控数值简谐振子 Transformer 上，作者不是只问“某物理变量是否可读”，而是提出候选内部算法，并用多种证据比较模型是否真的在执行这些算法。

其核心方法标准包括：

1. 候选 intermediate 是否能从 hidden state probe；
2. 该 intermediate 的编码强度是否与模型表现相关；
3. intermediate 是否能解释 hidden-state variance；
4. **对 intermediate 做 intervention 后，输出是否按候选算法的预测改变。**

最终目标是回答：

> 模型内部究竟运行什么计算，而不仅是存了什么变量。

### 对本项目的重要性

这是 Experiment 2 最直接的方法学原型之一。

我们的 Ball/Puck–Barrier 同样有明确解析计算图：

$$
(p,v,n,c)
\rightarrow
\tau
\rightarrow
v^+
\rightarrow
output.
$$

可以借鉴其思想：

- probe intermediate；
- 比较 emergence order；
- 对 intermediate 做 intervention；
- 检验 output 是否按真实方程变化。

### Gap

SHO 是小型、数值序列、专门训练的 toy Transformer；我们的目标是：

- 大型 pretrained visual/video model；
- 从 RGB 中建立物理 state；
- 比较 predictive model 与 multimodal LLM；
- 分析视觉 state → future prediction / judgment。

---

## 6. Emergent World Representations / Othello-GPT

**Li et al.**  
**发表状态：ICLR 2023 Oral。**

### 做了什么

研究只看 Othello move sequence 的 GPT 是否形成隐式棋盘 world state。

经典贡献：

- probe 内部 board state；
- 发现简单早期 probe 可能低估 representation；
- 对内部 state 做 intervention；
- 观察模型下一步行为是否随修改后的 world state 改变。

### 对我们的意义

Othello-GPT 是“**world state decoding + causal intervention**”最经典的范式之一。

它提醒我们：

- 解码能力和真实 causal use 必须区分；
- 更复杂 probe 可能只是把隐式信息读出来，不等于模型本身显式使用；
- 最有说服力的是对内部 world state 进行 counterfactual edit。

我们的 Ball–Barrier 是视觉物理版的类似问题。

---

## 7. Distributed Alignment Search (DAS)

**Geiger et al., 2024，正式同行评审方法论文。**

### 做了什么

DAS 不要求高层变量恰好对齐某个 neuron 或 probe weight，而是学习一个 distributed subspace，使：

- low-level neural intervention；
- high-level causal-model intervention

尽可能行为一致。

### 对我们的意义

若 velocity / barrier orientation 不是简单线性 probe direction，而是分布式编码，可用 DAS 作为 fallback。

当前不作为第一选择，因为线性/低维 interchange intervention 更透明、更容易控制。

---

## 8. Attention, Please! Revisiting Attentive Probing Through the Lens of Efficiency

**发表状态：ICLR 2026。**

### 做了什么

系统研究 standard pooled probing 为什么会低估 patch/local representation，并提出更高效的 attentive probing / learned-query aggregation。

核心思想：

$$
Q\xrightarrow{cross-attn}H_{patch}
$$

用少量 learned queries 直接选择有用 patch token，而不是先 mean pool。

### 对我们的意义

直接支持我们把：

- Mean Pooling；
- Attentive Pooling

分成两个独立 readout rung，并把“找到信息”与“重新计算关系”区分开。

---

## 9. Interpretability-guided Performance Improvement 前例

### 9.1 Sparse Feature Circuits

**发表状态：ICLR 2025。**

利用稀疏特征与 circuit 分析定位 task-relevant / irrelevant feature，并通过 SHIFT 等方法移除 shortcut/irrelevant feature，提高泛化性能。

对我们的启发：

- 如果发现 VLM 的 judgment 依赖 appearance shortcut；
- 可 suppress shortcut feature，测试 held-out render family 是否改善。

### 9.2 V-SEAM

**发表状态：EMNLP 2025。**

通过 semantic intervention 定位对 VQA 有正/负作用的 attention heads，再进行 head-level modulation，提高多个多模态模型的 VQA performance。

对我们的启发：

- physics-relevant heads 与 shortcut heads 可用于 selective strengthening/suppression；
- interpretability-guided performance improvement 不要求提出庞大新架构。

### 9.3 Multimodal Language Models See Better When They Look Shallower

**发表状态：EMNLP 2025。**

发现视觉塔中浅/中层对 localization/counting 等细粒度任务保留更好信息，并据此进行 cross-layer feature fusion，提高 multimodal performance。

对我们的启发：

若发现：

- state-rich layer 在中层；
- prediction-rich layer 在 predictor / later layer；

可尝试 interpretability-guided layer fusion，而不是只吃 final feature。

---

## 10. “Task performance 不等于 coherent world model”相关工作

### Evaluating the World Model Implicit in a Generative Model

**发表状态：NeurIPS 2024。**

强调一个模型能完成任务，不代表内部形成了 coherent world model；通过专门设计的诊断去区分行为成功与世界模型结构。

### What Has a Foundation Model Found? Using Inductive Bias to Probe for World Models

**发表状态：ICML 2025。**

进一步讨论怎样通过 probe / inductive bias 测试模型内部是否形成真正 world structure，而不是依赖 shortcut。

### 对我们的意义

直接支持本项目的方法论立场：

> 不把最终 benchmark accuracy 等同于“物理理解”；必须研究 representation、computation 与 causal use。

---

# Benchmark Landscape（项目形成阶段调研）

## 11. IntPhys / IntPhys2

### IntPhys

经典 Violation-of-Expectation benchmark，覆盖 object permanence、solidity、continuity 等 intuitive physics。

它最初吸引项目的原因：

- 不需要 language head；
- 可以用 native surprise / prediction error；
- 很接近“模型是否期待真实物理”。

后来认识到：

$$
\text{predictability}\neq\text{physical validity}.
$$

模型可以稳定预测一个持续漂浮的球，但该过程仍违反重力。

### IntPhys2

更难、更长时序、更强调：

- occlusion；
- object permanence；
- hidden transformation；
- solidity；
- camera excursion。

项目曾考虑把它作为主 judgment benchmark，但后续认为它：

- 过于窄地聚焦遮挡/状态持久；
- 非常难；
- 容易让 specialized geometric/trajectory 方法通过数据集结构获得高分；
- 不代表广义 rigid-body physical reasoning。

当前定位：**stress test / appendix**，不是主 physics definition。

---

## 12. Physion

Physion 经典地把模型分成：

$$
X_{\le t}\xrightarrow{E}p\xrightarrow{D}q\xrightarrow{C}P(contact).
$$

其中 standardized linear/SVM readout 是 task adaptor，不代表理论上认为 encoder 必须直接“存未来接触答案”。

该工作对本项目的重要纠正：

> future contact 从 encoder 线性可读并不一定“不自然”；predictive training 可能把 future-relevant function 编译进 representation。

当前 Physion 更适合：

- future-contact external sanity check；
- 不作为统一三类 benchmark。

---

## 13. CLEVRER

典型合成视频 causal reasoning benchmark，包含：

- descriptive；
- explanatory；
- predictive；
- counterfactual questions。

优点：

- object/event annotation 完整；
- causal reasoning 丰富。

问题：

- QA / symbolic reasoning 成分较强；
- 视觉和问题结构与我们主 diagnostic 不完全一致。

它证明 synthetic world 可同时支持多个 reasoning level，但我们希望物理计算图更简单、更适合 intervention。

---

## 14. ComPhy

关注 compositional physical reasoning，包含 object property / relation / interaction 等复杂设置。

对我们来说过宽，不适合作为最初 mechanistic system，但可作为 future extension 的参考。

---

## 15. PLATO / Physical Concepts / InfLevel / GRASP / PHYRE

这些工作在 intuitive physics、causal reasoning、planning、affordance / physical interaction 等方面提供不同范式。

项目早期广泛调研它们的主要目的不是直接选一个做主 benchmark，而是确认：

- “physics understanding”本来就存在多个 operationalization；
- 需要把 representation、prediction、judgment 分开。

详见 [[19_Benchmark_Literature_Notes]]。

---

# IntPhys2-specialized Follow-up

## 16. Temporal-attention probing

一些 follow-up 说明：简单 pooled representation 在 IntPhys2 上可能接近 chance，而保留 temporal token structure 的 attentive readout 可明显改善。

这进一步推动了本项目的 token-aware probe 设计。

## 17. 3DSPA

主要思想是显式恢复更结构化的 3D / spatiotemporal object information，再进行 physics anomaly / consistency 判断。

对项目的意义：

- specialized geometry-aware method 可以在 IntPhys2 上显著超过 general VLM/VJEPA readout；
- 因此 benchmark 高分不能简单解释为“通用物理理解更强”。

## 18. GeoPhys

使用 geometry / trajectory / 3D reconstruction 等更显式结构对 physical validity 进行判断。

对项目的意义类似：

> IntPhys2 的 specialized success 说明其任务结构可以被有针对性地 exploit，因此我们不把它作为统一 physics benchmark。

---

# V-JEPA Downstream Ecosystem

## 19. V-JEPA2 原始下游用法

原论文已经展示：

- frozen encoder + attentive probe；
- video QA；
- action anticipation；
- action-conditioned planning 等。

尤其 anticipation 中，predictor 可接收 context representation + future mask tokens，预测 future latent，再与 encoder representation 一起供 attentive probe 使用。

这直接证明：

> predictor layer probing future information 在工程和概念上都完全可行。

## 20. BADAS / BADAS-2.0

V-JEPA2 作为视频 representation backbone 进行下游 task-specific adaptation / action understanding。

意义：V-JEPA representation 可被轻量/局部 tuning 迁移，但本项目暂不把 fine-tuning 作为主轴。

## 21. PVI: Plug-in Visual Injection for VLA

将 V-JEPA2 的 temporal/dynamics representation 注入 VLA / multimodal policy。

意义：V-JEPA 与语义/语言模型 representation 具有互补性，支持我们未来在 Discussion 中提出 hybrid dynamics encoder + LLM reasoner 的方向。

## 22. PHANTOM

把 physics-aware / temporal representation 用于更复杂下游理解或操作任务，进一步显示 V-JEPA2 可作为物理动态前端。

## 23. ThinkJEPA / PiJEPA / StageWAM / JEPA hybrids

这些工作探索把 JEPA-style predictive representation 与：

- semantic reasoning；
- policy/world action model；
- multimodal module

组合。

它们支持一个 broad trend：

> dynamics-centric representation 与语义/决策模块可能是互补的。

但本项目不自己训练一个大型 hybrid system，因为成本与科学问题不匹配。

---

# 24. 当前 Related-Work Gap Statement

现有文献分别已经证明：

1. video encoder 中可以存在可解释的 physics representation；
2. readout 形式会显著影响 physics 可读性；
3. toy Transformer 可以通过 intermediate + intervention 恢复内部物理算法；
4. VLM 的视觉信息流与 VQA computation 可以被 mechanistically studied；
5. interpretability finding 可以用于性能改进。

但截至当前调研，没有看到一项工作同时：

$$
\boxed{
\text{V-JEPA encoder/predictor}
\leftrightarrow
\text{VLM vision/LLM}
}
$$

并沿：

$$
\boxed{
\text{State / Prediction / Judgment}
}
$$

系统研究：

- representation accessibility；
- aggregation vs relational computation；
- architecture-conditioned organization；
- physical intermediate 的 causal intervention。

这构成本项目当前最清晰的 academic gap。
