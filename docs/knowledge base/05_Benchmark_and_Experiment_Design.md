---
title: Benchmark and Experiment Design Specification
status: Current
updated: 2026-10-05
tags:
  - benchmark
  - experiment-design
  - simulator
  - rendering
  - causal-intervention
  - dataset
---

# Benchmark 与实验设计说明书

> **文档定位**
>
> 本文档是本项目关于 **benchmark、场景、物理系统、数据生成、任务定义、实验中涉及的物理量、Judgment violation、跨场景泛化、以及第二阶段 causal intervention 的统一规范**。
>
> 它的地位是本项目科学目标落到具体实验实现时的**正式规格说明书（specification）**。后续 simulator、renderer、Dataset Index、TaskManifestBuilder、dataset builder、counterfactual generator，以及与场景直接相关的实验操作，都应以本文档为准。
>
> 本文档**不负责**：
>
> - 具体模型架构与 checkpoint 选择，见 [[04_Model_Scope_and_Architectures]]；
> - 具体 probe/readout 网络结构，见 [[06_Probe_and_Readout_Design]]；
> - activation patching / steering / DAS 等方法本身的术语和算法细节，见 [[07_Mechanistic_Interpretability_and_Causal_Intervention]]。
>
> 但凡这些方法与“要改哪个物理量、在哪种场景上改、下游观察哪个物理量、什么样的 counterfactual 才有意义”有关，本文档给出实验层面的约束。
>
> 本文档由原 `05_Benchmark_and_Dataset_Design.md` 大幅重写而来。原文中仍成立的重要原则被保留；已经被后续讨论推翻或收窄的设计，以本文档为准。

---

# 0. 设计总纲

本项目 benchmark 的首要目标是：

> **构造一个足够干净、可解析、可控制、可生成精确中间物理变量、并适合 mechanistic causal analysis 的视觉物理世界。**

因此，数据集本身是一个 **diagnostic instrument**。

核心原则：

> **One World, Multiple Queries.**

即：

- 只建立一套统一 latent physics world；
- State、Prediction、Judgment 都从同一套 latent trajectory 派生；
- 不用三个完全不同的数据集分别代表三类能力；
- 尽可能让所有实验共享相同 scene distribution、物理参数、渲染逻辑与 ground truth。

这使我们可以把实验差异更可信地归因于：

- target 本身；
- model stage；
- representation organization；
- downstream computation；

而不是：

- 不同 benchmark 的场景复杂度；
- camera；
- label entropy；
- train-set size；
- simulator artifact；
- shortcut structure。

本 benchmark 的总体哲学是：

> **physically narrow, causally and visually broad.**

即：

- 物理规律尽量简单、统一；
- 但初始条件、几何关系、速度、碰撞时刻、视觉语义皮肤、反事实干预足够多样；
- 保持物理 computation graph 干净，同时避免依赖单一 appearance prior。

---

# 1. 全局空间规格、坐标与物理世界

## 1.1 Master frame 与 cell

v1 所有视频统一输出：

$$
\boxed{448\times448}
$$

RGB frame。

定义一个仅用于尺寸描述和跨模型空间尺度对齐的 coarse cell：

$$
\boxed{1\ \text{cell}=28\ \text{px}}.
$$

因此 full frame 为：

$$
16\times16\ \text{cells}.
$$

**注意：cell 不是 simulator 的离散网格。** 物理位置、速度、碰撞时刻、contact point 都必须在连续坐标中计算。

## 1.2 Physics world coordinate

Simulator 内统一采用连续二维 world coordinate：

- 原点：448×448 frame 中心；
- $x$ 轴：向右；
- $y$ 轴：向上；
- 长度单位：master-frame pixel。

因此 frame bounds：

$$
x\in[-224,224],\qquad y\in[-224,224].
$$

Renderer 转为图像坐标：

$$
x_{img}=x+224,
$$

$$
y_{img}=224-y.
$$

metadata 中优先保存 world coordinate；若模型训练需要 normalized coordinate，再由 task loader 派生。

角度的 canonical 序列化规约固定为：

```text
velocity_angle_rad ∈ [0, 2π)
post_velocity_angle_rad ∈ [0, 2π)
barrier_axis_angle_rad ∈ [0, π)
```

在当前 $x$ 向右、$y$ 向上的 world coordinate 中，正角度方向为逆时针。所有 `atan2` 结果必须先 wrap 到上述 canonical interval，再写入 metadata。

---

# 2. Visual Table 与 Physics ROI

## 2.1 Visual table

Visual table 的 **base playing-surface footprint** 固定为：

$$
\boxed{15\times11\ \text{cells}=420\times308\ \text{px}}.
$$

居中放置，因此：

$$
x\in[-210,210],
$$

$$
y\in[-154,154].
$$

桌边只承担**俯视水平桌面**的视觉语义，不参与 v1 物理碰撞。

对于 Air-Hockey family，语义桌沿允许在这个 420×308 base footprint 之外每侧再扩展 8 px，
因此可见 outer footprint 为 436×324 px；新增部分只用于大圆角和桌沿语义，仍不参与 physics。
其他 family 的 outer footprint 保持 420×308 px。

## 2.2 Physics ROI

固定物理硬边界：

$$
\boxed{14\times10\ \text{cells}=392\times280\ \text{px}}.
$$

居中：

$$
\boxed{x\in[-196,196],\qquad y\in[-140,140].}
$$

Physics ROI 与 visual table 四周各留 14 px 视觉缓冲。

### 关键定义

Physics ROI 不是仅用于 proposal 的松散范围，而是：

> **所有真实物理几何体与整段真实轨迹都必须完全包含在其中。**

因此：

- barrier 整个矩形必须完全位于 Physics ROI；
- ball 整个圆盘在所有时刻必须完全位于 Physics ROI；
- valid Judgment trajectory 必须满足；
- invalid Judgment trajectory 也必须满足；
- 第二阶段 source / counterfactual 若称为 intervention-safe，也必须满足。

---

# 3. v1 物理系统：Single Puck + Fixed Finite Barrier

## 3.1 Core system

v1 固定为：

$$
\boxed{\text{single moving puck/ball/disk + one fixed finite-width barrier}}.
$$

不加入：

- multi-ball；
- table-edge bounce；
- pocket / goal；
- multi-collision long rollout；
- 3D rigid-body dynamics。

## 3.2 Free motion

无 barrier interaction 时：

$$
p(t+\Delta t)=p(t)+v\Delta t,
$$

$$
v(t+\Delta t)=v(t).
$$

v1 不考虑：

- 平面内重力；
- 摩擦；
- 空气阻力；
- rolling resistance；
- spin；
- 自然减速。

所以 pre-contact motion 是严格匀速直线运动。

## 3.3 完全弹性碰撞

固定：

$$
\boxed{e=1}.
$$

对具体 long-face contact 的有向单位法向 $n$：

$$
v^+=v^- -2(v^-\cdot n)n.
$$

因此：

$$
\boxed{\|v^+\|=\|v^-\|}.
$$

第一版不随机 restitution coefficient。原因是材料对应的 $e$ 从普通视觉中不可可靠辨识；v1 只研究几何反射规律。

---

# 4. Ball 与 Barrier 几何

## 4.1 Moving object

球/圆盘直径固定：

$$
\boxed{d_{ball}=35\ \text{px}=1.25\ \text{cells}}.
$$

半径：

$$
\boxed{r=17.5\ \text{px}=0.625\ \text{cell}}.
$$

相对 full frame：

$$
35/448\approx7.81\%.
$$

这与既有 controlled physics probing 场景的 object scale 接近，并兼顾 spatial diversity 与 motion visibility。

## 4.2 Barrier

固定：

$$
\boxed{L=140\ \text{px}=5\ \text{cells}},
$$

$$
\boxed{w=28\ \text{px}=1\ \text{cell}}.
$$

定义：

- center $b=(b_x,b_y)$；
- long-axis angle $\phi\in[0,\pi)$；
- tangent：
  $$
  t=(\cos\phi,\sin\phi);
  $$
- canonical normal：
  $$
  n_c=(-\sin\phi,\cos\phi).
  $$

实际 collision event 的 `contact_normal_xy` 根据接触的具体 long face 派生，可以是 $\pm n_c$。其符号统一定义为：

> **从 barrier active face 指向碰撞前 ball center 所在的外部半平面。**

因此 clean incoming / outgoing 必须满足：

$$
v^-\cdot n_{contact}<0,
\qquad
v^+\cdot n_{contact}>0.
$$

反射公式对 $n$ 与 $-n$ 等价，但这一固定符号规约用于保证 `contact_face_id`、不穿墙检查与 metadata replay 的唯一性。

### State 语义

State 主 target 是：

$$
\boxed{\phi\in[0,\pi)}
$$

即 barrier 的无向长轴方向，而不是 signed normal。

## 4.3 Barrier 必须完整位于 Physics ROI

四顶点：

$$
b\pm\frac L2t\pm\frac w2n_c.
$$

要求四个顶点都**严格**位于 Physics ROI 内。

等号边界一律视为 ambiguous / too-close，reject。

## 4.4 只有 long faces 是 v1 合法碰撞面

v1 只允许：

$$
\boxed{\text{clean long-face collision}}.
$$

以下全部 reject：

- short-face first contact；
- corner first contact；
- simultaneous/ambiguous feature contact；
- endpoint-near contact；
- near-tangent contact。

## 4.5 Support / Clamp

v1 所有螺丝、clamp、support、固定脚必须：

$$
\boxed{\text{完全包含在 barrier rectangle footprint 内}}.
$$

因此 simulator 不需要处理额外 support geometry，同一 latent scene 的 accept/reject 不依赖 render family。

v1 禁止突出 barrier footprint 的 support。

---

# 5. 时间、帧与 Context/Future

## 5.1 固定时长

v1 固定：

$$
\boxed{fps=24},
$$

$$
\boxed{N=24\ \text{frames}},
$$

概念 clip interval：

$$
\boxed{[0,1.0\text{s})}.
$$

因此：

$$
T_{total}=1.0\text{s}.
$$

## 5.2 Canonical frame timestamp

Frame $i$ 对应 timestamp：

$$
\boxed{t_i=i/24},\qquad i=0,\dots,23.
$$

Canonical renderer 在这些时刻绘制 sharp instantaneous frame。

v1 Canonical **不加 motion blur**，避免 blur length 成为单帧 speed shortcut。

虽然最后一个渲染时刻为 $23/24$ s，simulator 仍定义：

$$
\boxed{p_T:=p(1.0\text{s})}.
$$

$p_T$ 是用于连续轨迹 ROI safety check 的未渲染右端点。因此 clip 观测区间仍是 $[0,1)$，但边界验证使用其闭包 $[0,1]$。

## 5.3 Context / Future

固定：

$$
\boxed{\text{Context frames}=0,\dots,7}
$$

共 8 帧；

$$
\boxed{\text{Future frames}=8,\dots,23}
$$

共 16 帧。

Context boundary：

$$
\boxed{t_c=8/24=1/3\text{s}}.
$$

所以：

$$
T_{context}:T_{future}=1:2.
$$

主 State target 定义在：

$$
\boxed{S_c=S(t_c^-)}.
$$

## 5.4 Collision frame index

Event time $t_e\in[0,1)$ 的 frame index：

$$
\boxed{k_e=\lfloor24t_e\rfloor}.
$$

若 event 恰好发生在 $t=k/24$，归属 frame $k$。

Ball position 在 collision time 连续，velocity 不连续。对逐帧 `velocity_xy[frame]` 和通用 `state_at(t)`，固定采用 **right-continuous** 规约：

```text
state_at(t_collision).velocity_xy = post_collision_velocity_xy
```

`CollisionEvent` 必须另行保存 `pre_collision_velocity_xy` 与 `post_collision_velocity_xy`。由于 renderer 在事件时刻只根据连续 position 绘制物体，这一规约不会破坏 Judgment good / bad 在 collision frame 的像素一致性。

## 5.5 Positive collision temporal window

固定：

$$
\boxed{k_{collision}\in\{12,13,\dots,19\}}.
$$

等价：

$$
\boxed{t_{collision}\in[12/24,20/24)}.
$$

即：

$$
[0.5,0.8333\ldots)\text{s}.
$$

这样 Future 开始后至少有 frames 8–11 的 future pre-contact evidence，且 collision 后至少保留 frames 20–23 的 post-contact evidence。

---

# 6. Scene Sampling 与 Speed

## 6.1 以 Context boundary state 为 anchor

优先采样：

$$
S_c=(p_c,v_c,b,\phi).
$$

其中：

$$
v_c=s(\cos\theta_v,\sin\theta_v).
$$

然后：

- 向后解析积分到 $t=0$ 构造 Context；
- 向前解析积分到 $t=1$ 构造 Future。

## 6.2 v1 默认 Proposal Prior

在给定各变量可行范围后，v1 纯 latent pilot 的默认 proposal prior 采用独立均匀采样：

$$
\boxed{
s\sim U(s_{min},s_{max})
}
$$

$$
\boxed{
\theta_v\sim U[0,2\pi)
}
$$

$$
\boxed{
\phi\sim U[0,\pi)
}
$$

$$
\boxed{
p_c\sim U(R_{center})
}
$$

Barrier orientation $\phi$ 采样后，barrier center 在该 orientation 的可行中心矩形内均匀采样。设：

$$
a=L/2,
\qquad
h=w/2,
$$

则 rotated barrier 在 world $x/y$ 方向的 half extent 为：

$$
e_x(\phi)=a|\cos\phi|+h|\sin\phi|,
$$

$$
e_y(\phi)=a|\sin\phi|+h|\cos\phi|.
$$

因此：

$$
\boxed{
b_x\sim U(-196+e_x,\ 196-e_x)
}
$$

$$
\boxed{
b_y\sim U(-140+e_y,\ 140-e_y)
}
$$

实现时两个坐标在该可行矩形内条件独立均匀采样。由于 Physics ROI 对边界采用 strict-inside 规则，数值上落入 boundary epsilon 的 proposal 仍标记为 ambiguous 并 reject。

默认：

```text
proposal_mode = "independent_uniform"
```

该 proposal mode 不预先指定 positive / negative label；所有 label 只能由解析几何、simulation 与 AcceptanceClassifier 决定。

若为了提高 positive acceptance 而加入 `positive_guided` / `negative_guided` proposal，必须：

- 显式保存 `proposal_mode`；
- 使用独立 seed stream；
- 仍通过同一 AcceptanceClassifier；
- 不把 proposal intent 当作 label；
- 在最终 dataset 中做 marginal diagnostics / matching。

随机数默认使用 NumPy `PCG64` + `SeedSequence`。`scene_seed` 与 `proposal_index` 必须是 $[0,2^{64})$ 内的非负整数。proposal mode 的整数编码冻结为：

```text
independent_uniform = 0
positive_guided    = 1
negative_guided    = 2
```

reference RNG construction 固定为：

```python
mode_code = PROPOSAL_MODE_CODE[proposal_mode]
seed_sequence = np.random.SeedSequence(
    [scene_seed, proposal_index, mode_code]
)
rng = np.random.Generator(np.random.PCG64(seed_sequence))
```

后续新增 proposal mode 必须追加新的、永不复用的整数编码。这样每个 `(scene_seed, proposal_index, proposal_mode)` 派生独立 RNG stream，保证串行与并行生成得到相同 latent proposal。

v1 simulator 必须实现且默认只启用 `independent_uniform`。`positive_guided` 与 `negative_guided` 的 code 仅为未来保留；在其 proposal algorithm 另行版本化前，传入这两个 mode 必须显式报 unsupported error，不能静默回退。

## 6.3 Speed 必须随机

固定 speed 会削弱 speed probe，并造成固定 displacement shortcut，因此 speed 必须连续采样。

代码必须 config 化：

```text
speed_min_cells_per_s
speed_max_cells_per_s
```

当前默认 pilot：

$$
\boxed{s\sim U(5,8.5)\ \text{cells/s}}
$$

即：

$$
\boxed{s\sim U(140,238)\ \text{px/s}}.
$$

24 fps 下约：

$$
5.83\sim9.92\ \text{px/frame},
$$

即：

$$
0.17\sim0.28
$$

个球直径 / frame。

### Speed range 尚保留 pilot 权限

这是当前仍明确允许根据 acceptance statistics 调整的核心连续参数。

正式大规模生成前至少比较：

```text
A: 5.0–8.5 cells/s   # 当前默认
B: 4.5–8.5 cells/s   # 更宽的低速端
C: 5.0–9.0 cells/s   # 仅作对照，重点检查方向性 rejection bias
```

最终选择标准：

1. speed variation 足够支持 speed State probe；
2. motion per frame 不过快；
3. accepted velocity-direction distribution 不被 speed 强烈扭曲；
4. collision incidence angle 足够多样；
5. spatial distribution 不集中到桌面长轴两端。

## 6.4 Ball-center legal region

由于整个 ball disk 必须在 Physics ROI 内，ball center 合法区域为 ROI erosion by radius $r$：

$$
\boxed{x\in[-178.5,178.5],\qquad y\in[-122.5,122.5].}
$$

尺寸：

$$
357\times245\ \text{px}.
$$

## 6.5 利用凸性做 trajectory boundary check

### 无碰撞

ball-center trajectory 为单线段：

$$
p_0\rightarrow p_T.
$$

只需检查：

$$
\boxed{p_0,p_T\in R_{center}}.
$$

### 一次反弹

trajectory：

$$
p_0\rightarrow p_{col}\rightarrow p_T.
$$

只需检查：

$$
\boxed{p_0,p_{col},p_T\in R_{center}}.
$$

不需要逐帧 boundary check。

### 重要

不能只检查视频起点与终点，因为 barrier 本体在 ROI 内并不自动保证 collision-time ball center 也位于 ball-center legal region。

---

# 7. Contact Geometry 与 Positive / Negative / Reject

## 7.1 三个术语严格区分

### Positive

进入最终 Contact dataset，label：

```text
contact = 1
```

### Negative

进入最终 Contact dataset，label：

```text
contact = 0
```

### Reject

latent proposal 完全不进入 Contact dataset。

**Reject 绝不能当作 negative。**

## 7.2 精确 disk-vs-rectangle first contact

Simulator 必须使用真实圆盘与 finite-width rectangle 的精确解析几何 / Minkowski geometry 求 first contact。

不能用：

- ball-center ray 与 barrier centerline 相交；
- 无限薄线段近似；

替代真实 collision geometry。

在 barrier-local frame：

$$
q=p-b,
$$

$$
u=q\cdot t,
$$

$$
d=q\cdot n_c.
$$

Barrier half-length：

$$
a=L/2=70\text{ px},
$$

half-width：

$$
h=w/2=14\text{ px}.
$$

first contact 必须分类为：

```text
none
long_face
short_face
corner
ambiguous
```

边界无法稳定分类时一律 `ambiguous -> reject`。

`contact_face_id` 的 canonical enum 为：

```text
long_pos_n
long_neg_n
short_pos_t
short_neg_t
corner_pos_t_pos_n
corner_pos_t_neg_n
corner_neg_t_pos_n
corner_neg_t_neg_n
null
```

其中 `pos_n / neg_n` 相对于 $n_c$，`pos_t / neg_t` 相对于 $t$；`null` 只用于 `none` 或无法唯一归属的 `ambiguous`。normal 定义为：

- `long_pos_n / long_neg_n` 分别取 $+n_c / -n_c$；
- `short_pos_t / short_neg_t` 分别取 $+t / -t$；
- corner 与 ambiguous event 不定义 reflection normal，写为 `null`。

所有非空 normal 都指向 pre-contact ball center 所在的 barrier 外部，因此满足统一的 $v^-\cdot n<0$。short / corner event 仅用于 reject diagnostics，不进入 positive dynamics pool。

### 数值边界策略

Simulator 使用 `float64` 做全部连续几何与时间计算，并将数值容差作为 versioned config 的一部分：

```text
spatial_epsilon_px = 1e-9
time_epsilon_s = 1e-12
angle_epsilon_rad = 1e-12
```

统一规则：

- 距任意 strict threshold / feature boundary 小于或等于对应 epsilon 时，标记 `numerical_boundary_ambiguous`并 reject；
- 若 event time 距 $k/fps$ 小于或等于 `time_epsilon_s`，先 snap 到精确 $k/fps$，再计算 `floor(fps * t)`；
- 容差只用于稳定边界分类，不得放宽 $d_1$、$d_2$、10°、ROI 或 collision window 等科学阈值；
- 任何 epsilon 变更都必须进入 `config_hash` 并触发新 dataset version。

## 7.3 Endpoint margin

固定：

$$
\boxed{d_1=0.625\ \text{cell}=17.5\ \text{px}=r}.
$$

Positive long-face contact 要求 surface contact point 在 long face 上，且轴向：

$$
\boxed{|u_{contact}|<L/2-d_1=52.5\text{ px}}.
$$

也即合法长边段长度：

$$
105\text{ px}=3.75\text{ cells}.
$$

等号边界 reject。

## 7.4 Impact angle threshold

定义：

$$
\boxed{\theta_{impact}=\angle(v^-,\text{barrier long axis})\in[0^\circ,90^\circ]}.
$$

可计算：

$$
\theta_{impact}=\arcsin\frac{|v^-\cdot n|}{\|v^-\|}.
$$

固定：

$$
\boxed{\theta_0=10^\circ}.
$$

Positive 要求：

$$
\boxed{\theta_{impact}>10^\circ}.
$$

恰好 10° reject。

## 7.5 Contact Positive 的完整资格

只有同时满足以下条件才进入 positive：

1. Context 完全无任何 barrier collision；
2. first future contact = `long_face`；
3. $|u_{contact}|<L/2-d_1$；
4. collision frame ∈ 12–19；
5. $\theta_{impact}>10^\circ$；
6. 非 short-face；
7. 非 corner；
8. 非 ambiguous / simultaneous feature contact；
9. barrier 整体在 Physics ROI；
10. ball 的 $p_0,p_{col},p_T$ 均在 center legal region；
11. 整段只发生这一次合法 barrier collision；
12. post-collision 不再次撞 barrier；
13. 不涉及 support geometry；
14. 所有 threshold 等号边界均 reject。

## 7.6 Contact Negative safety region

固定：

$$
\boxed{d_2=1.25\ \text{cells}=35\ \text{px}}.
$$

构造：

$$
\boxed{B_{safe}=B_{barrier}\oplus\mathrm{Disk}(d_2)}.
$$

这是 barrier rectangle 外扩 35 px 得到的圆角矩形。

从 Context boundary ball center 出发：

$$
\gamma(\lambda)=p_c+\lambda\hat v_c,\qquad\lambda\ge0.
$$

Negative 必须满足：

$$
\boxed{\gamma\cap B_{safe}=\varnothing}.
$$

因为 ball radius = 0.625 cell，所以此定义保证 ball surface 与真实 barrier boundary 的潜在最小 clearance 至少：

$$
d_2-r=0.625\text{ cell}=17.5\text{ px}.
$$

## 7.7 以下全部 Reject，而不是 Negative

- infinite ray 最终会撞真实 barrier，但碰撞晚于视频 window；
- infinite ray 会撞 short face；
- infinite ray 会撞 corner；
- infinite ray 虽不碰真实 rectangle，但进入 $d_2$ safety region；
- near-tangent / near-miss；
- Context 过去已经发生 contact；
- ball trajectory 出 ROI。

最终 negative 必须是：

> **沿当前方向无限延伸也明确、宽 margin 地避开 barrier 的 clean no-contact scene。**

# 8. Dataset 的三个 Task Views

术语规范：

> `split` 只用于 train / val / test。

Contact / Dynamics / Judgment 称为 **Task View / Task Pool**。

三个 View：

1. Contact Prediction；
2. Collision Dynamics；
3. Reflection Judgment。

集合关系应针对 **base latent scenes** 理解：

$$
\boxed{
\text{Judgment base scenes}
\subset
D_{dynamics}
\subset
D_{contact-positive}
\subset
D_{contact}.
}
$$

注意：invalid Judgment video 本身不是“物理上有效的 Dynamics 样本”。更准确的说法：

> **Judgment pairs are derived from dynamics-eligible positive latent scenes.**

---

# 9. Task View A：Contact Prediction

## 9.1 正式任务定义

不再使用旧表述：

> `will collide within future horizon?`

正式 operational target 是：

> **clean contact positive vs clean safe no-contact negative**。

即：

- positive：满足第 7.5 节完整 long-face collision 资格；
- negative：满足第 7.6 节无限射线 strict safety 条件；
- 中间所有 borderline / wrong-contact / time-insufficient proposal：reject。

可以简写为：

$$
\boxed{\text{clean contact positive / strict safe negative}}.
$$

`ray_hit` 只能作为几何 diagnostic，不能直接等同于 Contact label；所有 wrong-feature、时间窗口不合格和边界不清晰的 ray-hit proposal 都必须 reject。

## 9.2 “时间不够”绝不算 negative

如果：

- 几何上最终会碰；
- 但 collision 不在 frame 12–19；
- 或 collision 晚于视频末尾；

该 proposal：

$$
\boxed{\text{reject}}.
$$

这使 Contact task 只研究 clean geometry / trajectory relation，而不混入：

> “给定有限观察 horizon，时间够不够”。

---

# 10. Contact 正负比例与 Sampling Policy

## 10.1 Label balance

主 Contact dataset：

$$
\boxed{P(y=1)\approx P(y=0)\approx0.5}.
$$

这是 diagnostic benchmark 的设计，不追求现实世界 collision prevalence。

## 10.2 推荐流程

```text
sample latent proposals
        ↓
analytic geometry / simulation
        ↓
Physics ROI checks
        ↓
positive / negative / reject classification
        ↓
positive reservoir + negative reservoir
        ↓
marginal diagnostics
        ↓
stratified selection / balancing
        ↓
render
```

## 10.3 Proposal 可以 biased，最终 dataset 必须 controlled

若 positive 太少，可让 proposal 更常：

- velocity 大致朝向 barrier；
- ball/barrier 距离位于合理范围。

这属于未来可选的 `positive_guided` proposal mode，不是 v1 默认的 `independent_uniform`。启用时必须遵循第 6.2 节的 mode code、独立 RNG stream 与 provenance 规则。

但最终必须检查：

$$
P(s|y),\ P(\theta_v|y),\ P(\phi|y),\ P(p_c|y),\ P(b|y),\ P(\|b-p_c\||y).
$$

任何单变量明显决定 label 时，都应做：

- resampling；
- reweighting；
- stratified matching。

# 11. Task View B：Collision Dynamics

只对 Contact-positive 的 clean collision scene 定义：

$$
D_{dynamics}
=
\{x\in D_{contact}: y_{contact}=1\}.
$$

其中可生成以下 Prediction ground truth。

---

## 11.1 Time-to-collision

从 Context 结束时刻计：

$$
\boxed{
\tau=t_{collision}-t_c
}
$$

不是从视频 \(t=0\) 计。

---

## 11.2 Collision point

建议 simulator 同时保存：

1. ball center at collision：
   $$
   p_{center}^{contact};
   $$
2. 真正 barrier surface contact point：
   $$
   q_{contact}.
   $$

主 probe target 若写“collision point”，必须在实验中明确具体指哪一个。

当前更建议把：

$$
\boxed{q_{contact}=(q_x,q_y)}
$$

作为正式物理 contact point。

---

## 11.3 Post-collision velocity

保存：

$$
v^+=(v_x^+,v_y^+).
$$

同时派生：

$$
s^+=\|v^+\|,
$$

$$
\theta_{v^+}=\operatorname{atan2}(v_y^+,v_x^+).
$$

其中：

$$
\boxed{\theta_{v^+}}
$$

是 Collision Dynamics 最核心的 Prediction target。

---

## 11.4 Post-collision speed 的地位

因为：

$$
e=1
\Rightarrow
s^+=s^-,
$$

所以 post-collision speed 不应被包装成重要“future computation”发现。

它可以作为：

- sanity check；
- representation control；

但不是核心 scientific endpoint。

---

## 11.5 Future free-flight position

旧设计中的：

$$
x_{t+\Delta}=x_t+v_t\Delta
$$

可以保留为 control-only target。

由于它对 state 近似线性，不用于证明 predictor 做了 non-trivial future computation。

---

# 12. Task View C：Reflection Judgment

v1 Judgment 不研究一个 heterogeneous、universal 的“physical validity”。

第一版固定为：

$$
\boxed{\text{Reflection Consistency Judgment}}.
$$

目标：

> 模型是否能根据 pre-collision state 与 barrier geometry，判断 observed post-collision direction 是否符合反射规律。

## 12.1 v1 不加入的 violation

不加入：

- disappearance；
- recoloring；
- spontaneous acceleration；
- wrong restitution / speed magnitude；
- object permanence；
- arbitrary penetration；
- heterogeneous IntPhys-style violation families。

原因：第一版关注同一反射 law 内的 State → Prediction / Judgment 机制，而不是寻找 universal invalidity direction。

## 12.2 Valid trajectory

$$
v_{valid}^+=v^- -2(v^-\cdot n)n.
$$

且：

$$
\|v_{valid}^+\|=\|v^-\|.
$$

Valid metadata：

```text
validity = 1
angular_violation_deg = 0
angular_violation_rad = 0
normalized_violation_severity = 0
```

## 12.3 Invalid trajectory 的唯一正式 operator

v1 只使用一种正式生成 operator：

> **直接修改 post-collision outgoing direction。**

给定：

$$
\theta_{valid}^+,
$$

连续采样：

$$
\boxed{\delta\sim U(5^\circ,90^\circ)}
$$

以及：

$$
\sigma\in\{-1,+1\}.
$$

构造：

$$
\boxed{\theta_{bad}^+=\theta_{valid}^+ + \sigma\delta}.
$$

保持 speed：

$$
\boxed{\|v_{bad}^+\|=\|v^-\|}.
$$

所以：

$$
v_{bad}^+=\|v^-\|(\cos\theta_{bad}^+,\sin\theta_{bad}^+).
$$

## 12.4 Invalid outgoing 的独立几何检查

$\delta$ 的数值不代替任何以下 check。

### A. 不穿墙

bad outgoing 必须离开实际 contact face，不能继续进入 barrier。

### B. 不 near-tangent

定义 bad outgoing ray 与 barrier long axis 的锐角：

$$
\theta_{out,bad}\in[0^\circ,90^\circ].
$$

要求：

$$
\boxed{\theta_{out,bad}>10^\circ}.
$$

### C. Invalid trajectory 在 Physics ROI 内

检查：

$$
p_{col},\ p_T^{bad}\in R_{center}.
$$

### D. 不发生 second collision

invalid future 不得重新撞 barrier。

## 12.5 Alternate-barrier feasibility check

正式 violation 仍以“直接改变出射角”叙述，但每个 bad candidate 必须验证：

> 该 outgoing direction 本身能由 benchmark support 内另一个合法 barrier orientation 的正常反射产生。

反射几何中 barrier orientation 转 $\alpha$，固定 incoming direction 时 reflected direction 转 $2\alpha$。

因此：

$$
\boxed{\phi'=\phi+\sigma\frac{\delta}{2}\pmod\pi}.
$$

### 几何操作

把**整个原 barrier rectangle**以 collision-time ball center：

$$
p_{col}
$$

为旋转中心，刚体旋转：

$$
\sigma\frac{\delta}{2}.
$$

这与“重新构造一个与同一球圆相切的新 active long face”完全等价：

- 原 active face 与球圆相切；
- 绕球心旋转保持 line-to-center distance；
- 新 active face 仍与球圆相切；
- contact point 在 barrier axis 上的相对位置保持不变；
- endpoint margin 因刚体旋转保持不变。

### Feasibility 要求

alternate barrier：

1. 四顶点都严格在 Physics ROI 内；
2. contact 仍属于 long-face interior；
3. endpoint margin $d_1$ 仍满足；
4. 无 ambiguous geometry。

**Alternate barrier 不会被渲染进 invalid video。**

真实 invalid video 里 visible barrier 始终保持原来的 $\phi$。

该 alternate geometry 只是 support-feasibility validation；它不能替代后续的 valid/invalid marginal matching。

## 12.6 Good / Bad prefix 完全一致

对同一 Judgment pair：

$$
I^{good}(t)=I^{bad}(t),\qquad t\le t_{collision}.
$$

两者共享：

- Context；
- Future pre-contact；
- collision time；
- collision location；
- visible barrier；
- speed；
- render nuisance。

只在 post-collision outgoing direction 上分叉。

---

# 13. Judgment Targets 与 Sampling

## 13.1 Binary validity

$$
\boxed{y_{valid}\in\{0,1\}}.
$$

## 13.2 Canonical continuous severity

正式 GT：

$$
\boxed{\Delta\theta=d_{2\pi}(\theta_{bad}^+,\theta_{valid}^+)=\delta}.
$$

必须保存：

```text
angular_violation_deg
angular_violation_rad
```

主 severity probe 优先以 raw $\Delta\theta$ 为 GT。

## 13.3 Normalized severity

固定：

$$
\boxed{s_{violation}=\frac{\Delta\theta}{90^\circ}}.
$$

因此：

- valid = 0；
- invalid ≈ $[0.0556,1]$。

不要定义成 $(\delta-5^\circ)/85^\circ$，否则最轻 invalid 会与 valid 共用 0。

## 13.4 Continuous severity，不用离散 grid

正式 invalid proposal：

$$
\boxed{\delta\sim U(5^\circ,90^\circ)}.
$$

不使用固定：

```text
5°, 15°, 30°, 60°
```

作为主数据分布。

原因：离散 severity 是没有物理意义的人为模式。

## 13.5 Acceptance 会改变最终 severity distribution

alternate-barrier ROI、bad outgoing angle、post trajectory 等 rejection 会让 accepted $P(\delta)$ 偏离 uniform。

因此正式生成后必须统计 accepted severity histogram；若失衡，可对连续 $\delta$ 做 bin-based quota / resampling，但 bin 内仍连续采样。

## 13.6 Violation sign balancing

每次先从 $U(5^\circ,90^\circ)$ 采样一个连续 $\delta$，然后分别对 $+\delta$ 与 $-\delta$ 运行完整的：

- bad outgoing geometry check；
- ROI check；
- second-collision check；
- alternate-barrier feasibility check。

若 $+\delta$ 与 $-\delta$ 都合法，在两个符号中等概率选择。

若只有一侧合法，可保留，但最终必须统计：

$$
P(\sigma|invalid).
$$

必要时 balancing，避免“向某一侧偏就是 invalid”的 shortcut。

若两侧都不合法，该 $\delta$ 不使用，继续下一次采样，直到成功或达到 `max_violation_sampling_attempts`。

## 13.7 Judgment class balance

目标：

$$
\boxed{valid:invalid=1:1}.
$$

推荐每个 dynamics-eligible base scene 生成：

- 1 个 valid；
- 1 个 matched invalid。

若 invalid 在最大次数内无法生成：

- base scene 可继续用于 Contact / Dynamics；
- 不进入 Judgment pair dataset。

默认：

```text
max_violation_sampling_attempts = 128
```

该值是 config 参数，不是科学 claim。

# 14. 第一部分实验：要 probe 的物理量

本文档只规定**物理 target 与 parameterization**，不规定具体 probe architecture。

---

## 14.1 State targets

State 全部锚定在：

$$
t=t_c^-.
$$

### A. Pre-collision velocity：核心

#### Cartesian parameterization

$$
\boxed{(v_x,v_y)}
$$

#### Polar parameterization

$$
\boxed{s=\|v\|}
$$

与：

$$
\boxed{
\theta_v=\operatorname{atan2}(v_y,v_x)
}
$$

Cartesian 与 Polar 都应保留。

原因：

> probe 效果不好可能只是 target parameterization 与模型内部自然 geometry 不匹配。

我们不能预设模型天然以：

- Cartesian；
- magnitude + direction；

中的哪一种表达 motion。

#### Direction metric

因为：

$$
\theta_v\in[0,2\pi),
$$

不能直接用普通 scalar MSE 作为唯一评价。

应使用 circular error：

$$
d_{2\pi}(\hat\theta,\theta)
=
\min(
|\hat\theta-\theta|,
2\pi-|\hat\theta-\theta|
).
$$

---

### B. Barrier direction：核心

主 semantic target 定义为：

$$
\boxed{
\phi\in[0,\pi)
}
$$

即 barrier **长轴方向**。

不把“朝向小球的法向量”作为主 State concept，因为：

- barrier 本身视觉上最自然的是其延伸方向；
- normal 的正负选择需要额外 scene-dependent convention；
- 模型没有理由天然先把 barrier 与小球联合起来，再选“面向球”的 normal。

#### Physics normal 仍由 simulator 内部使用

Simulator 可由 \(\phi\) 导出：

$$
t=(\cos\phi,\sin\phi)
$$

以及两个 long-face normals：

$$
\pm n.
$$

实际碰撞时根据接触 face 决定法向量符号。

但 probe 的主要物理 concept 是：

$$
\phi
$$

而不是 signed normal。

---

### C. Barrier direction 的 parameterization robustness

#### 主语义形式：raw axis angle

$$
\phi\in[0,\pi)
$$

评价使用：

$$
d_{\pi}(\hat\phi,\phi)
=
\min(
|\hat\phi-\phi|,
\pi-|\hat\phi-\phi|
).
$$

#### Topology-correct auxiliary encoding

可以额外 probe：

$$
(\cos2\phi,\sin2\phi).
$$

它正确处理：

$$
\phi\sim\phi+\pi
$$

的无向线 topology。

但必须严格理解：

> 这是我们为了处理 target topology 选择的编码，不代表模型“天然存储 double-angle representation”。

#### 不把 \(\cos\phi\) 单独作为主 target

虽然在 \([0,\pi]\) 上 \(\cos\phi\) 一一对应，但它严重扭曲无向角度几何：

- \(1^\circ\) 与 \(179^\circ\) 对 barrier axis 来说只差 \(2^\circ\)；
- 但 cosine target 接近 \(+1\) 与 \(-1\)。

因此不作为首选形式。

---

### D. Position / geometry：辅助 State

保留：

- ball position \(p_c=(x_c,y_c)\)；
- barrier center \(b\)；
- relative distance；
- 可选 relative geometry feature。

它们不是当前最核心 headline State target，但对于：

- Contact；
- TTC；
- causal interpretation；

仍应完整保存和可 probe。

---

### E. Relative Geometry Metadata

为 GT oracle、debugging、shortcut diagnostics 保存：

#### Barrier center relative to ball

$$
\Delta b=b-p_c.
$$

#### Ball in barrier-local frame

$$
u_c=(p_c-b)\cdot t,
$$

$$
d_c=(p_c-b)\cdot n_c.
$$

还建议保存以下定义唯一的诊断量：

- `signed_center_clearance_to_nearest_long_face_contact_line_px`：
  $$
  |d_c|-(w/2+r);
  $$
- `endpoint_axial_margin_px`：
  $$
  L/2-|u_c|;
  $$
- `center_ray_min_distance_to_rectangle_px`：context-end ball-center infinite ray 到 closed physical barrier rectangle 的最小 Euclidean distance；
- `ball_surface_ray_min_clearance_to_rectangle_px`：
  $$
  \text{center-ray distance}-r;
  $$
- `candidate_collision_time_s`（若存在）；
- `actual_first_contact_feature`。

这些默认是：

> **metadata / oracle / diagnostics only**

而不是自动加入主 State probe matrix。

---

## 14.2 Prediction targets

### Contact Prediction

核心 binary：

$$
\boxed{\text{clean contact positive / strict safe negative}}
$$

注意它不再定义为简单 “within observed horizon”，也不等于未经筛选的 raw ray-intersection flag。`ray_hit` / `true_barrier_collision_exists` 只作为几何诊断字段，不直接等同于 Contact label。

---

### Collision Dynamics

对 positive subset：

- TTC：
  $$
  \tau=t_{collision}-t_c;
  $$
- contact point：
  $$
  q_{contact}=(q_x,q_y);
  $$
- post-collision velocity Cartesian：
  $$
  (v_x^+,v_y^+);
  $$
- post speed：
  $$
  s^+;
  $$
- post direction：
  $$
  \boxed{\theta_{v^+}}
  $$

其中：

> **post-collision direction 是第一部分最核心的 dynamics Prediction target。**

TTC / contact point 用于验证不同 future quantity 的 layerwise organization 是否有共同规律，但不是第二阶段 causal intervention 的主 endpoint。

---

## 14.3 Judgment targets

Reflection Judgment：

1. binary valid / invalid；
2. continuous angular violation：
   $$
   \Delta\theta
   $$

或其 normalized severity。

---

# 15. Broad Probe Training 与 Scene Generalization

Probe 的“泛化”不是所有实验都必须先满足的前提，而是一个独立、更强的 representation claim。

必须区分：

$$
\boxed{\text{within-domain decodability}}
$$

与：

$$
\boxed{\text{cross-domain alignment / invariance}}
$$

以及：

$$
\boxed{\text{causal use}}.
$$

它们不是同一个问题。

---

## 15.1 主 broad experiment：Pooled Diverse Training

第一部分主 layer map 中，不建议对每个：

- model；
- layer；
- target；
- readout；
- render family；

全部单独训练 probe。

否则组合爆炸。

主方案：

> **对 Diverse 数据统一训练一个 pooled probe。**

训练集均匀混合：

- Billiards；
- Air Hockey；
- Tabletop / Lab。

测试时：

- 报 overall；
- 同时报每个 family 的 subgroup performance。

这样首先回答：

> 在 heterogeneous visual domains 中，是否存在一个共同可学习的 readout？

---

## 15.2 Canonical 的角色

Canonical 主要用于：

$$
\boxed{\text{mechanistic cleanliness}}
$$

而不是要求：

> canonical-trained probe 必须 zero-shot 到全部 Diverse。

因此：

- Broad representation map：以 pooled Diverse 为主；
- Mechanistic causal experiment：Canonical subset；
- canonical → diverse transfer：可作为额外 robustness，不是项目成立前提。

---

## 15.3 Cross-domain generalization：Secondary analysis

只对：

- 少数核心 State target（尤其 velocity direction / barrier direction）；
- 少数代表层；
- 少数 readout；

做系统 cross-family transfer。

推荐：

### Leave-one-family-out

例如：

```text
train: billiards + air-hockey
test: tabletop
```

三个 family 轮流 held out。

### 可选 3×3 transfer matrix

```text
train family i → test family j
```

用于研究：

> 同一 physical variable 在不同 visual domain 中是否共享统一 coordinate system。

---

## 15.4 结果解释原则

### family-specific probe 都好，但 zero-shot transfer 差

支持：

> physical variable 在各域都可读，但 representation coordinate system domain-dependent。

不是 failure。

### pooled Diverse linear probe 好

支持：

> 至少在已观察 visual domains 上存在统一 linear readout。

### family-specific linear 好，pooled linear 差，但 pooled nonlinear 好

支持：

> 信息共享，但需要 context-dependent nonlinear readout。

### pooled / transfer 都差

说明 physical representation 更 strongly domain-conditioned。

仍然是科学结果，不是一票否决。

---

## 15.5 Paired render invariance 与真正 generalization 必须分开

同一个 latent trajectory：

$$
S_{0:T}
$$

可以渲染成：

$$
I^{billiards},
I^{airhockey},
I^{tabletop}.
$$

这些 paired renders 很适合研究：

> 同一 physics、不同 appearance 下 representation 怎样变化。

但这叫：

$$
\boxed{\text{controlled invariance analysis}}
$$

不等于真正 train→test generalization。

真正 held-out family test 中：

> test family 的 latent trajectories 也必须对 train latent scenes 不可见。

---

# 16. Train / Val / Test Split Integrity

## 16.1 Split 按 latent scene，而不是视频文件

同一 latent scene 的：

- 不同 render family；
- 不同 texture；
- good / bad Judgment pair；
- 相关 counterfactual variant；

默认必须被视为同一个 scene family，在普通 train/val/test 中不得泄漏。

---

## 16.2 Generalization experiment 例外必须显式定义

若专门做 same-latent paired invariance：

- 可以比较同一 scene 的不同 render；
- 但它不能被冒充成 held-out generalization。

若做 held-out semantic family：

- family held out；
- latent trajectory 同时也必须 held out。

---

# 17. 第二部分实验：Mechanistic Causal Microscope

第二部分目标不是再次做 representation steering，而是测试：

> **模型是否实际使用被识别出的 State representation，完成下游 physical Prediction / Judgment。**

核心逻辑：

$$
\text{State representation intervention}
\rightarrow
\text{downstream computation}
\rightarrow
\text{Prediction / Judgment change}.
$$

---

# 18. 第二阶段优先干预的 State 变量

v1 只优先考虑两个最直接影响反射关系的 State：

$$
\boxed{\theta_{v^-}}
$$

即 pre-collision / context-end velocity direction；

以及：

$$
\boxed{\phi}
$$

即 barrier axis direction。

暂不把：

- position；
- speed；
- barrier center；
- length；

作为第一批核心 intervention variable。

---

# 19. 第二阶段 Primary Causal Experiment A：State → Prediction

## 19.1 Intervention

尝试对内部 candidate representation 做：

$$
\theta_{v^-}: A\rightarrow B
$$

或：

$$
\phi: A\rightarrow B.
$$

具体 low-level 实现可能是：

- subspace interchange；
- token/region patching；
- 其他 causal intervention；

详见 [[07_Mechanistic_Interpretability_and_Causal_Intervention]]。

---

## 19.2 Primary downstream endpoint

只把：

$$
\boxed{\theta_{v^+}}
$$

作为第一版主 causal Prediction endpoint。

理论反射关系：

$$
\theta_{v^+}
=
f(\theta_{v^-},\phi).
$$

---

## 19.3 第一版不把 TTC / contact point 作为 causal endpoint

这不是因为 simulator 无法定义它们。

在一个人工 high-level world 中，如果我们规定：

$$
do(v_c\leftarrow v_c')
$$

并保持 \(p_c\) 不变，TTC 与 contact point 当然唯一确定。

真正的问题是：

> **低层 hidden-state intervention 并不天然等价于这个 high-level do-operation。**

模型内部 motion representation 很可能：

- 与 token spatial position 绑定；
- 与整段 trajectory 绑定；
- 是 local motion / optical-flow-like feature；
- 在不同时间位置用不同形式编码。

如果只修改所谓“velocity direction subspace”，可能造成：

- macro trajectory 仍暗示原方向；
- local token motion feature 却变成新方向；
- position、velocity、trajectory 不再一致；
- hidden state off-manifold。

因此：

> 我们无法自然可靠地声明：模型“认为球从 \(p_c\) 以新方向出发”。

于是 TTC / contact point 这类**高度依赖 position–trajectory coherence** 的 quantity 不适合第一版 causal endpoint。

---

## 19.4 Contact Prediction 也不纳入第一批 causal intervention

理由相同且更严重。

Contact 依赖：

$$
p_c,\quad v_c,\quad \phi,\quad b,\quad L.
$$

一个方向 patch 可能让内部：

- position；
- trajectory；
- velocity；

相互矛盾。

因此第二阶段主线暂不研究：

> patch direction → contact/no-contact。

Contact 继续作为第一部分 functional Prediction task。

---

# 20. Low-level patch 不能预先被称为 high-level `do`

必须明确：

$$
\boxed{
\text{low-level activation intervention}
\not\equiv
do(\text{physical variable})
}
$$

除非实验结果提供 causal alignment 证据。

因此论文/实验设计不应一开始写：

> “We perform \(do(v=v')\) inside the model.”

更严谨的表述是：

> 我们对一个与 velocity / barrier orientation 对齐的 candidate representation 做受控 intervention，并测试 downstream behavior 是否呈现与该 high-level physical counterfactual 一致的变化。

如果大量 matched trials 中：

$$
\theta_{v^+}^{model}
$$

系统地跟随：

$$
f(\theta_{v^-}^{intervened},\phi)
$$

或：

$$
f(\theta_{v^-},\phi^{intervened}),
$$

才逐步支持：

> 该 low-level intervention 近似实现了 high-level physical-variable intervention。

**causal alignment 本身就是实验要证明的对象，不是实验前提。**

---

# 21. 第二阶段 Primary Causal Experiment B：State → Judgment

这是第二阶段最重要、最漂亮的实验之一。

---

## 21.1 Base case

完整 observed video 是 valid：

$$
v_{obs}^+
=
R_{\phi}(v^-).
$$

模型/下游 readout 应判断：

$$
\text{valid}.
$$

---

## 21.2 只改内部 pre-state expectation，不改 observed future

例如内部 intervention：

$$
\theta_{v^-}\rightarrow\theta_{v^-}'.
$$

真实视频 post-collision trajectory 保持原样。

若模型真的用 pre-state velocity 构造 expectation，则新的内部 expected reflection 应近似：

$$
v_{CF}^{+*}
=
R_{\phi}(v^-').
$$

而 observed：

$$
v_{obs}^+
$$

没有改变。

于是新的物理不一致程度为：

$$
\Delta\theta_{CF}
=
d_{2\pi}
(
\theta(v_{obs}^+),
\theta(R_{\phi}(v^-'))
).
$$

理论上：

- invalid probability 应增加；
- predicted severity 应随 \(\Delta\theta_{CF}\) 改变。

---

## 21.3 Barrier direction intervention

同理，保持：

- incoming motion；
- observed post-collision trajectory；

不变，

内部尝试：

$$
\phi\rightarrow\phi'.
$$

新的 expectation：

$$
v_{CF}^{+*}
=
R_{\phi'}(v^-).
$$

再观察 Judgment 是否按：

$$
\Delta\theta_{CF}
$$

变化。

---

## 21.4 这个实验真正回答什么

不是：

> “我们能不能让模型更容易说 invalid？”

而是：

> **模型是否使用 State representation 构造物理 expectation，并用该 expectation 参与对观察结果的判断？**

这与简单：

$$
h'=h+\alpha u_{invalid}
$$

让模型偏向 “invalid” 完全不同。

---

# 22. Prediction → Judgment：Optional

只在第一部分出现明确 evidence，例如：

- Prediction information 明显比 Judgment 更早形成；
- 存在稳定 candidate prediction subspace；
- layerwise pattern 支持某条候选链；

才考虑：

$$
\boxed{
\text{Prediction representation}
\rightarrow
\text{Judgment}
}
$$

的干预。

它不是 v1 必做，也不预设 universal：

$$
\text{State}\rightarrow\text{Prediction}\rightarrow\text{Judgment}.
$$

---

# 23. 第二阶段 Source/Base Pair 的生成

## 23.1 Counterfactual label 不需要现在预渲染

当前生成主 benchmark 时，只需保存足够完整 latent metadata。

第二阶段开始后，可以按需：

1. 选择 base scene；
2. 选择目标 intervention；
3. 用 simulator 计算 high-level counterfactual；
4. 必要时生成 source scene；
5. render source input；
6. 抽取 source activation；
7. 做 low-level intervention。

不需要现在把所有潜在 counterfactual 视频全部生成。

---

## 23.2 但 real-source interchange 最终需要 source input

如果使用：

$$
h_A'=(I-P)h_A+Ph_B,
$$

则必须真的得到：

$$
h_B.
$$

因此：

> simulator counterfactual GT 可以不预渲染；  
> real-source activation patching 在执行时仍需要 source video/input。

---

## 23.3 Velocity source pair

尽量构造：

$$
S_A(t_c)=(p_c,v_A,\phi,\ldots)
$$

与：

$$
S_B(t_c)=(p_c,v_B,\phi,\ldots)
$$

即：

- context-end position 一样；
- barrier 一样；
- speed 可保持一样；
- 只改变 velocity direction。

然后向后积分得到 source Context。

这能最大程度减少 source/base 差异。

---

## 23.4 Barrier source pair

构造：

$$
(p_c,v_c,\phi_A,b,L,w)
$$

与：

$$
(p_c,v_c,\phi_B,b,L,w).
$$

保持：

- ball state；
- barrier center；
- length；
- width；
- appearance family；

尽量一致，只改变 barrier orientation。

---

# 24. Intervention-safe Subset

第二阶段不能对任何任意 base scene 做任意方向修改。

应专门从 Canonical 数据中建立：

$$
\boxed{D_{mech-safe}}
$$

要求对 base/source/high-level counterfactual：

- ball 整个圆盘全程位于 Physics ROI；
- barrier 整个矩形位于 Physics ROI；
- 都是 clean long-face collision；
- endpoint margin 满足 $d_1=0.625$ cell；
- impact angle / outgoing angle 满足 >10°；
- collision frame 都在 12–19；
- 不触 corner / short face；
- 不发生 second collision；
- source 与 base 的非目标物理量及 appearance 尽可能 matched。

这样 finite barrier 可以保留，不需要换成无限长墙。

---

# 25. 第二阶段的 manipulation check 与 causal outcome

如果一个 candidate State subspace 被修改，可以额外检查：

> State probe 是否认为被修改后的 representation 朝目标 state 移动？

这只是：

$$
\boxed{\text{manipulation sanity check}}
$$

不是核心 causal result。

核心结果是：

$$
\boxed{
\text{State intervention}
\rightarrow
\text{different downstream physical variable}
}
$$

例如：

$$
\theta_{v^-}
\rightarrow
\theta_{v^+},
$$

或：

$$
\theta_{v^-}
\rightarrow
J.
$$

因此：

- 原第一部分训练好的 State probe 可以继续使用；
- 原第一部分训练好的 Prediction probe 也可以继续使用；
- 不需要仅因为“独立性”再训练一套等价 Prediction probe。

真正需要避免的循环是：

> 用某 probe 定义 edit，又用同一个 probe 证明“被 edit 的同一个变量变了”，并把这当作 causal reasoning 结果。

---

# 26. Renderer 总体设计：Natural but Controlled

Renderer 的目标不是尽可能追求 photorealism，也不是做大规模 domain randomization，而是：

> **让模型自然地把视频理解成“水平桌面上的球/圆盘撞击一个固定挡板”，同时让所有视觉 nuisance 都保持可控、可记录、可平衡，并显著弱于真正的物理变量变化。**

Renderer 必须遵守以下最高优先级原则：

1. **physics–appearance 解耦**：视觉资产不得改变 simulator 的几何、accept/reject 或 task label；
2. **geometry fidelity**：ball、barrier、table 的可见轮廓必须与 latent geometry 一致；
3. **temporal consistency**：同一视频中的所有静态纹理、颜色、亮度参数必须固定，禁止逐帧重新采样造成 flicker；
4. **no hidden motion cue**：Canonical 不加 motion blur，ball 不使用可观察 rolling orientation 的纹理；
5. **no directional-world cue**：不使用具有固定世界方向的 cast shadow、斜向 illumination gradient 或 perspective texture；
6. **matched-pair consistency**：Judgment good/bad pair 必须共享完全相同的 appearance specification；
7. **mechanistic cleanliness first**：任何“更真实”但可能引入额外 shortcut 的视觉效果都优先不加入。

## 26.1 Canonical 与 Diverse 是两个 rendering regime

正式区分：

```text
render_regime ∈ {canonical, diverse}
```

### Canonical

Canonical 主要服务于：

$$
\boxed{\text{mechanistic cleanliness}}
$$

以及第二阶段 causal intervention。

Canonical 的视觉资产**全部固定**，不对每个 scene 随机变化：

- fixed surface；
- fixed outside-table background；
- fixed ball color；
- fixed barrier material；
- fixed table rail；
- fixed lighting / global tone；
- no texture randomization；
- no motion blur；
- no cast shadow。

当前 v1 Canonical 定义为一个 **neutral puck-table / lab-table hybrid**，视觉语义接近 air-hockey / lab tabletop，但不加入会分散注意力的复杂比赛线条。

推荐基础颜色：

```text
canonical_surface_rgb       = [226, 226, 221]   # off-white / light warm gray
canonical_outer_rail_rgb    = [226, 226, 221]   # same-tone hairline only; no wide rail
canonical_outside_rgb       = [48, 50, 52]      # dark charcoal
canonical_ball_rgb          = [182, 62, 56]     # muted red
canonical_barrier_rgb       = [76, 81, 86]      # dark neutral metal
canonical_bolt_rgb          = [181, 185, 188]   # visible cross-recess screw heads
```

Canonical surface 使用固定 seed 的低对比浅木纹，并移除不同颜色的宽桌沿；这仍属于 fixed
canonical asset，而不是 per-scene texture randomization。桌角使用约 6 px 小圆角。

这些 RGB 是 renderer v1 的默认值；若后续只做不改变结构的细微视觉调优，应增加 `renderer_version`，而不是改 simulator dataset version。

### Diverse

Diverse 主要服务于：

- broad layerwise probing；
- pooled-Diverse training；
- cross-family transfer；
- paired-render invariance analysis。

Diverse 包含三个 semantic family：

```text
billiards
air_hockey
tabletop
```

Diverse 的变化方式统一采用：

$$
\boxed{\text{discrete style preset} + \text{small continuous jitter}}
$$

而不是在整个 RGB / texture space 中无约束连续随机。

理由：

- discrete preset 便于 metadata 记录、balancing 与 shortcut audit；
- small jitter 避免每个 preset 看起来像完全重复的 sprite；
- 不会生成低对比、异常高饱和或语义不合理的组合。

## 26.2 Render nuisance 的随机性必须与 physics label 独立

除非做专门 controlled experiment，以下 appearance variable 的 sampling 必须与：

- Contact label；
- speed；
- velocity direction；
- barrier orientation；
- Judgment validity；
- violation severity；

独立。

至少包括：

- surface style；
- ball color；
- barrier material；
- outside-table background；
- global brightness / gamma jitter。

正式 dataset 必须检查：

$$
P(\text{appearance ID}\mid y)
$$

在不同 label 下没有明显失衡。

## 26.3 同一 appearance 在整段视频中完全固定

对一个 `render_variant_id`：

- table texture 不随 frame 变化；
- outside background 不随 frame 变化；
- ball color 不随 frame 变化；
- barrier texture / bolt pattern 不随 frame 变化；
- global brightness / gamma 不随 frame 变化。

如果 procedural texture 使用 random noise，必须在视频开始前由 `RenderSpec` 的固定 seed 生成一次，之后所有 frame 复用同一 texture。

---

# 27. Semantic Render Families 与背景设计

## 27.1 所有 family 的共同空间原则

Visual table 的 base playing-surface footprint 始终是：

$$
420\times308\ \text{px}=15\times11\ \text{cells}.
$$

Physics ROI 仍只存在于 latent geometry 中，**不得在画面中显式画成矩形框**。

桌面必须完整可见，桌外必须保留一圈 background，使模型能明确判断：

> 这是一个从上方观察的水平桌面，而不是填满 frame 的竖直纹理平面。

Visual table 的 outer rail / border 不得侵入 Physics ROI 形成新的潜在“物理墙”。

建议 outer rail 的可见厚度：

```text
6–10 px
```

通常小于 table 与 Physics ROI 之间每侧 14 px 的视觉 buffer。Air-Hockey 的 8 px rail
位于 420×308 base footprint 外侧，使 outer footprint 扩展为 436×324 px，不消耗内部 buffer。

## 27.2 桌外区域的统一设计原则

桌外区域必须：

- 低饱和；
- 中低亮度；
- 低纹理；
- 无强方向性；
- 与桌面有足够 contrast 以显示桌面边界；
- 不使用纯白 / 纯黑极端背景；
- 不使用棋盘格、地砖缝、透视地板等强结构纹理。

Diverse 中可以从 family-specific 的少量 preset 中离散采样，再做轻微亮度 jitter。

## 27.3 Billiards family

### Surface

语义必须保持为绿色 felt，不使用红桌、蓝桌、紫桌等大跨度变化。

建议 v1 预生成 4 个 base surface preset：

```text
billiards_surface_0 = [47, 112, 73]
billiards_surface_1 = [37, 101, 68]
billiards_surface_2 = [54, 121, 82]
billiards_surface_3 = [43, 95, 70]
```

允许在选中 base preset 后加入：

```text
surface_brightness_gain ~ U(0.96, 1.04)
surface_saturation_gain ~ U(0.96, 1.04)
hue_jitter_deg          ~ U(-2, 2)
```

但最终仍必须明显属于 green felt family。

Texture 只允许非常弱的无方向 fine noise / felt grain；luminance variation 建议不超过 base value 的约 3%。

### Table rail

以深褐 / dark walnut / near-black brown 为主，例如：

```text
[74, 48, 34]
[58, 42, 34]
[83, 53, 37]
```

允许极弱 wood-like variation，但不得出现明显单方向长木纹。

桌沿采用两层结构：外侧 7 px 为上述深色木制边沿，内侧 5 px 为绿色 felt cushion。
felt cushion 与主桌面之间必须有一条低对比但可见的分界线。outer corner 使用约 13 px
圆角，避免画框式直角。

### Pockets

保留六个标准 top-down 圆形 billiards pockets 作为 semantic cue，v1 直径约 14 px。
球袋周围不添加与其他外侧木沿不同色的金属/皮革 patch。

Pockets 只存在于 table edge；Physics ROI 与 ball-center legal region 已使主轨迹远离桌边，因此 pocket 不参与 v1 physics。

### Outside-table background

使用 dark charcoal / brown-gray，例如：

```text
[44, 42, 40]
[52, 48, 45]
```

只允许弱全局 noise，不画地板缝或透视线。

## 27.4 Air-Hockey family

### Surface

必须保持白 / off-white / very light gray：

```text
air_surface_0 = [238, 238, 235]
air_surface_1 = [232, 235, 238]
air_surface_2 = [244, 243, 237]
air_surface_3 = [235, 238, 236]
```

桌面必须加入浅色、低 contrast 的规则 air holes。v1 使用约 14 px 间距、约 1 px
可见直径的小孔；小孔只提供 air-hockey 语义，不参与 physics。

### Markings

应包含标准、完全对称且低 contrast 的：

- center line；
- center circle；
- zone / goal lines；
- 四个 face-off circles 及内部 crosshair；
- 对称 face-off dots；
- 可选 goal arcs / inset rink outline。

要求：

- 线宽细；
- 低 contrast；
- 左右/上下对称；
- 不根据 physics label 改变；
- 不生成恰好沿某条典型 ball trajectory 的单侧强线条。

推荐 marking luminance 与 surface 相差不超过约 10–15%。

### Rail

medium gray / blue-gray / dark neutral plastic：

```text
[92, 99, 105]
[82, 91, 103]
[110, 112, 114]
```

Air-Hockey playing surface 仍为 420×308 px；8 px rail 向其外侧扩展，因此 outer footprint
为 436×324 px。四角 radius 默认 58 px，明确形成大圆角 table/rink silhouette。

### Outside-table background

medium-dark neutral gray：

```text
[58, 61, 64]
[66, 68, 70]
```

## 27.5 Tabletop / Lab family

### Surface

必须以浅色为主：

```text
tabletop_surface_0 = [225, 219, 205]   # warm beige
tabletop_surface_1 = [224, 226, 222]   # neutral light gray
tabletop_surface_2 = [232, 228, 218]   # pale warm wood-like
tabletop_surface_3 = [219, 225, 228]   # pale blue-gray
```

允许：

- 极弱 low-frequency mottling；
- 弱而可辨认的 procedural 浅木纹；
- 低 contrast procedural texture。

禁止：

- 高对比、周期性或近似平行线网格的 wood grain；
- 砖缝；
- 网格；
- 长直线纹路；
- perspective floor texture。

wood grain 可沿桌面长轴形成弱方向性，以增强水平桌面语义，但必须非周期、独立采样且
luminance amplitude 约不超过 3.2%，并纳入 appearance–label independence audit。

### Table edge

Canonical 与 Tabletop 默认不画不同颜色的 picture-frame 式桌沿。桌面依靠木纹、桌外背景
contrast 和约 6 px 的小圆角表达边界；允许极细、同色系 edge line，但不允许形成宽 rail。

### Outside-table background

使用 desaturated warm gray / neutral gray：

```text
[72, 70, 67]
[68, 71, 72]
```

## 27.6 Lighting 与光影

v1 不使用真实 directional lighting。

明确禁止：

- directional cast shadow；
- barrier 在固定世界方向投射的长阴影；
- ball 单侧 shadow；
- across-frame directional illumination gradient；
- 会暗示 camera tilt / world vertical 的高光布局。

Canonical：

```text
directional_light = false
cast_shadow = false
global_brightness_gain = 1.0
global_gamma = 1.0
global_saturation_gain = 1.0
```

Diverse 只允许很轻的**全局、无方向** tone variation：

```text
global_brightness_gain ~ U(0.96, 1.04)
global_gamma           ~ U(0.97, 1.03)
global_saturation_gain ~ U(0.96, 1.04)
```

这些参数对整张视频固定。

若未来想引入更自然 lighting，必须作为单独 renderer version / robustness extension，而不是静默加入 v1。

---

# 28. Ball、Barrier 外观与 Visual Asset Creation

## 28.1 Ball：几何与纹理原则

Ball / puck 的可见 silhouette 必须严格对应：

$$
d_{ball}=35\ \text{px}.
$$

v1 ball 定义为：

> **solid-color, axisymmetric, orientation-free object**。

具体要求：

- 整体纯色填充；
- 只有 antialiased edge；
- 不画数字；
- 不画条纹；
- 不画 logo；
- 不画可观察方向的 highlight；
- 不画 rolling texture；
- 不随 frame 改变颜色或纹理。

这样视频本身不会告诉模型球是在 rolling 还是 sliding。

## 28.2 Canonical ball

Canonical ball 颜色固定：

```text
canonical_ball_rgb = [182, 62, 56]
```

即 muted red。

Canonical 不做任何 per-scene color jitter。

## 28.3 Diverse ball color sampling

Diverse 不在完整 RGB cube 连续采样，而使用：

$$
\boxed{\text{small discrete palette} + \text{weak jitter}}
$$

每个 family 默认 5 个 base color，均匀采样。

### Billiards ball palette

```text
muted_red    = [184, 72, 64]
cobalt_blue  = [63, 99, 158]
ochre        = [190, 147, 55]
muted_orange = [194, 103, 58]
ivory        = [215, 208, 191]
```

不使用绿色 ball，避免与 green felt 低对比。

### Air-Hockey ball palette

```text
red          = [190, 61, 57]
blue         = [55, 92, 154]
charcoal     = [62, 66, 70]
orange       = [201, 104, 50]
dark_teal    = [42, 102, 106]
```

不使用 white / near-white puck，避免与白色桌面低对比。

### Tabletop ball palette

```text
red          = [184, 67, 61]
blue         = [62, 97, 151]
orange       = [197, 111, 56]
dark_teal    = [48, 103, 104]
charcoal     = [69, 72, 74]
```

选中 base color 后允许：

```text
ball_brightness_gain ~ U(0.95, 1.05)
ball_saturation_gain ~ U(0.95, 1.05)
ball_hue_jitter_deg  ~ U(-2, 2)
```

最终 renderer 必须做 minimum-contrast check，避免 ball 与 local table surface 亮度/颜色过于接近；不满足时重新采 appearance，而不是改变 physics scene。

## 28.4 Barrier：必须在完全矩形 footprint 内表达“固定/很重”

Barrier 的可见 silhouette 必须严格是 simulator 的：

$$
140\times28\ \text{px}
$$

矩形 footprint。

不得添加任何超出 footprint 的：

- foot；
- clamp；
- handle；
- protrusion；
- shadow geometry。

### 固定视觉暗示

v1 使用：

> **105 px 厚重中央主体 + 两端各 17.5 px 扁平固定片 + 4 个 cross-recess screw heads**。

所有视觉固定结构完全位于 barrier rectangle 内。

沿 long axis 的分区固定为：

```text
left end plate    = 17.5 px
central body      = 105 px = 3.75 cell
right end plate   = 17.5 px
```

四个 screw head 只放在两端固定片上，每端两个：

```text
u = ±61.25 px
v = ±6 px
screw_head_radius = 5.5 px
screw_drive       = cross_recess
```

其中：

- $u$ 沿 barrier long axis；
- $v$ 沿 barrier short axis。

四个 screw 对称布置，十字槽在原始 448 视频尺度下应可辨认，且不能形成箭头、正负方向
或某一端“更重”的视觉暗示。

中央主体与两端固定片必须使用可区分但同材质系的颜色/明度；中央主体可再画完全位于其
105×28 footprint 内的 2 px inset bevel / border，以表达主体更高、端片更扁。

### 关键限制

Barrier 的视觉装饰必须保持 180° 对称，不能让模型通过纹理本身定义一个有向 arrow-like orientation。

## 28.5 Canonical barrier

固定：

```text
material_id = canonical_dark_metal
base_rgb    = [76, 81, 86]
screw_head_rgb = [181, 185, 188]
texture     = none
bevel       = enabled
bolt_count  = 4
screw_drive = cross_recess
```

## 28.6 Diverse barrier materials

每个 semantic family 默认提供 3 个离散 material preset，再做弱亮度 jitter。

### Billiards

```text
dark_wood   = [82, 54, 39]
near_black  = [52, 48, 45]
dark_brown  = [96, 63, 43]
```

### Air Hockey

```text
dark_plastic = [64, 69, 74]
blue_gray    = [73, 84, 98]
light_plastic = [155, 159, 161]
```

### Tabletop / Lab

```text
aluminum_gray = [130, 136, 140]
dark_metal    = [69, 74, 78]
matte_black   = [52, 54, 56]
```

Material texture 只能是低 contrast、近各向同性的细微 roughness；不得加入高 contrast wood grain、brushed-line direction、文字或 logo。

建议：

```text
barrier_brightness_gain ~ U(0.96, 1.04)
texture_luminance_amplitude <= 0.03
```

## 28.7 Visual assets 的来源：全部 procedural，不以生成式 AI 图片为主资产

v1 正式规定：

> **主要视觉资产使用 NumPy / OpenCV / Pillow 程序化生成，不使用生成式 AI 图片作为核心 background / texture source。**

原因：

- procedural asset 可 deterministic replay；
- 没有不可控 perspective / lighting cue；
- 易于记录 nuisance metadata；
- 易于保证 texture 与 label 独立；
- 易于做 matched good/bad render；
- 不会混入文字、logo、奇怪物体或语义 artifact。

推荐 asset pipeline：

```text
AssetBankConfig
        ↓
procedural surface preset generation
        ↓
procedural rail/background preset generation
        ↓
ball palette generation
        ↓
barrier material / bolt preset generation
        ↓
static AssetBank
        ↓
RenderSpec selects preset IDs + small jitter
```

### v1 Diverse 默认 asset bank 大小

每个 family 默认：

```text
surface_style_count           = 4
outside_background_count      = 2
ball_color_count              = 5
barrier_material_count        = 3
table_rail_style_count        = 3
```

Air-Hockey 可额外提供：

```text
marking_style_count = 3
```

这些数量用于第一版 asset generation；后续增加 asset 数量只需更新 `renderer_version / asset_bank_version`，不改变 physics dataset version。

## 28.8 Anti-aliasing 与 supersampling

最终输出：

$$
448\times448.
$$

推荐内部：

$$
896\times896\rightarrow448\times448
$$

或其他整数倍 supersampling 后 antialiased downsample。

所有物理位置仍定义在 448-space，supersampling 仅用于 rasterization。

## 28.9 RenderSpec 必须在视频级固定

一个 `appearance_spec_id` 决定一个视频的全部静态 visual nuisance。

对于 Judgment good / bad pair：

$$
\boxed{\text{appearance\_spec\_id}^{good}=\text{appearance\_spec\_id}^{bad}}
$$

也就是说：

- same surface preset；
- same texture；
- same ball color；
- same barrier material；
- same bolts；
- same global tone；
- same background；
- only post-collision trajectory differs。

第二阶段 matched source/base 若用于 mechanistic intervention，也应尽量复用相同 appearance spec。

---

# 29. 可选空间分析：Physical Information Globalization

这是一个 **Optional but highly motivated follow-up**，不是 v1 Must-have。

问题：

> 物理 motion information 是否从 object-local token 逐渐传播为全局 spatially redundant representation？

我们的球位置不固定，因此不应按绝对 image coordinates 对齐。

可以使用 object-centric 分析：

对每层 token，根据 token 空间中心到 ball center 的距离分组：

- ball-overlap；
- near-ball；
- far-background。

分别测试 velocity / direction decodability。

如果早期：

$$
P_{ball}\gg P_{far},
$$

而深层：

$$
P_{ball}\approx P_{far},
$$

则支持 spatial globalization。

这个分析尤其适合在出现：

- Mean Pooling 突然改善；
- Attentive Pooling → Mean gap 明显变化；

时作为机制解释。

它不是主 novelty，不应抢占主实验。

---

# 30. Benchmark Qualification：进入 Foundation Model 前必须完成

在正式跑大模型前，benchmark 必须先通过资格测试。

---

## 30.1 Full-GT oracle

使用 simulator 完整 state 与解析物理规则，任务必须接近 ceiling。

若 full-GT oracle 都不能正确完成：

> **benchmark invalid，必须先修。**

---

## 30.2 Prediction target qualification

对于用于“模型是否执行额外 computation”论证的 Prediction target，应检查：

$$
\text{GT-State Linear}
\ll
\text{GT-State MLP/Oracle}.
$$

如果某 target：

$$
\text{GT-State Linear}\approx100\%,
$$

则不适合用来证明 predictor 执行了额外 nonlinear relation computation。

它仍可做 control，但 claim 必须降级。

---

## 30.3 Label / nuisance marginal checks

至少检查：

- speed；
- velocity direction；
- barrier orientation；
- absolute ball position；
- barrier center；
- ball–barrier distance；
- impact angle；
- collision point；
- render family；
- object color；
- barrier material；
- texture。

不能存在：

> 单一 nuisance 高精度决定 label

的明显 shortcut。

---

## 30.4 Judgment shortcut baselines

至少做：

- first frame only；
- last frame only；
- random frame only；
- pre-only；
- post-only。

Reflection Judgment 的理想情况：

> 单独 pre / post 都显著弱于完整 `(pre, barrier, post)` relation。

此外必须检查 valid / invalid 的 marginal：

$$
P(\theta^-|valid)\approx P(\theta^-|invalid),
$$

$$
P(\phi|valid)\approx P(\phi|invalid),
$$

$$
P(\theta^+|valid)\approx P(\theta^+|invalid),
$$

以及 speed、collision point、violation sign、severity、render nuisance。

**Alternate-barrier feasibility 不能替代统计 marginal matching。**

---

## 30.5 Temporal controls

按 task 选择：

- frame shuffle；
- time reversal；
- single-frame baseline。

不应机械地对所有 State target 都使用。

---

## 30.6 Render / codec artifact check

必须人工和程序检查：

- valid/invalid 不因编码伪影区分；
- collision frame 不发生独特 compression artifact；
- invalid video 没有 discontinuity / pixel hack；
- good/bad 只在预期的 latent trajectory 处不同。

所有 Judgment 视频都必须从 latent trajectory **重新渲染**，不能通过像素级剪贴/扭曲构造。

---

## 30.7 Renderer / Asset Qualification

正式 foundation-model experiment 前，renderer 还必须通过以下检查：

### Temporal consistency

- 静态 background / texture 在 24 帧中逐像素固定；
- 不存在 per-frame random noise flicker；
- ball 只有位置变化，不存在颜色/纹理闪烁。

### Geometry fidelity

- ball visible diameter 与 latent 35 px 定义一致；
- barrier silhouette 与 $140\times28$ px rectangle 一致；
- bolt / bevel 全部位于 barrier footprint 内；
- table rail 不侵入 Physics ROI。

### No directional-light shortcut

- 无 cast shadow；
- 无固定方向 illumination gradient；
- 无 perspective texture cue。

### Appearance–label independence

用 metadata 直接训练简单 classifier / tabular baseline：

```text
surface_style_id
ball_color_id
barrier_material_id
outside_background_style_id
global tone parameters
```

不应能显著预测 Contact label 或 Judgment validity。

### Matched Judgment render

Good / bad pair 的 `appearance_spec_id` 必须完全相同。

如果仅凭 render metadata 就能区分 valid / invalid，则 benchmark invalid。

---

# 31. 一票否决 Failure Modes 与“只是结果”的现象

真正的一票否决应针对：

$$
\boxed{\text{benchmark validity}}
$$

而不是“模型没有按我们的预期泛化”。

---

## 31.1 必须修复，否则不能进入主实验

- Full-GT oracle 做不好；
- positive / negative / reject 三类实现与本文档不一致；
- reject 被误当 negative；
- Judgment first/last frame shortcut 接近满分；
- valid/invalid 有明显 renderer/codec artifact；
- Contact label 被 speed / angle / color / scene family 等单变量高精度预测；
- 主 “nonlinear Prediction” target 被 GT-state linear model 近乎满分解决；
- ball 或 barrier 任何时刻超出 Physics ROI；
- Context 中发生 collision；
- collision 不在 frames 12–19；
- short-face / corner / ambiguous contact 进入 positive；
- negative 中混入 “其实会撞，只是视频时间不够”；
- negative ray 进入 $d_2$ safety region；
- Judgment invalid 穿墙或 near-tangent；
- Judgment alternate-barrier feasibility 未实现；
- good/bad 的速度、方向、sign、severity 等 marginal 严重失衡且未控制；
- support 几何因 render family 改变 latent acceptance；
- background / texture 在视频中逐帧 flicker；
- renderer 引入 directional cast shadow / perspective cue；
- appearance style ID 与 Contact / Judgment label 存在明显相关；
- Judgment good/bad 没有共享同一 `appearance_spec_id`。

---

## 31.2 不是 failure，而是研究结果

以下都不构成项目失败：

- Canonical probe 无法 zero-shot 到 Diverse；
- Billiards-trained probe 无法迁移到 Tabletop；
- 三个 domain 各自可读，但不存在统一 linear readout；
- Judgment 没有统一 physical-validity direction；
- V-JEPA Judgment 弱；
- linear probe 可读但 causal intervention 无效；
- candidate state subspace 无法被独立、干净地操控；
- domain-general probe 需要 nonlinear readout。

这些现象反而可以揭示 representation 的：

- domain dependence；
- entanglement；
- causal irrelevance；
- non-manipulability。

---

## 31.3 Practical go/no-go

如果在最干净 Canonical scene 下：

- velocity；
- barrier orientation；

连较强 readout 都几乎无法恢复，

并且：

- collision-related Prediction 也基本无信号，

则第二阶段 State → Prediction causal mechanism 很难继续。

此时应优先排查：

- renderer 是否过度 OOD；
- clip sampling 是否不合适；
- activation extraction 是否有 bug；
- target 定义是否太难；
- backbone 本身是否真的没有相关 signal。

---

# 32. Simulator、Renderer、Dataset Index 与 Task Manifest 的代码职责

正式推荐把系统理解为四个层级：

$$
\boxed{\text{Simulator}}
\rightarrow
\boxed{\text{Renderer}}
\rightarrow
\boxed{\text{Dataset Index}}
\rightarrow
\boxed{\text{TaskManifestBuilder}}
$$

它们分别回答：

1. **Simulator**：世界发生了什么？
2. **Renderer**：这个物理世界长什么样？
3. **Dataset Index**：磁盘上实际存了哪些 latent scene、trajectory、render、Judgment pair？
4. **TaskManifestBuilder**：某个实验具体消费哪些样本、哪些 frame、哪些 target？

## 32.1 物理与渲染生成主流程

```text
PhysicsConfig
        ↓
SceneProposalSampler
        ↓
AnalyticGeometry / Simulator
        ↓
Continuous Trajectory + Events
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
        ↓
DatasetIndex
```

Judgment：

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
Matched Good / Bad Trajectories
        ↓
shared AppearanceSpec
        ↓
Renderer
        ↓
DatasetIndex
```

第二阶段：

```text
Stored Base Scene
        ↓
Counterfactual / Source Generator
        ↓
Intervention-safe Validation
        ↓
On-demand Source Rendering
```

## 32.2 `TaskLabelGenerator` 与 `TaskManifestBuilder` 必须严格区分

旧的 “Task Generator” 这个名字容易把两个完全不同的职责混在一起，v1 不再单独使用该模糊术语。

### `TaskLabelGenerator`

位于 simulator pipeline 内部。

职责：

> 从已经接受的 latent physics / exact event metadata 中派生 canonical task labels。

例如：

- State labels；
- `contact_binary`；
- TTC；
- contact point；
- post-collision direction；
- Judgment validity / severity。

它**不决定训练/测试 split，不做实验采样，不处理模型输入格式**。

### `TaskManifestBuilder`

位于完整 dataset 已生成之后。

职责：

> 从 Dataset Index 中构造某个具体实验要消费的 dataset view / manifest。

它：

- 不重新模拟 physics；
- 不重新计算 label；
- 不修改视频；
- 不复制视频作为默认行为；
- 只做 filtering、selection、balancing、field projection 与 task-level packaging。

因此更准确的概念是：

$$
\boxed{\text{TaskManifestBuilder} \approx \text{DatasetViewBuilder}}
$$

## 32.3 Renderer 的唯一输入是 latent trajectory + RenderSpec

Renderer 不得根据：

- Contact label；
- Judgment validity；
- violation severity；

选择视觉风格。

Renderer 只接收：

```text
trajectory_variant
appearance_spec
frame_times
```

并输出 RGB frames / encoded video。

## 32.4 Task manifest 定义的是“语义输入区间”，不是模型特定 tensor

例如：

- State / Contact / Dynamics 的观测语义区间是 Context frames 0–7；
- Judgment 的观测语义区间是 full video frames 0–23。

但具体 V-JEPA / VLM 如何：

- resize；
- resample frame；
- pack temporal tubelets；
- construct masked prediction input；

属于 model adapter / experiment code，不由 05 文档固定。

Task manifest 只需要明确：

```text
observation_start_frame
observation_end_frame
context_frame_indices
future_frame_indices
```

以及 target fields。

---

# 33. `PhysicsConfig`

至少：

```yaml
frame_width_px: 448
frame_height_px: 448
cell_px: 28

table_width_px: 420
table_height_px: 308

physics_roi_width_px: 392
physics_roi_height_px: 280

ball_diameter_px: 35
ball_radius_px: 17.5

barrier_length_px: 140
barrier_width_px: 28

fps: 24
num_frames: 24
num_context_frames: 8

collision_frame_min: 12
collision_frame_max: 19

endpoint_margin_px: 17.5        # d1 = 0.625 cell
negative_safety_margin_px: 35   # d2 = 1.25 cells
min_impact_angle_deg: 10
min_bad_outgoing_angle_deg: 10

speed_min_cells_per_s: 5.0
speed_max_cells_per_s: 8.5

proposal_mode: independent_uniform
speed_distribution: uniform_range
velocity_angle_distribution: uniform_0_2pi
barrier_axis_angle_distribution: uniform_0_pi
p_context_distribution: uniform_ball_center_legal_region
barrier_center_distribution: uniform_orientation_conditioned_feasible_region
rng_algorithm: numpy_pcg64_seedsequence

violation_delta_min_deg: 5
violation_delta_max_deg: 90
max_violation_sampling_attempts: 128

spatial_epsilon_px: 1.0e-9
time_epsilon_s: 1.0e-12
angle_epsilon_rad: 1.0e-12

restitution: 1.0
friction: 0.0
```

其中 speed range 是当前默认 pilot，必须保留 config 能力。`motion_blur` 不属于 `PhysicsConfig`，必须放在 `RenderSpec / RenderConfig` 中。

---

# 34. `SceneSpec`

至少：

```text
latent_scene_id
scene_seed
proposal_index
proposal_mode

p_context_xy
speed_px_per_s
speed_cells_per_s
velocity_angle_rad              # canonical range [0, 2π)
velocity_xy

barrier_center_xy
barrier_axis_angle_rad          # canonical range [0, π)
barrier_length_px
barrier_width_px

ball_radius_px
```

`split` 属于 dataset-level record，不是 latent physics 本身的构造字段。`velocity_xy`、`speed_*` 与 `velocity_angle_rad` 虽同时保存，但必须在 schema validation 中检查它们在数值容差内一致。

---

# 35. `Trajectory` / `CollisionEvent`

Frame state：

```text
trajectory_variant_id
frame_times_s
ball_center_xy[frame]
velocity_xy[frame]
p_end_at_t1_xy
barrier_vertices_xy
barrier_tangent_xy
```

`p_end_at_t1_xy` 是 $p(1.0\text{s})$ 的未渲染 safety endpoint。若 frame timestamp 恰好等于 collision time，`velocity_xy[frame]` 采用 post-collision velocity。

Event：

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
post_collision_angle_rad        # canonical range [0, 2π)
```

`contact_normal_xy` 必须按第 4.2 节的规约指向 pre-contact ball center 所在的外部半平面。

`future_first_contact_exists=true` 仅表示 $[t_c,1.0\text{s})$ 内存在真实 first contact。字段 nullability 固定为：

- `long_face / short_face`：全部 event 字段非空；
- `corner`：time、frame、face ID、ball center、surface point、axis coordinate、pre-velocity 与 feature 非空；normal、impact angle 和 post-collision quantities 为 `null`；
- `ambiguous`：time、frame、ball center、pre-velocity 与 feature 非空；其余 event 字段为 `null`；
- `future_first_contact_exists=false`：`first_contact_feature="none"`，其余 event 字段全部为 `null`。

无限射线上的 clip 外候选时间另存为 `candidate_collision_time_s`，不伪装成 clip 内 `CollisionEvent`。

---

# 36. `ContactClassification`

必须显式输出：

```text
status ∈ {positive, negative, reject}
contact_binary ∈ {1, 0, null}
```

建议额外保存：

```text
negative_safe_ray_no_intersection      # infinite center ray 不与 B_safe 相交
true_barrier_collision_exists          # infinite disk trajectory 与物理 rectangle 的任意 feature 存在 first contact
legal_long_face_collision_exists       # first contact 为 long-face interior
collision_in_positive_window           # legal collision frame ∈ [12, 19]
collision_after_positive_window        # legal collision frame >= 20
collision_after_clip                   # legal collision time >= 1.0 s
```

这样从数据结构上阻止 reject 与 negative 混淆。

---

# 37. `AcceptanceReport`

必须保存：

```text
accepted_for_contact
accepted_for_dynamics
judgment_base_geometry_eligible
status
rejection_reasons[]
```

`judgment_base_geometry_eligible` 只表示该 valid base 可以进入 JudgmentPairGenerator。是否在最大采样次数内成功生成 invalid pair，必须由 pair-generation metadata 中独立的 `judgment_pair_generated` 记录。

建议 rejection enum：

```text
barrier_outside_physics_roi
ball_start_outside_physics_roi
ball_collision_center_outside_physics_roi
ball_end_outside_physics_roi

context_collision
collision_too_early
collision_too_late

short_face_contact
corner_contact
ambiguous_contact_feature
endpoint_margin_violation
impact_angle_too_small

second_collision
multiple_contact

negative_ray_enters_safety_region
ray_hit_beyond_video
negative_not_strictly_safe

numerical_boundary_ambiguous
```

不要只返回 True / False；必须保留 rejection statistics。

---

# 38. `TaskLabels`

## State

```text
p_context_xy
velocity_xy
speed_px_per_s
speed_cells_per_s
velocity_angle_rad

barrier_axis_angle_rad
barrier_center_xy

relative_geometry
```

## Contact

```text
contact_binary
```

## Dynamics

```text
ttc_from_context_s

surface_contact_point_xy
ball_center_at_contact_xy

post_velocity_xy
post_speed_px_per_s
post_speed_cells_per_s
post_velocity_angle_rad
```

## Judgment

```text
validity_binary

angular_violation_deg
angular_violation_rad
normalized_violation_severity

violation_family = "reflection_direction"
violation_sign

latent_scene_id
judgment_pair_id
trajectory_variant_id
paired_trajectory_variant_id
```

---

# 39. `JudgmentVariantMetadata`

Pair-level metadata 先保存：

```text
judgment_pair_id
latent_scene_id
judgment_pair_generated
valid_trajectory_variant_id
invalid_trajectory_variant_id
judgment_seed
violation_sampling_attempt_count
```

Invalid variant 额外保存：

```text
delta_deg
delta_rad
sign

bad_post_velocity_angle_rad
bad_post_velocity_xy
bad_outgoing_angle_to_barrier_deg

alternate_barrier_rotation_deg
alternate_barrier_axis_angle_rad
alternate_barrier_vertices_xy
alternate_barrier_feasible

invalid_final_center_xy
invalid_trajectory_inside_roi
invalid_second_collision
```

---

# 40. `RelativeGeometry`

建议结构：

```text
barrier_center_minus_ball_xy
ball_u_in_barrier_frame
ball_d_in_barrier_frame
signed_center_clearance_to_nearest_long_face_contact_line_px
endpoint_axial_margin_px
center_ray_min_distance_to_rectangle_px
ball_surface_ray_min_clearance_to_rectangle_px
candidate_collision_time_s
actual_first_contact_feature
```

这些默认只用于 metadata / oracle / diagnostics。

---

# 41. `RenderSpec` / `AppearanceSpec`

Renderer 的视觉 nuisance 必须被显式结构化保存，而不是只存在于生成代码的随机状态中。

建议区分：

- `appearance_spec_id`：一套完整静态外观参数，可被多个 matched trajectory variant 复用；
- `render_variant_id`：某个具体 trajectory 使用某个 appearance spec 后得到的实际视频实例。

## 41.1 Canonical fields

至少保存：

```text
appearance_spec_id
render_seed
asset_bank_version
renderer_version

render_regime                 # canonical / diverse
render_family                 # canonical_neutral / billiards / air_hockey / tabletop

surface_style_id
surface_base_rgb
surface_texture_id
surface_texture_seed
surface_texture_strength

table_rail_style_id
outside_background_style_id

ball_color_id
ball_base_rgb
ball_brightness_gain
ball_saturation_gain
ball_hue_jitter_deg

barrier_material_id
barrier_base_rgb
barrier_brightness_gain
barrier_texture_strength
bolt_style_id
bolt_count

global_brightness_gain
global_gamma
global_saturation_gain

marking_style_id              # null unless applicable

support_inside_barrier_footprint
motion_blur
directional_light
cast_shadow
```

## 41.2 v1 强制不变量

```text
support_inside_barrier_footprint = true
motion_blur = false
directional_light = false
cast_shadow = false
```

Canonical 额外固定：

```text
render_regime = canonical
render_family = canonical_neutral
all style IDs fixed
all jitter gains = 1.0
all hue jitter = 0
```

## 41.3 Diverse sampling

Diverse 的 style ID 从对应 family 的有限 AssetBank 中离散均匀采样；连续 jitter 只在本文档允许的窄范围内采样。

所有 appearance random variable 必须由 `render_seed` / `appearance_spec_id` deterministic replay。

## 41.4 Matched render 规则

Judgment good/bad pair：

```text
same appearance_spec_id
same render_family
same surface_style_id
same ball_color_id
same barrier_material_id
same global tone
```

只允许 trajectory variant 不同。

第二阶段 matched source/base pair 若实验目标不是研究视觉 domain shift，也应尽量使用相同 `appearance_spec_id`。

## 41.5 Renderer 输出

每个 render 至少记录：

```text
render_variant_id
appearance_spec_id
trajectory_variant_id
video_path
frame_count
fps
width_px
height_px
codec
```

Renderer 不负责 task label，也不允许在 render 后通过 pixel editing 制造 invalid。

---

# 42. Dataset ID、Dataset Index、Split 与 TaskManifestBuilder

## 42.1 Canonical ID hierarchy

推荐：

```text
latent_scene_id
    ├── trajectory_variant_id(s)
    │     ├── appearance_spec_id(s)
    │     │      └── render_variant_id(s)
    │     └── ...
    └── judgment_pair_id
          ├── valid_trajectory_variant_id   -> trajectory reference
          └── invalid_trajectory_variant_id -> trajectory reference
```

Canonical schema 不再使用含义重叠的 `scene_id`、`base_scene_id`、`paired_scene_id` 或 `render_id` 别名。

建议 reference encoding：

```text
latent_scene_id = "ls-{scene_seed:016x}-{mode_code:02x}-{proposal_index:016x}"

physical trajectory_variant_id = "{latent_scene_id}:physical"
invalid trajectory_variant_id  = "{latent_scene_id}:invalid:{judgment_seed:016x}"
judgment_pair_id               = "{latent_scene_id}:pair:{judgment_seed:016x}"

appearance_spec_id             = "{latent_scene_id}:appearance:{render_seed:016x}"
render_variant_id              = "{trajectory_variant_id}:render:{render_seed:016x}"
```

同一个 Judgment good/bad pair 可以具有不同 `render_variant_id`，但必须引用同一个 `appearance_spec_id`。

第二阶段另有：

```text
source_scene_id
```

## 42.2 Split integrity

普通 train/val/test split 的单位：

$$
\boxed{\text{latent base scene}}.
$$

`split` 首先赋给 `latent_scene_id`，然后所有：

- trajectory variants；
- semantic skins；
- texture variants；
- Judgment good/bad pair；
-普通 counterfactual variants；

继承同一个 split。

它们不得跨 split。

same-latent paired-render invariance 是显式例外实验，但不能冒充 held-out generalization。

## 42.3 Dataset Index：完整数据集的事实来源

Renderer 完成后，磁盘上的“完整数据集”不应等价于某一个 task 的训练文件，而应由：

> **视频文件 + canonical metadata tables / Dataset Index**

组成。

推荐目录：

```text
dataset_root/
├── videos/
│   ├── canonical/
│   ├── billiards/
│   ├── air_hockey/
│   └── tabletop/
│
├── index/
│   ├── latent_scenes.parquet
│   ├── trajectories.parquet
│   ├── contact_classification.parquet
│   ├── judgment_pairs.parquet
│   ├── appearances.parquet
│   ├── renders.parquet
│   └── splits.parquet
│
└── manifests/
```

Canonical storage 推荐使用 **Parquet**：

- typed schema；
- 数组/数值字段更稳定；
- 读取高效；
- 便于后续 DataFrame analysis。

可以额外导出 JSONL 作为 human-readable / debugging 版本，但 JSONL 不作为唯一 canonical source。

## 42.4 `TaskManifestBuilder` 的职责

`TaskManifestBuilder` 从 Dataset Index 中生成轻量 task-level manifests。

它负责：

1. 根据 task eligibility 过滤 scene；
2. 继承 latent-scene split；
3. 选择 render regime / family；
4. 按实验需求做 label / family / style balancing；
5. 投影出该任务实际需要的 target fields；
6. 指定 observation / target frame semantics；
7. 输出 Parquet manifest；
8. 可选输出 JSONL mirror。

它**绝不**：

- 重算 collision；
- 重算 TTC；
- 从视频像素估 label；
- 修改 validity；
- 重新 render；
- 把 rejected scene 重新解释成 negative。

## 42.5 Common manifest fields

所有 task manifest 至少包含：

```text
sample_id
latent_scene_id
trajectory_variant_id
render_variant_id
appearance_spec_id
video_path
split
render_regime
render_family

observation_start_frame
observation_end_frame
context_frame_indices
future_frame_indices
```

其中 frame range 是 benchmark 语义定义，不代表模型最终一定直接读取相同数量的 RGB frame。

## 42.6 State manifest

State sample 默认引用 Context：

```text
observation_start_frame = 0
observation_end_frame   = 7
```

额外 target：

```text
p_context_xy
velocity_xy
speed_px_per_s
speed_cells_per_s
velocity_angle_rad
barrier_axis_angle_rad
barrier_center_xy
```

主实验可以只从 manifest 中选择核心 State fields，不需要重新生成 manifest 文件结构。

## 42.7 Contact manifest

只包含：

```text
status ∈ {positive, negative}
```

Rejected scene 永远不进入 Contact manifest。

输入语义：

```text
Context frames 0–7
```

Target：

```text
contact_binary
```

主训练 manifest 目标：

$$
P(y=1)\approx P(y=0)\approx0.5.
$$

## 42.8 Collision Dynamics manifest

只从：

```text
status = positive
accepted_for_dynamics = true
```

生成。

输入语义：

```text
Context frames 0–7
```

Target fields：

```text
ttc_from_context_s
surface_contact_point_xy
post_velocity_xy
post_speed_px_per_s
post_speed_cells_per_s
post_velocity_angle_rad
```

## 42.9 Judgment manifest

输入语义：

```text
full video frames 0–23
```

每个 matched pair 生成：

- 1 valid row；
- 1 invalid row。

字段至少：

```text
judgment_pair_id
validity_binary
angular_violation_deg
angular_violation_rad
normalized_violation_severity
violation_sign
```

good / bad 两行必须引用同一 `appearance_spec_id`。

主 Judgment manifest：

$$
\boxed{valid:invalid=1:1}.
$$

## 42.10 Diverse pooled manifest

Broad pooled-Diverse 主实验中，目标 family balance：

$$
\boxed{
\text{billiards}:
\text{air\_hockey}:
\text{tabletop}
\approx1:1:1
}.
$$

同时检查：

- ball color ID；
- surface style ID；
- barrier material ID；
- outside background ID；

在 physical labels 间没有明显相关性。

`TaskManifestBuilder` 可以通过 stratified selection 对这些 render nuisance 做近似平衡，而不修改底层视频或 physics metadata。

## 42.11 Paired-render invariance manifest

若研究同一 latent physics 在不同 semantic skin 中的 representation invariance，可生成显式 paired manifest：

```text
same latent_scene_id
same trajectory_variant_id
multiple render_variant_id
render_family ∈ {billiards, air_hockey, tabletop}
```

该 manifest 属于：

$$
\boxed{\text{controlled invariance analysis}}
$$

而不是 held-out-domain generalization。

## 42.12 Task manifest 应可重复生成，而不重新 render

这是引入 TaskManifestBuilder 的核心工程价值。

例如以后决定：

- speed probe 只用某个 speed range；
- Judgment 只分析 $\Delta\theta>20^\circ$；
- Tabletop 完全 held out；
- Canonical 只用于 mechanistic subset；

只需要重新构建 manifest，不需要重新模拟或渲染视频。

因此：

> **底层 dataset construction 与上层 experiment definition 必须彻底解耦。**

## 42.13 Versioning 与可重放性

保存：

```text
dataset_version
config_hash
simulator_version
renderer_version
asset_bank_version
scene_seed
proposal_index
proposal_mode
render_seed
judgment_seed
manifest_version
manifest_config_hash
```

只要 config + code version + seed 相同，应完整 replay。

改变会影响 latent distribution / qualification / violation distribution 的规则，必须新建 dataset version。

只改变视觉资产或 RenderSpec sampling，应更新 renderer / asset-bank version。

只改变 task selection / balancing，应更新 manifest version，而不必重新生成 physics dataset。

---

# 43. 正式渲染前的纯 Latent Pilot

先生成 10k–100k latent proposals，不渲染，统计：

## Sampling efficiency

- positive acceptance；
- negative acceptance；
- reject reason histogram。

## Spatial

- $p_c$ heatmap；
- barrier center heatmap；
- collision point heatmap。

## Angular

- $\theta_v$；
- $\phi$；
- impact angle；
- outgoing angle。

## Speed

- proposal speed；
- positive accepted speed；
- negative accepted speed。

## Judgment

- accepted $\delta$；
- violation sign；
- bad outgoing angle；
- alternate-barrier feasibility rate。

## Cross-correlation

重点：

- speed × label；
- direction × label；
- barrier orientation × label；
- collision point × label。

---

# 44. 当前仍保留 Pilot 权限的参数

核心几何与时间规格已经冻结。

主要仍允许在 pilot 后修改：

- speed range；
- 各 family asset preset 的具体 RGB 微调；
- procedural texture 的极弱 amplitude；
- Diverse 全局 brightness / gamma jitter 的窄范围；
- asset bank 数量是否在默认 4/2/5/3/3 基础上扩充。

但以下 renderer 原则已经冻结：

- Canonical appearance 固定；
- Diverse 使用 discrete preset + small jitter；
- ball 为纯色、无方向纹理；
- barrier 通过 footprint 内中央主体、端片、十字螺钉与 bevel 暗示固定；
- support 不得突出 barrier footprint；
- 不使用 directional cast shadow；
- 不使用生成式 AI 图片作为核心 asset source；
- 所有静态 texture 在视频内固定；
- Judgment good/bad 必须共享同一 appearance spec。

以下不再视为 pilot 未定项：

- 448×448 frame；
- 15×11 base playing surface（Air-Hockey outer rail 可扩展至 436×324 px）；
- 14×10 Physics ROI；
- 35 px ball；
- 5×1 cell barrier；
- 24 fps / 24 frames；
- 8 Context + 16 Future；
- collision frames 12–19；
- $d_1=0.625$ cell；
- $d_2=1.25$ cells；
- $\theta_0=10^\circ$；
- $\delta\in[5^\circ,90^\circ]$；
- normalized severity $=\delta/90^\circ$。

# 45. v1 明确不做 / Deferred

## Physics

- multi-ball；
- multi-collision long rollout；
- restitution variation；
- friction parameter estimation；
- spin / rolling dynamics；
- table-edge bounce；
- pocket interaction；
- 3D rigid-body dynamics。

## Judgment

- disappearance；
- recoloring；
- arbitrary penetration；
- heterogeneous violation families；
- “统一 physical validity axis”作为主问题。

## Causal Stage

- 第一版不主攻 TTC intervention；
- 第一版不主攻 contact-point intervention；
- 第一版不主攻 Contact Prediction intervention；
- 不默认 low-level edit 等价于 high-level `do`。

## Rendering

- 不使用纯白 PPT-like diagram 作为唯一主 domain；
- 不使用需要真实 3D rolling 才合理的复杂 billiard texture 作为核心 skin；
- 不使用生成式 AI background 作为 v1 核心资产；
- 不使用 directional cast shadow；
- 不使用 strong perspective / floor-grid texture；
- 不做强 domain randomization 或 photorealistic lighting。

---

# 46. Optional Future Extensions

如果主实验完成且有足够时间：

- second Judgment family；
- cross-violation transfer；
- pocket / goal prediction；
- stronger render OOD；
- external benchmark sanity check；
- spatial globalization analysis；
- prediction → judgment intervention；
- more detailed circuit-level scene matching。

外部 benchmark 不作为主实验必需部分。

如果 external validation 与第二阶段 causal analysis 二选一，当前优先：

$$
\boxed{\text{causal mechanistic experiment}}
$$

---

# 47. v1 最终实验地图

## Part I：Representation / Functional Accessibility

### State

核心：

$$
\boxed{v_x,v_y}
$$

$$
\boxed{s}
$$

$$
\boxed{\theta_v}
$$

$$
\boxed{\phi}
$$

辅助：

$$
p_c,\quad b,\quad \text{relative geometry}.
$$

### Prediction

Contact：

$$
\boxed{\text{clean contact positive / strict safe negative}}
$$

Dynamics：

$$
\tau,
\quad
q_{contact},
\quad
v_x^+,v_y^+,
\quad
s^+,
\quad
\boxed{\theta_{v^+}}.
$$

其中：

$$
\boxed{\theta_{v^+}}
$$

为核心。

### Judgment

$$
\boxed{\text{valid / invalid}}
$$

$$
\boxed{\Delta\theta}
$$

---

## Part II：Causal Mechanistic Experiments

### A. State → Prediction

Intervene：

$$
\boxed{\theta_{v^-}}
$$

或：

$$
\boxed{\phi}
$$

Observe：

$$
\boxed{\theta_{v^+}}
$$

### B. State → Judgment

Intervene：

$$
\boxed{\theta_{v^-}}
$$

或：

$$
\boxed{\phi}
$$

Observe：

$$
\boxed{P(\text{invalid})}
$$

以及：

$$
\boxed{\widehat{\Delta\theta}}
$$

### C. Optional：Prediction → Judgment

仅当 Part I 的 emergence pattern 支持该候选链时再做。

---

# 48. 给 Simulator / Dataset Generator 的最终 Checklist

## Proposal / RNG

- [ ] default `proposal_mode = independent_uniform`；
- [ ] speed、velocity angle、barrier axis angle、$p_c$ 按各自合法域均匀采样；
- [ ] barrier center 在给定 $\phi$ 后的 feasible rectangle 内条件均匀采样；
- [ ] accepted empirical distribution 与 proposal prior 分开统计；
- [ ] `PCG64 + SeedSequence` reference construction；
- [ ] serial / parallel replay identity。

## Geometry

- [ ] continuous world coordinates；
- [ ] frame / table / ROI bounds；
- [ ] ball-center eroded ROI；
- [ ] barrier 4 vertices；
- [ ] exact disk-vs-rectangle first contact；
- [ ] long / short / corner / ambiguous classification；
- [ ] $d_1=17.5$ px endpoint margin；
- [ ] $d_2=35$ px rounded safety region；
- [ ] infinite-ray safety intersection；
- [ ] strict equality-boundary rejection。

## Numerics

- [ ] all analytic geometry uses `float64`；
- [ ] spatial / time / angle epsilon 从 versioned config 读取；
- [ ] epsilon-neighborhood cases → `numerical_boundary_ambiguous`；
- [ ] near-frame event time 先 snap 再计算 frame index；
- [ ] epsilon 不放宽任何 scientific threshold。

## Time

- [ ] 24 fps；
- [ ] 24 frames；
- [ ] frame time $i/24$；
- [ ] Context 0–7；
- [ ] Future 8–23；
- [ ] $t_c=8/24$；
- [ ] collision frame = floor($24t$)；
- [ ] positive collision frame 12–19；
- [ ] $p_T=p(1.0\text{s})$ 作为未渲染 safety endpoint；
- [ ] exact-event velocity 使用 right-continuous post-collision value。

## Trajectory

- [ ] sample $S_c$；
- [ ] backward Context integration；
- [ ] forward Future integration；
- [ ] exact subframe collision time；
- [ ] elastic reflection $e=1$；
- [ ] no-contact: start/end ROI check；
- [ ] collision: start/contact/end ROI check；
- [ ] second-collision rejection。

## Contact

- [ ] explicit positive / negative / reject；
- [ ] never conflate reject and negative；
- [ ] positive first contact = long face；
- [ ] endpoint margin；
- [ ] impact angle >10°；
- [ ] collision frames 12–19；
- [ ] ray-hit beyond window = reject；
- [ ] short/corner = reject；
- [ ] safety-region near miss = reject。

## Judgment

- [ ] valid branch；
- [ ] continuous $\delta\sim U(5^\circ,90^\circ)$；
- [ ] ± sign；
- [ ] same speed；
- [ ] no penetration；
- [ ] bad outgoing angle >10°；
- [ ] invalid end-point ROI check；
- [ ] no second collision；
- [ ] alternate barrier rigid rotation by $\delta/2$ around collision ball center；
- [ ] alternate barrier 4 vertices inside ROI；
- [ ] raw $\Delta\theta$；
- [ ] normalized $\Delta\theta/90^\circ$；
- [ ] 1:1 matched good/bad；
- [ ] accepted severity/sign balancing。

## Metadata

- [ ] State labels；
- [ ] Contact labels；
- [ ] Dynamics labels；
- [ ] Judgment labels；
- [ ] relative geometry；
- [ ] acceptance report；
- [ ] rejection reasons；
- [ ] canonical ID namespace，无旧 alias；
- [ ] canonical angle wrapping；
- [ ] vector / time / frame field suffix 与 schema 一致；
- [ ] seeds / version hashes；
- [ ] complete replay possible。

## Renderer / Visual Asset Bank

- [ ] 448×448 output；
- [ ] 15×11 base playing surface；Air-Hockey outer rail = 436×324 px；
- [ ] 14×10 Physics ROI only exists in latent geometry, not drawn as an artificial box；
- [ ] Canonical = fixed neutral puck-table appearance；
- [ ] Diverse = billiards / air_hockey / tabletop；
- [ ] diverse style sampling = discrete preset + small continuous jitter；
- [ ] ball = solid-color, axisymmetric, no orientation texture；
- [ ] ball palette avoids low contrast with family surface；
- [ ] barrier silhouette exactly matches rectangle footprint；
- [ ] barrier fixed cue = 105 px central body + two 17.5 px end plates + 4 symmetric cross screws；
- [ ] support entirely inside barrier footprint；
- [ ] no motion blur；
- [ ] no directional light / cast shadow；
- [ ] no per-frame texture flicker；
- [ ] outside-table background low-texture / low-saturation；
- [ ] procedural assets only for v1 core；
- [ ] all appearance parameters serialized in `AppearanceSpec`；
- [ ] semantic skin independent of physics validity；
- [ ] Judgment good/bad share same `appearance_spec_id`；
- [ ] Judgment invalid created from latent trajectory and fully rerendered, never pixel-edited。

## Dataset Index / TaskManifestBuilder

- [ ] latent-scene split assigned before task manifests；
- [ ] all render / judgment variants inherit latent-scene split；
- [ ] canonical index tables stored in Parquet；
- [ ] task manifests reference video paths, do not duplicate videos by default；
- [ ] State manifest uses Context semantics；
- [ ] Contact manifest contains only positive / negative, never reject；
- [ ] Dynamics manifest contains only accepted positives；
- [ ] Judgment manifest uses full video and matched 1:1 valid/invalid pairs；
- [ ] pooled Diverse family ratio approximately 1:1:1；
- [ ] style / color / material IDs checked for label correlation；
- [ ] manifest rebuild does not rerun simulator or renderer；
- [ ] manifest_version + manifest_config_hash saved。

## Qualification before foundation-model experiments

- [ ] pure-latent pilot；
- [ ] acceptance vs speed / direction；
- [ ] positive/negative marginal checks；
- [ ] Judgment valid/invalid marginal checks；
- [ ] full-GT oracle；
- [ ] first/last/random/pre/post Judgment controls；
- [ ] codec/render artifact inspection。

# 49. 一句话总结

v1 benchmark 不是一个“尽量像真实世界的小游戏”，而是一个围绕单一解析反射规律构造的、可被严格控制和因果干预的视觉物理实验平台：

$$
\boxed{
\text{clean pre-collision State}
\rightarrow
\text{geometric Contact / collision dynamics Prediction}
\rightarrow
\text{reflection consistency Judgment}
}
$$

第一部分研究：

> 这些物理变量在模型内部何时、以何种形式变得可访问。

第二部分研究：

> 模型是否真的使用其中的 State representation 去完成下游 Prediction 与 Judgment。

而整个 benchmark 设计的首要原则始终是：

> **宁可物理范围窄，也不要引入会破坏 mechanistic interpretation 的模糊性、不可辨识参数、边缘碰撞、时间歧义或视觉 shortcut。**
