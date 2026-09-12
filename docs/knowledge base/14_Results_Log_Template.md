---
title: Results Log Template
status: Template
updated: 2026-09-12
tags: [template, results]
---

# 结果记录模板

> 建议每个“可复用、会进入论文或影响设计”的结果都单独记录，而不是只留在 TensorBoard / WandB / stdout 中。

## Result ID

`RESULT-YYYYMMDD-XXX`

## 对应实验

- Experiment ID：
- Git commit：
- Config：
- Checkpoint：
- Dataset version：

## 科学问题

本结果试图回答什么？

## 设置

- Model：
- Module / layer：
- Target：
- Readout：
- Train split：
- Eval split：
- Seed：
- Metrics：

## 主要结果

| 条件 | Metric 1 | Metric 2 | 备注 |
|---|---:|---:|---|
|  |  |  |  |

## 图 / 文件

- Figure：
- CSV/JSON：
- Checkpoint / probe：
- Activation cache：

## 结果解释

### 直接证据支持什么

只写当前证据真正能支持的 claim。

### 不能支持什么

例如：

- decodable 不代表 causal use；
- pooled probe 失败不代表 full tokens 无信息。

## 与当前理论的关系

- 支持：
- 冲突：
- 无法区分：

## Follow-up

- [ ] 重复 seed
- [ ] shortcut control
- [ ] token-aware probe
- [ ] causal intervention
- [ ] robustness model

## 是否需要更新知识库

- [[03_Theory_State_Prediction_Judgment]]：是 / 否
- [[11_Decision_Log_and_Idea_Evolution]]：是 / 否
- [[13_Open_Questions_and_TODO]]：是 / 否
