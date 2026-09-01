# pi-council

把一个任务**并行**派发给多个不同大模型「会诊」，收集各路独立观点，汇总成一份 Markdown 报告。全程**只读**，专为头脑风暴、方案研讨、方案评审、代码审核设计。

## 为什么用它

- **群智群策**：一路一个模型、一个独立进程，意见互不污染——同一家族的模型容易趋同，不同厂商的模型才能真的吵起来
- **绝对只读**：每路被硬性限制在 `read / grep / find / ls` 四个工具内，写文件、`bash` 全部被禁，说评审就只做评审
- **面向 Agent 设计**：结构化产出（状态表含 thinking 档位 + 观点全文 + token/成本），调用方 agent 拿到结果即可继续综合汇报

## 前置条件

- 已安装并认证 [pi CLI](https://pi.dev)：`npm install -g @earendil-works/pi-coding-agent`
- Python 3.8+（纯标准库，macOS / Linux / Windows 均可）

## 快速开始

**首次使用**——配置你的模型阵容（先用 `pi --list-models` 看看本机有什么）：

```bash
python3 scripts/council.py "这个缓存设计方案有什么问题？" \
  --models deepseek/deepseek-v4-pro,litellm/m3/glm-5.3,openai-codex/gpt-5.6-sol --save
```

**之后**——阵容已保存，直接派题：

```bash
python3 scripts/council.py "帮我评审这个重构思路" -m review
```

读完 stdout 里的 `output_path=` 指向的 `result.md`，就是全部结果。

## 常用参数

| 参数 | 作用 | 默认 |
| --- | --- | --- |
| `-m <模式>` | `discuss` / `brainstorm` / `review` / `code-review` | `discuss` |
| `-f <文件>` | 焦点文件嵌入 prompt（最多 4 个，评审代码必用） | 无 |
| `-w <目录>` | 各路的工作目录，`-f` 相对路径基于此 | 当前目录 |
| `--models a,b,c` | 单次覆盖阵容（`--save` 则另存为默认） | 已存阵容 |
| `--thinking <档位>` | 思考深度 `off`~`max`，成本/质量主杠杆 | `high` |
| `--synthesize <模型>` | 收齐后追加一路「主席」做总结 | 不启用 |
| `--timeout <秒>` | 单路超时；慢思考模型建议调到 1500 | 600 |
| `--events` | 保留原始事件流（默认只给失败路保留） | 关 |

## 它是怎么工作的

```text
你的任务原文
   │  主 agent 最小编辑塑形：保留你的措辞，只补 lane 拿不到的上下文
   ▼
你确认：任务文本 + 派发阵容（确认前不派发）
   ▼
council.py ──┬─ pi --model A ──┐
             ├─ pi --model B ──┼─ 并行、只读、互不感知
             └─ pi --model C ──┘
   │
   ▼
result.md（状态表含 thinking 档位 + 各路观点全文 + 可选主席总结）
```

每路实际执行：`pi -p --mode json --tools read,grep,find,ls --no-session --no-approve --model <模型>`，prompt 走 stdin。

## 安全边界（如实说明）

- 工具白名单限制的是「能做什么」，不是「能读什么」——lane 仍可读你账号能读的任何文件
- 任务、焦点文件和 lane 读到的内容会**发给阵容里的每一家供应商**，涉密代码请勿上车
- 不写会话、不信任项目级配置；详细论证见 [SKILL.md](SKILL.md)

## 产物与成本

- 每次运行落在 `<state>/runs/run-<时间戳>/`：每路完成时立即写入 `<model>.md`，全部结束后再生成 `result.md`；当日志显示某路 `done` / `FAILED` 时，对应 Markdown 已落盘；最终状态表记录各路及可选主席模型使用的 thinking 档位，便于审计
- 原始事件流默认不落盘（`--events` 开启，失败路始终保留）
- 运行结束 stderr 会汇报累计占用（`N runs, X MB`），觉得多了直接删 `runs/` 即可
- 成本 = N 路 token 之和，状态表按每路全轮次累计；3~4 路是性价比甜区

## 测试

```bash
python3 -m unittest discover -s tests
```

`SKILL.md` 是给 agent 的完整契约（冷启动、输出契约、故障处理）；本 README 面向人。
