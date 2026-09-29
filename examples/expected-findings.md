# Hand-written teaching notes

[English](expected-findings.md) | [简体中文](expected-findings.zh-CN.md)

These are expected findings written for the synthetic example. They are not an AI response and do not prove that any specific model detected them.

1. **Crash after append, before progress update:** the item is persisted in `store`, but its ID is absent from `state["done"]`. Retrying appends it again. The happy-path test never exercises this window.
2. **Duplicate ID within one batch:** `state["done"]` is updated only after the loop, so two previously unseen entries with the same ID are both appended.
3. **A local in-memory set is not a complete crash fix:** updating a temporary set during the loop addresses same-batch duplication, but cannot make two separate persistent stores atomic. A storage-level unique ID / idempotent upsert, or a suitable transaction, is needed for the stated crash requirement.

A useful reviewer should explain these sequences and suggest focused tests. It should not claim to have executed the code or accessed a real database.
