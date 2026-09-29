# Observed synthetic review

[English](observed-review-summary.md) | [简体中文](observed-review-summary.zh-CN.md)

This is a human-written summary of one actual two-stage run on 2026-09-29, not a verbatim transcript. The reviewed subject was the deliberately flawed fictional importer in [packet.md](packet.md), not the toolkit's source.

The scanner identified two core failures: a crash after appending an item but before recording progress permits duplicate insertion on retry; duplicate IDs inside the same batch are both inserted because progress is updated only after the loop.

The reviewer confirmed both traces, noted that the happy-path test cannot catch either failure, and added a scope-dependent concern about passing a one-shot iterator as `items`. The reviewer recommended idempotent storage or a suitable transaction, plus crash-injection and same-batch duplicate tests.

The wrapper verified both responses against exported model/session metadata and saved them with `REVIEW_COMPLETED`. This establishes one successful review execution and useful findings on a small synthetic example. It does not prove a general defect-detection rate.

See [VALIDATION.md](../VALIDATION.md) for the environment, model IDs, hashes, and limits. Full raw session exports and logs are not part of this public example.
