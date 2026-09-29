# Contributing

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

Keep changes focused on the explicit-packet, two-stage OpenCode v2 workflow.

Run `python3 -B -m unittest discover -s tests -v` before proposing a change. Tests must use synthetic data and a fake CLI. Include a regression test for a behavior or failure mode you change.

Describe the problem, the resulting behavior, and validation scope in your pull request. Real-provider checks are optional and must be reported separately from offline tests. Do not attach credentials, personal packets, session exports, or logs containing private data.

New CLI/schema support must validate reported model/session identity and fail clearly when compatibility is unknown. Do not silently fall back to another model or convert incomplete runs into successful results.
