# Codex-Memory-Plugin

Current template version: `v0.1.5`

中文 / Chinese first. English summary is below.

一个**不是把“记忆”写成零散规则，而是把经验写成可检索、可审查、可版本化预测模型**的本地系统。

它和很多“记忆功能”最大的差别，不是“能不能记住一条东西”，而是**记住的对象是什么**：

- 不是只记一条“应该怎么做”的规则。
- 而是记一个更像模型的关系：
  如果在某种条件下这样做，更可能发生什么；
  如果换一种做法，又更可能发生什么。
- 这意味着一条记忆可以不只是单结论，还可以有分支、备选结果、对比路径。

换句话说，这个项目的核心不是“存规则”，而是**建模**。

## 入口 / Start here

如果你是普通使用者：

- 你要找的是一个**本地、文件型、可建模用户与系统自身行为**的记忆框架
- 先看下面的“为什么这和普通记忆不一样”
- 然后直接跳到“快速开始”

如果你是开发者：

- 先读 `PROJECT_SPEC.md`
- 再看 `.agents/skills/local-kb-retrieve/`
- 最后看 `local_kb/` 和 `tests/`

## 为什么这和普通记忆不一样

- **它记录的是预测，不只是建议。**
  一条卡片不是“以后应该这样”，而是“在这个场景里，这个动作更可能带来这个结果”。
- **它允许 alternatives。**
  也就是说，不只是“正确答案”，还可以明确保留“如果走另一条路径，会更可能变差到哪里”。
- **它会对用户建模。**
  不是抽象的人格标签，而是“这个用户在什么任务里，更可能偏好什么结构、讨厌什么遗漏、如何判断结果是否清晰”。
- **它也会对自己建模。**
  也就是对 Codex / runtime 本身的行为建模：在什么提示、流程、工具条件下，更可能犯什么错，修正后又会改善什么。
- **它是文件型、可审查、可版本化的。**
  你可以在 Git 里看到每条结构化经验如何被记录、修改、对比、发布。

## 这套系统实际在建模什么

这里至少有三类模型：

1. **任务模型**
   例如：面对某类仓库发布、调试、汇报任务时，什么做法更可能成功。
2. **用户模型**
   例如：某个用户在 GitHub README 上更可能希望先看到版本号、用户入口、中文优先结构，而不是先看开发者说明。
3. **自我 / 运行时模型**
   例如：当 KB postflight 只是隐含要求时，Codex 更可能漏掉经验回写；当它被显式纳入 done 条件时，回写更稳定。

这也是这个项目很有吸引力的地方：
它不是只说“我记住了一条偏好”，而是把**用户怎么反应**、**系统自己怎么犯错**、**改完之后为什么更好**，都放进同一个建模框架里。

## 一个最小例子

下面这个例子不是“规则清单”，而是一条真正带分支的模型：

```yaml
id: pref-release-presentation
type: preference
scope: private
domain_path:
  - repository
  - github-publishing
  - readme-presentation
if:
  notes: When preparing a public GitHub page for this user.
action:
  description: Hide version visibility and place developer setup before the user entry.
predict:
  expected_result: Review friction is more likely and the page is less likely to feel clear.
  alternatives:
    - when: If version is visible and the user entry appears early
      result: The page is easier for this user to scan and approve.
use:
  guidance: Keep version visible, surface the user entry early, and preserve the chosen bilingual structure.
```

重点不是 YAML 本身，而是这条结构表达的是：

- 条件是什么
- 动作是什么
- 结果更可能怎样
- 换一种做法时又会怎样

这就是“模型”，而不是单条规则。

## 这也是为什么它能处理“修正”而不只是“结论”

很多系统最后只会留下一个成功结论。

这个仓库现在开始更强调**对比证据**（contrastive evidence）：

- 原来走了一条较弱路径，结果更差
- 后来改成另一条路径，结果更好
- 两边都被保留下来

这样未来的卡片不只会说“推荐这样做”，还可以明确说：

- 如果重复旧路径，更可能发生什么坏结果
- 如果采用修正路径，更可能得到什么改善

这让记忆从“静态建议”更接近“可操作模型”。

## 快速开始

先安装：

```bash
python scripts/install_codex_kb.py --json
python scripts/install_codex_kb.py --check --json
```

做一次检索：

```bash
python .agents/skills/local-kb-retrieve/scripts/kb_search.py \
  --path-hint "repository/github-publishing/readme-presentation" \
  --query "prepare a public GitHub page for this user" \
  --top-k 5
```

## 这个公开仓库里放什么，不放什么

这个仓库公开发布的是：

- 工作流
- schema
- skills
- 检索、记录、maintenance 工具
- 安全可公开的示例结构

默认**不应该**顺手把这些真实运行内容一起公开：

- 你的 live private cards
- 你的真实 `kb/history`
- 你的真实 `kb/candidates`
- 任何用户特定、敏感、未确认可公开的经验

## Repository layout

```text
.
├─ AGENTS.md
├─ PROJECT_SPEC.md
├─ README.md
├─ VERSION
├─ docs/
├─ .agents/
├─ kb/
├─ local_kb/
├─ schemas/
├─ scripts/
├─ templates/
└─ tests/
```

## English Summary

Codex-Memory-Plugin is a local, file-based predictive memory system for Codex.

Its core idea is not “store one more rule,” but “store an explicit model”:

- under what condition
- taking what action
- makes what result more likely
- and what alternative path would likely lead to a different result

That is why this project is different from flat rule memory:

- it treats memory as **predictive modeling**
- it supports **alternative branches**, not only one canonical answer
- it can model the **user**
- it can also model **Codex / runtime behavior itself**
- it stays **inspectable, versioned, and Git-reviewable**

In practice, this means one repository can accumulate:

- task models
- user-specific preference models
- runtime/self-behavior models
- contrastive evidence about weaker paths versus revised stronger paths

If you want to understand the architecture, start with `PROJECT_SPEC.md`.
If you want to use it, start with `scripts/install_codex_kb.py`.
