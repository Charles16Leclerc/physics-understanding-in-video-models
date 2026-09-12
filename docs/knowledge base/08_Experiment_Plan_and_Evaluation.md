---
title: Experiment Plan and Evaluation
status: Current
updated: 2026-09-12
tags: [experiment-plan, evaluation]
---

# 实验计划与评测

## 1. 总体执行顺序

项目不应一开始就把：

\[
\text{模型}\times\text{任务}\times\text{层}\times\text{probe}\times\text{数据}
\]

全部铺满。

当前推荐分阶段：

1. benchmark qualification；
2. simulator/render pipeline sanity；
3. V-JEPA2 ViT-L cheap layer sweep；
4. token-aware probe；
5. Qwen2.5-VL 对应分析；
6. architecture comparison；
7. mechanistic causal microscope；
8. robustness / scale-up；
9. Optional interpretability-guided improvement。

## 2. Stage 0：Benchmark Qualification

在 foundation model 进入之前先验证任务本身。

### 2.1 Split integrity — 必须

- split 按 latent scene / initial condition，而不是按 render video；
- 同一 trajectory 的不同 texture / background 不能跨 split；
- 固定 deterministic seed 和 scene ID。

### 2.2 Nuisance marginal check — 必须

确认 label 不被以下单变量强预测：

- color；
- scene family；
- speed magnitude；
- absolute x/y position；
- barrier angle；
- texture；
- clip length。

### 2.3 GT-state → target readout — 必须

对 simulator 真 state 直接训练与模型 probe 同类 readout。

#### Prediction 资格目标

希望出现：

\[
\text{GT-State Linear} \ll \text{GT-State MLP/Oracle}.
\]

例如：

\[
60\%\quad vs\quad 99\%.
\]

若 Linear(state) 已经 99%，则这个 target 不适合用来证明 “predictor 执行了额外关系计算”。

### 2.4 Judgment shortcut baselines — 必须

至少：

- first frame only；
- last frame only；
- random frame only；
- pre-state only；
- post-state only。

这些都应接近 chance 或显著低于 full relation oracle。

### 2.5 Full-GT oracle — 必须

用完整 \((pre,geometry,post)\) / analytic rule 应接近 ceiling。

否则先排查：

- label bug；
- ambiguous transition；
- simulator/render mismatch。

### 2.6 Temporal controls — task-dependent

- frame shuffle；
- temporal reverse；
- single-frame baseline。

只对真正需要 temporal information 的任务运行。

## 3. Stage 1：Simulator + Renderer Pilot

小规模生成：

- canonical scene；
- 至少两个 diverse render family；
- valid/invalid matched pairs。

人工检查：

- 明确是俯视水平 surface；
- barrier 看起来固定；
- 运动连续；
- invalid transition 不因 artifact 太显眼；
- collision timing 与 GT 对齐。

同时验证 codec / frame-rate 不会产生明显时间偏差。

## 4. Stage 2：V-JEPA2 Cheap Full-Depth Map

主模型：V-JEPA2 ViT-L + predictor。

所有层 × 所有核心 target：

- Mean-Linear；
- Mean-MLP。

State target：

- position；
- velocity；
- speed；
- heading；
- barrier normal。

Prediction target：

- collision-within-H；
- TTC；
- post-collision velocity。

Judgment target：

- valid/invalid；
- violation severity（若 pilot 成功）。

输出：完整 layerwise curve。

## 5. Stage 3：Token-aware Readout

对 preregistered normalized depths：

- Attentive Pooling；
- Relational Transformer。

目标是区分：

\[
\text{pooling/aggregation limitation}
\]

与：

\[
\text{need for additional relational computation}.
\]

### 示例解释

如果：

- Mean-Linear 55%；
- Mean-MLP 57%；
- Attentive Pooling 92%；
- Relational Transformer 93%；

说明主要问题是 information localization / aggregation。

若：

- Attentive 60%；
- Relational 92%；

则更支持还需要新的 token-token computation。

## 6. Stage 4：Qwen2.5-VL 分析

### Vision tower

对 vision layers 做与 V-JEPA encoder 类似的：

- Mean-Linear / MLP；
- 部分 token-aware probe。

### Merger boundary

probe merger output，观察：

- state 是否保留；
- temporal relation 是否改变；
- 是否只是维度/patch merge 造成 accessibility 变化。

### LLM

至少区分：

- visual token hidden state；
- question token；
- answer/decision position。

研究：

- state 在 visual tokens 中是否保持；
- prediction 在哪类 token / 哪些 depth 形成；
- judgment 是否与 prediction 同步、提前或分叉。

## 7. Stage 5：Architecture Comparison

重点不是原始 accuracy 谁更高，而是比较结构：

- State 在哪里 explicit；
- Prediction 从哪里开始 readout class 降低；
- Judgment 是否有稳定层级；
- V-JEPA predictor 是否表现出专门 future computation；
- VLM 是否表现为 task-conditioned branch。

推荐主图：

- model stage × target × readout class heatmap；
- layerwise normalized accessibility curve；
- State/Prediction/Judgment 三类 schematic。

## 8. Stage 6：Mechanistic Microscope

从同一 benchmark 的 canonical subset 选约 1k–3k scenes。

重点 target：

- \(v\)；
- \(n\)；
- \(\tau\)；
- collision；
- validity。

流程：

1. 确定高可读层；
2. 找 candidate subspace；
3. matched source/base pair；
4. interchange intervention；
5. 与真实 counterfactual output 对齐；
6. 必要时 patch token/head/path。

## 9. Stage 7：Robustness

优先级：

1. V-JEPA2 ViT-g 关键结果 scale-up；
2. V-JEPA2.1 ViT-L；
3. held-out semantic render family；
4. LLaVA-OneVision；
5. external benchmark sanity check。

## 10. 外部 benchmark 的当前定位

### Current

不是主矩阵的一部分。

只作为：

- ecological validity；
- qualitative trend check；
- appendix robustness。

如果时间不足，宁可不做外部 benchmark，也要完成 causal experiment。

## 11. Optional：Interpretability-guided Improvement

只有在主机制结果自然指向某种改进时才做。

可能：

### Layer fusion

若中层 state / predictor feature 比 final representation 更有 physics signal：

\[
[h_{state-rich},h_{prediction-rich},h_{final}]
\rightarrow
\text{tiny fusion head}.
\]

### Selective tuning

若定位出 causal physics heads / layers：

- 只对这些位置做 LoRA；
- 与 same-parameter random LoRA 比较。

### Shortcut suppression

若 VLM 明显依赖 appearance shortcut：

- suppress shortcut subspace / heads；
- enhance physics-relevant pathway；
- 测 held-out skin OOD。

这部分不作为项目成立的必要条件。

## 12. Metrics

根据 target 类型：

- classification：accuracy / balanced accuracy / AUROC；
- regression：R² / MAE / normalized error；
- direction：angular error；
- severity：correlation + calibration；
- causal intervention：counterfactual agreement / causal effect size。

## 13. Oracle-normalized accessibility

跨 task 原始 accuracy 不可直接比较。

可考虑：

\[
\tilde P=
\frac{P-P_{chance}}
{P_{oracle}-P_{chance}}.
\]

再定义 readout threshold：

\[
C^*(y,l)=
\min\{C(r):\tilde P\ge\tau\}.
\]

### Tentative

是否把该量作为 paper main metric，需要等 pilot 看其稳定性。
