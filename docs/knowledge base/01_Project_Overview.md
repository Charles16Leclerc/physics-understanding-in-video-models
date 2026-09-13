---
title: 研究提案总纲
status: Current
updated: 2026-09-13
tags: [overview, proposal, motivation, theory, experiment-design]
---

# 研究提案总纲

> 本文档不是一个简短的 project summary，而是一份用于长期维护、对外讲述和制作 PPT 的**研究提案总纲**。它不替代各个细分设计文档，而是严格依据当前知识库中已经形成的详细设计，系统回答：**为什么这个问题值得研究、为什么我们的理论划分与模型选择不是 arbitrary、为什么采用 mechanistic interpretability、实验怎样逐层回答科学问题、各项设计为什么这样做，以及什么样的结果能够构成有效科学结论。**
>
> 细节分别见：[[02_Motivation_and_Research_Questions]]、[[03_Theory_State_Prediction_Judgment]]、[[04_Model_Scope_and_Architectures]]、[[05_Benchmark_and_Dataset_Design]]、[[06_Probe_and_Readout_Design]]、[[07_Mechanistic_Interpretability_and_Causal_Intervention]]、[[08_Experiment_Plan_and_Evaluation]]、[[09_Engineering_Compute_and_Code_Architecture]]、[[10_Related_Work]]、[[12_Risks_Failure_Modes_and_Claim_Discipline]]。

## 工作标题

**From State to Prediction and Judgment: Dissecting Physical Reasoning across Predictive Video Models and Video-Language Models**

标题使用 `and` 而不是早期的 `to ... to ...`，是为了避免暗示一个对所有模型都成立的 universal causal chain。当前理论立场是：

> **State、Prediction、Judgment 是三个需要被分别研究的功能对象；不同训练范式与架构可能以截然不同的方式组织它们。**

---

# 1. 研究从哪里开始：先把“模型怎样理解物理”这个问题问清楚

本研究围绕的大问题仍然是：

> **大规模预训练模型究竟怎样理解物理？**

这个问题看起来直观，但如果不先分析“physical understanding”究竟指什么，后续实验很容易变成若干彼此缺少理论联系的 benchmark、probe 和可视化结果。

现有工作在讨论“模型是否理解物理”时，常用的观测形式包括：

- trajectory / velocity / acceleration decoding；
- future contact prediction；
- violation-of-expectation；
- video QA；
- physical plausibility judgment；
- generated-video physical fidelity；
- 其他物理属性或下游任务。

这些任务并不等价。一个模型可能非常准确地编码位置和速度，却无法判断一个已经发生的反射过程是否违反物理；反过来，一个 VLM 也可能借助粗粒度视觉证据和 LLM 中已有的世界知识，正确回答“这段视频是否合理”，却没有形成 metrically precise 的 velocity / acceleration state。

因此，本项目形成过程中的第一步就是：

> **把“物理理解”这个混合概念拆解为若干可实验、功能上有差别、又与现实模型结构相对应的对象。**

这构成了本研究第一根理论支柱。

# 2. 理论支柱一：Physical State / Prediction / Judgment 三分法

本项目将“physical understanding”操作化为三个主要功能目标：

$$
\boxed{\text{Physical State}},\qquad
\boxed{\text{Physical Prediction}},\qquad
\boxed{\text{Physical Judgment}}.
$$

## 2.1 Physical State：当前世界是什么状态？

State 指模型从已经观察到的视频中形成的、描述当前物理世界的表示。候选变量包括位置 $p$、速度 $v$、speed、heading、barrier geometry / normal、object / contact state 等。

它回答的是：**What is happening now?**

State 是所有模型最自然的共同起点，因为无论模型之后用于预测还是问答，都首先需要从视觉输入中提取某种可用的世界表示。

## 2.2 Physical Prediction：接下来会发生什么？

Prediction 指模型根据当前状态形成未来事件或未来状态的能力。候选 target 包括是否在 horizon $H$ 内碰撞、time-to-collision $\tau$、post-collision velocity $v^+$、contact point，以及部分 future-position control。

这里有一个重要限制：主 Prediction task 不能只是当前 state 的简单线性函数。例如

$$
x_{t+\Delta t}=x_t+v_t\Delta t
$$

如果 encoder 已经线性表示 $x_t,v_t$，future position 自然也可能线性可读，这并不能证明模型内部真的执行了额外的 prediction computation。因此主 prediction target 应尽量要求：

$$
\boxed{\text{non-trivial relational / nonlinear computation}}
$$

## 2.3 Physical Judgment：已经发生的事情是否符合物理？

Judgment 指模型对**已经观察到的动态过程**进行物理合理性判断。候选 target 包括 valid / invalid transition、violation severity、violation type，以及少量 counterfactual / causal judgment。

它回答的是：**Should this have happened?**

Judgment 被纳入研究，一方面因为它是检验“模型懂不懂物理”最直观的行为形式之一；另一方面，当前大量视频物理保真度 benchmark 与 evaluator 正是使用 VLM 完成 physical plausibility judgment，因此它具有直接现实意义。

# 3. 为什么三分法选择不是 arbitrary：它与两类模型的原生功能共同形成

这个三分法不是先凭直觉切成三块，再任意找两个模型来验证。它与 V-JEPA 和 VLM 的训练目标、模块划分和真实使用方式是同步形成的。

> **V-JEPA × VLM 与 State × Prediction × Judgment 不是两个独立维度机械相乘，而是同一个 architecture-conditioned scientific design。**

## 3.1 V-JEPA：State → Prediction 有强结构先验

V-JEPA 的基本结构是：

$$
X\xrightarrow{E}Z\xrightarrow{P}\hat Z.
$$

Encoder 将视觉输入组织成 latent representation；Predictor 在 predictive latent objective 下，对 masked / target latent 做条件预测。所以 State 与 Prediction 并不是我们强行赋予 V-JEPA 的功能标签，而是其模型结构和训练范式天然提供的两个分析对象。

Encoder 中我们有理由预期形成 object state、position、velocity、geometry、contact / motion cues。但不能把 encoder 理解成“人工设计的最小物理状态估计器”，因为它本身在 predictive objective 下训练，future-relevant relation 完全可能提前被“编译”或线性化到 encoder representation 中。

因此，如果 future contact 在 encoder 中已经能被简单 readout 读取，这并不是理论失败，而可能说明 predictive pretraining 使当前 representation 本身变得 anticipatory / future-oriented。

原始 V-JEPA2 predictor 更准确地应描述为 **latent conditional inference / masked latent completion module**，而不是直接称为“物理定律 reasoner”。但它仍然是最自然的地方去测试 future-related quantity 是否变得更 explicit、state relation 是否被转换成更易读的 future representation，以及某个 prediction target 所需 readout class 是否降低。

Judgment 并不是 V-JEPA 的 native training objective，因此没有理论理由预设 judgment 必须在 predictor 后部出现、一定晚于 prediction，或所有 violation task 共享统一的 physical-validity axis。

因此对 V-JEPA，当前最合理的理论结构是：

$$
\boxed{\text{State}\rightarrow\text{Prediction}}
$$

具有较强 architecture-conditioned 先验，而 Judgment 的位置和实现方式很难在实验之前做判断。

## 3.2 VLM：Prediction 与 Judgment 更可能是并列的 task-conditioned reasoning

现代支持视频的 VLM 大致是：

$$
\text{video}
\rightarrow
\text{vision tower}
\rightarrow
\text{merger/projector}
\rightarrow
\text{LLM}
\rightarrow
\text{text output}.
$$

它通常没有一个独立模块被专门训练成 $z_t\rightarrow z_{t+1}$。因此对 VLM 来说，Prediction 与 Judgment 都可以只是“根据视觉内容回答某类问题”的不同 task-conditioned readout。

更合理的结构先验是：

$$
\boxed{
\text{visual state}
\rightarrow
\begin{cases}
\text{prediction}\\
\text{judgment}
\end{cases}
}
$$

甚至 Judgment 可能比 Prediction 更符合 VLM 原生 QA 形式。此外，VLM 拥有巨大的语言与世界知识先验，因此可能通过

$$
\text{coarse visual evidence}+\text{textual/world prior}\rightarrow\text{judgment}
$$

得到正确答案，而无需在 vision tower 中形成精确的 metrical dynamics state。

因此，VLM 最终回答正确，并不自动等价于其视觉前端精确理解了动力学。

# 4. 理论支柱二：要回答“模型怎样理解物理”，就必须进入模型内部

三分法解决的是“我们的问题到底在问什么？”。接下来必须回答“怎样才能真正回答它？”

如果只观察黑箱 input-output performance，我们最多知道模型做没做对，却无法回答：

- 它是否真的形成了 velocity / geometry state；
- prediction 是从哪些 state representation 中计算出来的；
- judgment 是从 dynamics evidence 得到的，还是主要依赖语言先验；
- 一个 probe 出来的变量是否真的被 downstream computation 使用；
- V-JEPA 与 VLM 是否采用不同内部组织。

因此，仅靠 benchmark accuracy 不足以回答“模型怎样理解物理”。这自然引出了本研究的第二根方法论支柱：

> **在物理场景下，对大规模预训练模型进行内部表征提取，并进一步通过因果干预研究这些表征是否被实际使用。**

现有相关工作已经分别建立了几块方法学地基：

- 在物理场景下对 V-JEPA / video encoder 的内部表征做 layerwise probing；
- 对 VLM 做内部表征与因果机制分析（非物理场景）；
- 在受控物理 toy model 上，通过 probing + intervention 反推内部算法。

因此，本项目的 motivation 不是“别人没做过，所以做一个空白实验”，而是：

1. 先从第一性问题出发，把 physical understanding 拆清楚；
2. 再根据模型训练范式形成 architecture-conditioned hypotheses；
3. 最后选择 mechanistic interpretability 作为能够直接回答内部组织与因果链条的研究方法。

# 5. 核心科学问题

## RQ1：State representation 在哪里、以什么形式出现？

研究 position / velocity / heading / geometry 等量在哪些层可读、是否存在 layerwise emergence，以及 V-JEPA encoder 与 VLM vision tower 的 state accessibility 是否存在系统差异。

## RQ2：V-JEPA predictor 是否把隐式 state relation 转换为更显式的 future representation？

如果对 simulator 真 state （之后会详解）：

$$
\text{Linear}(s)\ll\text{MLP}(s),
$$

而模型内部出现：

$$
\text{Linear}(h_E)\ll\text{Linear}(h_P),
$$

则可支持 predictor 将原本需要额外 nonlinear computation 的关系转换成了更 explicit 的 future representation。

## RQ3：VLM 中 Prediction 与 Judgment 是否共享顺序结构？

不预设答案。可能是 prediction 先、judgment 先、同层并行、依赖不同 token / pathway，或共享 vision evidence 后在 LLM 中分叉。

## RQ4：Probe 出来的变量是否真的被模型使用？

必须区分：

$$
\boxed{\text{decodable}\neq\text{causally used}}
$$

因此第二阶段将使用 activation patching、ablation、matched interchange intervention 等方法。

## RQ5：两类模型是否形成系统性不同的 physical organization？

最终目标不是得出“谁更懂物理”的排行榜式结论，而是得到 architecture-level scientific finding。

# 6. 第一部分实验：Functional / Computational Accessibility Map

研究空间是：

$$
\text{model family}
\times
\text{functional target}
\times
\text{network location}
\times
\text{readout class}.
$$

核心问题是：

> **什么物理信息在什么位置变得可访问？为了从当前 representation 中恢复它，还需要多少 aggregation 或额外 computation？**

当前四类 readout：

1. **Mean-Linear**：pooled representation 中是否已经线性显式；
2. **Mean-MLP**：pooled summary 中是否需要 static nonlinear mapping；
3. **Attentive Pooling**：信息是否在局部 token 中，只是 mean pooling 注意不到；
4. **Relational Transformer**：即使找到 relevant tokens，是否仍需要额外 token-token relation computation。

这把两个常被混淆的问题拆开：

$$
\boxed{\text{Aggregation}}
\qquad\text{vs}\qquad
\boxed{\text{Computation}}.
$$

- Aggregation 对应 mean pooled vs attentive 的分别；
- Computation 对应 linear vs MLP 、attentive pooling vs transformer 的分别。

Layer sweep 采用：cheap pooled probe 全层跑；token-aware probe 使用预先规定的 normalized depth grid；若出现明显分数 layerwise transition，再局部 refinement。

# 7. 第二部分实验：Mechanistic Microscope

第二部分不是另起一个 toy story，而是对第一部分同一个物理世界的“显微镜式”机制分析。

例如 Ball–Wall 场景有已知计算图：

$$
(p,v,n,c)
\rightarrow
\text{relative geometry}
\rightarrow
\tau_{collision}
\rightarrow
v^+
\rightarrow
\text{prediction/judgment}.
$$

证据层级分为：

1. **Decodability**：probe 证明变量 accessible；
2. **Causal Localization**：token / region / head patching 与 ablation 定位 causal site；
3. **Causal Semantics**：matched interchange intervention 检验内部 counterfactual 是否与 physics simulator counterfactual 一致；
4. **Circuit**：进一步做 writer / reader / path patching。

最重要的目标不是“patch 后 logit 变了”，而是：

$$
\boxed{
\text{internal counterfactual}
\approx
\text{physics simulator counterfactual}
}
$$

因为我们有解析 simulator，可以精确计算 $do(n=n_B)$ 或 $do(v=v_B)$ 后的正确反事实结果。这使得 **Interchange Intervention Accuracy** 成为可能。

# 8. 为什么必须自建统一 Benchmark

数据集本身是 mechanistic diagnosis 的实验仪器，而不是普通工程配套。

主原则：

> **One World, Multiple Queries.**

同一个 latent physical trajectory 同时产生 State、Prediction、Judgment、counterfactual labels 和多种 visual render。

这样避免三个任务来自三个完全不同 benchmark 时，被 scene complexity、camera、dataset size、label entropy、shortcut 等 confound 淹没。

主 benchmark 的构造理念：

> **physically narrow, causally and visually broad**

即物理规律简单统一，但 initial condition、geometry、velocity、counterfactual relation、appearance、semantic skin 足够丰富。

当前主系统：

$$
\boxed{\text{single moving ball/disk/puck + fixed finite barrier}}
$$

采用平面 2D 解析、event-based dynamics。选择它是因为：
- GT intermediate 简单而精确；
- nonlinear relational prediction 易构造；
- matched counterfactual 清楚；
- 因果 intervention 有明确高层语义；
- 而且很重要地，初状态微小改变不会导致结果的巨大改变（反例：Ball-Ball），对模型预测很友好。

# 9. Judgment 的关键：Matched Physical Violations

Invalid case 不能简单是“向上运动”“特别快”“某种颜色”，否则 probe 会走 shortcut。

正确反射：

$$
v^+_{good}=v^--2(v^-\cdot n)n.
$$

Bad case 使用另一个合法 normal $n'$ 生成：

$$
v^+_{bad}=v^--2(v^-\cdot n')n',
$$

但画面仍显示 $n$。

目标是让单变量 marginals 近似匹配：

$$
P(v^+|good)\approx P(v^+|bad),\quad
P(n|good)\approx P(n|bad),\quad
P(v^-|good)\approx P(v^-|bad),
$$

真正错误只存在于 $(v^-,n,v^+)$ 的条件关系中。

# 10. 渲染设计：控制语义先验与重力歧义

如果图像只是“木纹 + 圆 + 线”，模型可能无法判断这是俯视水平桌面还是正视竖直平面，因此不能公平要求它判断 image-plane 中是否应该有重力。

当前计划使用明确俯视语义的多个 render family：

- billiards-like overhead table；
- air-hockey-like table；
- 显示完整桌面边界的 lab/tabletop surface。

同一 latent physics 跨多个 semantic skin 渲染，目的不是普通数据增强，而是检验 physics organization 是否跨 world semantics 稳定。

Canonical 是固定、简单、自然的 overhead tabletop；Diverse 改变 scene family、surface、object skin、barrier material、mild lighting。Mechanistic Stage 直接使用 Canonical 子集，保证：

$$
D_{mech}\subset D_{broad}.
$$

# 11. Benchmark Qualification：先验证任务，再跑模型

在 foundation model 进入之前，最好要做：

- split integrity；
- nuisance marginal balance；
- GT-state → target Linear / MLP baseline；
- first/last/random frame、pre-only、post-only judgment shortcut tests；
- full-GT oracle；
- same-physics different-render transfer。

其中最重要的一项是，主 Prediction task 应满足，直接用gt当前状态物理量训练探针：

$$
\text{GT-State Linear}\ll\text{GT-State MLP/Oracle}.
$$

否则它不适合作为“predictor 是否执行了额外关系计算”的诊断任务。

# 12. 当前主模型为什么这样选

## Predictive side：V-JEPA2 ViT-L + native predictor

主开发模型：

- Encoder：约 300M，24 layers，hidden 1024，16 heads；
- Predictor：约 22M，12 layers，hidden 384，12 heads。

选择 V-JEPA2 作为主模型，是因为其 encoder–predictor 结构和 predictive objective 与理论最干净。V-JEPA2.1 当前作为 robustness model，用于测试更强 dense/deep self-supervision 是否改变 state/prediction organization。

## VLM side：Qwen2.5-VL-7B

选择标准不是“只选排行榜最强”，而是：

- 原生视频支持；
- 开源；
- 中间 activation 可访问；
- 能力足够强；
- 4×A800 可现实运行；
- 架构边界相对干净。

分析路径：

$$
\text{Video ViT}\rightarrow\text{Patch Merger}\rightarrow\text{LLM}.
$$

VLM 还必须明确 probe 的 token type，例如 visual-token hidden states、question token、answer / decision position。

# 13. 实验执行顺序

当前推荐：

1. Benchmark qualification；
2. Simulator/render sanity；
3. V-JEPA2 cheap full-depth map；
4. Token-aware probes；
5. Qwen2.5-VL analysis；
6. Architecture comparison；
7. Mechanistic causal microscope；
8. Robustness / scale-up；
9. Optional interpretability-guided improvement。

理由是：先确保 benchmark 成立，再用便宜实验发现结构，最后把最昂贵的 full-token 与 causal analysis 集中到真正值得研究的层和变量上。

# 14. 工程与算力可行性

主实验冻结 pretrained backbone，只训练小型 readout。真正瓶颈是 foundation model forward 与 activation storage，而不是 probe 本身。

因此采用 hybrid strategy：

- Mean-Linear / Mean-MLP：缓存全层 pooled feature；
- Attentive / Relational：只在少量预设层 online forward 或缓存 full tokens；
- Mechanistic subset：约 1k–3k canonical scenes 保存更完整 activation。

4×A800 下的 Must-have 包括 V-JEPA2 ViT-L 全层 pooled probing、predictor 全层 probing、Qwen2.5-VL 主要 layer map、至少一套 token-aware readout、至少一组有完整 control 的 causal intervention。

# 15. 为什么当前不把 SFT / V-JEPA–LLM / 性能提升作为主线

主问题是 pretrained model 本身已经形成怎样的 physical organization。大规模 fine-tuning 会混淆 pretraining 自发结构与 benchmark supervision 新教进去的结构，因此主实验默认冻结 backbone。

早期“V-JEPA dynamics representation + LLM reasoning 可能是更好 physics evaluator”的 intuition 仍然保留，但不自己训练 V-JEPA–LLM，因为 video-language alignment 成本高，而且会把研究问题拉向 evaluator engineering。

性能提升属于 Optional Extension。若主结果自然指向某种机制，可以尝试 layer fusion、selective LoRA / circuit tuning、shortcut suppression，但不为了“必须涨点”硬加新模块。

# 16. Related Work 提供的是方法学地基，而不只是“空白证明”

**Interpreting Physics in Video World Models (ICML 2026)** 证明大型 pretrained video encoder 的 physics representation 可以被逐层 probing 分析。

**Do Video Foundation Models Understand Intuitive Physics? A Layerwise Probing Analysis** 表明 readout 形式对 physics probing 结论影响很大，直接推动本项目区分 aggregation complexity 与 computational complexity。

**How Do Transformers “Do” Physics? Investigating the Simple Harmonic Oscillator** 提供了“probe candidate intermediate + intervene intermediate”的直接方法学原型。

**Othello-GPT / Emergent World Representations** 提供了“decode internal world state + counterfactual edit + observe downstream behavior”的经典范式。

已有 VLM mechanistic interpretability 则证明 visual information 到 LLM task-relevant abstraction 的内部路径可以被分析与干预。

因此，本项目不是因为“没人做过某个组合”才成立，而是把已经成熟的方法汇聚到一个由理论问题自然导出的研究对象上。

# 17. 预期贡献

1. **Architecture-aware functional decomposition**：把 physical understanding 系统化为 State、Prediction、Judgment，但不假设 universal causal chain。
2. **Computational Accessibility Map**：分析 model family × target × location × readout class，并区分 aggregation 与 relational computation。
3. **Architecture-specific physical organization**：解释 predictive pretraining 与 multimodal-language training 如何塑造不同内部组织。
4. **Causal mechanistic validation**：用 matched patching / interchange intervention 检验物理变量是否真的被 downstream computation 使用，并与解析 simulator counterfactual 对齐。

# 18. 为什么负结果也有价值

本项目不是押注一个必须成立的 performance hypothesis，而是在区分多个关于内部组织的竞争解释。

有意义的结果可以包括：

- Prediction 在 encoder 已经 explicit，说明 anticipatory encoding 提前形成；
- predictor 没显著降低 future target 的 readout class，说明其作用可能更接近 masked latent completion；
- VLM vision tower metrical state 弱但 LLM judgment 强；
- Prediction 与 Judgment 在 VLM 中走不同 pathway；
- probe 很强但 causal intervention 无效，说明 decodability 与 causal use 分离。

因此真正关键的是 benchmark 是否干净、实验是否能区分解释、claim 是否与证据等级匹配。

# 19. Claim 纪律

统一原则：

$$
\boxed{
\text{encoded}
\neq
\text{used}
\neq
\text{causally necessary}
\neq
\text{the algorithm}
}
$$

- probe → `encodes / contains / makes accessible`；
- geometry → `organizes / factorizes`；
- ablation / patching → `causally contributes under intervention`；
- interchange → `supports alignment with a high-level causal variable`；
- path/circuit evidence → 才更接近 `computes / transmits / uses`。

这些不是写论文时的措辞修饰，而是整个研究设计成立的必要部分。

# 20. 一句话总结整套研究逻辑

本项目不是从“某个实验没人做过”出发，而是从一个更基本的问题出发：

> **大规模预训练模型究竟怎样理解物理？**

为了把问题问清楚，我们首先把混合的 physical understanding 拆成：

$$
\boxed{\text{State}},\quad
\boxed{\text{Prediction}},\quad
\boxed{\text{Judgment}}.
$$

然后根据 V-JEPA 与 VLM 的训练范式，提出不同的 architecture-conditioned organization hypothesis：V-JEPA 对 `State → Prediction` 有更强结构先验，而 VLM 的 Prediction / Judgment 更可能是从视觉表示出发的并列 task-conditioned reasoning。

为了真正回答“怎样理解”而不仅是“做没做对”，我们进一步采用 mechanistic interpretability：先建立 layer × target × readout 的 accessibility map，再通过 matched activation patching / interchange intervention 检验内部物理变量是否真的参与 downstream computation。

最终希望回答的不是“哪个模型物理 benchmark 分数更高”，而是：

> **不同预训练目标究竟塑造了怎样的内部物理世界表征、未来计算与判断机制。**
