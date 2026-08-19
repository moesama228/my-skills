# My Skills

面向 AI coding agents 的个人技能仓库。这里的技能遵循 [Agent Skills](https://agentskills.io/) 目录约定，尽量保持小型、可组合，并在技能自身的 `SKILL.md` 中声明适用场景和环境要求。

## 安装

本仓库使用 [`npx skills`](https://www.skills.sh/docs/cli) 安装技能。运行以下命令后，安装器会发现仓库中的技能，并让你选择目标技能和 coding agent：

```bash
npx skills@latest add moesama228/my-skills
```

先查看可安装的技能：

```bash
npx skills@latest add moesama228/my-skills --list
```

安装指定技能：

```bash
npx skills@latest add moesama228/my-skills --skill skill-creator-portable
```

默认安装到当前项目。需要在用户级目录中使用时，添加 `--global`：

```bash
npx skills@latest add moesama228/my-skills --global
```

## 分类

| 分类 | 内容 |
| --- | --- |
| [Engineering](skills/engineering/) | 软件设计、实现、测试、调试和交付工作流 |
| [Frontend](skills/frontend/) | Web 界面、交互、可访问性和浏览器工作流 |
| [Playground](skills/playground/) | 轻量、趣味、探索性以及尚未形成独立领域的技能 |
| [Productivity](skills/productivity/) | 跨项目的通用效率和元工作流 |

Playground 是孵化分类，不是永久的杂项分类。当其中至少 3 个技能形成具有相同主要用户目标的稳定技能簇时，该技能簇必须迁移到新的独立分类。完整判定和迁移要求见 [Playground graduation](AGENTS.md#playground-graduation)。

## 可用技能

### Engineering

- [`commit-plus`](skills/engineering/commit-plus/SKILL.md)：安全、原子化地检查、分组并提交 Git 变更，同时保留范围外的本地工作。

### Playground

- [`fun-fact`](skills/playground/fun-fact/SKILL.md)：介绍一条简短可靠、附带原理解释的冷知识，并在用户需要时查证来源。

### Productivity

- [`markdown-document-export`](skills/productivity/markdown-document-export/SKILL.md)：将 Markdown 导出为精美的 PDF 或 Word 文档，并保留 Mermaid、本地图片和样式。
- [`pdf-toc-links`](skills/productivity/pdf-toc-links/SKILL.md)：为文本型或扫描型 PDF 添加侧边栏书签和可点击的目录页链接。
- [`skill-creator-portable`](skills/productivity/skill-creator-portable/SKILL.md)：创建、更新和审查符合 Agent Skills 规范的可移植技能，并可选择生成 OpenAI 元数据适配层。

## 目录约定

每个可安装技能都是 `skills/<category>/<skill-name>/` 下包含 `SKILL.md` 的独立目录。分类 README 只用于导航，不会被识别为技能。具体兼容性、依赖和许可证以各技能目录中的声明为准。
