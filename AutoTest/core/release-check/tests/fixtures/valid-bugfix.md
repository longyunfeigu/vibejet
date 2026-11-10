---
type: bugfix
source_branch: fix/sample-bug_bob_20261020
author: bob
services: [backend]
safety: writes-test-data
risk: high
regression: true
tools: [api]
---
## 背景与目标
保存流程时偶发 500。

## 入口
流程编辑接口。

## 怎么算对
1. [P0] 连续保存 20 次，状态码全部为 200。

## 绝不能坏的底线
已有流程内容不变。

## 前置数据与清理
用 e2e- 前缀建一个流程，测完删除。

## 容易误判的地方
保存后列表刷新有延迟，不算失败。

## 本次改动
保存时改为先释放数据库连接再调用 LLM。

## 复现条件
保存期间 LLM 调用耗时超过 30 秒。

## 旧版本的错误现象
接口返回 500，日志出现 QueuePool limit reached。

## 修复后应有的现象
接口返回 200，日志不再出现 QueuePool limit reached。

## 根因
LLM 调用期间一直占着数据库连接。
