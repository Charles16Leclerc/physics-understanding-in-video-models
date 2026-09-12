---
title: Open Questions and TODO
status: Current
updated: 2026-09-12
tags: [open-questions, todo]
---

# Open Questions 与 TODO

> 本文档只记录尚未决定的事项。每个问题解决后，不删除原条目；在其下追加 `Resolved`、日期、决策和理由，并同步 [[11_Decision_Log_and_Idea_Evolution]]。

## A. Benchmark Physics

### Open Question A1 — finite-barrier 精确碰撞公式与边界 case

需要最终确定：

- segment endpoints 的接触判定；
- disk radius offset；
- 端点碰撞是否视作 point obstacle；
- corner collision 的反射法向如何定义；
- 是否直接排除端点极近 case 以保持物理简单。

### Open Question A2 — friction 是否加入

当前倾向：第一版不加或固定极小摩擦。

需要 pilot 判断：

- 完全匀速是否视觉上过“滑”；
- billiards skin 下无摩擦是否违背模型先验；
- air-hockey skin 是否能自然解决。

### Open Question A3 — violation operators 最终集合

候选：

- wrong reflection normal；
- wrong restitution / speed magnitude；
- impossible penetration；
- spontaneous direction change；
- delayed collision response。

需要选择足够多样但仍共享简单物理计算图的子集。

### Open Question A4 — counterfactual task 是否放主实验

例如：

- 如果 barrier 旋转 \(\Delta\theta\)，是否仍碰撞？
- 如果 barrier 移除，未来位置在哪里？

当前倾向：先不让 counterfactual 成为第三大类之外的额外主轴；可作为 Judgment/Prediction 的 advanced subset。

## B. Rendering

### Open Question B1 — canonical 主要 skin

候选：

- air-hockey；
- billiards；
- lab tabletop。

当前略偏 air-hockey / neutral tabletop，因为 physics semantics 最匹配。

### Open Question B2 — diverse family 比例

需要决定三种 skin 的 sample 比例，以及 train/test 是否做 held-out-family split。

### Open Question B3 — shadow model

是否加入固定轻微阴影以强化俯视/立体感？

风险：shadow 本身可能成为 motion cue / nuisance。

### Open Question B4 — texture pool

需要准备：

- surface textures；
- puck colors/material；
- barrier styles。

原则：避免任何 texture 与 label 相关。

### Open Question B5 — resolution / FPS / duration

需要兼顾：

- V-JEPA/Qwen native preprocessing；
- 速度可视觉识别；
- token 数量与计算量；
- collision 前后帧数。

## C. Task Definition

### Open Question C1 — State target 最终集合

主候选：

- \(p_x,p_y\)；
- \(v_x,v_y\)；
- speed；
- heading；
- barrier normal。

是否加入：

- distance-to-barrier；
- contact state；
- TTC 前置 derived state？

### Open Question C2 — Prediction target 最终集合

候选：

- will-collide-within-H；
- TTC；
- post-collision velocity；
- contact point。

需要先通过 GT-state qualification。

### Open Question C3 — Judgment target 最终集合

至少：

- binary valid/invalid。

强烈考虑：

- severity regression。

### Open Question C4 — query time

模型看到视频到哪个时间点？

例如 Prediction：

- collision 前固定帧数截止；
- 还是随机 query time？

需要控制避免 position 直接泄漏 TTC。

## D. Probe Architecture

### Open Question D1 — attentive pooling query 数

候选：1 / 4 / 8 learned queries。

### Open Question D2 — attention heads / hidden width

应固定跨 layer/model，或用相同比例映射？

### Open Question D3 — relational transformer depth

当前倾向 1 block；是否需要 2-block robustness？

### Open Question D4 — Mean-MLP width

当前建议固定 512 hidden，需要 pilot 确认不过窄/不过强。

### Open Question D5 — object-mask pooled state control

哪些 State target 必须同时报告 oracle-mask pooled 版本？

## E. Layer / Token Sampling

### Open Question E1 — exact normalized-depth grid

24-layer、32-layer、40-layer、LLM 28-layer 的统一归一化点需要最终列 config。

### Open Question E2 — VLM LLM token positions

最终至少保留哪些：

- mean visual token；
- selected visual tokens；
- final question token；
- first answer token；
- EOS / decision token？

### Open Question E3 — V-JEPA predictor token semantics

predictor 的 context / mask / target token 在不同 eval setup 中如何对应，需要结合官方 code 确定 probe interface。

## F. Causal Intervention

### Open Question F1 — 第一个 intervention variable

优先候选：

1. barrier normal \(n\)；
2. velocity \(v\)。

barrier orientation 的 counterfactual 可能最直观。

### Open Question F2 — interchange pairing algorithm

需要匹配：

- 尽可能相同 appearance；
- 相似非目标 state；
- 仅目标变量明显不同；
- source activation 在自然 manifold 上。

### Open Question F3 — selectivity metric

干预某变量后，除了目标 output 改变，还要测：

- 其他 state readout 是否保持；
- unrelated task 是否保持；
- activation norm / distribution shift。

### Open Question F4 — 什么时候触发 DAS

建议预设标准，例如：

- linear subspace probe 好但 intervention 无 selectivity；或
- nonlinear probe 明显强、linear 持续弱。

## G. Model Scope

### Open Question G1 — Qwen2.5-VL 具体 checkpoint

7B-Instruct 是否最合适？是否需要 base/non-instruct 对照？

### Open Question G2 — V-JEPA2 checkpoint

ViT-L 的具体官方 checkpoint / preprocessing / clip length 配置。

### Open Question G3 — robustness model 顺序

当前建议：

1. ViT-g key experiments；
2. V-JEPA2.1-L；
3. LLaVA-OneVision；
4. Qwen3-VL。

需要根据主结果调整。

## H. External Data

### Open Question H1 — 投稿前是否必须 external sanity check

当前判断：不是科学上必须。

若 reviewer-generalization 风险过高，可加一个极轻 external trend validation。

## I. Performance Improvement

### Open Question I1 — 是否增加 interpretability-guided performance method

候选：

- layer fusion；
- selective LoRA；
- shortcut suppression。

只有当主结果自然指向其中一个时才做。

## J. Publication / Narrative

### Open Question J1 — 最终标题

当前工作标题：

> From State to Prediction and Judgment: Dissecting Physical Reasoning across Predictive Video Models and Video-Language Models

可能投稿前需要根据实际结果缩短。

### Open Question J2 — 最终 contribution emphasis

取决于结果可能更偏：

- architecture organization；
- computational accessibility；
- causal algorithm recovery；
- VLM vs predictive model contrast。
