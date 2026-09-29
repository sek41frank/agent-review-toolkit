# 参与贡献

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

改动应聚焦于显式材料包、两阶段 OpenCode v2 审阅流程。

提交改动前运行 `python3 -B -m unittest discover -s tests -v`。测试应使用合成数据和模拟 CLI。对改变的行为或失败场景添加回归测试。

在 PR 中说明问题、修改后的行为和验证范围。真实模型服务验证是可选项，应与离线测试分开报告。不要附带凭据、私人材料包、会话导出或包含私人数据的日志。

新增 CLI 或导出格式支持时，必须核验报告的模型和 session 身份；兼容性未知时明确失败。不得静默切换模型，或把未完成的运行记为成功。
