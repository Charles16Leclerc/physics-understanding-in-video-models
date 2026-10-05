---
title: Open Questions and TODO
status: Current
updated: 2026-10-05
tags:
  - open-questions
  - todo
---

# Open Questions 与 TODO

> 本文档只记录尚未决定的事项。每个问题解决后，不删除原条目；在其下追加 `Resolved`、日期、决策和理由，并同步 [[11_Decision_Log_and_Idea_Evolution]]。

## A. Benchmark Physics

### Open Question A1 — finite-barrier 精确碰撞公式与边界 case

需要最终确定：

- segment endpoints 的接触判定；
- disk radius offset；
- 端点碰撞是否视作 point obstacle；
- corner collision 的反射法向如何定义；
- 是否直接排除端点极近 case 以保持物理简单。

### Resolved — 2026-10-04

v1 已在 [[05_Benchmark_and_Experiment_Design]] 中冻结 finite-barrier contact 规则：

- moving object 为半径 $r=0.625$ cell 的 disk；
- barrier 为 finite-width rectangle；
- 只有 long-face interior collision 可进入 positive；
- short-face、corner、ambiguous simultaneous contact 全部 reject；
- 不为 corner 定义反射法向，因为 corner 不属于 v1 合法物理事件；
- surface contact point 到两端的轴向 margin 固定为：

$$
d_1=r=0.625\text{ cell}
$$

- threshold 等号边界统一视为 ambiguous，reject。

### Open Question A2 — friction 是否加入

当前倾向：第一版不加或固定极小摩擦。

需要 pilot 判断：

- 完全匀速是否视觉上过“滑”；
- billiards skin 下无摩擦是否违背模型先验；
- air-hockey skin 是否能自然解决。
### Resolved — 2026-10-04

v1 固定：

$$
\boxed{\text{friction}=0}
$$

不再使用“无摩擦或极小固定摩擦”两套定义。

视觉语义通过 overhead tabletop / air-hockey-like / billiards-like render family 保证场景可被自然理解；是否加入摩擦只作为未来数据版本的 extension。

### Open Question A3 — violation operators 最终集合

候选：

- wrong reflection normal；
- wrong restitution / speed magnitude；
- impossible penetration；
- spontaneous direction change；
- delayed collision response。

需要选择足够多样但仍共享简单物理计算图的子集。

### Resolved — 2026-10-04

v1 Judgment 不再混合多个 violation family。

唯一主任务为：

$$
\boxed{\text{Reflection Consistency Judgment}}
$$

唯一正式 invalid operator 为：

$$
\theta_{\mathrm{bad}}^+
=
\theta_{\mathrm{valid}}^+
+
\sigma\delta
$$

其中：

$$
\sigma\in\{-1,+1\},
\qquad
\delta\sim U(5^\circ,90^\circ)
$$

保持 post-collision speed 不变。

同时对 bad trajectory 做：

- 不穿墙；
- outgoing angle $>10^\circ$；
- ROI；
- second collision；

等检查。

另外把原 barrier 绕 collision-time ball center 旋转 $\sigma\delta/2$，作为 alternate legal reflection 的 support-feasibility check。该 alternate barrier 不出现在真实 invalid video 中。

wrong restitution、penetration、disappearance 等其他 violation family 全部 deferred。

### Open Question A4 — counterfactual task 是否放主实验

例如：

- 如果 barrier 旋转 \(\Delta\theta\)，是否仍碰撞？
- 如果 barrier 移除，未来位置在哪里？

当前倾向：先不让 counterfactual 成为第三大类之外的额外主轴；可作为 Judgment/Prediction 的 advanced subset。

### Resolved for v1 core scope — 2026-10-04

不新增第四类 “Counterfactual Task”。

Counterfactual 的主要作用进入第二阶段 mechanistic intervention：

- State → Prediction；
- State → Judgment。

它属于 causal analysis 方法，而不是与 State / Prediction / Judgment 并列的新 benchmark axis。

更广泛的 explicit counterfactual QA 可作为 future extension。

## B. Rendering

### Open Question B1 — canonical 主要 skin

候选：

- air-hockey；
- billiards；
- lab tabletop。

当前略偏 air-hockey / neutral tabletop，因为 physics semantics 最匹配。

### Open Question B2 — diverse family 比例

需要决定三种 skin 的 sample 比例，以及 train/test 是否做 held-out-family split。

### Open Question B3 — shadow model

是否加入固定轻微阴影以强化俯视/立体感？

风险：shadow 本身可能成为 motion cue / nuisance。

### Open Question B4 — texture pool

需要准备：

- surface textures；
- puck colors/material；
- barrier styles。

原则：避免任何 texture 与 label 相关。

### Open Question B5 — resolution / FPS / duration

需要兼顾：

- V-JEPA/Qwen native preprocessing；
- 速度可视觉识别；
- token 数量与计算量；
- collision 前后帧数。

### Resolved — 2026-10-04

v1 已固定 master resolution：

$$
448\times448
$$

并固定：

$$
24\text{ fps},
\qquad
24\text{ frames},
\qquad
T=1.0\text{s}
$$

Context：

```text
frames 0–7
```

Future：

```text
frames 8–23
```

Context boundary：

$$
t_c=\frac{8}{24}=\frac13\text{s}
$$

合法 positive collision frame：

```text
12–19 inclusive
```

Speed range 仍保留为 pilot-adjustable 参数；当前默认：

$$
s\sim U(5,8.5)\text{ cells/s}
$$

正式确定 speed range 前需先跑 latent acceptance / angular-distribution pilot。


## C. Task Definition

### Open Question C1 — State target 最终集合

主候选：

- \(p_x,p_y\)；
- \(v_x,v_y\)；
- speed；
- heading；
- barrier normal。

是否加入：

- distance-to-barrier；
- contact state；
- TTC 前置 derived state？

### Resolved — 2026-10-04

v1 核心 State target：

$$
(v_x,v_y),
\qquad
s,
\qquad
\theta_v,
\qquad
\phi
$$

其中：

$$
\phi\in[0,\pi)
$$

是 barrier long-axis direction。

位置 $p_c$、barrier center 与 relative geometry 保留为 auxiliary State / oracle variables。

signed barrier normal 不再是主 State target；具体 collision event 的 `contact_normal` 是 simulator 派生量。

### Open Question C2 — Prediction target 最终集合

候选：

- will-collide-within-H；
- TTC；
- post-collision velocity；
- contact point。

需要先通过 GT-state qualification。

### Resolved — 2026-10-04

Prediction 分成两个 Task Views。

### Contact

不再使用：

```text
will-collide-within-H
```

而使用 clean Contact classification：

- positive：满足全部 clean long-face collision 条件；
- negative：context-end ball-center infinite ray 明确避开 barrier 的 $d_2$ rounded safety region；
- 其他中间 / ambiguous case：reject。

“最终会撞、只是视频时间不够”的 scene 必须 reject。

### Collision Dynamics

仅对 Contact-positive scene：

- TTC；
- surface contact point；
- post-collision velocity；
- post-collision direction。

其中 post-collision direction 是当前最核心 Prediction target。


### Open Question C3 — Judgment target 最终集合

至少：

- binary valid/invalid。

强烈考虑：

- severity regression。

### Resolved — 2026-10-04

v1 Judgment target：

1. binary valid / invalid；
2. continuous angular violation $\Delta\theta$。

Canonical severity GT 为 raw：

$$
\Delta\theta
$$

辅助 normalized field：

$$
\text{normalized severity}
=
\frac{\Delta\theta}{90^\circ}
$$

Invalid $\Delta\theta$ 连续采样，不使用离散 severity grid。


### Open Question C4 — query time

模型看到视频到哪个时间点？

例如 Prediction：

- collision 前固定帧数截止；
- 还是随机 query time？

需要控制避免 position 直接泄漏 TTC。

### Resolved — 2026-10-04

主 State query time 固定在 Context boundary：

$$
t_c=\frac{8}{24}=\frac13\text{s}
$$

State 定义为：

$$
S_c=S(t_c^-)
$$

Prediction 统一从同一 Context 结束状态出发。

random query time 不属于 v1 主设计；若以后研究 temporal robustness，可作为 future extension。


## D. Probe Architecture

### Open Question D1 — attentive pooling query 数

候选：1 / 4 / 8 learned queries。

### Open Question D2 — attention heads / hidden width

应固定跨 layer/model，或用相同比例映射？

### Open Question D3 — relational transformer depth

当前倾向 1 block；是否需要 2-block robustness？

### Open Question D4 — Mean-MLP width

当前建议固定 512 hidden，需要 pilot 确认不过窄/不过强。

### Open Question D5 — object-mask pooled state control

哪些 State target 必须同时报告 oracle-mask pooled 版本？

## E. Layer / Token Sampling

### Open Question E1 — exact normalized-depth grid

24-layer、32-layer、40-layer、LLM 28-layer 的统一归一化点需要最终列 config。

### Open Question E2 — VLM LLM token positions

最终至少保留哪些：

- mean visual token；
- selected visual tokens；
- final question token；
- first answer token；
- EOS / decision token？

### Open Question E3 — V-JEPA predictor token semantics

predictor 的 context / mask / target token 在不同 eval setup 中如何对应，需要结合官方 code 确定 probe interface。

## F. Causal Intervention

### Open Question F1 — 第一个 intervention variable

优先候选：

1. barrier normal \(n\)；
2. velocity \(v\)。

barrier orientation 的 counterfactual 可能最直观。

### Resolved — 2026-10-04

v1 第一批 causal intervention variables 固定为：

$$
\boxed{\theta_{v^-}}
$$

与：

$$
\boxed{\phi}
$$

即：

- pre-collision / context-end velocity direction；
- barrier axis direction。

第一批 State → Prediction 主 endpoint：

$$
\boxed{\theta_{v^+}}
$$

第一批 State → Judgment endpoints：

- valid / invalid；
- reflection violation severity。

TTC、contact point、Contact Prediction 不作为第一版 direction intervention 的主要 causal endpoint。

### Open Question F2 — interchange pairing algorithm

需要匹配：

- 尽可能相同 appearance；
- 相似非目标 state；
- 仅目标变量明显不同；
- source activation 在自然 manifold 上。

### Resolved for v1 primary pairs — 2026-10-04

主 matched-pair 构造由 [[05_Benchmark_and_Experiment_Design]] 规定。

### Velocity-direction pair

保持：

- $p_c$ 相同；
- barrier 相同；
- speed 相同；
- appearance 尽量相同；

主要只改变：

$$
\theta_{v^-}
$$

### Barrier-direction pair

保持：

- $p_c$ 相同；
- $v_c$ 相同；
- barrier center / length / width 相同；
- appearance 尽量相同；

主要只改变：

$$
\phi
$$

所有 source / base / counterfactual 必须通过 intervention-safe geometry qualification。

需要强调：matched pair 只能减少 confound；low-level interchange 是否真正实现 high-level `do` 仍需要 downstream counterfactual consistency 来验证。


### Open Question F3 — selectivity metric

干预某变量后，除了目标 output 改变，还要测：

- 其他 state readout 是否保持；
- unrelated task 是否保持；
- activation norm / distribution shift。

### Open Question F4 — 什么时候触发 DAS

建议预设标准，例如：

- linear subspace probe 好但 intervention 无 selectivity；或
- nonlinear probe 明显强、linear 持续弱。

## G. Model Scope

### Open Question G1 — Qwen2.5-VL 具体 checkpoint

7B-Instruct 是否最合适？是否需要 base/non-instruct 对照？

### Open Question G2 — V-JEPA2 checkpoint

ViT-L 的具体官方 checkpoint / preprocessing / clip length 配置。

### Open Question G3 — robustness model 顺序

当前建议：

1. ViT-g key experiments；
2. V-JEPA2.1-L；
3. LLaVA-OneVision；
4. Qwen3-VL。

需要根据主结果调整。

## H. External Data

### Open Question H1 — 投稿前是否必须 external sanity check

当前判断：不是科学上必须。

若 reviewer-generalization 风险过高，可加一个极轻 external trend validation。

## I. Performance Improvement

### Open Question I1 — 是否增加 interpretability-guided performance method

候选：

- layer fusion；
- selective LoRA；
- shortcut suppression。

只有当主结果自然指向其中一个时才做。

## J. Publication / Narrative

### Open Question J1 — 最终标题

当前工作标题：

> From State to Prediction and Judgment: Dissecting Physical Reasoning across Predictive Video Models and Video-Language Models

可能投稿前需要根据实际结果缩短。

### Open Question J2 — 最终 contribution emphasis

取决于结果可能更偏：

- architecture organization；
- computational accessibility；
- causal algorithm recovery；
- VLM vs predictive model contrast。
