# 合成审阅材料：可安全重试的导入

[English](packet.md) | [简体中文](packet.zh-CN.md)

整个例子完全虚构，不含生产数据或凭据。这是英文示例的中文译本；已有真实运行记录对应英文原版。

## 要求

每个 ID 最多导入一次，包括进程崩溃或重试之后。同一批次中的重复 ID 不应生成重复记录。store 与 state 表示分别持久化的数据结构，两者之间没有事务。

## 代码：importer.py

```python
def import_batch(items, store, state):
    for item in items:
        if item["id"] not in state["done"]:
            store.append(item)
    state["done"].update(item["id"] for item in items)
```

## 已有合成测试：test_importer.py

```python
def test_repeat_after_success():
    store = []
    state = {"done": set()}
    items = [{"id": "item-001", "value": "example"}]
    import_batch(items, store, state)
    import_batch(items, store, state)
    assert len(store) == 1
```

这个正常流程测试仅作为上下文，没有模拟崩溃。示例使用列表表示 store，以说明持久化边界，并非真实数据库实现。

## 请评估

说明代码和测试是否足以满足要求。给出具体失败顺序，并建议最小的验证或修正。区分确认的问题和对存储行为的假设。
