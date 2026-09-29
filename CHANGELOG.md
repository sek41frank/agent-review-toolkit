# Changelog

[English](CHANGELOG.md) | [简体中文](CHANGELOG.zh-CN.md)

## 0.1.0 — candidate

- Extract a two-stage review workflow into a dependency-free Python CLI.
- Configure scanner/reviewer models and resolve OpenCode from PATH or `--cli`.
- Preflight OpenCode v2 capabilities before model requests.
- Record packet hashes, model/session metadata, response consistency, and explicit failure states.
- Clean up preflight process groups on timeout/interruption and avoid missing-artifact links in failed reports.
- Save both reviewer responses and a readable result index.
- Include a synthetic retry-safety example, bilingual instructions, and offline regression tests.

See VALIDATION.md for the actual validation scope of this candidate.
