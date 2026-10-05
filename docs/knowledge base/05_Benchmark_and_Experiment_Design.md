---
title: Benchmark and Experiment Design Specification
status: Current
updated: 2026-09-23
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
> 它的地位是本项目科学目标落到具体实验实现时的**正式规格说明书（specification）**。后续 simulator、renderer、task generator、dataset builder、counterfactual generator，以及与场景直接相关的实验操作，都应以本文档为准。
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

---

# 2. Visual Table 与 Physics ROI

## 2.1 Visual table

Visual table 固定为：

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

实际 collision event 的 `contact_normal` 根据接触的具体 long face 派生，可以是 $\pm n_c$。

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

## 6.2 Speed 必须随机

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

## 6.3 Ball-center legal region

由于整个 ball disk 必须在 Physics ROI 内，ball center 合法区域为 ROI erosion by radius $r$：

$$
\boxed{x\in[-178.5,178.5],\qquad y\in[-122.5,122.5].}
$$

尺寸：

$$
357\times245\ \text{px}.
$$

## 6.4 利用凸性做 trajectory boundary check

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
long_face
short_face
corner
ambiguous
```

边界无法稳定分类时一律 `ambiguous -> reject`。

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
\boxed{\text{ray-hit / safe no-hit}}.
$$

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

## 10.1 Time-to-collision

从 Context 结束时刻计：

$$
\boxed{
\tau=t_{collision}-t_c
}
$$

不是从视频 \(t=0\) 计。

---

## 10.2 Collision point

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

## 10.3 Post-collision velocity

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

## 10.4 Post-collision speed 的地位

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

## 10.5 Future free-flight position

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

## 11.1 v1 不加入的 violation

不加入：

- disappearance；
- recoloring；
- spontaneous acceleration；
- wrong restitution / speed magnitude；
- object permanence；
- arbitrary penetration；
- heterogeneous IntPhys-style violation families。

原因：第一版关注同一反射 law 内的 State → Prediction / Judgment 机制，而不是寻找 universal invalidity direction。

## 11.2 Valid trajectory

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

## 11.3 Invalid trajectory 的唯一正式 operator

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

## 11.4 Invalid outgoing 的独立几何检查

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

## 11.5 Alternate-barrier feasibility check

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

## 11.6 Good / Bad prefix 完全一致

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

## 12.1 Binary validity

$$
\boxed{y_{valid}\in\{0,1\}}.
$$

## 12.2 Canonical continuous severity

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

## 12.3 Normalized severity

固定：

$$
\boxed{s_{violation}=\frac{\Delta\theta}{90^\circ}}.
$$

因此：

- valid = 0；
- invalid ≈ $[0.0556,1]$。

不要定义成 $(\delta-5^\circ)/85^\circ$，否则最轻 invalid 会与 valid 共用 0。

## 12.4 Continuous severity，不用离散 grid

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

## 12.5 Acceptance 会改变最终 severity distribution

alternate-barrier ROI、bad outgoing angle、post trajectory 等 rejection 会让 accepted $P(\delta)$ 偏离 uniform。

因此正式生成后必须统计 accepted severity histogram；若失衡，可对连续 $\delta$ 做 bin-based quota / resampling，但 bin 内仍连续采样。

## 12.6 Violation sign balancing

若 $+\delta$ 与 $-\delta$ 都合法，等概率选 sign。

若只有一侧合法，可保留，但最终必须统计：

$$
P(\sigma|invalid).
$$

必要时 balancing，避免“向某一侧偏就是 invalid”的 shortcut。

## 12.7 Judgment class balance

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

# 14.1 State targets

State 全部锚定在：

$$
t=t_c^-.
$$

## A. Pre-collision velocity：核心

### Cartesian parameterization

$$
\boxed{(v_x,v_y)}
$$

### Polar parameterization

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

### Direction metric

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

## B. Barrier direction：核心

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

### Physics normal 仍由 simulator 内部使用

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

## C. Barrier direction 的 parameterization robustness

### 主语义形式：raw axis angle

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

### Topology-correct auxiliary encoding

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

### 不把 \(\cos\phi\) 单独作为主 target

虽然在 \([0,\pi]\) 上 \(\cos\phi\) 一一对应，但它严重扭曲无向角度几何：

- \(1^\circ\) 与 \(179^\circ\) 对 barrier axis 来说只差 \(2^\circ\)；
- 但 cosine target 接近 \(+1\) 与 \(-1\)。

因此不作为首选形式。

---

## D. Position / geometry：辅助 State

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

## E. Relative Geometry Metadata

为 GT oracle、debugging、shortcut diagnostics 保存：

### Barrier center relative to ball

$$
\Delta b=b-p_c.
$$

### Ball in barrier-local frame

$$
u_c=(p_c-b)\cdot t,
$$

$$
d_c=(p_c-b)\cdot n_c.
$$

还建议保存：

- nearest long-face normal clearance；
- nearest endpoint axial clearance；
- ray minimum distance to barrier；
- candidate collision time（若存在）；
- actual first-contact feature type。

这些默认是：

> **metadata / oracle / diagnostics only**

而不是自动加入主 State probe matrix。

---

# 14.2 Prediction targets

## Contact Prediction

核心 binary：

$$
\boxed{\text{ray-hit / no-hit}}
$$

注意它不再定义为简单 “within observed horizon”。

---

## Collision Dynamics

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

# 14.3 Judgment targets

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

## 14.1 主 broad experiment：Pooled Diverse Training

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

## 14.2 Canonical 的角色

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

## 14.3 Cross-domain generalization：Secondary analysis

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

## 14.4 结果解释原则

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

## 14.5 Paired render invariance 与真正 generalization 必须分开

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

## 15.1 Split 按 latent scene，而不是视频文件

同一 latent scene 的：

- 不同 render family；
- 不同 texture；
- good / bad Judgment pair；
- 相关 counterfactual variant；

默认必须被视为同一个 scene family，在普通 train/val/test 中不得泄漏。

---

## 15.2 Generalization experiment 例外必须显式定义

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

## 18.1 Intervention

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

## 18.2 Primary downstream endpoint

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

## 18.3 第一版不把 TTC / contact point 作为 causal endpoint

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

## 18.4 Contact Prediction 也不纳入第一批 causal intervention

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

## 20.1 Base case

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

## 20.2 只改内部 pre-state expectation，不改 observed future

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

## 20.3 Barrier direction intervention

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

## 20.4 这个实验真正回答什么

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

## 22.1 Counterfactual label 不需要现在预渲染

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

## 22.2 但 real-source interchange 最终需要 source input

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

## 22.3 Velocity source pair

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

## 22.4 Barrier source pair

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

# 26. Canonical 与 Diverse Rendering

## 25.1 Canonical

Canonical 不是纯白数学示意图。

应是：

- 简洁；
- 自然；
- 明确俯视；
- 无 clutter；
- fixed camera；
- fixed lighting；
- fixed puck style；
- fixed barrier style；
- fixed surface；
- **no motion blur**。

其目的是：

$$
\boxed{\text{低 nuisance + natural visual semantics}}
$$

供第二阶段 mechanistic experiment 使用。

---

## 25.2 Diverse

Diverse 与 Canonical 共享同一 physics distribution，但改变视觉 nuisance：

- semantic family；
- surface material；
- object color / simple skin；
- barrier material；
- mild brightness/shadow；
- 少量合理外观变化。

当前避免：

- 太剧烈 camera variation；
- 大范围视角变化；
- 强 clutter；
- 会改变物理语义的物体替换。

---

# 27. Semantic Render Families

## 26.1 Billiards-like overhead table

特征：

- 完整桌框可见；
- green / blue / red felt；
- pockets 可作为 top-down billiards semantic cue；
- moving object 使用 plain solid ball / puck-like disk；
- 内部 barrier 是明显固定的 rail。

不要使用：

- cue stick；
- triangle rack；

作为 fixed wall，因为现实中这些对象可移动，会与 simulator prior 冲突。

若画面有 pockets：

> 主 v1 trajectory 必须与 pockets 保持安全距离。

Pocket interaction 不是 v1 physics。

---

## 26.2 Air-hockey-like table

可能是物理语义最干净的一类：

- overhead；
- horizontal plane；
- low-friction semantic；
- puck；
- plastic rail/barrier；
- rink/table markings。

它与：

$$
\text{constant-speed planar puck dynamics}
$$

高度一致。

---

## 26.3 Tabletop / Lab surface

要求：

- 完整桌面边缘可见；
- 桌外保留 background / floor；
- wood / gray lab table / rubber mat；
- barrier 可以是固定 acrylic / metal / wooden rail。

必须避免整张图只是：

> “一块 texture 填满 frame”

导致无法知道是 horizontal tabletop 还是 vertical plane。

---

# 28. Object Texture 与 Rolling

v1 moving object 更适合：

- puck；
- plain disk；
- solid-color axisymmetric ball；
- radial shading。

不建议直接用：

- numbered billiard ball；
- striped billiard ball；

然后只做 2D sprite translation。

原因：

- 真实球面滚动会改变纹理；
- 简单 image-plane rotation 也不等于真实 3D rolling；
- 会制造与 simulator 不一致的视觉 motion cue。

第一版优先保持 axisymmetric appearance。

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

## 29.1 Full-GT oracle

使用 simulator 完整 state 与解析物理规则，任务必须接近 ceiling。

若 full-GT oracle 都不能正确完成：

> **benchmark invalid，必须先修。**

---

## 29.2 Prediction target qualification

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

## 29.3 Label / nuisance marginal checks

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

## 29.4 Judgment shortcut baselines

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

## 29.5 Temporal controls

按 task 选择：

- frame shuffle；
- time reversal；
- single-frame baseline。

不应机械地对所有 State target 都使用。

---

## 29.6 Render / codec artifact check

必须人工和程序检查：

- valid/invalid 不因编码伪影区分；
- collision frame 不发生独特 compression artifact；
- invalid video 没有 discontinuity / pixel hack；
- good/bad 只在预期的 latent trajectory 处不同。

所有 Judgment 视频都必须从 latent trajectory **重新渲染**，不能通过像素级剪贴/扭曲构造。

---

# 31. 一票否决 Failure Modes 与“只是结果”的现象

真正的一票否决应针对：

$$
\boxed{\text{benchmark validity}}
$$

而不是“模型没有按我们的预期泛化”。

---

## 30.1 必须修复，否则不能进入主实验

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
- support 几何因 render family 改变 latent acceptance。

---

## 30.2 不是 failure，而是研究结果

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

## 30.3 Practical go/no-go

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

# 32. Simulator / Dataset 代码职责

正式推荐流程：

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
Matched Good / Bad Render
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

violation_delta_min_deg: 5
violation_delta_max_deg: 90
max_violation_sampling_attempts: 128

restitution: 1.0
friction: 0.0
motion_blur: false
```

其中 speed range 是当前默认 pilot，必须保留 config 能力。

---

# 34. `SceneSpec`

至少：

```text
scene_id
seed
split

p_context_xy
speed_px_per_s
speed_cells_per_s
velocity_angle_rad
velocity_xy

barrier_center_xy
barrier_axis_angle_rad
barrier_length_px
barrier_width_px

ball_radius_px
```

---

# 35. `Trajectory` / `CollisionEvent`

Frame state：

```text
frame_times
ball_center_xy[frame]
velocity_xy[frame]
barrier_vertices
barrier_tangent
```

Event：

```text
first_contact_exists
first_contact_time
first_contact_frame
first_contact_feature

contact_face_id
contact_normal
ball_center_at_contact
surface_contact_point
contact_axis_coordinate
impact_angle_deg

pre_collision_velocity
post_collision_velocity
post_collision_angle
```

---

# 36. `ContactClassification`

必须显式输出：

```text
status ∈ {positive, negative, reject}
contact_label ∈ {1, 0, null}
```

建议额外保存：

```text
negative_safe_ray_no_intersection
true_barrier_collision_exists
collision_after_video_window
```

这样从数据结构上阻止 reject 与 negative 混淆。

---

# 37. `AcceptanceReport`

必须保存：

```text
accepted_for_contact
accepted_for_dynamics
accepted_for_judgment_base
status
rejection_reasons[]
```

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
post_speed
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

paired_scene_id
base_scene_id
```

---

# 39. `JudgmentVariantMetadata`

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
alternate_barrier_vertices
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
nearest_long_face_clearance
nearest_endpoint_axis_clearance
ray_min_distance_to_barrier
```

这些默认只用于 metadata / oracle / diagnostics。

---

# 41. `RenderSpec`

至少：

```text
render_id
render_seed
render_family

surface_style
surface_texture

object_style
object_color

barrier_style
barrier_material

lighting_variant
support_style
```

v1 必须：

```text
support_inside_barrier_footprint = true
motion_blur = false
```

Renderer 不负责物理，不允许在 render 后通过 pixel hack 制造 invalid。

---

# 42. Dataset ID、Split 与可重放性

推荐：

```text
latent_scene_id
    ├── render_variant_id
    └── judgment_pair_id
          ├── valid_variant
          └── invalid_variant
```

第二阶段另有：

```text
source_scene_id
```

普通 train/val/test split 的单位：

$$
\boxed{\text{latent base scene}}.
$$

同一 latent scene 的 semantic skins、texture variants、Judgment good/bad pair、普通 counterfactual variants 不得跨 split。

保存：

```text
dataset_version
config_hash
simulator_version
renderer_version
scene_seed
render_seed
judgment_seed
```

只要 config + code version + seed 相同，应完整 replay。

改变会影响 latent distribution / qualification / violation distribution 的规则，必须新建 dataset version。

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
- render texture asset 数量；
- lighting nuisance 幅度；
- 具体 semantic skin asset。

以下不再视为 pilot 未定项：

- 448×448 frame；
- 15×11 visual table；
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
- 不使用需要真实 3D rolling 才合理的复杂 billiard texture 作为核心 skin。

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
\boxed{\text{ray-hit / no-hit}}
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

## Time

- [ ] 24 fps；
- [ ] 24 frames；
- [ ] frame time $i/24$；
- [ ] Context 0–7；
- [ ] Future 8–23；
- [ ] $t_c=8/24$；
- [ ] collision frame = floor($24t$)；
- [ ] positive collision frame 12–19。

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
- [ ] seeds / version hashes；
- [ ] complete replay possible。

## Renderer

- [ ] 448×448 output；
- [ ] 15×11 visual table；
- [ ] 14×10 Physics ROI only exists in latent geometry, not drawn as an artificial box；
- [ ] support entirely inside barrier footprint；
- [ ] no canonical motion blur；
- [ ] semantic skin independent of physics validity；
- [ ] Judgment invalid created from latent trajectory and fully rerendered, never pixel-edited。

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
