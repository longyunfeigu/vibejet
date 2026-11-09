---
type: feature
source_branch: feature/sample-feature_alice_20261020
author: alice
services: [backend]
safety: readonly
risk: low
regression: true
tools: [browser]
---
## 背景与目标
让管理员在列表页看到每个 agent 的最近通话时间。

## 入口
Agent 列表页。

## 怎么算对
1. [P0] 列表接口返回的每一项都有字段 last_call_at，值为 ISO 时间或 null。

## 绝不能坏的底线
列表分页数量不变。

## 前置数据与清理
无需造数据，只读。

## 容易误判的地方
从未打过电话的 agent 显示「-」是正确的。

## 本次改动
列表接口新增 last_call_at 字段，前端新增一列。
