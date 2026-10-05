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

$$
\boxed{\text{decodable} \neq \text{causally used}}
$$

一个变量可以在 hidden state 中高度可读，但模型 downstream 完全不通过该路径使用它。

因此第二阶段目标是从：

$$
\text{representation analysis}
$$

升级到：

$$
\text{causal computation analysis}.
$$

## 2. Ground-truth computation graph

主 Ball/Puck–Barrier benchmark 提供一个完全已知的解析物理系统。

在 Context boundary：

$$
S_c=
(p_c,v_c,b,\phi,L,w,r)
$$

其中：

- $p_c$：ball position；
- $v_c$：pre-collision velocity；
- $b$：barrier center；
- $\phi$：barrier axis direction；
- $L,w$：barrier geometry；
- $r$：ball radius。

这些 state 首先决定相对几何关系以及 Contact：

$$
(p_c,v_c,b,\phi,L,r)
\rightarrow
\text{relative geometry}
\rightarrow
\text{contact / no-contact}
$$

对于 clean contact-positive scene，又进一步决定：

$$
\tau_{\mathrm{collision}},
\qquad
q_{\mathrm{contact}},
\qquad
v^+
$$

其中完全弹性反射满足：

$$
v^+
=
v^-
-
2(v^-\cdot n_{\mathrm{contact}})
n_{\mathrm{contact}}
$$

这里的 $n_{\mathrm{contact}}$ 是 simulator 根据实际接触 long face 派生的 event variable，而不是当前主 State probe target。

对于第二阶段 causal analysis，当前最核心、最干净的局部物理关系进一步收窄为：

$$
\boxed{
(\theta_{v^-},\phi)
\rightarrow
\theta_{v^+}
}
$$

以及：

$$
\boxed{
(\theta_{v^-},\phi,v^+_{\mathrm{obs}})
\rightarrow
\text{Reflection Judgment}
}
$$

这使我们可以提出具体、可证伪的内部 computation hypothesis，而不是只做 feature discovery。

## 3. 线性 feature / subspace 的基本形式

若 scalar target：

$$
\hat y=w^\top h+b.
$$

归一化：

$$
u=\frac{w}{\|w\|}.
$$

### 3.1 Projection / erasure

移除该一维 candidate subspace：

$$
h_\perp=(I-uu^\top)h.
$$

然后继续跑模型后半部分。

若 downstream performance 显著下降，说明该方向具有 causal importance。

但不能因此声称：

> “这就是模型唯一的 native velocity neuron/direction”。

因为表示可能 redundant/high-dimensional。

## 4. 多维变量与 candidate subspace

例如二维 velocity：

$$
\hat v=Wh+b,
\qquad W\in\mathbb R^{2\times D}.
$$

对 \(W^\top\) 做正交化：

$$
U=\operatorname{orth}(W^\top),
\qquad U^\top U=I.
$$

candidate velocity subspace projection：

$$
P_v=UU^\top.
$$

这只是一个 readout-defined candidate subspace，不自动等于模型唯一真实编码子空间。

## 5. Interchange Intervention

这是当前最推荐的 causal test。

设：

- base scene A；
- source scene B；
- 某 candidate concept subspace projection \(P\)。

构造：

$$
\boxed{
h_A'=(I-P)h_A+Ph_B
}
$$

等价：

$$
h_A'=h_A+P(h_B-h_A).
$$

概念上：

> 保留 A 的其他 representation，只把某个 high-level variable（例如 wall orientation 或 velocity）替换成 B 的值。

### 5.1 Barrier orientation intervention：当前 v1 主要例子

构造 matched base/source，使：

- $p_c$ 相同；
- $v_c$ 相同；
- barrier center、length、width 相同；
- appearance 尽量一致；
- 只改变 barrier axis direction：

$$
\phi_A\neq\phi_B
$$

在 base activation 中只替换 candidate barrier-orientation representation，然后让模型 downstream computation 正常继续。

当前第一批主 Prediction endpoint **不是** will-collide / TTC，而是：

$$
\boxed{\theta_{v^+}}
$$

若 downstream post-collision-direction representation 系统地朝：

$$
f(\theta_{v^-},\phi_B)
$$

所对应的解析反射方向变化，则支持该 candidate internal representation 对 downstream reflection computation 具有 causal contribution。

进一步地，在已经观察完整 valid trajectory 的 Judgment task 中，可以保持 observed future 不变，只修改内部 barrier representation，测试 Reflection Judgment 是否按照新的 counterfactual reflection expectation 改变。

### 5.2 Velocity-direction intervention：当前 v1 主要例子

构造：

$$
S_A(t_c)
=
(p_c,v_A,\phi,\ldots)
$$

与：

$$
S_B(t_c)
=
(p_c,v_B,\phi,\ldots)
$$

尽量保持：

- $p_c$ 相同；
- speed 相同；
- barrier geometry 相同；
- appearance 相同；

只改变 velocity direction：

$$
\theta_{v_A}\neq\theta_{v_B}
$$

对 candidate velocity-direction representation 做 interchange 后，第一批主要观察：

$$
\boxed{\theta_{v^+}}
$$

与 Reflection Judgment 是否按解析物理关系变化。

当前第一版不把：

- TTC；
- contact point；
- Contact Prediction

作为这类 intervention 的主要 causal endpoint，因为 low-level direction edit 可能与内部 position / trajectory representation 产生不一致。

## 6. 为什么 interchange 比简单 steering 更强

普通 steering：

$$
h'=h+\alpha u
$$

只能说明沿某方向可以控制输出。

问题：

- 可能 off-manifold；
- \(u\) 可能只是 probe geometry；
- 不一定对应一个真实 high-level variable intervention。

Interchange 使用真实 source activation：

$$
Ph_B
$$

因此更接近 on-manifold，并且有清晰的高层 counterfactual 语义。

## 7. 解析 steering：把 probe output 改成目标值

若：

$$
v=Wh+b
$$

希望从当前 \(v\) 改成 \(v^*\)：

$$
W(h+\delta h)+b=v^*.
$$

即：

$$
W\delta h=v^*-v.
$$

最小范数解：

$$
\boxed{
\delta h=W^\top(WW^\top)^{-1}(v^*-v)
}
$$

若 \(W\) 满 row rank。

### Caveat

该操作可能把 activation 推离 data manifold，因此当前优先级低于 interchange intervention。

## 8. Activation Patching 不要求先有 probe direction

这是非常重要的原则：

> **Probe 不是 causal intervention 的必要前提。**

例如可以直接：

$$
h_l^{ball}(A)\leftarrow h_l^{ball}(B)
$$

或 patch 某些 token / head / residual stream，观察 downstream output。

因此若 linear probe 找不到干净 direction，也不意味着第二阶段无法继续。


## 8A. Activation Patching / Steering / Ablation 的严格辨析

本节补充一个对第二阶段实验非常重要的术语与证据层级框架。

### 8A.1 为什么“整层 A → B 替换”通常没有科学意义

若直接把场景 A 在某层的完整 hidden state：

$$
H_l(A)
$$

全部替换为：

$$
H_l(B),
$$

然后模型后半部分输出也变得更像 B，这几乎只说明：

> 后半部分依赖前半部分的内部状态。

因为此时模型收到的已经近似是“B 到第 \(l\) 层为止的全部内部状态”。因此真正有科学意义的 activation patching 必须是：

$$
\boxed{\text{localized intervention}}
$$

即只替换一个受控的内部部分。

### 8A.2 有意义的 Activation Patching 可以 patch 什么

Activation patching 并不要求先找到 linear probe direction。可以直接 patch：

1. **attention head**
   $$
   a_{l,h}(A)\leftarrow a_{l,h}(B)
   $$

2. **MLP / residual contribution**

3. **单个 token**
   $$
   h_{l,i}(A)\leftarrow h_{l,i}(B)
   $$

4. **一组空间/时间区域 token**
   例如只替换 barrier 所在区域：
   $$
   h_{l,i}(A)\leftarrow h_{l,i}(B),
   \qquad i\in S_{\mathrm{barrier}}
   $$

5. **某个低维 concept subspace**
   $$
   h_A'=(I-P)h_A+Ph_B
   $$

6. **特定 sender → receiver path**
   这属于更后期的 path patching / circuit analysis。

因此：

> **Activation patching 本身不需要 linear probe。**

Linear probe 主要是在我们希望做“概念选择性的 subspace patching”时，用来提供一个 candidate subspace。

### 8A.3 Matched source/base pair 是可解释性的关键

如果 A/B 同时在多个因素上不同，例如：

- 球颜色；
- 背景；
- speed；
- velocity direction；
- barrier orientation；

那么即使只 patch 某个 token / subspace，也很难知道到底换进去了什么信息。

因此 v1 mechanistic experiment 优先构造高匹配度 pair。

##### Barrier-direction pair

$$
A=(p_c,v_c,b,\phi_A,L,w,\text{appearance})
$$

$$
B=(p_c,v_c,b,\phi_B,L,w,\text{same appearance})
$$

主要只让：

$$
\phi_A\neq\phi_B
$$

##### Velocity-direction pair

$$
A=(p_c,s,\theta_A,\phi,\text{appearance})
$$

$$
B=(p_c,s,\theta_B,\phi,\text{same appearance})
$$

主要只让：

$$
\theta_A\neq\theta_B
$$

这样 patching 才具有尽可能清楚的反事实语义。

但即使 pair 很干净，也不能自动声称低层 edit 就等于 high-level `do` intervention；这种 causal alignment 仍需要 downstream counterfactual behavior 来验证。

### 8A.4 Token / region patching 仍不等于 concept-level patching

即使只替换：

$$
h_{\mathrm{barrier}}(A)\leftarrow h_{\mathrm{barrier}}(B),
$$

该 token 仍可能同时包含：

- barrier orientation；
- position；
- texture；
- surrounding context；
- global scene information；
- relation / prediction information。

因此严格 claim 只能是：

> barrier-region representation causally contributes to prediction.

不能直接说：

> 我们已经只替换了“wall orientation”。

如果要接近后者，应进一步做 subspace-level interchange intervention。

### 8A.5 Mean pooling 与 activation patching 没有必然关系

Activation patching 的科学意义并不是因为“先做过平均”。

事实上，patching 往往越保留：

- token；
- head；
- layer；
- position；
- path

这些结构信息，越容易精确 localization。

Mean pooling 主要属于 probe/readout 的 aggregation 操作，不是 patching 的必要步骤。

---

## 8B. Steering 与 Patching 的区别

### 8B.1 Steering

典型形式：

$$
\boxed{
h'=h+\alpha v
}
$$

其中 \(v\) 可以来自：

- probe weight；
- class mean difference；
- CAV；
- PCA direction；
- SAE feature；
- learned steering vector。

Steering 更主要回答：

> 沿某个方向修改 activation，能否控制模型行为？

它更接近：

$$
\boxed{\text{control}}
$$

而不天然等于 causal diagnosis。

### 8B.2 Mean-difference / contrastive steering

若：

$$
\mu_A=\mathbb E[h\mid A],
\qquad
\mu_B=\mathbb E[h\mid B],
$$

构造：

$$
v_{\mathrm{concept}}=\mu_A-\mu_B,
$$

再做：

$$
h'=h+\alpha v_{\mathrm{concept}},
$$

更准确地属于：

- contrastive activation steering；
- activation addition；
- representation engineering；

而不是典型 activation patching。

### 8B.3 为什么 interchange 通常比 steering 更严谨

Steering：

$$
h+\alpha v
$$

可能把 activation 推到模型训练分布之外，即：

$$
\boxed{\text{off-manifold intervention}}
$$

而 interchange patching 使用真实 source activation：

$$
Ph_B,
$$

因此被替换的部分至少来自真实样本，更接近 on-manifold。

当然二者不是绝对二分。统一写成：

$$
h_A'
=
h_A+\alpha P(h_B-h_A)
$$

时：

- \(\alpha=1\)：完整 subspace patching；
- \(0<\alpha<1\)：source/base interpolation；
- \(\alpha>1\)：逐渐接近 extrapolative steering。

所以二者的区别更主要来自：

- 是否使用真实 source value；
- intervention 的构造方式；
- 研究目的：diagnosis 还是 control。

---

## 8C. Ablation、Causal Tracing、Interchange、Path Patching

### 8C.1 Ablation / Concept Erasure

Ablation 问：

> 这个组件或 subspace 是否对任务必要？

例如：

$$
h'=(I-P)h.
$$

或：

$$
a_{\mathrm{head}}=0.
$$

因此它更接近：

$$
\boxed{\text{necessity}}
$$

而不是“这个内部变量是否具有某个具体 physical semantics”。

### 8C.2 Causal Tracing

Causal tracing 通常是 activation patching 的一个经典 protocol：

1. clean input 正常运行；
2. 构造 corrupted input，使模型行为受损；
3. 在 corrupted run 某个 site 恢复 clean activation；
4. 测试正确行为是否恢复。

形式：

$$
h_l^{\mathrm{corrupt}}
\leftarrow
h_l^{\mathrm{clean}}.
$$

所以可理解为：

$$
\boxed{
\text{clean → corrupt → restore 型 activation patching}
}
$$

### 8C.3 Interchange Intervention

Interchange intervention 比 generic patching 更强，因为它不仅问：

> “这个 site 会不会影响 output？”

而是预先指定一个 high-level causal variable，并检验低层 intervention 是否呈现与该 high-level counterfactual 一致的 downstream effect。

当前 v1 最核心的 high-level 关系是：

$$
Y=f(\Theta,\Phi)
$$

其中：

$$
\Theta=\theta_{v^-},
\qquad
\Phi=\phi,
\qquad
Y=\theta_{v^+}
$$

例如，希望测试 barrier-axis representation 时，对 high-level model 可以定义：

$$
\Phi_A\rightarrow\Phi_B
$$

对应解析 counterfactual：

$$
Y_{\mathrm{CF}}
=
f(\Theta_A,\Phi_B)
$$

低层则尝试：

$$
h_A'
=
(I-P_\Phi)h_A
+
P_\Phi h_B
$$

若 patched model 的 downstream post-collision prediction 系统地接近：

$$
Y_{\mathrm{CF}}
$$

则支持 candidate low-level subspace 与 high-level barrier-orientation variable 之间存在 causal alignment。

对 velocity direction 同理。

但必须强调：

$$
\boxed{
\text{low-level interchange}
\not\equiv
do(\Phi=\Phi_B)
}
$$

是实验开始前的默认立场。

模型内部的 velocity / orientation feature 可能与 position、trajectory、token anchor 等变量纠缠。因此 low-level edit 是否真的近似实现 high-level intervention，本身就是要通过 downstream counterfactual consistency 检验的科学问题。

### 8C.4 Path Patching

普通 patching 更像测试“节点”：

- 某个 head；
- 某个 MLP；
- 某个 token；
- 某个 residual site。

Path patching 则进一步问：

> 某个 sender 对 output 的影响，是否通过特定 receiver / path 传递？

例如：

$$
H_v
\rightarrow
H_c
\rightarrow
\text{Output},
$$

其中：

- \(H_v\)：candidate velocity writer；
- \(H_c\)：candidate collision computation unit。

这更适合 circuit discovery 的后期，而不应一开始就作为主实验。

---

## 8D. 本项目的证据层级

### Level 1：Decodability

方法：

- linear probe；
- MLP / attention probe。

回答：

> 某物理变量是否存在、是否 accessible？

证据性质：

$$
\boxed{\text{correlational}}
$$

### Level 2：Causal Localization

方法：

- ablation；
- token patching；
- region patching；
- head patching。

回答：

> 哪些内部 site 对 prediction / judgment 具有 causal contribution？

但还不能证明其具体物理语义。

### Level 3：Causal Semantics

方法：

$$
\boxed{\text{matched interchange intervention}}
$$

回答：

> 某内部 representation 是否与 velocity direction / barrier axis direction 等 high-level physical variable 存在可验证的 causal alignment，并被 downstream reflection Prediction / Judgment computation 使用？

核心标准：

$$
\boxed{
\text{internal counterfactual effect}
\approx
\text{physics-simulator counterfactual effect}
}
$$

注意，这里的目标不是预先假定低层 patch 就是 high-level `do`，而是用 counterfactual agreement 检验二者是否近似对齐。
### Level 4：Circuit

方法：

- writer / reader analysis；
- path patching；
- sender → receiver intervention。

目标：

> 恢复 state representation 如何被转换为 prediction / judgment 的具体计算路径。

---

## 8E. 本项目第二阶段推荐 protocol

当前 v1 第二阶段建议按以下顺序推进：

1. **State representation localization**  
   优先寻找 $\theta_{v^-}$ 与 $\phi$ 的 candidate representation / subspace。

2. **matched token / region activation patching**  
   先确认 ball-motion / barrier-region representation 对 downstream reflection task 具有 causal contribution。

3. **matched concept-level interchange intervention**  
   使用真实 source activation 尝试替换 velocity-direction 或 barrier-axis representation。

4. **State → Prediction causal test**  
   主要观察：

$$
\theta_{v^+}
$$

5. **State → Judgment causal test**  
   保持 observed future 不变，测试内部 State intervention 是否系统改变：
   - valid / invalid judgment；
   - predicted reflection inconsistency / severity。

6. **projection / ablation**  
   测试 candidate representation 对这些 downstream tasks 的必要性。

7. **specificity controls**  
   包括 random subspace、wrong region、unrelated physical variable、unmatched source control。

8. 若结果稳定，再做 **head analysis / path patching**。

9. 若简单线性 / low-dimensional candidate subspace 无法支撑 causal semantics，再考虑 DAS。

当前第一版不把 TTC、contact point 或 Contact Prediction 作为 direction intervention 的主要 causal endpoint。

### 8E.1 Ball–Barrier 推荐案例

#### Barrier-direction intervention

Base：

$$
A=(p_c,v_c,b,\phi_A,L,w)
$$

Source：

$$
B=(p_c,v_c,b,\phi_B,L,w)
$$

保持：

- same context-end ball position；
- same velocity；
- same speed；
- same barrier center / size；
- same appearance；

主要只改变：

$$
\phi_A\rightarrow\phi_B
$$

低层 intervention 后，观察 downstream：

$$
\theta_{v^+}^{\mathrm{patched}}
$$

是否接近 simulator counterfactual：

$$
f(\theta_{v^-},\phi_B)
$$

#### Velocity-direction intervention

Base / source 保持：

- $p_c$ 相同；
- barrier 相同；
- speed 相同；

主要只改变：

$$
\theta_{v^-}^{A}\rightarrow\theta_{v^-}^{B}
$$

然后观察：

$$
\theta_{v^+}^{\mathrm{patched}}
$$

是否按：

$$
f(\theta_{v^-}^{B},\phi)
$$

变化。

同一 intervention 还可继续测试 Reflection Judgment，从而区分：

$$
\text{State representation is decodable}
$$

与：

$$
\text{State representation is causally used in downstream physical computation}
$$

---

## 8F. 术语速查表

| 方法 | 典型操作 | 主要问题 | 是否要求 linear probe |
|---|---|---|---|
| Linear Probe | \(y=Wh+b\) | 信息能否线性读取？ | 本身就是 probe |
| MLP Probe | \(y=g(h)\) | 信息能否非线性读取？ | 否 |
| Ablation | \(h'=(I-P)h\) / zero head | 这个信息/组件是否必要？ | 否 |
| Activation Patching | \(a_A\leftarrow a_B\) | 这个内部 site 是否 causally relevant？ | 否 |
| Causal Tracing | corrupted run 中恢复 clean activation | 正确信息从哪里恢复/传递？ | 否 |
| Interchange Intervention | 用 source 的某 causal-variable representation 替换 base | 内部表示是否与高层 causal variable 对齐？ | 不一定 |
| Subspace Patching | \(h_A'=(I-P)h_A+Ph_B\) | 某低维 representation 是否有 causal role？ | \(P\) 可由 probe 得到，也可不用 |
| Steering / ActAdd | \(h'=h+\alpha v\) | 能否沿某方向控制行为？ | 否，但常用 probe/mean-diff 得到 \(v\) |
| Concept Erasure | 去除某 subspace | 去掉候选概念后行为怎样？ | 常需要 concept subspace |
| DAS | 学习 \(P\) 最大化 interchange correctness | 找到 causally aligned distributed subspace | 不要求 linear probe |
| Path Patching | 只让某 sender→receiver path 被替换 | 哪条计算路径真正传递信息？ | 否 |

一句话记忆：

> **Probe 是“读”；Ablation 是“删”；Steering 是“推”；Activation Patching 是“换”；Interchange Intervention 是“有语义地换”；Path Patching 是“只让这条路换”。**


## 9. Nonlinear probe 可以怎样干预

若：

$$
y=g(h)
$$

且 \(g\) 是 MLP，没有唯一 concept direction。

局部可用 Jacobian：

$$
J(h)=\frac{\partial g}{\partial h}.
$$

局部线性化：

$$
g(h+\delta h)\approx g(h)+J\delta h.
$$

要改变到 \(y^*\)：

$$
\delta h\approx J^+(y^*-g(h)).
$$

### 重要限制

$$
\nabla_h g
$$

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

理想但非必须的结果是：

$$
E:
\quad
v,\ s,\ \theta_v,\ \phi
$$

等 current State information 逐渐形成；

随后 predictor 中：

$$
\theta_{v^+}
$$

以及其他 collision-dynamics quantities 变得更 explicit / 更低 readout cost。

更强的 causal evidence 是：

> 对 candidate $\theta_{v^-}$ 或 $\phi$ representation 做 matched intervention 后，predictor 中的 post-collision direction 按解析 reflection law 系统变化，并进一步影响 Reflection Judgment。

如果只能 decode State，但 intervention 不产生相应 downstream effect，则说明：

$$
\text{decodable}
\neq
\text{causally used}
$$

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

$$
\text{decode}
$$

直接跳到：

$$
\text{the model uses this variable to reason}.
$$
