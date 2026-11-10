---
type: bugfix                  # feature | bugfix
source_branch: fix/xxx        # 分支全名
author: your-handle            # git 作者名（小写、无空格）
services: [backend]           # 服务键 backend | frontend | grpc，见 STANDARD.md 第 3 节
safety: readonly              # readonly | writes-test-data | costly
risk: high                    # high | medium | low
regression: false             # 可省略，默认 false；true = 以后每次验证都做回归
tools: [browser]              # _shared/tools.md 里的工具名
# cost_estimate: 3 calls      # safety 为 costly 时必填
# requires: [service:grpc]   # 环境可能没有的依赖（目前只有 service:<名>），见 STANDARD.md 1.15
# supersedes: 2026-10/feature/someone-old.md   # 你有意改掉其行为的旧指导
---

## 背景与目标
<!-- 为谁解决什么问题？改之前怎样，改之后怎样？ -->

## 入口
<!-- AI 从哪里开始：页面路径、接口、配置项。不写环境名、地址和账号。
     每个接口、日志、页面元素后面紧跟源分支代码的 `文件:行`（从仓库根目录写起），一行列多个接口的每个都要附（1.13）。
     用 AI 写的，先调 skill `writing-release-check`。 -->

## 怎么算对
<!-- 可观测的信号：字段值、状态码、数据库记录、日志关键字、带阈值的数值。
     至少一个信号要能被程序判断。不要写「功能正常」。
     写成列表，每条开头标级别（见 STANDARD.md 1.4）：
     [P0] 基本功能有没有实现 / bug 有没有修好  [P1] 主要场景  [P2] 不阻塞主流程的小问题，失败只记录
     不写「不适用」，也不要求复现旧 bug 或切回旧版本（STANDARD.md 1.11、1.12）；写到的接口、日志、页面元素附 `文件:行`（1.13）。
     [P0] 必须拿来就能跑：只用测试账号、不停服务、不等流量、不长时间观察、产线上做也安全（1.5）。
1. [P0] …
2. [P1] …
-->

## 绝不能坏的底线
<!-- 相邻功能、必须保持不变的老行为。每条不标级别按 [P1] 算；只需记录的在开头标 [P2]。 -->

## 前置数据与清理
<!-- 需要什么数据、怎么造（优先接口，名字带 e2e- 前缀）、怎么清。「只读，无需数据」也是合格答案。_shared/fixtures.md 里的常驻对象（e2e-fixture-…）可以直接按名字引用，不用建也不用清，但不能改它。 -->

## 容易误判的地方
<!-- 看着像 bug 其实不是的现象，以及反过来的。 -->

## 本次改动
<!-- 这个分支改了什么，新行为应该是什么样。 -->

## 深度提示
<!-- 可选：你认为最容易出问题的边界、并发、多语言。 -->

## 旧版本的错误现象
<!-- 旧版本上能看到的错误：状态码、日志行、错误的值。 -->

## 修复后应有的现象
<!-- 修复后能看到什么，写具体信号。 -->

## 根因
<!-- 一句话。帮 AI 推断还有哪些相邻场景受同一根因影响。 -->
