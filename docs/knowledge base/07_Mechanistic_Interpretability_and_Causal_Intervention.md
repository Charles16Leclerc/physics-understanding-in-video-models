---
title: Mechanistic Interpretability and Causal Intervention
status: Current
updated: 2026-09-12
tags: [mechanistic-interpretability, causal, patching, intervention]
---

# Mechanistic Interpretability 与因果干预

## 1. 为什么第二阶段不能只继续做 probe

Probe 回答的是：

> 信息是否可以从 representation 中读出？

但：

\[
\boxed{\text{decodable} \neq \text{causally used}}
\]

一个变量可以在 hidden state 中高度可读，但模型 downstream 完全不通过该路径使用它。

因此第二阶段目标是从：

\[
\text{representation analysis}
\]

升级到：

\[
\text{causal computation analysis}.
\]

## 2. Ground-truth computation graph

主 benchmark 的 Ball/Puck–Barrier 提供已知算法：

\[
(p,v,n,c)
\rightarrow
\text{relative geometry}
\rightarrow
\tau_{collision}
\rightarrow
v^+
\rightarrow
\text{prediction/judgment}.
\]

候选 intermediate：

- position \(p\)；
- velocity \(v\)；
- barrier normal \(n\)；
- distance / relative geometry；
- time-to-contact \(\tau\)；
- post-collision velocity \(v^+\)；
- final collision/validity output。

这使我们可以提出**具体可证伪的内部算法假设**，而不是只做 feature discovery。

## 3. 线性 feature / subspace 的基本形式

若 scalar target：

\[
\hat y=w^\top h+b.
\]

归一化：

\[
u=\frac{w}{\|w\|}.
\]

### 3.1 Projection / erasure

移除该一维 candidate subspace：

\[
h_\perp=(I-uu^\top)h.
\]

然后继续跑模型后半部分。

若 downstream performance 显著下降，说明该方向具有 causal importance。

但不能因此声称：

> “这就是模型唯一的 native velocity neuron/direction”。

因为表示可能 redundant/high-dimensional。

## 4. 多维变量与 candidate subspace

例如二维 velocity：

\[
\hat v=Wh+b,
\qquad W\in\mathbb R^{2\times D}.
\]

对 \(W^\top\) 做正交化：

\[
U=\operatorname{orth}(W^\top),
\qquad U^\top U=I.
\]

candidate velocity subspace projection：

\[
P_v=UU^\top.
\]

这只是一个 readout-defined candidate subspace，不自动等于模型唯一真实编码子空间。

## 5. Interchange Intervention

这是当前最推荐的 causal test。

设：

- base scene A；
- source scene B；
- 某 candidate concept subspace projection \(P\)。

构造：

\[
\boxed{
h_A'=(I-P)h_A+Ph_B
}
\]

等价：

\[
h_A'=h_A+P(h_B-h_A).
\]

概念上：

> 保留 A 的其他 representation，只把某个 high-level variable（例如 wall orientation 或 velocity）替换成 B 的值。

### 5.1 Barrier orientation 例子

A：竖直 barrier，当前运动会碰撞。

B：另一 barrier orientation，使相同速度不会碰撞。

若替换 A 内部的 barrier-orientation representation 后，模型 downstream prediction 变成 no collision，并与真实 counterfactual 一致，则提供强 causal evidence：

> 该内部变量参与了 future prediction。

### 5.2 Velocity 例子

替换：

\[
v_A\rightarrow v_B
\]

后观察：

- \(\tau\)；
- will-collide；
- post-collision prediction；
- judgment

是否按 ground-truth physics 改变。

## 6. 为什么 interchange 比简单 steering 更强

普通 steering：

\[
h'=h+\alpha u
\]

只能说明沿某方向可以控制输出。

问题：

- 可能 off-manifold；
- \(u\) 可能只是 probe geometry；
- 不一定对应一个真实 high-level variable intervention。

Interchange 使用真实 source activation：

\[
Ph_B
\]

因此更接近 on-manifold，并且有清晰的高层 counterfactual 语义。

## 7. 解析 steering：把 probe output 改成目标值

若：

\[
v=Wh+b
\]

希望从当前 \(v\) 改成 \(v^*\)：

\[
W(h+\delta h)+b=v^*.
\]

即：

\[
W\delta h=v^*-v.
\]

最小范数解：

\[
\boxed{
\delta h=W^\top(WW^\top)^{-1}(v^*-v)
}
\]

若 \(W\) 满 row rank。

### Caveat

该操作可能把 activation 推离 data manifold，因此当前优先级低于 interchange intervention。

## 8. Activation Patching 不要求先有 probe direction

这是非常重要的原则：

> **Probe 不是 causal intervention 的必要前提。**

例如可以直接：

\[
h_l^{ball}(A)\leftarrow h_l^{ball}(B)
\]

或 patch 某些 token / head / residual stream，观察 downstream output。

因此若 linear probe 找不到干净 direction，也不意味着第二阶段无法继续。

## 9. Nonlinear probe 可以怎样干预

若：

\[
y=g(h)
\]

且 \(g\) 是 MLP，没有唯一 concept direction。

局部可用 Jacobian：

\[
J(h)=\frac{\partial g}{\partial h}.
\]

局部线性化：

\[
g(h+\delta h)\approx g(h)+J\delta h.
\]

要改变到 \(y^*\)：

\[
\delta h\approx J^+(y^*-g(h)).
\]

### 重要限制

\[
\nabla_h g
\]

可能主要反映 **probe 自己学出的 decision geometry**，而不是 backbone 的 native concept representation。

因此：

> MLP 能解码某量，不意味着 MLP gradient 可以直接解释成模型的该物理变量方向。

## 10. Distributed Alignment Search (DAS)

### Fallback

如果线性 / 低维 readout-defined subspace 无法得到稳定 causal intervention，可考虑 DAS。

DAS 直接寻找一个 distributed subspace，使 low-level neural intervention 与预先定义的 high-level causal intervention 一致。

适合回答：

> 某高层变量并不沿 probe weight 直接编码，而是分布在一个旋转后的低维子空间中时，能否仍建立 causal alignment？

当前不一开始就用 DAS，因为：

- 工程复杂；
- 优化过程更难解释；
- 容易把大量自由度引入 mechanistic claim。

## 11. 第二阶段优先级

当前推荐顺序：

1. linear / low-dimensional probe localization；
2. matched interchange intervention；
3. direct activation patching；
4. projection / ablation；
5. 必要时 path patching / head analysis；
6. 若简单方法不足，再用 DAS。

## 12. 从 layer 到 circuit

如果某个中间物理变量在某层出现，并通过 intervention 显示 causal relevance，可进一步分析：

- 哪些 attention heads 写入该 variable；
- 哪些 heads / MLP 读取它；
- writer → reader path；
- ablate 单头或小 head set；
- path patching。

只有在结果足够稳定时才扩展到完整 circuit analysis，避免 scope 过大。

## 13. 最希望看到的机制结果

理想但非必须：

### V-JEPA

\[
E: p,v,n
\]

逐渐形成，随后：

\[
P: \tau, v^+, collision
\]

更显式，并且 patch \(v/n\) 会按解析规律改变 future prediction。

### VLM

可能看到：

- vision tokens 保留 state；
- question/answer residual stream 中 prediction 与 judgment 分别形成；
- 两者 causal pathway 部分共享或分叉。

若 V-JEPA 与 VLM 显示不同内部组织，将直接支撑本项目 architecture-conditioned narrative。

## 14. Claim 层级

统一写作纪律：

- probe：`encodes / contains / makes accessible`；
- geometry：`organizes / factorizes`；
- ablation / patching：`causally contributes under intervention`；
- interchange：`supports alignment with a high-level causal variable`；
- circuit：`computes / transmits / uses`。

禁止从：

\[
\text{decode}
\]

直接跳到：

\[
\text{the model uses this variable to reason}.
\]
