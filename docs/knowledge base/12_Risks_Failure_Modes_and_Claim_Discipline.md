---
title: Risks, Failure Modes, and Claim Discipline
status: Current
updated: 2026-09-12
tags: [risks, failure-modes, claims]
---

# 风险、失败模式与 Claim 纪律

## 1. 最大科学风险：Probe 结果最容易被过度解释

最基本层级：

\[
\text{probe decodable}
\not\Rightarrow
\text{model uses it}
\not\Rightarrow
\text{it is causally necessary}
\not\Rightarrow
\text{it is the model's algorithm}.
\]

任何论文写作都必须严格对应证据等级。

## 2. Mean Pooling 失败可能伪装成 Representation 失败

若完整 token 中信息很局部，mean pooling 可能：

- 稀释；
- 正负抵消；
- 混淆 object identity。

所以 pooled linear probe 失败不能直接写：

> “该层没有 velocity information”。

必须结合：

- object-mask pooling；
- attentive pooling；
- full-token probe。

## 3. Probe 成功可能是 Probe 自己完成了任务

强 MLP / Transformer probe 可能直接从基础 state 中重新计算 future collision。

因此“强 probe performance”不能自动证明 backbone 已经显式表示 final answer。

必须结合：

- readout class；
- GT-state baseline；
- layerwise comparison；
- causal intervention。

## 4. Future target 本身线性会制造假“预测”发现

若：

\[
x_{t+\Delta}=x_t+v_t\Delta,
\]

且 encoder 线性表示 \(x_t,v_t\)，则 future position 自然线性可读。

这不证明模型“预测了未来”。

因此主 Prediction target 应通过 GT-state linear/nonlinear qualification。

## 5. Synthetic benchmark shortcut

高风险 shortcut：

- color 与 label 相关；
- invalid case 总是某个方向；
- 某些 barrier angle 更常为 bad；
- valid/invalid 速度分布不同；
- 第一帧/最后一帧就能判断；
- render family 暗示 label。

解决：

- marginal matching；
- latent-scene split；
- single-frame baseline；
- GT-state controls；
- held-out skin transfer。

## 6. Semantic-prior mismatch

如果 simulator 规定某物体固定不动，但 renderer 看起来像现实中应该移动的物体（例如台球杆、三角架），模型的“错误”可能其实来自更真实的 world prior。

因此视觉 object semantics 应尽量与模拟物理一致。

## 7. 过度抽象 rendering 导致 OOD

纯白背景 + 圆 + 线可能让 natural-video pretrained 模型把场景当 icon/diagram。

因此 canonical 应简洁但自然，不必追求完全像数学示意图。

## 8. 单一 toy benchmark 可能产生漂亮但不可泛化的 circuit

风险：

- 模型只学/调用 billiards-specific prior；
- circuit 只对一套 skin 有效。

缓解：

- 多 semantic render families；
- same physics / held-out skin；
- 关键趋势可选 external sanity check。

但不能为了 generality 牺牲 mechanistic cleanliness。

## 9. V-JEPA vs VLM 接口不匹配

两类模型功能并不等价：

- V-JEPA predictor 输入/输出 latent；
- VLM 最终输出语言 token；
- LLM 有巨大 pretrained knowledge。

因此禁止简单用一个 benchmark score 得出：

> “A 比 B 更懂物理”。

正确 claim：

> 比较它们在 State/Prediction/Judgment 上的内部组织方式和 accessibility pattern。

## 10. LLM 不能放进简单 complexity ladder

预训练 LLM ≠ 一个更大的 scratch Transformer probe。

它带有：

- 大量参数；
- world knowledge；
- language prior；
- instruction training。

因此应作为 separate reasoner，而不是 `Linear<MLP<Attention<LLM` 的最后一格。

## 11. 不同模型 layer depth 不天然对齐

V-JEPA 24 层、VLM vision 32 层、LLM 28 层等，raw layer index 不可直接比较。

可使用：

- normalized depth；
- module boundary；
- emergence transition；
- within-model curve。

跨模型最重要的是功能 stage，不是“第 12 层 vs 第 12 层”。

## 12. Probe hyperparameter search 可制造 layer-selection bias

若每层独立搜索不同：

- MLP depth；
- hidden width；
- dropout；

最终性能同时反映 representation 与 probe architecture。

因此主实验固定 architecture，只小范围统一调优化超参。

## 13. Causal intervention 的 off-manifold 风险

简单：

\[
h'=h+\alpha u
\]

可能让 activation 离开真实 data manifold，模型输出变化并不能证明该 variable 在自然 computation 中如此使用。

优先：

- matched interchange；
- real-source activation patching。

## 14. Linear probe direction 不一定是 causal variable direction

\[
w_{probe}\neq\Delta\mu\neq v_{causal}
\]

一般不相等。

Probe weight 只是最佳 readout 方向之一，可能受：

- redundancy；
- covariance；
- superposition；
- feature basis

影响。

## 15. 小 causal effect 不证明“不存在”

可能原因：

- variable 有多重冗余编码；
- patch 的位置不对；
- downstream 有 backup pathway；
- intervention 太局部；
- probe subspace 没对齐真正 causal subspace。

因此 negative intervention 需要谨慎表述。

## 16. 大 causal effect 也不证明“唯一存储”

一个被 ablate 后性能崩溃的方向可能是 bottleneck，但不意味着变量只存那里。

## 17. Judgment 天然可能 heterogeneous

不同 violation：

- wrong reflection；
- spontaneous acceleration；
- penetration；
- disappearance；

可能走完全不同机制。

不能预设“physical-validity dimension”唯一存在。

这不一定是实验失败，反而可成为结论。

## 18. “V-JEPA 懂物理”必须拆开

可能同时出现：

- state representation 强；
- future prediction 强；
- law parameter 不准确；
- physical judgment 弱；
- generation/control 又是另一回事。

建议层级：

1. representation/perception；
2. dynamics/prediction；
3. law/parameter knowledge；
4. judgment；
5. generative/causal deployment。

## 19. 性能提升不是必要 contribution

Mechanistic paper 不要求必须：

- 提出新架构；
- SOTA；
- downstream +X%。

真正要求是：

> 新、可信、可重复、非平凡的内部机制发现。

若能自然导出 improvement 是加分，不应牺牲主科学问题。

## 20. 顶会风险评估

### Weak Version

只做：

- 大量 layerwise probing；
- 报告哪层最好；

风险：容易被认为是已有 probing 工作的扩展。

### Strong Version

- 统一 benchmark；
- shortcut controls；
- architecture-conditioned State/Prediction/Judgment organization；
- aggregation vs computation readout analysis。

已经更像独立科学贡献。

### Strongest Version

再加入：

- ground-truth intermediate；
- matched interchange intervention；
- causal path / circuit evidence；

则更接近真正高水平 mechanistic interpretation 论文。
