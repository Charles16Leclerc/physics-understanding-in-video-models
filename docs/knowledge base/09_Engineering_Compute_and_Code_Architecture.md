---
title: Engineering, Compute, and Code Architecture
status: Current
updated: 2026-09-12
tags: [engineering, compute, code, activations]
---

# 工程、算力与代码架构

## 1. 总体原则

本项目算力主要消耗在：

- frozen foundation model forward；

而不是：

- probe 本身的训练；
- simulator；
- renderer。

另外，存储资源层面：

- 大量中间层 token 的存储也很容易触碰存储上限。

因此工程优化核心是：

> **减少重复的大模型 inference，同时避免 full-token activation 爆硬盘。**

## 2. Simulator / Renderer / Task Generator 解耦

推荐代码结构：

```text
Physics parameters
        ↓
Analytic Simulator
        ↓
Trajectory + exact GT
        ↓
Rendering / nuisance sampler
        ↓
Frames / MP4
        ↓
Task generator
        ↓
State / Prediction / Judgment samples
```

### Simulator

输入：

- initial position；
- velocity；
- radius；
- barrier endpoints / normal；
- restitution；
- frame rate / horizon。

输出：

- per-frame physical state；
- exact collision events；
- TTC；
- pre/post velocity；
- contact point。

### Renderer

只负责把 \(S_t\) 画成 RGB：

- background / table；
- puck/ball sprite；
- barrier；
- shading / texture；
- mild nuisance。

**Renderer 不负责物理。**

### Task Generator

从 GT 生成：

- regression target；
- classification target；
- matched invalid pair；
- counterfactual pair；
- QA prompt metadata（若 VLM 需要）。

## 3. 推荐 2D 技术栈

第一版完全不需要 Unity / Unreal / Blender physics。

推荐：

- NumPy：解析模拟；
- OpenCV：高速 raster drawing / compositing；
- Pillow：部分 texture / mask / image IO；
- FFmpeg：编码 MP4。

### Anti-aliasing

可以高分辨率 render 后 downsample，例如：

$$
1024^2\rightarrow256^2.
$$

避免斜 barrier / 圆边出现明显 aliasing artifact。

## 4. Dataset metadata

每个 latent scene 建议有唯一 `scene_id`，保存 JSON/JSONL：

```text
scene_id
seed
split
physics_params
initial_position
initial_velocity
barrier_normal
barrier_endpoints
radius
restitution
collision_time
collision_frame
pre_collision_velocity
post_collision_velocity
contact_point
validity
violation_type
violation_magnitude
render_family
render_seed
```

关键原则：

- physics metadata 与 render metadata 分开；
- same latent scene 的所有 render variant 共享同一 split。

## 5. Frozen-backbone probe 训练

标准 online 模式：

```python
with torch.no_grad():
    H = backbone(x)
H = H.detach()

pred = probe(H)
loss = criterion(pred, y)
loss.backward()
optimizer.step()
```

因为 backbone 冻结：

- 不保存 backbone backward graph；
- backward 只经过 probe；
- 显存成本远低于 full fine-tuning。

## 6. Offline caching vs online forward

### Offline feature cache

先把 activation 全算出存硬盘。

优点：

- probe 训练快；
- 不重复跑 backbone。

缺点：

- full token tensor 非常大。

### Online frozen backbone

每个 batch 重新 forward，activation 用完释放。

优点：

- 不占大量硬盘。

缺点：

- 多 epoch / 多 probe 会重复 inference。

## 7. 为什么 pooled feature 可以全缓存，full tokens 不一定

示例：

$$
N=1568,\quad D=1024.
$$

fp16 单 clip 单层 full tokens：

$$
1568\times1024\times2\text{ bytes}\approx3.2\text{ MB}.
$$

10k clips × 8 layers 约：

$$
256\text{ GB}.
$$

而 pooled feature：

$$
1024\times2\text{ bytes}\approx2\text{ KB/clip/layer}.
$$

几乎可忽略。

## 8. 推荐 Hybrid Strategy

### Mean-Linear / Mean-MLP

一次 backbone forward，缓存所有层 pooled feature。

这样 cheap full-depth sweep 后续不需要重复跑 backbone。

### Attentive / Relational probe

只对 preregistered 6–7 个重点 layer：

- online forward；或
- 只缓存这些层 full tokens。

### Mechanistic subset

将样本缩到约：

$$
1k\sim3k
$$

再保存 full activations / attention / token tensors。

## 9. 一次 forward 服务多个 probes

冻结 backbone 后，同一个 batch 可以一次拿：

$$
H_4,H_8,H_{12},H_{16},\ldots
$$

并同时训练多个独立 cheap probe：

$$
P_4(H_4),P_8(H_8),\ldots
$$

full-token attentive probe 受显存限制，可每次只训练少数层。

## 10. VLM 工程注意事项

### 10.1 Vision + LLM activation 很大

不能默认把全部：

- vision patches；
- merger output；
- 28 层 LLM 所有 tokens

都长期保存。

需要分 stage 抽取。

### 10.2 Token subset

LLM 层可只保存：

- visual token pooled/selected representation；
- question token；
- answer position。

真正 mechanistic subset 再保留 full residual stream。

## 11. 4×A800 资源策略

### Must-have

- V-JEPA2 ViT-L 全层 pooled probing；
- V-JEPA predictor 全层 probing；
- Qwen2.5-VL 主要 layer map；
- 至少一套 full-token attentive/relational probe；
- 至少一组 causal intervention。

### Nice-to-have

- ViT-g key layers；
- V-JEPA2.1；
- LLaVA-OneVision；
- external benchmark；
- interpretability-guided improvement。

## 12. 不建议早期做的工程

### Rejected / Deferred

- 训练 V-JEPA–LLM alignment；
- 大规模 LoRA/full FT；
- 3D physics engine；
- 一开始生成极大规模视频库；
- 全模型所有层 full activation 离线缓存。

## 13. Git / Obsidian / Codex 工作流

本知识库本身建议与代码仓库一起管理：

```text
repo/
  docs/
    ...knowledge base...
  src/
  configs/
  data_generation/
  experiments/
  results/
```

Codex 每次重要实验后：

1. 保存 config 与 commit hash；
2. 写 [[16_Experiment_Record_Template|实验记录]]；
3. 更新 [[14_Results_Log_Template|结果日志]]；
4. 若改变研究设计，更新 [[11_Decision_Log_and_Idea_Evolution|Decision Log]]，不要覆盖历史。
