# Screen Inventory — 随手食记

- 来源 PRD: docs/project/requirements.md（版本 v1.0，2026-07-05）
- 生成日期: 2026-07-08
- 确认状态: 假设待审批（无人值守重跑；覆盖 2026-07-05 旧板——旧板走 Tailwind CDN + 自造暖色系，不符现行"单文件自包含 + DESIGN.md token 唯一来源"合同）

| 屏名 | 来源条目 | 屏型 | P0 | 状态集 | 设备框 | 锚点 |
|------|----------|------|----|--------|--------|------|
| 记录一餐 /record | E1 R1–R6, NFR 5.1/5.3 | operational ⚠️ 推断 (Confidence: H，移动拍照工作流，与 epic-1 plan 判定一致) | ✅ | 默认, 首次授权确认, 上传中, 上传失败, 识别中, 结果确认, 无法识别, 服务不可用, 保存成功 | phone | s-record, s-record--consent, s-record--uploading, s-record--upload-error, s-record--recognizing, s-record--result, s-record--unrecognized, s-record--unavailable, s-record--saved |
| 今日总览（首页） | E2 R1–R4, NFR 5.1 | operational | ✅ | 默认, 空, 超出目标, 加载 | phone | s-home, s-home--empty, s-home--over, s-home--loading |
| 目标设置（首次引导） | E3 R1 | operational ⚠️ 推断 (Confidence: M，也可视作 onboarding/front-of-house；按"高频设置表单"归 operational) | — | 默认 | phone | s-goal-setup |
| 目标编辑 | E3 R2 | operational | — | 默认 | phone | s-goal-edit |
| 历史列表 | E4 R1 | operational | — | 默认 | phone | s-history |
| 趋势 | E4 R2–R3 | operational | — | 默认 | phone | s-trends |

注：

- 登录屏（NFR 5.3）不入板：已实现（`frontend/src/routes/login/`，front-of-house 编辑艺术轨），
  板内在 Epic 1 注记框引用"未登录 → 跳既有登录守卫"，不重设计。
- 记录一餐的"重算中 / 保存中 / 保存失败"为瞬时微状态，不单独出帧；在"结果确认"帧注记框说明
  （与 epic-1 review pack 的 13 态 Screen Contract 相比，板只画讲得清产品长相的 9 帧）。⚠️ 推断 (Confidence: M)
- 分区归属：屏按来源 Epic 分区；E3 两帧同屏型同分区。
- 设备框全部 phone 390px：PRD §1.2 使用场景以手机浏览器为主。
