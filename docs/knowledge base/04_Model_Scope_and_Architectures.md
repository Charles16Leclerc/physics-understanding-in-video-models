---
title: Model Scope and Architectures
status: Current
updated: 2026-09-12
tags: [models, vjepa, vlm, architecture]
---

# 研究对象、模型与架构

## 1. 总称问题

“Video Foundation Models (VFM)”在学界并不严格只指 ViT encoder，但对本项目而言仍不够准确，因为研究对象包括：

- V-JEPA encoder；
- V-JEPA predictor；
- VLM vision tower；
- merger/projector；
- LLM backbone。

因此当前更推荐标题中的总称：

> **Predictive Video Models and Video-Language Models**

而不是把所有东西都笼统叫 VFM。

## 2. 主 Predictive Model：V-JEPA2

### 2.1 为什么选 V-JEPA2 而不是直接 V-JEPA2.1

**Current：V-JEPA2 作为主模型。**

原因：

- encoder–predictor 结构与本项目理论最干净；
- 原始 predictive objective 更容易解释；
- predictor 尺度小且结构统一；
- 已有文献和我们前期讨论都围绕 V-JEPA2 展开，便于与 Joseph / IntPhys / anticipation 等结果连接。

### 2.2 开发主模型：ViT-L

V-JEPA2 ViT-L：

- encoder 约 300M；
- 24 layers；
- hidden dim 1024；
- 16 attention heads。

native predictor：

- 约 22M；
- 12 layers；
- hidden dim 384；
- 12 heads。

这一组合足够大，但明显比 1B ViT-g 省资源，适合 pipeline 开发和全层 probing。

### 2.3 规模 robustness

若主结论稳定，可将关键实验扩展到：

- V-JEPA2 ViT-g，约 1B，40 layers，hidden 1408，22 heads。

不建议一开始全规模平铺，避免算力被 activation extraction 吃掉。

## 3. V-JEPA2.1

### Tentative robustness model

V-JEPA2.1 不是简单“V-JEPA2 更强版”，而是在训练中加入更强的 dense prediction / deep self-supervision / multi-level representation 约束。

因此它很适合作为一个 secondary scientific control：

> 当 pretraining 更直接鼓励 dense/local state representation 时，State/Prediction accessibility 是否系统变化？

当前不作为主模型，避免同时改变代际与架构细节。

## 4. 主 VLM：Qwen2.5-VL-7B

### 4.1 选择标准

VLM 不是“只选排行榜最强”。需要同时满足：

- 原生视频支持；
- 开源权重与代码；
- 中间层 activation 可访问；
- 架构足够干净；
- 4×A800 能现实运行；
- 能力足够强，避免结果被“模型本来就太差”主导。

### 4.2 为什么 Qwen2.5-VL 合适

其结构大致为：

\[
\text{Video}
\rightarrow
\text{Video ViT}
\rightarrow
\text{Patch Merger}
\rightarrow
\text{Qwen2.5 LLM}.
\]

视觉塔大致：

- 32 layers；
- hidden 1280；
- 16 heads；
- temporal patch size = 2；
- 原生 video-aware。

LLM：

- 约 7B；
- 28 layers；
- hidden 3584；
- 28 query heads / 4 KV heads。

Patch Merger 是相对简单的 projection/merging 结构，而不是独立大型 Q-Former 或多层 cross-modal transformer，这使得 mechanistic boundary 更清楚。

## 5. VLM 中“probe 哪个 token”是独立问题

进入 LLM 后，representation 不是一个单一向量。至少应区分：

- visual-token hidden states；
- question-token hidden states；
- answer / decision position hidden states。

例如可能出现：

- velocity 一直存在于 visual tokens；
- `will collide?` 只在 question/answer token 的 residual stream 中逐渐形成。

因此 VLM 的 layerwise analysis 必须同时指定：

\[
\text{layer} + \text{token position/type}.
\]

## 6. 为什么不首选 Qwen3-VL

### Rejected as primary / Tentative robustness

Qwen3-VL 更强、更现代，但采用 multi-level visual injection / DeepStack 类设计：中间视觉特征会在多个 LLM depth 再次注入。

这会导致 mechanistic confound：

> 某个 quantity 在 LLM layer 15 突然变得可读，可能只是因为刚刚有新的视觉特征注入，而不是 LLM 内部逐层 computation 的结果。

因此当前：

- Qwen2.5-VL：primary mechanistic VLM；
- Qwen3-VL：以后可做 robustness。

## 7. LLaVA-OneVision 的角色

### Optional extension

LLaVA-OneVision 是很好的第二个 VLM，因为结构经典、干净：

\[
\text{SigLIP image encoder}
\rightarrow
\text{simple MLP projector}
\rightarrow
\text{Qwen2 LLM}.
\]

近似结构：

| 组件 | 参数量 | 层数 | hidden dim | heads |
|---|---:|---:|---:|---:|
| SigLIP SO400M | ~400M | 27 | 1152 | 16 |
| projector | ~20M | 2-layer MLP | 1152→3584 | — |
| Qwen2-7B | ~7B | 28 | 3584 | 28 Q / 4 KV |

它与 Qwen2.5-VL 的差异很有科学意义：

- V-JEPA：predictive video SSL；
- Qwen2.5-VL：native video vision tower + LLM；
- LLaVA-OneVision：image-oriented vision tower + LLM。

如果资源允许，这三者构成很好的 architecture/training spectrum。

## 8. 组件规模对比

| 模型组件 | 参数量 | Layers | Hidden dim | Heads | 备注 |
|---|---:|---:|---:|---:|---|
| V-JEPA2 ViT-L Encoder | ~300M | 24 | 1024 | 16 | 主开发 encoder |
| V-JEPA2 ViT-H Encoder | ~600M | 32 | 1280 | 16 | 可选 |
| V-JEPA2 ViT-g Encoder | ~1B | 40 | 1408 | 22 | 关键结果 scale-up |
| V-JEPA2 Predictor | ~22M | 12 | 384 | 12 | 专门 predictive module |
| V-JEPA2.1 ViT-B/L/g/G | ~80M/300M/1B/2B | 约 12/24/40/48 | 768/1024/1408/1664 | 12/16/22/26 | robustness family |
| Qwen2.5-VL Vision Encoder | ~hundreds M | 32 | 1280 | 16 | 原生视频 |
| Qwen2.5-VL Patch Merger | ~tens M | 2-layer MLP | 约 5120→3584 | — | 简单对齐层 |
| Qwen2.5-VL LLM | ~7B | 28 | 3584 | 28Q/4KV | 大型 general reasoner |
| LLaVA-OneVision SigLIP | ~400M | 27 | 1152 | 16 | image-oriented |
| LLaVA-OneVision Projector | ~20M | 2-layer MLP | 1152→3584 | — | 简单 projector |
| LLaVA-OneVision Qwen2 | ~7B | 28 | 3584 | 28Q/4KV | LLM |

一个值得强调的规模差异：

\[
\text{V-JEPA predictor}\approx22M
\]

而：

\[
\text{VLM LLM}\approx7B.
\]

两者容量相差数百倍，且功能先验完全不同。这正是本项目比较价值的一部分：

- 小型专门 predictor 是否更有效地把 state 变成 future representation；
- 大型 general LLM 是否更适合 judgment / task-conditioned reasoning。

## 9. 初始 scope

### Must-have

- V-JEPA2 ViT-L + native predictor；
- Qwen2.5-VL-7B。

### Scale / robustness

- V-JEPA2 ViT-g 的关键实验；
- V-JEPA2.1 ViT-L。

### Optional architecture robustness

- LLaVA-OneVision-7B；
- Qwen3-VL（仅当值得承担额外 interpretability complexity）。

## 10. 初期明确不做

### Rejected / Out of scope

- 自己训练 V-JEPA–LLM multimodal alignment；
- 对所有大模型 full fine-tuning；
- 一开始就比较大量 VLM leaderboard 模型；
- 将视频 diffusion generator 作为主模型族；
- 将 VLA policy head 作为主分析对象。
