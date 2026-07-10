# UI 执行闸（vj-work）

> 出口闸条目（A/B 轨、富度 R1–R4、工艺 C1–C5）以 `.claude/rules/frontend.md` 为唯一真相源，
> 本文件不复述；间距数值以 `docs/project/DESIGN.md` §Spacing Hierarchy 为准。
> 这里只承载 vj-work 侧的执行协议：参考图批量闸、独立视觉审计、cross-screen polish。
> 设计背景：规则本就精确，翻车洞在"实现者自评 + 没人看像素"
> （实证见 memory `frontend-taste-gate-not-checklist`）。

## 参考图批量前置闸（Phase 2，一次处理全部屏，fast/strict 均不豁免）

1. 从 task-index lanes + task docs 收集全部 UI class = critical 的屏清单。
2. 逐屏登记参考图来源：已批准参考图 `docs/reference/research/designs/{epic-id}/{screen-id}.png`，
   或继承屏型金标准 `docs/reference/research/designs/golden/`（`vj-design-md-matcher` Phase 4.5
   产出）+ `DESIGN.md` §Reference Skeletons。
3. 两者皆无的屏：用该屏 Screen Contract + `DESIGN.md` token 渲染一次性 HTML 并截图作为候选。
   参考图一律 HTML 直出，**禁止生图模型画 UI**（实测：文字糊、方向坍缩、AI 模板味）。
4. 全部候选**一次性提交审批**（批图是秒级操作）；批准后把路径登记进各 task 的派发字段。
   执行中不再逐屏 STOP 等人。
5. 范围控制：仅 front-of-house 屏 + 每个屏型的第一张屏需新出参考图；同屏型后续屏直接继承
   金标准，不重复出图、不重复审批。
6. 降级阶梯（记入 `_ledger.md`，不静默跳过参考图闸，也不因此阻塞非 UI task）：
   - 渲染可用但审批不可达 → 用未批候选图作对照基准继续，标"假设待审批 + Confidence"，
     收尾报告列出待批清单。
   - 渲染不可用但有屏型金标准 → 金标准 + `DESIGN.md` §Reference Skeletons 文字契约。
   - 渲染不可用且金标准也缺 → 仅文字契约执行，标"假设待审批 + Confidence: L"并在收尾
     报告显式列出该屏；front-of-house 屏同时降 UI 预期为"结构正确优先"，不在无参照物时
     追求品牌表达。
   - 该屏同时命中 strict trigger 且无人值守 → strict fail closed 优先（见 SKILL.md
     Phase 2），不走降级。
7. 本 epic 新批准的参考图作为同屏型后续屏的对照基准；晋升为跨 epic 屏型金标准
   （`golden/`）仍归 `vj-design-md-matcher`，本 skill 不写 golden 目录。

## 独立视觉审计（标 done / commit 前）

适用范围：每个整屏交付（frontend-composition task）的屏——无论屏型是 front-of-house 还是
operational——以及其他 UI class = critical 的 task。UI class = functional 的局部改动走
targeted browser check，不需独立审计。

判定权独立于实现（与 frontend.md A5/B5 同源）：

1. 必须存在真实桌面截图（实现 subagent return contract 里的 artifact 路径）。
2. pass/fail 由**非实现该屏的一方**产出，二选一：
   - orchestrator 亲自 Read 截图——"只 ingest 小结、不读 transcript"的上下文卫生原则
     **不豁免看 UI 截图**，截图是轻量 artifact，必须看；
   - 派独立 visual-audit subagent：输入仅 = 截图 + 该屏 frontend.md 对应轨 checklist +
     一张同类密集参考（存在已批参考图时升级为"实现截图 ↔ 参考图并排对照"）；
     **不给实现代码、不给实现 subagent 的小结**。
3. 输出带**截图实测值**的 pass/fail：首屏最大空容器高度占比、页框 padding、最小区块 gap；
   有参考图时偏差清单按"参考图里有而实现里没有/走样"逐项列——审计从主观判美丑降级为
   客观找图差。
4. 实现 subagent 自写 "passes" 不构成过闸；无对照的主观 pass 不接受。
   不过闸不得标该 Screen done、不得 commit 该屏。
5. admin/后台屏几乎都是 operational：不调 `design-taste-frontend`（对后台 out-of-scope），
   craft 真相源 = `frontend-dev-guidelines/resources/dense-ui-craft.md`，出口走 B 轨客观硬线。

## Cross-screen visual polish pass（前端 Epic，E2E polish wave 内、收尾前）

动机：各屏由不同 subagent 持最小上下文实现，taste 与规格会跨屏漂移（页框 padding、页头规格、
区块 gap、字号档、同类组件多套实现、accent 用量）；单屏闸查不出跨屏不一致。

- 触发：UI critical/functional 屏 ≥3 → 派独立 audit subagent 做专门 pass；
  ≤2 屏 → orchestrator 在逐屏独立审计时顺手核对跨屏一致性，不另派。
- 输入：全部屏桌面截图（复用各屏出口闸证据，不重截）+ `DESIGN.md` §Spacing Hierarchy /
  字阶表 + `dense-ui-craft.md` 反模式速查。
- 输出漂移清单：跨屏页框 padding 是否一致、页头规格是否一致、字号档是否超标、
  同类组件是否多套实现、accent 是否超预算——逐项给 Screen + 文件定位。
- 修复：统一修（优先抽共享组件/常量，**禁止逐屏手调出第三种规格**）；修完重截受影响屏、
  过对应轨闸；漂移清单与修复结果记入收尾变更叙事。
