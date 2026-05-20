# Epic & Story 生成器 Skill

将需求文档（PRD + Architecture）转化为轻量 Epic 和 Story，聚焦验收标准。

## 何时使用

- 完成技术设计，准备拆分开发任务
- 已有 PRD + Architecture（必需），API Design + Data Model（推荐）
- 需要将功能需求转化为可执行的 Story

## 使用方式

```bash
/epic-story-generator
```

Skill 自动检测上游文档、提取约束、引导 Epic/Story 拆分。

## 前置条件

- **必需**: `docs/project/requirements.md`, `docs/project/architecture.md`
- **推荐**: `docs/project/api_spec.md`, `docs/project/database_schema.md`

## 工作流程

```
Phase 1: 初始化 → 检测文档 + 提取约束 + 选择模式
Phase 2: Epic 识别 → 从 PRD/Architecture 推导 + 用户确认
Phase 3: Story 拆分 → INVEST 原则 + 用户确认粒度
Phase 4: 验收标准 → checkbox 格式，覆盖正常/异常/边界
Phase 5: 生成验证 → 填充模板 + 完整性检查
```

## Story 格式（~15 行）

```markdown
### Story X.Y: [标题]

**用户故事**: 作为 [角色]，我可以 [功能]，以便 [价值]

#### 验收标准
- [ ] [正常流程条件]
- [ ] [异常场景条件]
- [ ] [边界条件]

**参考**: docs/project/api_spec.md §X, docs/project/database_schema.md §Y
**依赖**: Story X.Z / 无
```

## 输出结构

按每个 Epic 的 Story 数自动选择平铺或展开：

```
docs/tasks/
├── kanban_board.md                            # 全局索引：Next 编号 + Story 状态表
└── epics/
    ├── epic-1-search-system.md                # <3 Story → 平铺单文件
    ├── epic-2-content-management.md           # <3 Story → 平铺
    └── epic-3-user-auth/                      # ≥3 Story → 展开为目录
        ├── epic.md
        └── stories/
            ├── us001-phone-register.md
            ├── us002-phone-login.md
            └── us003-password-reset.md
```

- **kanban_board.md** 由 skill 在首次运行时从 `kanban_board.template.md` 复制生成，记录 `Next Epic Number` / `Next Story Number` 和全局 Story 状态。do-story 完成 Story 时回写 `Done`。
- **平铺 vs 展开**：阈值是该 Epic 的 Story 数 `<3` 还是 `≥3`，由 Phase 5 自动判定。

## 设计理念

- **Story 只写 What**（验收标准），不写 How（实施方案）
- **How 属于 Plan 阶段**：`"实现 Story X.Y"` → Plan mode → Triage → 方案设计
- **轻量优先**：~15 行/Story，避免文档膨胀

## 与其他 Skill 的协作

```
product-requirements → architecture → api-design → data-model
                                                      ↓
                                          epic-story-generator
                                                      ↓
                                    "实现 Story X.Y" → Plan → do-story
```

---

**Skill 版本**: v2.1
**最后更新**: 2026-05-20
