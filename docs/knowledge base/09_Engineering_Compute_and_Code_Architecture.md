---
title: Engineering, Compute, and Code Architecture
status: Current
updated: 2026-10-05
tags:
  - engineering
  - compute
  - code
  - activations
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

## 2. Simulator / Acceptance / Task / Renderer 解耦

当前正式代码流以 [[05_Benchmark_and_Experiment_Design]] 为准：

```text
PhysicsConfig
        ↓
SceneProposalSampler
        ↓
Analytic Geometry / Simulator
        ↓
Continuous Trajectory + Exact Events
        ↓
AcceptanceClassifier
        ↓
positive / negative / reject
        ↓
TaskLabelGenerator
        ↓
RenderSpecGenerator
        ↓
Renderer
        ↓
DatasetWriter
```

Judgment 额外经过：

```text
Dynamics-eligible Base Scene
        ↓
JudgmentPairGenerator
        ↓
Invalid Direction Proposal
        ↓
Bad-Trajectory Geometry Check
        ↓
Alternate-Barrier Feasibility Check
        ↓
Matched Good / Bad Render
```

第二阶段 mechanistic experiment：

```text
Stored Base Scene
        ↓
Counterfactual / Source Generator
        ↓
Intervention-safe Validation
        ↓
On-demand Source Rendering
```

### Simulator / Geometry

主输入：

- context-end ball position $p_c$；
- velocity / speed / direction；
- ball radius；
- barrier center；
- barrier axis angle $\phi$；
- barrier length；
- barrier width；
- frame/time config。

其中：

- barrier endpoints 为派生量；
- `contact_normal_xy` 是具体 collision event 的派生量；
- restitution 在 v1 固定为 $1$，不是采样变量；
- friction 在 v1 固定为 $0$。

默认 proposal prior 为 [[05_Benchmark_and_Experiment_Design#6.2 v1 默认 Proposal Prior]] 规定的独立均匀采样：speed、velocity angle、barrier axis angle、context-end ball center 分别在各自合法域均匀采样，barrier center 在给定 axis angle 后的 orientation-conditioned feasible rectangle 内均匀采样。任何 guided / conditional sampler 都必须使用不同的 `proposal_mode` 并保存其 provenance。

随机数实现固定为 NumPy `PCG64 + SeedSequence`；每个 proposal 按 05 冻结的 mode-code mapping 与 reference construction，由 `(scene_seed, proposal_index, proposal_mode)` 确定随机流，使并行顺序不改变样本。核心解析几何使用 `float64`，空间、时间和角度边界统一使用 05 中冻结的 epsilon；落在 epsilon 邻域内的 proposal 记为 `numerical_boundary_ambiguous`，不得由容差强行接收。

Simulator 输出：

- continuous trajectory；
- per-frame state；
- exact collision time；
- collision frame；
- contact feature；
- contact normal；
- ball center at contact；
- surface contact point；
- pre/post velocity；
- TTC；
- auxiliary relative geometry。

### AcceptanceClassifier

必须显式区分：

```text
positive
negative
reject
```

其中 reject 绝不能作为 Contact negative 使用。

它负责：

- Physics ROI；
- long / short / corner contact；
- endpoint margin；
- impact angle；
- collision-time window；
- negative safety region；
- second collision；
- ambiguous numerical boundary；

等所有 clean-scene qualification。

### TaskLabelGenerator

只从已经接受的 latent scene / exact GT 生成：

- State labels；
- Contact labels；
- Collision Dynamics labels；
- Reflection Judgment labels；
- auxiliary oracle quantities。

### Renderer

Renderer 只负责把 latent state / trajectory 变成 RGB：

- table / background；
- puck / ball appearance；
- barrier；
- lighting；
- texture；
- semantic family。

**Renderer 不负责物理，也不负责决定一个 scene 是否是 positive / negative。**

Judgment invalid video 必须先在 latent trajectory 层生成完整 bad trajectory，再完整重新渲染；禁止在 rendered pixels 上做剪贴或几何扭曲。

## 3. 推荐 2D 技术栈

第一版完全不需要 Unity / Unreal / Blender physics。

推荐：

- NumPy：解析模拟；
- OpenCV：高速 raster drawing / compositing；
- Pillow：部分 texture / mask / image IO；
- FFmpeg：编码 MP4。

### Anti-aliasing

当前 master output resolution 固定为：

$$
448\times448
$$

Renderer 可以在更高分辨率内部 supersample，例如：

$$
896^2\rightarrow448^2
$$

再做 antialiased downsampling。

所有 latent physics coordinates 始终定义在 448-space；supersampling 只属于 rasterization implementation，不得改变物理几何。

## 4. Dataset metadata

Canonical schema 以 [[05_Benchmark_and_Experiment_Design]] 为准。工程层至少保证以下字段可追踪。

### Scene identity / reproducibility

```text
dataset_version
config_hash
simulator_version
renderer_version

latent_scene_id
trajectory_variant_id
render_variant_id
judgment_pair_id

scene_seed
proposal_index
proposal_mode
render_seed
judgment_seed
split
```

### Core State

```text
p_context_xy

velocity_xy
speed_px_per_s
speed_cells_per_s
velocity_angle_rad

barrier_center_xy
barrier_axis_angle_rad
barrier_length_px
barrier_width_px

ball_radius_px
```

注意：

- `barrier_axis_angle_rad` 是主 State geometry；
- `contact_normal_xy` 不是它的别名；
- barrier endpoints 是由 center / axis / length / width 派生的几何量。

### Collision / Dynamics event

```text
future_first_contact_exists
first_contact_time_s
first_contact_frame_index

first_contact_feature
contact_face_id
contact_normal_xy
ball_center_at_contact_xy
surface_contact_point_xy
contact_axis_coordinate_px

impact_angle_deg

pre_collision_velocity_xy
post_collision_velocity_xy
post_collision_angle_rad
```

### Contact classification

```text
status ∈ {positive, negative, reject}
contact_binary ∈ {1, 0, null}

negative_safe_ray_no_intersection
true_barrier_collision_exists
legal_long_face_collision_exists
collision_in_positive_window
collision_after_positive_window
collision_after_clip
```

### Judgment

```text
validity_binary

angular_violation_deg
angular_violation_rad
normalized_violation_severity

violation_family
violation_sign

latent_scene_id
judgment_pair_id
trajectory_variant_id
paired_trajectory_variant_id
```

### Rendering

```text
render_variant_id
render_seed
render_family
surface_style
object_style
barrier_style
lighting_variant
motion_blur
```

`motion_blur` 属于 `RenderSpec / RenderConfig`，不属于 `PhysicsConfig`；v1 固定为 `false`。

### Acceptance provenance

```text
accepted_for_contact
accepted_for_dynamics
judgment_base_geometry_eligible
rejection_reasons[]
```

Judgment pair-generation metadata 另存：

```text
judgment_pair_generated
valid_trajectory_variant_id
invalid_trajectory_variant_id
violation_sampling_attempt_count
```

关键原则：

- physics metadata 与 render metadata 分开；
- positive / negative / reject 三态必须显式保存；
- `scene_id`、`base_scene_id`、`paired_scene_id`、`render_id` 不作为 canonical alias 使用；
- same latent base scene 的不同 render variant 与 Judgment pair 默认共享同一 train/val/test split；
- metadata 必须足够完整，使 scene 能够 deterministic replay。

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
