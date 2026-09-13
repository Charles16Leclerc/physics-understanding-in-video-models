---
title: Motivation and Research Questions
status: Current
updated: 2026-09-12
tags: [motivation, research-questions]
---

# 研究动机与科学问题

## 1. “模型怎样理解物理”为什么太模糊

本研究仍然围绕“模型怎样理解物理”这个大问题进行展开。而研究问题的第一步，就是搞清楚你在问什么。

“理解物理”这个概念有许多截然不同的表现形式。而现有工作在研究“模型是否/怎样理解物理”这个问题时，常常把多种不同的形式混在一起，例如：

- violation-of-expectation (VoE)；
- video QA accuracy；
- future contact prediction；
- trajectory / velocity decoding；
- generated-video physical plausibility；
- ……

这些任务是截然不同的。

一个模型可能极其准确地编码速度，却不会判断某条轨迹是否违反物理规律；反过来，一个 VLM 也可能只从粗粒度视觉证据和语言世界知识出发，正确回答“这段视频合理吗”，而没有形成 metrically accurate 的 velocity / acceleration state。

所以我们做的第一件事是把常见的“物理理解”概念拆分为以下三点：

- 对当前物理状态进行表征；
- 预测未来物理状态或事件；
- 判断已经观察到的事件是否符合物理规律。

也即，本项目将 “physical understanding” 操作化为三个主要目标：

$$
\boxed{\text{Physical State}},\qquad
\boxed{\text{Physical Prediction}},\qquad
\boxed{\text{Physical Judgment}}.
$$

在这个三分法的框架下，我们就能更加清晰地研究”模型怎样理解物理“这个问题了。

对于这样的三分法选取的详细思想，详见：[[03_Theory_State_Prediction_Judgment|理论框架：State、Prediction 与 Judgment]] 。

因此第一个研究动机是理论范式上的：

> **把杂糅的”物理理解“分解为state、prediction、judgement。**

## 2.研究”模型怎样理解物理“，就要研究内部因果链条

人工神经网络是一个黑箱，我们永远不知道它内部是怎样思考的——直到可解释性方法出现。

如果仅靠黑箱外的 input-output 分析，不探究模型内部的表征模式与思维流程，就不可能真正回答”模型怎样理解物理“。所以此时应用 mechanistic interpretability 的研究方法研究模型在物理理解任务下的内部可解释特征就显得至关重要了。

而纵观可解释性领域，已经被涉足的工作包括：

- 对 VJEPA 在物理场景下的内部表征做提取；
- 对 VLM 做内部表征提取 + 因果干预（非物理场景）；
- 对特定物理场景的 toy model 做内部表征提取 + 因果干预。

可以发现，这三类工作的思想交汇指出了一个未曾涉足的交点：

> **在物理场景下对大规模预训练模型—— VJEPA 和 VLM ——做内部表征提取 + 因果干预。**

这可能是”模型怎样理解物理“这个科学问题在研究方法论上最佳的投影了。这便是第二个研究动机——基于研究方法论的动机。

## 3. 三分法详解

### 3.1 Physical State：现在发生了什么？

候选 target：

- 位置 \(p\)；
- 速度 \(v\)；
- speed；
- heading；
- barrier geometry / normal；
- contact state；
- object identity。

这些量最接近视觉 encoder 对当前观测世界应该表征的内容。

### 3.2 Physical Prediction：接下来会发生什么？

候选 target：

- 是否会在 horizon \(H\) 内发生碰撞；
- time-to-collision \(\tau\)；
- post-collision velocity \(v^+\)；
- 选定的 future position control。

主 prediction task 应尽量满足：

> **不是当前 state 的简单线性函数，而是确实需要 relational / nonlinear computation。**

### 3.3 Physical Judgment：刚刚发生的事情是否应该发生？

候选 target：

- valid / invalid transition；
- violation severity；
- 少量 counterfactual / causal physical question。

重要：Judgment 不被定义成 universal `State → Prediction → Judgment` 链的最后一步。它是独立的 functional target，其与 Prediction 的关系应由架构和实验决定。

## 4. 为什么比较 V-JEPA 与 VLM

本项目并不是简单进行“模型排行榜式比较”。V-JEPA 与 VLM 被选中，是因为它们的训练目标与结构本身对 physical computation 提供了不同先验。

### V-JEPA

- 以 predictive latent objective 训练；
- 具有显式 encoder / predictor；
- `State → Prediction` 有天然架构意义；
- Judgment 不是 native task。

### VLM

- 视觉预训练 + multimodal alignment + caption/QA + instruction tuning；
- 通常没有专门的 latent future predictor；
- 有大型 LLM backbone，带来强 world knowledge 与逻辑推理能力；
- Prediction 与 Judgment 都可视作 general video understanding / VQA 下的 task-conditioned readout。

总得来说，根据两类模型的架构和训练机制理解，我们的理论预测是：

**VJEPA：**
$$
\text{current state}\rightarrow\text{future prediction}.
$$

而 judgement 不清楚。

**VLM：**

$$
\text{visual state}
\rightarrow
\begin{cases}
\text{prediction}\\
\text{judgment}
\end{cases}
$$

事实上，在想法产生的过程中，我们并不是先想出物理理解三分法，再去找的VJEPA/VLM。相反，三分法×两类模型的想法其实是同步慢慢完善得到的。三分法的选取很大程度上也受到了VJEPA和VLM的模型架构、训练范式的启发。

因此：

> **V-JEPA × VLM 与 State × Prediction × Judgment 不是两个独立维度机械相乘，而是同一个 architecture-conditioned scientific design。**

## 5. 核心研究问题（RQs）

### RQ1：State representation 在哪里、以什么形式出现？

- V-JEPA encoder 是否比 VLM vision tower 更早、更低 readout cost 地表征速度、方向、几何等量？
- 不同 state variable 是否具有不同 layerwise emergence？

### RQ2：V-JEPA predictor 是否把 state 中隐式的未来关系“编译”为更显式的 future representation？

核心测试范式：

若 ground-truth state 上：

$$
\text{Linear}(s) \ll \text{MLP}(s)
$$

但模型中：

$$
\text{Linear}(h_E) \ll \text{Linear}(h_P),
$$

则可支持：predictor 将原本需要额外 nonlinear computation 的关系转化为更 explicit 的 representation。

### RQ3：VLM 中 Prediction 与 Judgment 是顺序计算还是并行 task-conditioned reasoning？

可能出现：

- 二者在不同 LLM depth 才可读；
- 二者依赖不同 token 类型；
- 二者共享 vision evidence，但在 LLM 中分叉；
- Judgment 甚至比 Prediction 更早/更容易出现。

### RQ4：Judgment 是否存在统一的 “physical validity” representation？

不同 violation family 是否共享同一子空间/同一 circuit？

也可能得到反结论：

$$
S_{\text{wall-validity}} \perp S_{\text{other-validity}}
$$

即所谓 “physical plausibility” 并不是统一概念，而是一组 task-specific consistency mechanism。

### RQ5：probe 出来的物理变量是否真的被模型使用？

区分：

$$
\text{decodable} \neq \text{causally used}.
$$

通过 activation patching / interchange intervention 检验 state variable 与 downstream prediction/judgment 的因果关系。

### RQ6：不同模型家族是否形成系统性不同的 physical organization？

期望不是简单比较“谁分数高”，而是得到 architecture-level 结构结论，例如：

- V-JEPA：predictive hierarchy；
- VLM：视觉 evidence 到多个 task-conditioned reasoning 分支。

## 6. 为什么这个项目不依赖单一正结果

这是一个观察型 + 机制型科学问题，而不是“提出新模块必须涨点”的方法论文。

不同可能结果都能区分竞争解释：

- 预测在 encoder 已经 explicit → predictive compilation 提前发生；
- predictor 没让未来变量更 explicit → 原始 V-JEPA predictor 可能更多承担 masked latent completion 而非显式 forward simulation；
- VLM vision tower state 很弱但 judgment 强 → LLM prior / coarse cues 很重要；
- Judgment task 之间完全不共享 representation → 不存在统一 physical-validity axis；
- 线性 probe 能读但干预无效 → representation 有信息但不走该 causal path。

因此项目具有较强的 negative-result robustness。

## 7. 不作为当前核心科学问题的内容

### Rejected / Deferred：谁是最好的 physics evaluator？

早期想法是直接比较 V-JEPA-based evaluator 与 VLM evaluator，并尝试做 V-JEPA–LLM。

当前不作为核心：

- 没有合适的开源完整 V-JEPA–LLM checkpoint；
- 自己做 video-language alignment 成本太高；
- 会把研究问题从“内部物理组织”拉向“评测器性能工程”。

### Deferred：监督微调前后 physics structure 如何变化

主实验首先研究 pretrained backbone 本身，因此默认冻结 backbone，只训练 readout。

若后续出现明确现象（例如 SFT 只是让已有 physics signal 对齐到 judgment 输出），再作为 follow-up。
