---
title: Unified Benchmark and Dataset Design
status: Current
updated: 2026-09-12
tags: [benchmark, dataset, simulator, rendering]
---

# 统一 Benchmark / 数据集设计

## 1. 数据集不是工程配套，而是研究工具

本项目的 dataset 不是“先找个数据跑实验”，而是为了让 mechanistic claim 成立而设计的 **diagnostic instrument**。

如果 State、Prediction、Judgment 分别来自三个完全不同 benchmark，则任何差异都可能来自：

- 场景复杂度；
- 物体/背景多样性；
- camera motion；
- clip length；
- label entropy；
- train-set size；
- shortcut structure；
- simulator/rendering artifact。

因此主设计原则是：

> **One World, Multiple Queries.**

同一个 latent physical world 产生三类任务，而不是用三个 benchmark 代表三种“能力”。

## 2. 数据生成的因子分解

设物理参数为 \(\theta\)：

\[
S_{0:T}=\operatorname{Simulate}(\theta).
\]

其中 \(S_t\) 是精确物理状态。

视觉 nuisance 单独记为 \(\nu\)：

\[
I_t=R(S_t,\nu).
\]

任务标签全部从 simulator state 生成：

\[
Y_S=g_S(S),\qquad
Y_P=g_P(S_{0:T}),\qquad
Y_J=g_J(S_{0:T},\text{counterfactual relation}).
\]

**原则：GT 永远来自 simulator，不从 rendered image 反推。**

## 3. 当前主物理系统

### Current

\[
\boxed{\text{single moving disk/puck + fixed finite barrier}}
\]

底层是平面 2D 刚体运动。

### 为什么不需要 general-purpose physics engine

对于该系统，解析/事件驱动 simulation 比 PyBullet、MuJoCo、Blender physics 更好：

- 无 collision tolerance artifact；
- 无 penetration correction；
- 无 timestep-dependent result；
- 无 engine-specific restitution；
- 计算量极低；
- intermediate ground truth 精确。

### 为什么第一版不做 multi-ball

单 puck + barrier 已经足够生成：

- State；
- 非线性 Prediction；
- Judgment；
- matched counterfactual；
- causal intervention。

多球/多碰撞会引入额外 binding、long-rollout sensitivity 和复杂事件分支，不是第一篇工作所必需。

注意：单次 two-ball collision 本身并不混沌，真正敏感的是多球、多次碰撞、长 rollout。Ball–Ball 只是当前不必要，不是永久排除。

## 4. 解析动力学

令固定 barrier 的支撑线为：

\[
n^\top x=c.
\]

puck 中心为 \(p\)，速度为 \(v\)，半径 \(r\)。可解析求出 time-to-contact \(\tau\)。

完全弹性固定 barrier：

\[
v^+=v^- -2(v^-\cdot n)n.
\]

带 restitution \(e\)：

\[
v^+=v^--(1+e)(v^-\cdot n)n.
\]

有限线段 barrier 还要求 contact point 落在 segment endpoints 之间。有限 geometry 很重要，因为它能让 `will collide?` 变成真正 relational 的任务，而不是“某个坐标过阈值”。

### Event-based simulation

不要简单 Euler：

1. 计算一个 frame interval 内的精确碰撞时刻；
2. 移动到 contact；
3. 解析更新速度；
4. 用剩余 sub-frame time 继续运动。

由此得到精确 GT：

- \(\tau_{collision}\)；
- pre-collision velocity；
- post-collision velocity；
- contact point；
- collision frame；
- sub-frame collision time。

## 5. State / Prediction / Judgment 标签

### 5.1 State

候选：

- \(p_x,p_y\)；
- \(v_x,v_y\)；
- speed；
- heading；
- barrier normal / orientation；
- distance-to-barrier；
- contact state；
- object mask / identity metadata。

### 5.2 Prediction

主 target 应需要非平凡关系计算：

- will collide within horizon \(H\)?
- time-to-contact \(\tau\)；
- post-collision velocity \(v^+\)；
- 可选 contact point。

#### Control only：future free-flight position

\[
x_{t+\Delta t}=x_t+v_t\Delta t
\]

本身对 state 是线性的，因此即使 encoder 可线性解码 future position，也不能证明其内部完成了“预测计算”。只能作为 sanity control。

### 5.3 Judgment

候选：

- observed transition valid / invalid；
- violation severity；
- violation type；
- 少量 counterfactual judgment。

Judgment 的设计核心不是制造荒谬错误，而是让单独的 state marginal 都看起来合理，错误只存在于它们之间的关系。

## 6. Matched Physical Violations

### Barrier reflection 例子

正确：

\[
v^+_{good}=v^--2(v^-\cdot n)n.
\]

为了构造“看起来合理但关系错误”的 bad case，采样另一个合法 barrier orientation \(n'\)：

\[
v^+_{bad}=v^--2(v^-\cdot n')n',
\]

但画面中实际 barrier 仍保持 \(n\)。

这样：

- incoming velocity 本身正常；
- outgoing velocity 本身来自合法反射分布；
- barrier orientation 本身正常；
- 真正错误的是 \((v^-,n,v^+)\) 之间的条件关系。

目标是让：

\[
P(v^+|good)\approx P(v^+|bad),
\]

\[
P(n|good)\approx P(n|bad),
\]

\[
P(v^-|good)\approx P(v^-|bad).
\]

避免 “bad = 向上运动 / 大速度 / 某种颜色” 这类 trivial shortcut。

## 7. Violation Severity

### Tentative，强烈建议

用连续/分级误差控制 invalidity，例如：

\[
\theta_{bad}=\theta^*+\delta
\]

其中：

\[
\delta\in\{5^\circ,15^\circ,30^\circ,60^\circ\}
\]

或连续采样。

价值：

- 避免只有 binary ceiling/floor；
- 可画 sensitivity curve；
- 可研究不同 layer/readout 对 subtle vs obvious violation 的差异；
- 区分 anomaly detection 与精细 physics consistency judgment。

## 8. 渲染：必须显式解决重力方向歧义

### 8.1 问题

如果图像只是“木纹 + 一个圆 + 一条线”，模型可能无法判断：

- 这是俯视水平桌面；
- 还是正视竖直平面。

若 scene orientation 本身 ambiguous，就不能公平要求模型知道重力是否作用于 image plane。

### 8.2 当前方案：多个明确的俯视水平场景 family

#### Family A：billiards-like overhead table

- 完整可见的桌框；
- green / blue / red felt variants；
- 球袋可以作为“俯拍台球桌”的 semantic cue；
- moving object 使用 plain colored ball / puck-like disk；
- 内部障碍物做成 **fixed barrier rail**，而不是台球杆或三角架。

为什么不把球杆/三角架当墙：

- 它们在现实中可移动；
- 若模拟成 infinite-mass barrier，反而与模型真实世界先验冲突。

可以通过固定支座、夹具、螺钉样式让 barrier 明显是固定物。

#### Family B：air-hockey-like table

这一 family 与模拟物理最匹配：

- 顶视水平桌面；
- 摩擦很低；
- puck；
- plastic fixed barrier；
- rink/table markings 提供方向/场景语义。

从“physics semantics 与 simulator law 一致”角度，它可能比台球更干净。

#### Family C：tabletop / lab surface

- 画面必须看到完整桌面边缘，不能让 texture 填满整个 frame；
- 桌外保留 floor/background；
- wood / gray lab table / rubber mat 等；
- obstacle 使用固定亚克力条、金属 rail、木挡条等。

### 8.3 为什么要多个 semantic skins

与其随机几十种背景贴图，不如保持：

\[
\text{same latent physics} + \text{different world semantics}.
\]

这样可直接检验：

> 发现的 state/prediction/judgment organization 是否只是某种 billiards prior，还是跨视觉语义稳定？

## 9. Canonical 与 Diverse

### Canonical

不是纯白 PPT 示意图，而是固定、简单、自然的俯视 tabletop：

- 固定背景；
- 固定红色或单一颜色 puck；
- 固定 barrier style；
- fixed camera；
- fixed lighting；
- 无 clutter。

### Diverse

从同一 physics distribution 生成，但改变：

- scene family；
- surface material；
- puck/ball skin；
- barrier material；
- mild brightness/shadow；
- 可选轻微 camera / color nuisance（主实验初期不宜过强）。

第二阶段 mechanistic experiment 直接使用 Canonical subset：

\[
D_{mech}\subset D_{broad}.
\]

避免第二部分突然换成纯白背景造成 domain shift。

## 10. 球/圆盘贴图与 rolling 问题

### 当前倾向

物理层可以继续叫 ball/puck，但 renderer 更倾向 **puck / plain disk** 或轴对称球体外观。

原因：真实台球有三维滚动。如果使用号码球/条纹球，但只把 2D sprite 平移，会出现纹理没有随真实球面滚动而变化的问题；若简单让 sprite 在 image plane 内旋转，又不等价于真实 rolling。

因此第一版 diverse skin 建议：

- plain solid colors；
- radial shading；
- axis-symmetric appearance；
- air-hockey puck skin。

号码/条纹台球可以后续作为更真实 renderer 的 optional extension。

## 11. Pocket / goal 扩展

### Tentative future task

台球场景的自然 extension：

- will the ball enter a pocket?

这会引入：

\[
p,v\rightarrow trajectory\rightarrow pocket intersection.
\]

但第一版主任务中，若保留 pockets 作为视觉 cue，应保证 trajectory 与 pocket 有足够安全距离，避免引入第二种 interaction affordance。

## 12. Bench 合格性：必须通过的 shortcut tests

详见 [[08_Experiment_Plan_and_Evaluation]]，这里列核心项。

### 12.1 Latent-scene split — 必须

同一个 latent trajectory 的不同 render skin 必须进入同一个 split。

否则 train/test 会通过同一物理轨迹泄漏。

### 12.2 Label / nuisance marginal balance — 必须

检查：

- color；
- barrier orientation；
- speed magnitude；
- absolute position；
- scene family；
- texture。

不能单独决定 label。

### 12.3 GT-state → target baseline — 必须

对 simulator 真 state 训练：

- linear probe；
- MLP。

Prediction 理想情况：

\[
\text{Linear}(s) \ll \text{MLP}(s)\approx ceiling.
\]

否则任务可能太简单，无法证明 predictor 做了关系计算。

### 12.4 Judgment 单阶段 shortcut — 必须

至少测试：

- first frame only；
- last frame only；
- random frame only；
- pre-state only；
- post-state only。

理想上都接近 chance，而 full relation 可接近 ceiling。

### 12.5 Full-GT oracle — 必须

确认标签无 bug、任务本身可解。

### 12.6 Same-physics different-render transfer — 强烈建议

train probe on skin A，test on held-out skin B/C。

若仍有效，更支持物理而非 appearance shortcut。

### 12.7 Frame shuffle / time reversal — 任务相关

仅对真正需要时序的任务使用，不应机械套给所有 state variable。

## 13. 外部数据集的定位

### Current

**不作为主实验必须部分。**

原因：

- 缺少干净连续 state GT；
- scene / task / difficulty 不匹配；
- shortcut 不受我们控制；
- 很可能破坏主实验的可解释性。

### Optional sanity check

如果时间充裕，只做最轻量 external validation：

- 在 Physion 验证 future contact trend；
- 在某现成 judgment benchmark 验证 VLM late-layer trend；
- 不强行复制完整 State×Prediction×Judgment 矩阵。

如果必须在 external benchmark 与第二阶段 causal experiment 二选一，当前优先：

\[
\boxed{\text{causal mechanistic experiment}}
\]
