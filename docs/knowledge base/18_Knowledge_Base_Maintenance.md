---
title: Knowledge-Base Maintenance
status: Current
updated: 2026-09-12
tags: [maintenance, workflow]
---

# 知识库维护规范

## 1. 核心原则：不覆盖研究历史

本知识库不是一份永远“只展示最新正确答案”的说明书。

研究中非常有价值的信息包括：

- 被后续实验推翻的假设；
- 曾经合理、后来发现有 confound 的设计；
- 暂时因算力/时间搁置的方向；
- negative result；
- failed experiment；
- reviewer / 导师提出但未采用的建议。

因此：

> **除纯粹拼写错误或重复外，不静默删除历史研究判断。**

## 2. 状态标记

统一使用：

- `Current`
- `Tentative`
- `Open Question`
- `Rejected`
- `Superseded`
- `Invalidated`

### Rejected

设计经过分析后明确不作为当前方案，但不一定“科学上错误”。

### Superseded

旧版本被更精确/合理的新版本替代。

### Invalidated

已有实验事实直接证明旧假设不成立。

## 3. 修改理论时怎么写

不要把旧理论直接删掉。

推荐格式：

```markdown
### Earlier formulation
旧说法……

### Problem
后来发现……

### Current formulation
现在采用……

### Status
Superseded, YYYY-MM-DD
```

并同步更新：

- [[11_Decision_Log_and_Idea_Evolution]]；
- 对应当前设计文档。

## 4. 实验结果写入流程

每次重要实验至少保存：

1. Experiment record；
2. Results log；
3. config；
4. git commit；
5. raw metric / CSV / plot path；
6. 初步解释；
7. claim boundary。

不要只保留截图或聊天中的口头结论。

## 5. 周报

建议每周创建：

```text
logs/weekly/YYYY-WXX.md
```

使用 [[15_Weekly_Log_Template]]。

周报重点不是流水账，而是：

- 本周解决了哪个不确定性；
- 哪个假设被支持/削弱；
- 哪些工程 blocker；
- 设计是否发生变化。

## 6. 文件职责

### 当前设计

写在：

- `01–09`。

### 研究历史

写在：

- [[11_Decision_Log_and_Idea_Evolution]]。

### 文献

写在：

- [[10_Related_Work]]；
- [[19_Benchmark_Literature_Notes]]；
- [[20_VJEPA_Downstream_Survey]]。

### 未解决问题

写在：

- [[13_Open_Questions_and_TODO]]。

### 风险与 claim 边界

写在：

- [[12_Risks_Failure_Modes_and_Claim_Discipline]]。

## 7. Codex 更新规范

Codex 在服务器执行任务时，如果发现：

- 代码实现与文档假设冲突；
- checkpoint architecture 与文档数字不同；
- benchmark 存在 shortcut；
- 实验出现重大 negative result；

应当：

1. 不擅自重写理论；
2. 创建实验记录；
3. 在对应文档标记 discrepancy；
4. 在 [[13_Open_Questions_and_TODO]] 新增问题；
5. 等研究者确认后更新 `Current` 设计。

## 8. 文件命名

核心知识库文件保持稳定编号和英文 slug，原因：

- Git 链接稳定；
- Obsidian wikilink 稳定；
- Codex 易引用；
- 后续论文/代码注释可直接链接。

正文使用中文，技术术语保留常见英文。

## 9. Git 建议

重大设计变化单独 commit，例如：

```text
docs: revise judgment theory from sequential to architecture-conditioned
```

实验结果：

```text
exp: add VJEPA-L velocity layer sweep results
```

不要把大量代码重构和理论文档改写混在同一个 commit。

## 10. Source of Truth

本仓库文档应逐步成为该项目的 single source of truth。

聊天、会议、白板中的关键结论最终都应沉淀到这里，否则后续：

- ChatGPT；
- Codex；
- 合作者；
- 未来的自己

都会因上下文不一致而重复讨论或误用旧设计。
