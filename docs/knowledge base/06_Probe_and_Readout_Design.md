---
title: Probe and Readout Design
status: Current
updated: 2026-09-12
tags: [probe, readout, pooling, attention, layers]
---

# Probe / Readout 设计

## 1. 时空 token 应该怎样理解

视频 ViT 输入经过 tubelet/patch embedding 后，每个 token 初始对应一个时空块 \((t,x,y)\)。

但进入 global self-attention 后：·

$$
h_i' = h_i + \sum_j \alpha_{ij}W_Vh_j.
$$

因此经过一层后，第 \(i\) 个 token 理论上已经可以从全视频其他 token 获取信息。

更准确的表述：

> **深层 token 是以某个时空位置为 anchor 的 contextualized representation，而不是只描述该 patch 的局部 descriptor。**

它仍保留位置锚点，但可能同时包含：

- local appearance；
- object identity；
- whole-object motion；
- global event；
- 与其他区域交互后的上下文。

## 2. 为什么不同 token 可以在同一 feature space 中比较/池化

Transformer 对所有 token 共享 \(W_Q,W_K,W_V,W_{MLP}\)，因此不同位置的 \(h_i\in\mathbb R^D\) 位于同一 learned feature space。

可以用一个概念方向的直觉例子理解：如果某个 direction \(w_v\) 表示“向右运动”，球在左上或右下时都有可能满足：

$$
w_v^\top h_i>0.
$$

现实中 representation 是 distributed / superposed，不是一维对应一个概念，但共享表征空间使 pooling、linear probing、token similarity 在数学上有意义。

## 3. Mean Pooling 到底测什么

设：

$$
H=[h_1,\ldots,h_N],\quad h_i\in\mathbb R^D.
$$

mean pooling：

$$
\bar h=\frac1N\sum_i h_i.
$$

linear probe：

$$
\hat y=w^\top\bar h+b
=\frac1N\sum_i w^\top h_i+b.
$$

这说明：

> **Mean-pool + linear probe 等价于对每个 token 使用同一个 linear detector，再平均 detector score。**

### 3.1 Pooling 稀释问题

若只有 \(k\) 个 token 真正含目标物体运动信号：

$$
w^\top h_i=s
$$

而其余 token 近似 0，则：

$$
w^\top\bar h\approx \frac{k}{N}s.
$$

信号会被稀释。

更严重时，不同 token 的正负 contribution 可能互相抵消。

因此：

> **“mean-pooled representation 中线性可读”比“完整 token tensor 中线性包含该信息”更弱、更具体。**

论文中应严格写：

> `linearly decodable from the mean-pooled representation at layer l`

而不要直接说：

> `linearly represented in the full layer`。

## 4. 为什么 Mean Pooling 仍可能很强

两个原因：

1. 同一语义 direction 在不同 token 的 feature space 中对齐，可以相加；
2. 深层 self-attention 可能把局部物体信息 broadcast 到大量 token，使运动/事件信息变得 globalized。

因此 mean pooling 本身也是一个有意义的 representation test：

> **目标信息是否已经以 token-wise aligned、全局可聚合的方式存在？**

## 5. Mean-MLP 不能恢复已经被 pooling 丢掉的信息

如果：

$$
H\rightarrow \bar h
$$

已经丢失信息，那么再强的：

$$
f_{MLP}(\bar h)
$$

也无法恢复。

因此：

- Mean-Linear → Mean-MLP：测试 global summary 中 linear vs nonlinear accessibility；
- full-token attention：测试完整 token structure 中是否还存在 mean pooling 没保留的信息。

## 6. 主 probe ladder

当前建议分四类，而不是只照搬三类 probe。

| Readout | 输入 | 新增能力 | 解释 |
|---|---|---|---|
| Mean-Linear | \(\bar h\) | 无 nonlinear computation | pooled representation 是否线性显式 |
| Mean-MLP | \(\bar h\) | static nonlinear mapping | pooled summary 中是否 nonlinear-accessible |
| Attentive Pooling | full \(H\) | learnable token selection / aggregation | 信息是否在局部 token 中，只是 mean pooling 抹掉 |
| Relational Transformer | full \(H\) | token-token interaction + aggregation | 是否仍需要额外 relational computation |

后两种方法的分别把两种困难拆开：

### Aggregation difficulty

只需要找到 relevant tokens。

### Computational difficulty

需要比较多个 state/token 之间的关系。

## 7. Attentive Pooling 的建议实现

当前更倾向 **learned query cross-attention**：

$$
Q\in\mathbb R^{m\times d_q},\qquad
Z=\operatorname{CrossAttn}(Q,H).
$$

其中：

- \(m\) 可取少量 learned queries；
- query 负责选择/聚合 relevant token；
- 不先让 frozen tokens 互相做新的 self-attention。

这样可作为纯 aggregation control。

可能设计：

- 1 query：最简单；
- 4/8 queries：允许不同 query 关注不同 object/temporal part；
- multi-head cross attention；
- 最终 mean/concat queries → small output head。

### Open Question

具体 query 数、head 数、hidden width 在 pilot 中确定，但主实验一旦定下应全层固定，避免每层不同 architecture。

## 8. Relational Transformer Probe

在 full tokens 上先加一层小 self-attention：

$$
H'=\operatorname{TransformerBlock}(H)
$$

再用 learned query cross-attention：

$$
z=\operatorname{CrossAttn}(q,H').
$$

这类 probe 允许：

- token-token interaction；
- temporal/spatial relation reasoning；
- 再聚合成 task output。

如果：

- attentive pooling 弱；
- relational transformer 强；

更支持“不是简单找 token，而是需要新关系计算”。

## 9. Mean-MLP 结构

### Current recommendation

主实验使用固定的一层 hidden MLP，例如：

$$
D\rightarrow512\rightarrow output.
$$

中间可用：

- LayerNorm；
- GELU；
- 轻量 dropout。

不建议对每个 layer 用 Optuna 搜不同深度/宽度，因为会把 layer difference 与 readout difference 混在一起。

### Optional robustness

可在 appendix 对比：

- 1-hidden-layer MLP；
- 2-hidden-layer MLP。

若结论不变即可。

## 10. 为什么不把 LLM 放进同一 readout ladder

预训练 LLM 不是“比小 Transformer 再复杂一级的 probe”。它同时拥有：

- 数十亿参数；
- 大规模语言知识；
- 世界知识先验；
- instruction / reasoning training。

因此应单独归类为：

> **knowledge-rich pretrained reasoner**

否则无法区分：

- representation accessibility；
- external pretrained knowledge。

## 11. Layer sweep 策略

### 11.1 不使用“先挑一个物理量选层”的方法

### Rejected

如果用 velocity 的 layerwise curve 选择“代表层”，再去测其他量，会引入 selection bias。不同量可能有不同 emergence pattern。

### 11.2 Cheap full-depth map

对每一层、每一个 target 都训练：

- Mean-Linear；
- Mean-MLP。

这些 probe 很便宜，可以获得完整 layerwise curve。

### 11.3 Expensive token-aware map

对：

- Attentive Pooling；
- Relational Transformer；

使用预先规定、target-independent 的 normalized depth grid。

例如 24 层 encoder：

$$
\{0,4,8,12,16,20,24\}.
$$

40 层：选约 6–7 个归一化深度。

V-JEPA predictor 只有 12 层，可以考虑全部跑。

### 11.4 局部 refinement

如果 coarse grid 发现明显突变，例如：

$$
L_8=55\%,\qquad L_{12}=91\%,
$$

再补 \(L_9,L_{10},L_{11}\)。

论文中明确：

- coarse grid 是主分析；
- refinement 是对 transition zone 的细化；

避免 cherry-picking。

## 12. Object-mask pooling

State probing 时，global mean 失败可能是：

- velocity representation 不存在；
- 或者 representation 存在，但 global aggregation 找不到目标 object。

由于 simulator 有 GT mask，可定义：

$$
h_l^{object}=
\operatorname{Pool}_{i\in mask_{object}}H_{l,i}.
$$

这样回答：

> **给定正确 object binding 后，这层是否表示了该 object 的 state？**

这可把：

- object localization / binding；
- physical-state encoding

分开分析。

注意：oracle mask pooling 是诊断工具，不代表真实 downstream 系统拥有 GT mask。

## 13. VLM probe 位置

VLM 中至少区分：

1. vision tower 各层；
2. merger/projector 输出；
3. LLM early / middle / late；
4. LLM 中不同 token position/type。

建议同时记录：

- visual tokens；
- question token；
- answer/decision position。

避免笼统说“LLM 第 15 层 representation”。
