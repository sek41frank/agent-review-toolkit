# agent-review-toolkit

[English](README.md) | 简体中文

把需求、代码和测试结果交给另一位 AI 检查，并留下可以核对的审阅记录。

例如，AI 写好了一个导入程序，普通测试已经通过。你还想检查“运行中断后再执行，会不会重复导入”，就可以把要求、代码和测试放进材料包，用这个工具组织一次复核。

## 它怎样工作

1. 你提供一份 Markdown 材料包。
2. 第一位 AI 找出可能的问题。
3. 第二位 AI 阅读原始材料，并参考第一位的意见，说明哪些问题成立、哪些不成立，以及有没有遗漏。
4. 工具检查执行记录，保存两份意见和结果索引。
5. 你阅读意见，决定是否修改代码和补测试。

第二位 AI 会看到第一位的意见，因此这不是盲审。`REVIEW_COMPLETED` 表示两份回复通过了身份和一致性检查，不能作为“代码已经批准”或“意见一定正确”的结论。

## 准备条件

- Python 3.10+，无额外 Python 依赖。
- macOS 或 Linux。首版未支持 Windows。
- OpenCode **v2**，并已经通过 OpenCode 保存可用的模型服务认证。
- 你有权使用所选模型。真实运行会把材料发送给对应服务，可能产生费用。

首版使用 [OpenCode v2 命令接口](https://opencode.ai/v2/docs/cli/commands/)。v1 会在预检时被拒绝。预检通过只证明版本和命令参数匹配，模型权限和真实回复需要另行运行验证。

## 第一次使用

下载或克隆仓库，在仓库目录打开终端。

```sh
python3 review.py --check-cli
cp models.example.json models.local.json
```

修改 `models.local.json`，填入自己在 OpenCode 中可用的模型。可以使用 `provider/model`，也可以加上推理档位，写成 `provider/model#variant`。示例里的模型名称仅为配置例子，不保证每个账号都能调用；可以先运行 `opencode models` 查看可用模型。

```sh
mkdir -p runs
python3 review.py --config models.local.json \
  --packet examples/packet.md --output runs/example-001
```

如果找不到 OpenCode，在命令末尾补上 `--cli /path/to/opencode`。每次运行使用新的输出目录；父目录需要存在，输出路径的上级目录不能是符号链接。

运行后打开 `runs/example-001/REVIEW.md`，再看 `scanner.text.md` 和 `reviewer.text.md`。

示例是完全虚构的导入程序。[预期问题说明](examples/expected-findings.zh-CN.md)由人编写，帮助理解要检查什么，不是假装生成的 AI 审阅结果。

## 怎样准备自己的材料

复制 [examples/packet.md](examples/packet.md)，替换其中三部分：

- **要求**：程序应该做什么，失败、重试时应该怎样处理。
- **代码**：与问题相关的代码或改动，最好带文件名。
- **测试和限制**：已经测过什么，还有哪些情况没有证据。

首版材料包上限为 128 KiB。审阅者只依据提供的材料作判断，代码之外的上下文需要由你补充。

## 结果是什么意思

| 情况 | 含义 |
| --- | --- |
| `REVIEW_COMPLETED` | 两阶段执行与回复的身份、一致性检查通过；仍需阅读和判断意见 |
| `FAILED` | 本次复核未完成，查看 `result.json` 的失败原因 |
| 预检或参数错误 | 终端显示错误；可能尚未生成结果目录 |
| 审阅者没有发现问题 | 只表示这次提供材料下没有提出问题，不能证明代码没有缺陷 |

`result.json` 保存请求与实际报告的模型、session、CLI 版本和服务报告的成本字段。未显式指定 variant 时，只匹配 provider/model，并记录观察到的 variant；不声称验证了你未指定的推理档位。这些是对 CLI 导出记录的核验，不是对服务后台模型身份的独立证明。

## 运行边界

工具为两个审阅代理设置禁止工具调用的权限，并检查导出里是否出现工具调用。它还限制子进程继承的环境变量。**这不是操作系统沙箱**：OpenCode 仍以你的用户运行，可使用自身的配置、认证、日志和会话存储。审阅过程使用新的输出目录作为工作目录。

只通过 shell 环境变量提供的 API key 不会传入子进程；请使用 OpenCode 保存的本机认证。没有自动脱敏，材料会发送给你配置的服务。输出包含原始材料、日志和完整回复，可能含有敏感内容；`runs/` 已加入 Git 忽略规则。

`--timeout` 默认为每个子进程 180 秒，不是整个复核的总时限。失败不会自动重试。工具负责产生意见与记录，后续修改代码、采纳意见和发布由你决定。

退出码：`0` 表示执行核验完成，`1` 表示已记录的复核失败，`2` 表示参数、配置、单独预检或输出准备错误。

## 离线测试

```sh
python3 -m unittest discover -s tests -v
```

测试使用模拟 CLI，不调用模型，也不需要 API key。真实试用的验证范围另记在 [VALIDATION.md](VALIDATION.zh-CN.md)。

首版为实验性 v0.1.0 候选，采用 [MIT 许可证](LICENSE)。

## 配套文档与语言

[中文材料包](examples/packet.zh-CN.md) · [实际审阅摘要](examples/observed-review-summary.zh-CN.md) · [参与贡献](CONTRIBUTING.zh-CN.md) · [更新记录](CHANGELOG.zh-CN.md)

使用说明、贡献指南、更新记录、验证记录和示例解释均提供中英文对应版本，可通过页面顶部链接切换。英文材料原版保持不变，以保留已记录的哈希；中文译本未另行调用真实模型验证。CLI 参数、JSON 字段、状态码和生成报告的标题保留英文，其含义在两种语言的文档中解释。模型回复语言取决于你的材料与指令。
