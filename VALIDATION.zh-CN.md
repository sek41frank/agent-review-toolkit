# 候选版验证记录

[English](VALIDATION.md) | [简体中文](VALIDATION.zh-CN.md)

本文将实际观察结果与预期兼容范围分开记录。

## 环境与 CLI 预检

- 日期：2026-09-29。
- 平台：macOS；Python 3.12.14。
- 实际 CLI 输出：`opencode v2.0.19`。
- 候选版 `--check-cli` 成功，所需 run/export 参数齐全。

## 离线测试

本地运行 `python3 -B -m unittest discover -s tests -v`：**23 项测试通过**。

测试使用模拟 CLI 和合成输入，覆盖两阶段成功、session/模型/文本不匹配、回复缺失或不完整、工具调用拒绝、超时、输出保留、配置解析、可选 variant、相对 CLI 路径、v1/不兼容 CLI 拒绝、FIFO 拒绝、中断清理、预检后代进程清理和失败报告链接完整性。

独立本地审阅还使用真实本地进程复测了 FIFO 和中断边界：非普通材料/配置文件被及时拒绝，Ctrl-C 后模拟模型的子进程被终止。该次本地代码审阅没有遗留高优先级问题。

## 真实合成材料试用

候选版使用 `examples/packet.md` 调用了真实配置服务，完成两个阶段。

- 最终状态：`REVIEW_COMPLETED`。
- 第一阶段请求与导出元数据：`deepseek/deepseek-flash#low`。
- 第二阶段请求与导出元数据：`opencode/claude-sonnet-5#medium`。
- 两阶段均通过模型/session/文本检查，状态为 `VERIFIED`。
- 材料 SHA-256：`3cdd0ca87155671264a2c95992adf74ced1d8bc63f569cf3d0f1db3982e3d399`。
- 当时工具源码 SHA-256：`a03037ca999d5cd6b9f7af07d7d74fcd247510bf596c459467a84650105aadd3`。
- 两份回复均发现崩溃重试和批内重复 ID 问题，见 [实际审阅摘要](examples/observed-review-summary.zh-CN.md)。

这仅是一次实际运行，不保证模型持续可用或每次发现相同问题。模型身份来自 CLI 导出的元数据。原始会话导出和日志未纳入公开候选。

## 验证限制

- GitHub CI 尚未运行；计划中的 macOS/Linux 与 Python 3.10/3.12 组合尚未全面验证。
- 未真实测试其他 OpenCode v2 补丁版本和模型服务商。
- 上述真实试用发生在最终预检/报告修复之前。修复后通过了 23 项离线测试及新的真实 CLI 预检，没有再次调用模型。
- 中文示例为英文示例的配套译本，未另行进行真实模型试用。

## 已授权的源码交叉复核

源码材料包由 `deepseek/deepseek-flash#low` 和 `opencode/claude-sonnet-5#medium` 只读审阅。两者的导出身份和回复均通过核验，工具调用被禁用。材料包 SHA-256：`bef08696c3e5f38eda67ab761e34003be5a3808363ee294ac58f2bc459b762d4`。

随后修复了两项采纳问题：预检超时/中断应终止整个进程组，失败索引不应链接不存在的文件。新增了三项回归测试。关于 POSIX `subprocess.run` 无限通信的说法未被证实，实际确认的问题是后代进程清理；其他推测未作为已确认缺陷。

最终源码 SHA-256：`15fd39c1672b62a9639f509ce0daa5bb5dc986bce9ad1b78961a1958700649e6`。外部模型审阅的是修复前版本，最终修复已通过独立本地增量复核，含三个新增测试。审阅完成不等于自动批准发布。
