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

# 1. v1 物理世界：Single Puck + Fixed Finite Barrier

## 1.1 Core system

v1 主系统固定为：

$$
\boxed{\text{single moving puck/ball/disk + one fixed finite-width barrier}}
$$

底层是二维平面中的刚体质点/圆盘运动。

第一版**不做 multi-ball**，原因是：

- 单球 + barrier 已经足够构造 State、Prediction、Judgment；
- 可以得到解析 ground truth；
- 可以构造 matched counterfactual；
- 可以做 State → Prediction / Judgment causal intervention；
- multi-ball 会引入额外 object binding；
- 多次碰撞和长时间 rollout 会增加敏感性与分支；
- 会模糊第一篇工作真正想研究的内部物理 computation。

---

## 1.2 Plane dynamics

在没有 barrier interaction 时：

$$
p(t+\Delta t)=p(t)+v\Delta t,
$$

$$
v(t+\Delta t)=v(t).
$$

第一版：

- 不考虑平面内重力；
- 不考虑摩擦；
- 不考虑空气阻力；
- 不考虑球自旋；
- 不考虑滚动阻力；
- 不考虑速度自然衰减。

视觉语义上，场景应明确是**水平平面俯拍**，避免模型把图像理解为竖直平面并期待 image-plane gravity。

---

## 1.3 完全弹性碰撞

第一版固定：

$$
\boxed{e=1}.
$$

固定 barrier 的理想完全弹性反射：

$$
v^+=v^- -2(v^-\cdot n)n,
$$

其中 \(n\) 是**实际接触 long face** 对应的单位法向量。

于是：

$$
\|v^+\|=\|v^-\|.
$$

### 为什么固定完全弹性

不在 v1 中随机 restitution coefficient，原因是：

- 从视觉中通常无法唯一知道材料对应的 \(e\)；
- 如果模型预测不同 \(e\)，很难判断是“物理推理错了”还是“材料参数不可辨识”；
- 本项目 v1 更关注**几何碰撞规律**，而不是材料参数估计；
- post-collision speed 因此不是核心 Prediction target，也不作为 Judgment violation 主线。

---

# 2. Barrier 的物理与视觉定义

## 2.1 Barrier 是 finite-width rectangular rail

物理几何上，barrier 应定义为具有：

- center \(b=(b_x,b_y)\)；
- length \(L\)；
- width \(w\)；
- long-axis orientation \(\phi\)；

的矩形固定障碍物。

其中：

$$
\boxed{\phi\in[0,\pi)}
$$

描述 barrier **长轴本身的无向方向**。

例如：

- \(0^\circ\)：水平；
- \(90^\circ\)：竖直；
- \(0^\circ\) 与 \(180^\circ\) 是同一方向。

---

## 2.2 只有 long faces 是 v1 合法碰撞面

虽然 renderer 中 barrier 有有限宽度，但 v1 benchmark 只允许：

$$
\boxed{\text{ball 与 barrier long face 的干净碰撞}}
$$

所有以下情况都应 reject：

- 与 short face 接触；
- 与四个矩形角发生 corner collision；
- 与视觉固定脚/支座发生几何重叠；
- 极近端点碰撞；
- 极近切线/擦边碰撞。

原因：

> v1 的目标是研究最干净的反射几何，而不是把矩形障碍物所有边缘 contact mode 都引入 task。

---

## 2.3 Barrier 的视觉固定结构

为了让模型理解 barrier 是**固定**的，renderer 可以加入：

- 螺丝；
- clamp；
- 支座；
- 固定脚；
- 与桌面连接结构。

优先方案：

> 这些视觉固定部件应尽量落在 barrier 本体 footprint 内，不额外扩大物理 collision geometry。

这样视觉语义可以表达“固定”，但不会引入新的碰撞对象、在 barrier 的矩形形状上加上更多不规则突出部，使轨迹生成更麻烦。

如果最终美术设计确实让固定脚伸出 barrier footprint，则必须：

- 为其定义 exclusion mask；
- 任何小球 swept disk 与这些 support zone 有交集的 scene 全部 reject。

---

## 2.4 为什么保留 finite barrier，而不改成无限长墙

第一部分 Contact Prediction 的价值很大程度上来自 finite geometry：

> 球的射线是否真正穿过 barrier 的有效长边范围？

如果 barrier 无限长，很多 contact task 会退化为更简单的 half-plane crossing。

因此 v1 保留 finite barrier。

第二阶段 causal intervention 也不为了“方便”切换到无限长 barrier；而是在 finite-barrier 数据中选取：

$$
\boxed{\text{intervention-safe subset}}
$$

确保 base/source/counterfactual 都是干净 long-face collision。

---

# 3. 时间结构：Context 与 Future

## 3.1 统一视频长度

所有视频统一：

- 总时长 \(T\)；
- frame rate \(fps\)；
- frame count；
- 分辨率；
- clip sampling 逻辑。

当前可以先以约 2 秒为 pilot 直觉，但：

> **代码中绝不能写死 2 秒。**

真正固定的是参数：

```text
T_total
T_context
T_future = T_total - T_context
fps
collision_pre_margin
collision_post_margin
```

---

## 3.2 当前默认：Future 约为 Context 的 2 倍

当前推荐：

$$
\boxed{T_{future}\approx 2T_{context}}.
$$

例如若总长约 2 秒，可先尝试：

$$
T_{context}\approx0.67s,
\qquad
T_{future}\approx1.33s.
$$

这是**当前默认设计**，精确值需要结合：

- V-JEPA 输入 frame 数；
- temporal tubelet；
- VLM 视频采样策略；
- fps；
- 速度范围；
- 接受率；

在 pilot 中最终确定。

### 为什么 Future 应明显长于 Context

Context 的核心作用只是提供足够视觉证据估计：

- 运动方向；
- 速度大小；
- 当前位置；
- barrier geometry。

而 Future 需要同时容纳：

1. collision 前运动；
2. collision event；
3. collision 后充分运动。

如果 Future 太短：

- 大量本来合格的 collision scene 会被 reject；
- collision time 分布会过度集中；
- post-collision evidence 不足；
- Judgment 变得脆弱。

---

## 3.3 Context 内禁止碰撞

所有主 benchmark scene 必须满足：

$$
\boxed{\text{Context 内没有任何 barrier collision}}
$$

即：

$$
t_{collision}>T_{context}.
$$

这保证：

- State probe 观察的是 clean pre-collision dynamics；
- Prediction 任务确实关于未观察 future；
- Judgment 的 pre/post 结构清晰。

---

## 3.4 Collision 必须位于 Future 的内部，而非边界

对于 collision-positive scene，不只要求：

$$
T_{context}<t_{collision}<T.
$$

而应要求：

$$
\boxed{
T_{context}+\Delta_{pre}
<
t_{collision}
<
T-\Delta_{post}
}
$$

其中 \(\Delta_{pre},\Delta_{post}\) 应以“至少若干帧”为主要定义，而非先锁定具体秒数。

理由：

- collision 太接近 Future 起点，会缺少 future 中的 pre-contact evidence；
- collision 太接近视频末尾，会缺少 post-collision trajectory；
- Judgment 尤其需要充分 post-collision 证据。

---

# 4. State 的统一时间锚点

为了让 State 与 Prediction 真正共享同一个 causal anchor，主 State 应统一定义在：

$$
\boxed{
t_c=T_{context}
}
$$

即 Context 结束、Future 开始的边界时刻。

定义：

$$
S_c=S(t_c^-).
$$

核心包括：

$$
p_c,\quad v_c,\quad \phi,\quad b,\quad L,\quad w,\quad r.
$$

后续文档中，尽量避免把 \(v_c\) 叫“视频初始速度”。

虽然在无碰撞、匀速 Context 中其数值与 \(t=0\) 速度一致，但为了 causal semantics，统一称为：

> **context-end / pre-collision velocity**

更准确。

---

# 5. 推荐 scene sampling：以 Context 边界状态为中心

## 5.1 先采 \(S_c\)，再前后模拟

当前推荐 generator 不以 \(t=0\) 为主锚点，而优先采样：

$$
S_c=
(p_c,v_c,\text{barrier geometry}).
$$

然后：

- 向后解析积分到 \(t=0\)，构造 Context；
- 向前解析积分到 \(T\)，构造 Future。

这样更自然，因为项目真正研究的 Prediction 输入状态就是：

$$
S_c.
$$

---

## 5.2 采样变量

建议至少采样：

- context-end ball position \(p_c=(x_c,y_c)\)；
- speed \(s\)；
- velocity direction \(\theta_v\)；
- barrier center \(b\)；
- barrier long-axis angle \(\phi\)；
- barrier length \(L\)（第一版可固定或小范围采样）；
- barrier width \(w\)（第一版可固定）；
- ball radius \(r\)（第一版建议固定）。

其中：

$$
v_c=s(\cos\theta_v,\sin\theta_v).
$$

---

## 5.3 Speed 必须随机，而不是固定

虽然完全弹性碰撞满足：

$$
s^+=s^-,
$$

速度大小仍应在：

$$
s\in[s_{min},s_{max}]
$$

中随机采样。

原因：

- 增加数据多样性；
- 避免模型只记固定 displacement/frame；
- 使 speed 本身成为可 probe 的 State 量；
- 降低固定速度 shortcut。

但 speed range 必须经过 balancing 检查，避免：

> 高速球天然更容易在有限 Future 内发生正类碰撞

导致 speed 成为 Contact label 的 shortcut。

---

# 6. Scene Acceptance / Rejection：统一清洁性规范

任何 trajectory 进入正式 benchmark 前，都必须经过 deterministic acceptance filter。

核心概念：

$$
\boxed{\text{clean single-interaction trajectory}}
$$

---

## 6.1 整段视频内球必须完全在可视区域

对所有 frame / 连续时刻：

- 小球圆盘必须完全在画面内；
- 不允许球中心在画面内但部分圆盘出界；
- 不允许 Future 末尾刚好出界。

桌面边缘在 v1 中主要是**视觉语义元素**，不是物理反弹对象。

因此：

> 数据生成必须保证球不会到达桌面/画面边缘，从而不需要引入 table-edge collision。

---

## 6.2 Barrier 必须完整可见

整个 finite barrier：

- 本体；
- 固定结构；

必须完全落在画面内。

不允许 barrier 被 crop。

---

## 6.3 Context 必须完全无碰撞

向后模拟的整个 Context 中：

- 不得接触 barrier；
- 不得擦边；
- 不得与支座 overlap。

---

## 6.4 Positive collision 必须是唯一 clean long-face collision

Collision Dynamics / Judgment 使用的 positive scene 必须满足：

- 只有一次有效 barrier collision；
- collision 在 long face；
- contact point 距端点有 margin；
- 不触碰 short face；
- 不触碰 corner；
- 不触碰 support；
- 碰撞角不接近切线；
- post-collision trajectory 保持在画面内。

---

## 6.5 排除 near-tangent collision

当：

$$
|v^-\cdot n|<\epsilon_v
$$

时，属于极近切向擦碰。

这类 scene 应 reject，因为：

- 数值上对微小扰动敏感；
- 像素离散后“到底算没算碰”可能模糊；
- 不适合干净的物理判断。

---

## 6.6 排除 borderline near-miss

对于 Contact negative，如果球轨迹只比 barrier 有效碰撞区域擦过极小距离，也应 reject。

即设置：

$$
\epsilon_{miss}>0
$$

作为 negative margin。

目的：

> 避免“数学上没碰，但视觉上几乎无法区分”的标签边界。

---

## 6.7 支座/固定脚 exclusion

若 renderer 的固定部件超出 barrier footprint，则任何：

$$
\text{swept ball disk}\cap\text{support zone}\neq\emptyset
$$

的 scene 全部 reject。

---

# 7. Dataset 的两个 Task Views

术语规范：

> `split` 只用于 `train / val / test`。

Contact / Dynamics / Judgment 不叫 split，而叫：

- **Task View**
- 或 **Task Pool**

推荐数据关系：

$$
\boxed{
D_{judgment}
\subset
D_{dynamics}
\subset
D_{contact}
}
$$

---

# 8. Task View A：Contact Prediction

## 8.1 任务定义必须从 “within horizon” 修正为几何相交

旧表述：

> `will collide within future horizon?`

容易混入一种模糊 negative：

> 几何上最终会碰，但当前视频太短所以没看到。

v1 正式定义应改为：

> **如果小球保持当前 context-end 速度沿射线无限前进，并忽略桌面边缘，它是否会与 barrier 的合法 long-face collision geometry 相交？**

也即：

$$
\boxed{\text{Will the current trajectory intersect the barrier?}}
$$

---

## 8.2 Positive

Positive scene 必须同时满足：

1. 几何上：
   $$
   \text{ray-hit}=1;
   $$
2. 实际碰撞属于合法 long-face collision；
3. 该碰撞发生在可观察 Future 的合法时间窗：
   $$
   t_c+\Delta_{pre}
   <
   t_{collision}
   <
   T-\Delta_{post}.
   $$

---

## 8.3 Negative

Negative 必须严格满足：

$$
\boxed{\text{ray-hit}=0}
$$

即：

> 在不考虑桌面边缘的情况下，小球沿当前速度方向射线无限延伸也永远不会发生我们定义的合法 barrier collision。

---

## 8.4 必须 reject 的“时间不够”轨迹

若：

$$
\text{ray-hit}=1
$$

但：

$$
t_{collision}>T
$$

或超出合法 collision window，则：

$$
\boxed{\text{reject}}
$$

而不是标为 negative。

这样 Contact Prediction 只研究：

> trajectory geometry / intersection relation

而不混入：

> “时间够不够”的额外判断。

---

## 8.5 几何判定必须考虑 ball radius 与 barrier width

`ray-hit` 不能只用 ball-center ray 与 barrier centerline 的线段相交。

真正需要判断的是：

> **沿射线移动的圆盘 swept volume 是否与 barrier 的允许 long-face contact region 相交。**

并继续排除：

- short edge；
- corner；
- support；
- near tangent；
- borderline miss。

---

# 9. Contact 正负比例与 sampling policy

## 9.1 不保留所谓“自然 collision prevalence”

如果完全独立均匀采样：

- \(p_c\)；
- \(\theta_v\)；
- barrier；

positive collision 可能非常少。

但本 benchmark 是 diagnostic benchmark，不是在估计现实世界：

> “随机扔一个球有多大概率撞墙”。

所谓“自然 prevalence”本身就由我们人为设定的 parameter prior 决定。

因此 Contact 主任务应主动控制 label balance。

当前建议：

$$
\boxed{P(y=1)\approx P(y=0)\approx0.5}
$$

或接近均衡。

---

## 9.2 推荐生成策略：大量 proposal → simulate → filter → stratified selection

因为 2D analytic simulator 很便宜，推荐：

```text
sample latent proposals
        ↓
analytic simulate
        ↓
cleanliness filters
        ↓
positive / negative reservoirs
        ↓
marginal checks + stratified matching
        ↓
selected latent scenes
        ↓
render
```

这比一开始就强行把所有 velocity 朝 barrier 采更干净。

---

## 9.3 Biased proposal 可以用于效率，但最终 benchmark 必须 controlled

如果 positive 太少，可以让 proposal distribution 稍微偏向：

- velocity 朝向 barrier；
- 合理距离；
- 合理 angle。

但这只是 proposal efficiency。

最终 benchmark 必须检查：

$$
P(s|y),
\quad
P(\theta_v|y),
\quad
P(\phi|y),
\quad
P(p_c|y),
\quad
P(d_{barrier}|y)
$$

是否严重分离。

必要时做 coarse-bin stratified matching。

原则：

> **proposal distribution 可以 biased；final benchmark distribution 必须 controlled。**

---

# 10. Task View B：Collision Dynamics

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

# 11. Task View C：Reflection Judgment

v1 Judgment 不研究“宇宙统一的 physical validity”。

第一版主动收窄为：

$$
\boxed{\text{Reflection Consistency Judgment}}
$$

目标是研究：

> 模型是否能根据 pre-collision state 与 barrier geometry，判断 observed post-collision direction 是否符合反射规律。

---

## 11.1 为什么只保留一个干净 violation family

第一版不把以下现象混进主 Judgment：

- disappearance；
- recoloring；
- spontaneous acceleration；
- object permanence；
- arbitrary penetration；
- heterogeneous IntPhys-style violations。

原因：

- 这些现象对应不同 physical / visual mechanisms；
- 会迫使项目转向“有没有统一 physical-invalidity direction”；
- 会削弱 analytic causal graph；
- 不利于 State → Prediction / Judgment 的机制分析。

因此：

> **Judgment 越干净越好。**

---

## 11.2 Valid trajectory

完全弹性反射：

$$
v_{valid}^+
=
v^--2(v^-\cdot n)n.
$$

速度大小保持不变。

---

## 11.3 Invalid trajectory：只破坏反射方向

Invalid case：

- pre-collision trajectory 不变；
- barrier geometry 不变；
- collision time / collision location尽量保持同一事件定义；
- post-collision speed 保持：
  $$
  \|v_{bad}^+\|=\|v^-\|;
  $$
- 只改变 outgoing direction。

核心错误是：

$$
\boxed{
\theta_{obs}^{+}\neq\theta_{physics}^{+}
}
$$

---

## 11.4 不允许通过“穿墙”制造 trivial invalid

Invalid outgoing ray 必须仍在 barrier 的合法离开半平面。

也就是说：

> 球反射方向可以错误，但不能直接继续穿过 barrier。

否则模型可以仅靠 solidity / penetration cue 做判断，而不需要理解 reflection law。

---

## 11.5 Preferred matched violation construction

优先方法：

1. 保持真实 visible barrier orientation \(\phi\)；
2. 采样另一个合法 orientation \(\phi'\)；
3. 用 \(\phi'\) 对同一 incoming velocity 计算一个**本身合法的** outgoing velocity：
   $$
   v_{bad}^+=R_{\phi'}(v^-);
   $$
4. 但视频里实际 barrier 仍是 \(\phi\)。

这样：

- incoming velocity 本身正常；
- outgoing velocity 本身来自合法反射分布；
- barrier orientation 本身正常；
- 真正错误的是：
  $$
  (v^-,\phi,v^+)
  $$
  三者之间的关系。

简单角度旋转：

$$
\theta_{bad}^+
=
\theta_{valid}^++\delta
$$

也可作为实现方式，但必须同时满足：

- speed unchanged；
- 不穿墙；
- 角度分布/marginal 不产生 shortcut；
- 误差 severity 可控。

---

## 11.6 Good / Bad pair 共享同一 prefix

Judgment pair 应尽量做到：

$$
I_{0:t_{collision}}^{good}
=
I_{0:t_{collision}}^{bad}.
$$

或者至少在碰撞前完全一致。

两条视频只在 post-collision future 分叉。

这样 Judgment 真正测试：

> observed transition 与物理 expectation 的一致性。

---

# 12. Judgment targets

v1 两个核心 Judgment target：

## 12.1 Binary validity

$$
\boxed{
y_{valid}\in\{0,1\}
}
$$

---

## 12.2 Continuous violation magnitude

最自然的物理量是：

$$
\boxed{
\Delta\theta
=
d_{2\pi}
(
\theta_{obs}^+,
\theta_{physics}^+
)
}
$$

其中：

$$
d_{2\pi}(a,b)
=
\min(|a-b|,2\pi-|a-b|).
$$

这比人为定义一个无物理含义的 scalar 更自然。

如果实验/可视化需要 \(0\sim1\) severity，可再定义：

$$
s_{violation}
=
\frac{\Delta\theta}{\Delta\theta_{max}}.
$$

但 raw angular discrepancy 应保留为 canonical GT。

---

## 12.3 Violation severity sampling

可以使用：

$$
\delta\in
\{5^\circ,15^\circ,30^\circ,60^\circ\}
$$

或连续采样。

具体 severity grid 暂不锁死，由 pilot 决定。

价值：

- 区分 subtle vs obvious violation；
- 画 sensitivity curve；
- 避免只有 binary ceiling/floor；
- 研究 Judgment information 的 layerwise emergence 是否随 severity 改变。

---

# 13. 第一部分实验：要 probe 的物理量

本文档只规定**物理 target 与 parameterization**，不规定具体 probe architecture。

---

# 13.1 State targets

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

# 13.2 Prediction targets

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

# 13.3 Judgment targets

Reflection Judgment：

1. binary valid / invalid；
2. continuous angular violation：
   $$
   \Delta\theta
   $$

或其 normalized severity。

---

# 14. Broad Probe Training 与 Scene Generalization

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

# 15. Train / Val / Test Split Integrity

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

# 16. 第二部分实验：Mechanistic Causal Microscope

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

# 17. 第二阶段优先干预的 State 变量

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

# 18. 第二阶段 Primary Causal Experiment A：State → Prediction

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

# 19. Low-level patch 不能预先被称为 high-level `do`

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

# 20. 第二阶段 Primary Causal Experiment B：State → Judgment

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

# 21. Prediction → Judgment：Optional

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

# 22. 第二阶段 Source/Base Pair 的生成

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

# 23. Intervention-safe Subset

第二阶段不能对任何任意 base scene 做任意方向修改。

应专门从 Canonical 数据中建立：

$$
\boxed{D_{mech-safe}}
$$

要求对 base/source/high-level counterfactual：

- 都保持球在画面内；
- 都是 clean long-face collision；
- contact point 远离 endpoint；
- 不触 corner / short face / support；
- 不 near-tangent；
- collision time 都在合法 Future window；
- 不引入额外 table-edge interaction。

这样 finite barrier 可以保留，不需要换成无限长墙。

---

# 24. 第二阶段的 manipulation check 与 causal outcome

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

# 25. Canonical 与 Diverse Rendering

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
- fixed surface。

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

# 26. Semantic Render Families

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

# 27. Object Texture 与 Rolling

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

# 28. 可选空间分析：Physical Information Globalization

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

# 29. Benchmark Qualification：进入 Foundation Model 前必须完成

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
- absolute position；
- distance-to-barrier；
- render family；
- object color；
- barrier material；
- texture；
- clip length。

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

# 30. 一票否决 Failure Modes 与“只是结果”的现象

真正的一票否决应针对：

$$
\boxed{\text{benchmark validity}}
$$

而不是“模型没有按我们的预期泛化”。

---

## 30.1 必须修复，否则不能进入主实验

- Full-GT oracle 做不好；
- Judgment first/last frame shortcut 接近满分；
- valid/invalid 有明显 renderer/codec artifact；
- Contact label 被颜色/scene family 等 nuisance 单变量高精度预测；
- 主 “nonlinear Prediction” target 被 GT-state linear model 近乎满分解决；
- ball/barrier 出画；
- context 中发生 collision；
- collision 经常位于 temporal boundary；
- 大量 corner / short-edge / support contact；
- negative 中混入 “其实会撞，只是视频时间不够”；
- good/bad 的速度或方向 marginal 严重不平衡。

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

# 31. Simulator / Renderer / Task Generator 的代码职责

推荐严格解耦：

```text
Physics / Scene Proposal
        ↓
Analytic Simulator
        ↓
Continuous Trajectory + Events
        ↓
Acceptance / Rejection
        ↓
Task Label Generator
        ↓
Render Specification
        ↓
Renderer
        ↓
Dataset Builder
```

第二阶段另加：

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

# 32. 推荐代码模块

Codex 实现时建议至少拆成以下职责。

## 32.1 `PhysicsConfig`

保存：

```text
T_total
T_context
fps
frame_size
physical_play_area
ball_radius
barrier_length
barrier_width
speed_min
speed_max
collision_pre_margin
collision_post_margin
endpoint_margin
tangent_epsilon
near_miss_margin
```

---

## 32.2 `SceneState / SceneSpec`

至少：

```text
scene_id
seed

p_context
speed
velocity_angle
velocity_xy

barrier_center
barrier_axis_angle
barrier_length
barrier_width

ball_radius
```

---

## 32.3 `Trajectory`

保存连续/离散状态：

```text
times
ball_center[t]
velocity[t]
barrier_geometry
```

事件：

```text
ray_hit
collision_exists
collision_time
collision_frame
collision_subframe_time

contact_face
contact_normal
ball_center_at_contact
surface_contact_point

pre_collision_velocity
post_collision_velocity
post_collision_angle
```

---

## 32.4 `AcceptanceReport`

不要只返回 True/False。

必须记录：

```text
accepted
rejection_reasons[]
```

可能原因：

```text
ball_out_of_frame
barrier_out_of_frame
context_collision
collision_outside_window
ray_hit_beyond_video
short_face_contact
corner_contact
support_contact
near_tangent
near_miss
endpoint_too_close
post_collision_out_of_frame
multiple_or_ambiguous_contact
```

这对之后诊断 sampling efficiency 极其重要。

---

## 32.5 `TaskLabels`

### State

```text
p_context
velocity_xy
speed
velocity_angle
barrier_axis_angle
barrier_center
relative_geometry
```

### Contact

```text
ray_hit_binary
```

### Dynamics

```text
ttc_from_context
surface_contact_point
ball_center_at_contact
post_velocity_xy
post_speed
post_velocity_angle
```

### Judgment

```text
validity
angular_violation
normalized_violation_severity
violation_family = reflection_direction
paired_scene_id
```

---

## 32.6 `RenderSpec`

Physics 与 visual nuisance 必须分开：

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

Renderer **不负责物理**。

---

## 32.7 `CounterfactualSpec`

为第二阶段预留：

```text
base_scene_id

intervention_variable
source_value
target_value

intervention_safe

counterfactual_post_direction
counterfactual_reflection_error
source_scene_spec
```

这些字段可以第二阶段按需生成，不必现在全部 materialize。

---

# 33. Dataset Metadata 与可重放性

每个 scene 必须能够仅凭 metadata 完整重建。

必须保存：

- config version；
- simulator version；
- seed；
- scene physical state；
- task labels；
- render seed；
- render family；
- pair relation；
- split；
- acceptance provenance。

尤其必须保存：

$$
p_c,\quad v_c,\quad \theta_v,\quad \phi,\quad b,\quad L,\quad w,\quad r.
$$

这决定第二阶段能否随时生成：

$$
\theta_v\rightarrow\theta_v'
$$

或：

$$
\phi\rightarrow\phi'
$$

的 source / counterfactual scene。

---

# 34. Train / Val / Test 与 render variant 的组织

建议层级：

```text
latent_scene_id
    ├── render_variant_1
    ├── render_variant_2
    ├── render_variant_3
    └── judgment_pair(s)
```

普通 split 基于：

```text
latent_scene_id
```

而不是 video path。

同一 latent scene 的所有普通 render variant 和 judgment pair 默认属于同一 split。

---

# 35. v1 数据集建议的三类平衡

## 35.1 Contact label balance

约：

```text
positive : negative ≈ 1 : 1
```

---

## 35.2 Render family balance

Pooled Diverse 主实验中：

```text
Billiards
Air Hockey
Tabletop
```

尽量近似均衡。

---

## 35.3 Judgment balance

Good / Bad matched pair 天然可做到：

```text
valid : invalid = 1 : 1
```

Violation severity 在 invalid 中再按预定 distribution 平衡。

---

# 36. 当前仍需 Pilot 决定的参数

以下不要硬编码为“理论结论”，而应 config 化：

- 总视频长度 \(T\)；
- fps；
- Context:Future 的精确比例；
- collision pre/post frame margin；
- speed range；
- barrier length / width；
- ball radius；
- allowed play area margin；
- endpoint margin；
- tangent epsilon；
- near-miss margin；
- violation severity distribution；
- render texture 数量；
- lighting nuisance 幅度；
- 每个 semantic family 的具体资产。

当前理论默认：

$$
T_{future}\approx2T_{context}
$$

但最终值以 pilot 接受率与模型输入规格共同确定。

---

# 37. v1 明确不做 / Deferred

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

# 38. Optional Future Extensions

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

# 39. v1 最终实验地图

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

# 40. 给 Simulator 实现的最终 Checklist

在开始正式大规模生成前，必须确认：

- [ ] 物理系统只有 single puck + finite-width fixed barrier；
- [ ] 完全弹性 \(e=1\)；
- [ ] Context 内绝无 collision；
- [ ] Future 约为 Context 的 2 倍，具体时长 config 化；
- [ ] collision-positive event 离 Future 两端有 frame margin；
- [ ] 球全程不出画；
- [ ] barrier 全部可见；
- [ ] table edge 不参与物理；
- [ ] 只允许 long-face collision；
- [ ] short edge / corner / support collision 全 reject；
- [ ] near-tangent reject；
- [ ] borderline near-miss reject；
- [ ] Contact negative 必须 `ray_hit = 0`；
- [ ] `ray_hit = 1` 但超出视频时长的 scene reject；
- [ ] speed 随机采样；
- [ ] Contact positive/negative 最终分布近似平衡；
- [ ] speed / angle / position 等 marginals 做 shortcut 检查；
- [ ] State 统一锚定在 \(t_c\)；
- [ ] barrier State 语义采用 axis angle \(\phi\in[0,\pi)\)；
- [ ] Judgment 只做 reflection-direction inconsistency；
- [ ] invalid 保持 speed 不变；
- [ ] invalid 不能穿墙；
- [ ] good/bad prefix 相同；
- [ ] violation severity 保存 raw \(\Delta\theta\)；
- [ ] canonical 与 diverse 共用同一 physics generator；
- [ ] render family 至少包含 billiards / air-hockey / tabletop；
- [ ] moving object 使用不需要真实 rolling texture 的外观；
- [ ] metadata 足以完整 replay；
- [ ] split 按 latent scene；
- [ ] source/counterfactual generation 接口为第二阶段预留；
- [ ] acceptance report 保存明确 reject reason；
- [ ] full-GT oracle、shortcut baseline、marginal checks 先通过，再跑 foundation model。

---

# 41. 一句话总结

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
