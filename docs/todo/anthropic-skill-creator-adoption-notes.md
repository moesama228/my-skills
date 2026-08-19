# Anthropic `skill-creator` 可选优化备忘录

本文总结从 [Anthropic 官方 `skill-creator`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator/skills/skill-creator) 中值得选择性吸收到 [`skill-creator-portable`](../../skills/productivity/skill-creator-portable/SKILL.md) 的设计。目标不是复刻一套 Claude 专用评测平台，而是在不破坏 Agent Skills 可移植性的前提下补充可验证、可分发的工程能力。

## 取舍原则

- 通用核心不依赖某个厂商的 CLI、模型标识、安装目录、权限模型或产品 UI。
- 结构校验与行为评测保持分离：前者确定格式是否合规，后者观察技能是否真的改善结果。
- 评测、打包和报告能力均为可选分支，不要求每个技能携带开发期文件。
- 固定次数和阈值只作为可配置默认值，不升级为规范要求。
- 优先增加小而确定的接口，再考虑自动优化和可视化等高成本能力。

## 当前状态

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| 独立前向测试 | 已吸收 | 对复杂或高风险技能，使用独立 subagent 执行真实请求；隔离预期答案、疑似缺陷和作者结论，并只根据观察到的失败做定点修改。 |
| 结构校验 | 已具备 | `validate_skill.py` 检查 Agent Skills frontmatter、目录名、质量警告和本地链接。 |
| 工具链单元测试 | 已具备 | 当前测试覆盖初始化、OpenAI 可选适配和校验器行为。 |
| 标准化行为评测 | 尚未实现 | 没有统一 eval schema、基线对照 runner、触发测试或报告格式。 |
| `.skill` 打包 | 尚未实现 | 当前仓库通过 `npx skills` 从 GitHub 安装，没有额外的归档产物。 |

## 建议选择性吸收

### 1. 可选的 `evals/evals.json` 约定

为需要行为验证的技能定义一个厂商无关的测试集格式。该目录只在技能确实需要可重复评测时创建，不属于 Agent Skills 规范的必需结构。

建议覆盖的信息包括：

- 稳定的 case ID 和真实用户请求。
- 执行所需的 fixture 或原始输入。
- 可观察的成功条件或断言，而不是期望输出全文。
- 是否预期触发该技能，供 discovery 测试使用。
- 权限、副作用、超时和成本边界。

schema 不应包含 Claude、Codex 或其他厂商的模型 ID、会话参数和工具调用格式。

### 2. 可插拔的 Skill/基线对照评测接口

对同一个请求和同一组输入分别运行：

1. 可使用目标 Skill 的执行者。
2. 无法使用目标 Skill 的基线执行者。

比较实际输出、生成产物和可观察不变量，判断 Skill 是否带来真实增益。独立 subagent 可以作为常见执行机制，但 runner 接口只描述输入、输出和隔离要求，不绑定具体的 subagent API。

建议记录：

- 每个断言是否通过以及支持判断的证据。
- 运行耗时、重试和失败原因。
- token 或成本指标（环境能够可靠提供时）。
- 无法自动判定、需要人工审阅的差异。

第一版只需支持外部命令或 agent adapter；不要直接内置某个厂商的调用命令。

### 3. 独立的触发测试指南

当触发评测形成稳定工作流后，将详细方法放入 `references/evaluation.md`，只在创建测试集、诊断误触发或优化 `description` 时读取。

指南应包含：

- 正例：用户确实需要该 Skill，但措辞和上下文有变化。
- 近邻负例：请求与 Skill 相似，但不应触发。
- 重复运行：识别偶然命中和高方差结果。
- 训练集/保留集拆分：避免针对已知 prompt 过拟合。
- 同时观察漏触发与误触发，而不是只提高召回率。
- 只根据失败类别修改 `description`，并用保留集复验。

Anthropic 使用的样本数、重复次数和迭代上限可以作为经验默认值，但不应写成 portable Skill 的硬性规则。

### 4. 通用 `.skill` 打包脚本

增加类似以下接口的确定性工具：

```bash
python scripts/package_skill.py <skill-directory> [--output <directory>]
```

脚本应：

- 打包前运行结构校验并在错误时停止。
- 生成以技能目录为根的 ZIP 格式 `.skill` 文件。
- 排除缓存、临时文件和构建产物。
- 拒绝意外覆盖已有归档，除非用户显式请求。
- 对开发期的 `evals/`、`tests/` 是否进入归档采用明确、可配置的策略。
- 保留所有运行时引用的 scripts、references、assets 和厂商扩展。

`.skill` 是可选分发格式，不应被描述成 Agent Skills 规范的合规要求，也不取代仓库当前的 `npx skills` 安装方式。

## 暂不优先吸收

以下能力有价值，但在缺少稳定 eval schema 和 runner 之前会显著增加复杂度：

- grader、comparator、analyzer 等专用评测 Agent。
- HTML 人工审阅器和实时报告页面。
- 自动重写 `description` 的多轮优化循环。
- benchmark 聚合、方差分析和历史趋势报告。
- 自动选择模型或根据产品环境切换执行流程。

它们应建立在真实使用需求和已积累的评测数据之上，而不是作为初始工具链的默认组成部分。

## 明确不吸收

- `claude` CLI、Claude 模型 ID 或 Claude 专属命令。
- Claude Code、Claude.ai、Cowork 等产品分支。
- 厂商安装路径、临时目录和 UI 操作约定。
- 对所有技能修改强制运行昂贵的行为评测。
- 将固定样本数、运行次数或阈值解释成规范要求。
- 为每个技能预先创建空的 `evals/`、报告或占位文件。

## 推荐实施顺序

1. **评测约定**：设计最小 `evals/evals.json` schema，并用手工或 subagent 流程验证两个真实技能。
2. **触发指南**：把稳定下来的 discovery 测试方法写入按需加载的 `references/evaluation.md`。
3. **通用打包**：实现 `package_skill.py` 及覆盖成功、非法技能、缓存排除和覆盖保护的测试。
4. **Runner 接口**：实现可插拔 Skill/基线执行器，先支持外部命令，再按需求增加厂商 adapter。
5. **报告与优化**：只有在前述数据结构稳定后，再评估 HTML viewer、grader 和自动 description 优化。

每一步都应保持可独立交付：未启用评测或打包能力时，`skill-creator-portable` 仍然可以只依靠 `SKILL.md` 和结构校验完成通用的技能创建、更新与审查。
