# UI Surfaces

跨 Epic 稳定 Screen 合同（由 vj-epic-plan 在命中 UI delta 时同步；vj-work 的 Screen context 与截图 gate 以本文件为整屏体验真相源）。

## screen-meal-record（introduced by Epic 1，状态：planned）

| 字段 | 值 |
|------|----|
| Route | `/record`（beforeLoad 登录守卫） |
| Screen type | operational（DESIGN.md 全局 UI 系 / Soft Structuralism 轨） |
| Primary Job | 30 秒内完成"拍照 → 识别 → 修正 → 保存"一餐 |
| Role | 记录者（登录用户） |
| Covered Units | Epic 1 U1–U5（Story 1.1–1.5） |
| Regions | ①拍摄/上传区（默认态主视觉）②识别状态区 ③明细确认区（紧凑列表 + 总热量锚 + 餐次 + 保存）④文本补录区（仅失败态） |
| Information Priority | 默认态：拍照入口 > 说明；结果态：总热量 > 明细 > 餐次 > 保存 |
| Key States | 默认 / 首次发送授权确认(仅首次，一等态，PRD §5.3) / 上传中 / 识别中 / 结果就绪 / 重算中(纯前端) / 无法识别 / 服务不可用 / 保存中 / 保存成功 / 保存失败 / 未登录(守卫跳转) |
| Richness Floor | 全状态可达且各有 颜色+图标+文案 三件套；失败态保留照片缩略 + 重试/补录双入口；不空屏（DESIGN.md §Richness Floor 暂无 operational 全局行，本行即本屏地板） |
| Forbidden Patterns | 裸居中表单；每道菜大卡堆；纯 toast 传达失败；默认态出现文本输入框 |
| API-for-UI | [api/meal-log.md](../api/meal-log.md) 三端点；`AI_UNAVAILABLE`→服务不可用态；`status=unrecognized`→补录态 |
| App shell | 套现有 `AppShell`（`frontend/src/components/layout/`）；本 Epic 不新增导航项 |
| Screen done | 浏览器完整走通 拍照(或选图)→识别→修正→保存，且 Key States 逐一可达 |
| Design source | `docs/project/DESIGN.md`（operational 轨）+ `docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html`（结构参考） |
